"""
App installer: validate, extract, materialize systemd/nginx, manage lifecycle.

Layout (everything under /data/apps/<id>/ so it survives a reflash):

    /data/apps/<id>/                extracted archive contents
    /data/apps/<id>/manifest.json   the manifest
    /data/apps/<id>/config.env      generated from manifest config[] + user values
    /data/apps/<id>/<data_dir>/     subdirs from manifest data_dirs[]

Systemd units: /etc/systemd/system/app-<id>-<svc>.service
Nginx drop-in: /etc/nginx/locations.d/apps/<id>.conf

Public API:
    preflight(archive_bytes)            -> AppManifest (validate without installing)
    install(archive_bytes, config)      -> InstalledApp
    uninstall(app_id)
    update_config(app_id, config)       -> InstalledApp
    control(app_id, action)             action ∈ {start,stop,restart}
    status(app_id)                      -> {service_name: "active" | ...}
    reconcile()                         -> [str]   (re-materialize from disk state)
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.app_install import InstalledApp
from app.models.app_manifest import AppManifest
from app.services import app_store
from app.services.generators import app_env, app_nginx, app_systemd

APPS_DIR = Path("/data/apps")
SYSTEMD_DIR = Path("/etc/systemd/system")
NGINX_LOCATIONS_DIR = Path("/etc/nginx/locations.d/apps")

# TODO: source from a single appliance-version constant when one exists.
APPLIANCE_VERSION = "1.0.0"


class InstallError(Exception):
    pass


# -- public API ---------------------------------------------------------


def preflight(archive_bytes: bytes) -> AppManifest:
    """Validate archive + manifest without modifying anything on disk."""
    manifest = _read_manifest(archive_bytes)
    _check_compatibility(manifest)
    return manifest


def install(archive_bytes: bytes, config_values: dict | None = None) -> InstalledApp:
    config_values = config_values or {}
    sha256 = hashlib.sha256(archive_bytes).hexdigest()

    manifest = _read_manifest(archive_bytes)
    _check_compatibility(manifest)

    if app_store.get(manifest.id) is not None:
        raise InstallError(f"app {manifest.id!r} already installed; uninstall first")

    merged_config = _validate_config(manifest, config_values)

    install_dir = APPS_DIR / manifest.id
    user = f"app-{manifest.id}"

    install_dir.mkdir(parents=True, exist_ok=False)
    _extract_archive(archive_bytes, install_dir)
    _ensure_user(user)

    for sub in manifest.data_dirs:
        (install_dir / sub).mkdir(parents=True, exist_ok=True)

    _run("chown", "-R", f"{user}:{user}", str(install_dir))

    record = InstalledApp(
        id=manifest.id,
        version=manifest.version,
        manifest=manifest,
        config_values=merged_config,
        installed_at=datetime.now(timezone.utc),
        enabled=True,
        archive_sha256=sha256,
    )

    _run_hook(manifest, install_dir, "pre_install", merged_config)
    _write_config_env(record)
    _write_systemd_units(record)
    _write_nginx_drop_in(record)

    _systemctl("daemon-reload")
    for svc in manifest.services:
        unit = app_systemd.unit_name(manifest.id, svc.name)
        _systemctl("enable", "--now", unit)
    if manifest.web_ui is not None:
        _run("nginx", "-s", "reload", check=False)

    _run_hook(manifest, install_dir, "post_install", merged_config)

    app_store.upsert(record)
    return record


def uninstall(app_id: str) -> None:
    record = app_store.get(app_id)
    if record is None:
        raise InstallError(f"app {app_id!r} not installed")

    install_dir = APPS_DIR / app_id

    if install_dir.exists():
        try:
            _run_hook(record.manifest, install_dir, "pre_uninstall", record.config_values)
        except InstallError:
            # Don't let a broken hook strand the install — keep tearing down.
            pass

    for svc in record.manifest.services:
        unit = app_systemd.unit_name(app_id, svc.name)
        _systemctl("disable", "--now", unit, check=False)

    for svc in record.manifest.services:
        path = SYSTEMD_DIR / app_systemd.unit_name(app_id, svc.name)
        path.unlink(missing_ok=True)
    _systemctl("daemon-reload", check=False)

    nginx_path = Path(app_nginx.conf_path(app_id))
    if nginx_path.exists():
        nginx_path.unlink()
        _run("nginx", "-s", "reload", check=False)

    if install_dir.exists():
        shutil.rmtree(install_dir)

    _run("userdel", f"app-{app_id}", check=False)

    app_store.delete(app_id)


def update_config(app_id: str, config_values: dict) -> InstalledApp:
    record = app_store.get(app_id)
    if record is None:
        raise InstallError(f"app {app_id!r} not installed")

    merged = _validate_config(record.manifest, config_values)
    record.config_values = merged
    _write_config_env(record)

    for svc in record.manifest.services:
        unit = app_systemd.unit_name(app_id, svc.name)
        _systemctl("restart", unit, check=False)

    app_store.upsert(record)
    return record


def control(app_id: str, action: str) -> None:
    if action not in ("start", "stop", "restart"):
        raise InstallError(f"invalid action {action!r}")
    record = app_store.get(app_id)
    if record is None:
        raise InstallError(f"app {app_id!r} not installed")
    for svc in record.manifest.services:
        unit = app_systemd.unit_name(app_id, svc.name)
        _systemctl(action, unit)


def status(app_id: str) -> dict[str, str]:
    record = app_store.get(app_id)
    if record is None:
        raise InstallError(f"app {app_id!r} not installed")
    out: dict[str, str] = {}
    for svc in record.manifest.services:
        unit = app_systemd.unit_name(app_id, svc.name)
        _, txt = _systemctl("is-active", unit, check=False)
        out[svc.name] = txt.strip() if txt else "unknown"
    return out


def reconcile() -> list[str]:
    """Re-materialize systemd units, nginx drop-ins, and config.env from
    the persisted record set. Called at startup; cheap if nothing's
    installed and idempotent if the world already matches state."""
    actions: list[str] = []
    for record in app_store.get_all():
        install_dir = APPS_DIR / record.id
        if not install_dir.exists():
            actions.append(f"warn: install dir missing for {record.id}")
            continue
        _write_config_env(record)
        _write_systemd_units(record)
        _write_nginx_drop_in(record)
        actions.append(f"reconciled {record.id}")
    if actions:
        _systemctl("daemon-reload", check=False)
        _run("nginx", "-s", "reload", check=False)
    return actions


# -- helpers ------------------------------------------------------------


def _run(*args: str, check: bool = True) -> tuple[int, str]:
    result = subprocess.run(list(args), capture_output=True, text=True)
    if check and result.returncode != 0:
        raise InstallError(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.returncode, (result.stdout + result.stderr).strip()


def _systemctl(*args: str, check: bool = True) -> tuple[int, str]:
    return _run("systemctl", *args, check=check)


def _read_manifest(archive_bytes: bytes) -> AppManifest:
    try:
        tf = tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz")
    except tarfile.ReadError as e:
        raise InstallError(f"archive is not a valid tar.gz: {e}") from e

    member = None
    for candidate in ("./manifest.json", "manifest.json"):
        try:
            member = tf.getmember(candidate)
            break
        except KeyError:
            continue
    if member is None:
        raise InstallError("manifest.json not found at archive root")

    fh = tf.extractfile(member)
    if fh is None:
        raise InstallError("manifest.json is not a regular file")

    try:
        data = json.loads(fh.read())
    except json.JSONDecodeError as e:
        raise InstallError(f"manifest.json is not valid JSON: {e}") from e

    try:
        return AppManifest.model_validate(data)
    except Exception as e:
        raise InstallError(f"manifest.json failed schema validation: {e}") from e


def _check_compatibility(manifest: AppManifest) -> None:
    if manifest.compatibility.target_arch != "aarch64":
        raise InstallError(
            f"app target_arch={manifest.compatibility.target_arch!r}, "
            f"appliance is aarch64"
        )
    if not _semver_ge(APPLIANCE_VERSION, manifest.compatibility.min_appliance_version):
        raise InstallError(
            f"appliance v{APPLIANCE_VERSION} < required "
            f"v{manifest.compatibility.min_appliance_version}"
        )


def _semver_ge(a: str, b: str) -> bool:
    """True if semver `a` >= semver `b`. Strips pre-release/build metadata."""
    def parts(v: str) -> tuple[int, int, int]:
        core = v.split("-", 1)[0].split("+", 1)[0]
        major, minor, patch = (core.split(".") + ["0", "0", "0"])[:3]
        return (int(major), int(minor), int(patch))

    return parts(a) >= parts(b)


def _validate_config(manifest: AppManifest, config_values: dict) -> dict:
    """Coerce + validate user-supplied config values against the manifest."""
    merged: dict = {}
    for field in manifest.config:
        if field.key in config_values:
            v = config_values[field.key]
        elif field.default is not None:
            v = field.default
        elif field.required:
            raise InstallError(f"config field {field.key!r} is required")
        else:
            continue

        if field.type == "int":
            try:
                v = int(v)
            except (ValueError, TypeError) as e:
                raise InstallError(f"{field.key!r} must be int: {e}") from e
            if field.min is not None and v < field.min:
                raise InstallError(f"{field.key!r}={v} below min {field.min}")
            if field.max is not None and v > field.max:
                raise InstallError(f"{field.key!r}={v} above max {field.max}")
        elif field.type == "bool":
            v = bool(v)
        elif field.type == "select":
            if str(v) not in (field.choices or []):
                raise InstallError(f"{field.key!r}={v!r} not in choices {field.choices}")
        else:  # string, password, path
            v = str(v)
        merged[field.key] = v
    return merged


def _extract_archive(archive_bytes: bytes, dest: Path) -> None:
    """Extract a tar.gz to dest with path-traversal + symlink guards."""
    dest_resolved = dest.resolve()
    try:
        tf = tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz")
    except tarfile.ReadError as e:
        raise InstallError(f"archive read failed: {e}") from e

    for member in tf.getmembers():
        if member.name.startswith("/") or ".." in Path(member.name).parts:
            raise InstallError(f"archive contains unsafe path: {member.name!r}")
        target = (dest / member.name).resolve()
        try:
            target.relative_to(dest_resolved)
        except ValueError as e:
            raise InstallError(f"archive escapes install dir: {member.name!r}") from e
        if member.issym() or member.islnk():
            raise InstallError(f"archive contains symlinks: {member.name!r}")

    tf.extractall(dest, filter="data")


def _ensure_user(name: str) -> None:
    rc, _ = _run("id", "-u", name, check=False)
    if rc == 0:
        return
    _run("useradd", "-r", "-M", "-s", "/usr/sbin/nologin", name)


def _write_config_env(record: InstalledApp) -> None:
    text = app_env.generate(record)
    target = APPS_DIR / record.id / "config.env"
    target.write_text(text)
    target.chmod(0o600)


def _write_systemd_units(record: InstalledApp) -> None:
    for svc in record.manifest.services:
        text = app_systemd.generate_unit(record, svc)
        path = SYSTEMD_DIR / app_systemd.unit_name(record.id, svc.name)
        path.write_text(text)
        path.chmod(0o644)


def _write_nginx_drop_in(record: InstalledApp) -> None:
    text = app_nginx.generate(record)
    if text is None:
        return
    NGINX_LOCATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(app_nginx.conf_path(record.id))
    path.write_text(text)
    path.chmod(0o644)


def _run_hook(
    manifest: AppManifest,
    install_dir: Path,
    hook_name: str,
    config_values: dict,
) -> None:
    rel = getattr(manifest.hooks, hook_name)
    if not rel:
        return

    hook_path = install_dir / rel
    if not hook_path.exists():
        raise InstallError(f"hook {hook_name} script not found: {hook_path}")
    hook_path.chmod(0o755)

    env = os.environ.copy()
    env.update({
        "APP_ID": manifest.id,
        "APP_VERSION": manifest.version,
        "INSTALL_DIR": str(install_dir),
        "DATA_DIR": str(install_dir),
    })
    for k, v in config_values.items():
        env[k] = str(v)

    result = subprocess.run(
        [str(hook_path)],
        cwd=install_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InstallError(
            f"hook {hook_name} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
