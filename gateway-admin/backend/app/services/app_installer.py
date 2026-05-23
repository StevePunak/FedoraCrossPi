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
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.app_install import InstalledApp
from app.models.app_manifest import AppManifest
from app.services import app_store
from app.services.generators import app_env, app_nginx, app_systemd
from app.services.hooks import HookError, run_hook

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

    merged_config = _validate_config(manifest, config_values)

    install_dir = APPS_DIR / manifest.id
    user = f"app-{manifest.id}"

    # Install-over-existing-record is the supported "update" path. If we
    # have a prior record AND an install_dir on disk (the normal case for
    # an upgrade; also the post-restore case where the backup contained
    # only `backup_paths` subtrees), snapshot those subtrees aside so we
    # can move them back over the freshly-extracted archive. Restore is
    # how downloads/state/db survive a binary swap.
    prior_record = app_store.get(manifest.id)
    snapshot_dir: Path | None = None
    if prior_record is not None and install_dir.exists():
        keep = _effective_backup_paths(prior_record.manifest)
        if keep:
            snapshot_dir = Path(tempfile.mkdtemp(prefix=f"app-{manifest.id}-snap-"))
            for kp in keep:
                src = install_dir / kp
                if src.exists():
                    shutil.copytree(src, snapshot_dir / kp, symlinks=True)

    try:
        # Sweep any orphan state from a previous install / failed install
        # of this id so extraction isn't blocked by stale dirs/units.
        _rollback(manifest, install_dir)
        install_dir.mkdir(parents=True, exist_ok=False)

        _extract_archive(archive_bytes, install_dir)
        _ensure_user(user)
        uid, gid = _lookup_user_ids(user)

        for sub in manifest.data_dirs:
            (install_dir / sub).mkdir(parents=True, exist_ok=True)

        # Move the snapshot back over the freshly-extracted tree. The
        # archive's data_dirs are empty templates; the snapshot is the
        # real persisted state.
        if snapshot_dir is not None:
            for entry in snapshot_dir.iterdir():
                target = install_dir / entry.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.move(str(entry), str(target))

        _run("chown", "-R", f"{user}:{user}", str(install_dir))

        record = InstalledApp(
            id=manifest.id,
            version=manifest.version,
            manifest=manifest,
            config_values=merged_config,
            installed_at=datetime.now(timezone.utc),
            enabled=True,
            archive_sha256=sha256,
            uid=uid,
            gid=gid,
        )

        _run_hook(manifest, install_dir, "pre_install", merged_config)
        _write_config_env(record)
        _write_systemd_units(record)
        _write_nginx_drop_in(record)

        _systemctl("daemon-reload")

        # post_install runs before services start so hooks can prep runtime
        # artifacts the units depend on (e.g. building a Python venv from
        # bundled wheels). Otherwise systemd races the hook and ExecStart
        # hits ENOENT until restart-on-failure recovers.
        _run_hook(manifest, install_dir, "post_install", merged_config)

        for svc in manifest.services:
            unit = app_systemd.unit_name(manifest.id, svc.name)
            _systemctl("enable", "--now", unit)
        if manifest.web_ui is not None:
            _run("nginx", "-s", "reload", check=False)

        app_store.upsert(record)
        return record
    except Exception:
        _rollback(manifest, install_dir)
        raise
    finally:
        if snapshot_dir is not None:
            shutil.rmtree(snapshot_dir, ignore_errors=True)


def _effective_backup_paths(manifest: AppManifest) -> list[str]:
    """Subpaths inside install_dir that should survive an install-over
    (and that the gateway backup should include). `backup_paths is None`
    means fall back to `data_dirs`; an empty list is explicit opt-out;
    a list is the override."""
    paths = manifest.backup_paths if manifest.backup_paths is not None else manifest.data_dirs
    return [p.strip("/") for p in paths if p.strip("/")]


def _rollback(manifest: AppManifest, install_dir: Path) -> None:
    """Remove anything install() may have created for this app id. Safe to
    run even if nothing exists yet — every step is missing_ok / check=False."""
    for svc in manifest.services:
        unit = app_systemd.unit_name(manifest.id, svc.name)
        _systemctl("disable", "--now", unit, check=False)
        (SYSTEMD_DIR / unit).unlink(missing_ok=True)
    _systemctl("daemon-reload", check=False)

    nginx_path = Path(app_nginx.conf_path(manifest.id))
    if nginx_path.exists():
        nginx_path.unlink()
        _run("nginx", "-s", "reload", check=False)

    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)


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
    """Re-materialize the runtime side of every installed app from the
    persisted records. Called at startup; idempotent. After a reflash
    /data survives but the rootfs is fresh — no app users, no unit files
    in /etc/systemd/system, no enable symlinks. This brings them all back.

    Steps per record:
      1. Ensure the app's system user exists with the *same* uid/gid the
         install_dir is chown'd to (record-pinned if present, otherwise
         captured now and written back).
      2. Re-chown install_dir defensively in case the user pre-existed
         with a different uid.
      3. Rewrite config.env / units / nginx drop-in from the record.
      4. Enable + start each service for apps marked enabled. (Install
         did `enable --now`; the wants/ symlink lives on rootfs, so a
         reflash wipes it and we have to redo this every boot.)
    """
    any_web_ui = False
    needs_daemon_reload = False
    actions: list[str] = []
    for record in app_store.get_all():
        install_dir = APPS_DIR / record.id
        if not install_dir.exists():
            actions.append(f"warn: install dir missing for {record.id}")
            continue

        user = f"app-{record.id}"
        _ensure_user(user, uid=record.uid, gid=record.gid)
        # If the record predates uid/gid persistence (or the user was
        # somehow re-created with different ids), capture the current
        # ids and write them back so the next reflash has them pinned.
        live_uid, live_gid = _lookup_user_ids(user)
        if record.uid != live_uid or record.gid != live_gid:
            record = record.model_copy(update={"uid": live_uid, "gid": live_gid})
            app_store.upsert(record)

        _run("chown", "-R", f"{user}:{user}", str(install_dir), check=False)

        _write_config_env(record)
        _write_systemd_units(record)
        _write_nginx_drop_in(record)
        needs_daemon_reload = True
        if record.manifest.web_ui is not None:
            any_web_ui = True
        actions.append(f"reconciled {record.id}")

    if needs_daemon_reload:
        _systemctl("daemon-reload", check=False)
    if any_web_ui:
        _run("nginx", "-s", "reload", check=False)

    # Now that units are loaded, enable+start each service for enabled
    # apps. Done in a second pass after daemon-reload so systemd sees
    # the freshly-written unit files.
    for record in app_store.get_all():
        if not record.enabled:
            continue
        install_dir = APPS_DIR / record.id
        if not install_dir.exists():
            continue
        for svc in record.manifest.services:
            unit = app_systemd.unit_name(record.id, svc.name)
            _systemctl("enable", "--now", unit, check=False)

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
    """Extract a tar.gz to dest. Path-traversal is enforced explicitly here
    plus belt-and-suspenders by tarfile's `data` extraction filter, which
    also rejects symlinks pointing outside the destination, special device
    files, and absolute paths. Real-world apps need internal symlinks
    (libfoo.so -> libfoo.so.1.2.3, etc.), so we don't reject them outright."""
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

    tf.extractall(dest, filter="data")


def _ensure_user(name: str, uid: int | None = None, gid: int | None = None) -> None:
    """Create the per-app system user+group if missing. When uid/gid are
    supplied (after a reflash, recovered from the InstalledApp record),
    re-create with those exact numeric ids so file ownership in /data
    still matches. Without them, useradd picks the next free system id
    and the install_dir would need a chown.
    """
    rc, _ = _run("id", "-u", name, check=False)
    if rc == 0:
        return
    if gid is not None:
        # Create the group first so we can pin -g; useradd -U would
        # otherwise create one with whatever gid happens to be free.
        _run("groupadd", "-r", "-g", str(gid), name, check=False)
        args = ["useradd", "-r", "-M", "-s", "/usr/sbin/nologin", "-g", str(gid)]
        if uid is not None:
            args += ["-u", str(uid)]
        _run(*args, name)
    else:
        # No pinning requested. -U makes useradd create a same-name group
        # with the same id as the user (the original behavior).
        _run("useradd", "-r", "-M", "-U", "-s", "/usr/sbin/nologin", name)


def _lookup_user_ids(name: str) -> tuple[int, int]:
    """Resolve a user name to (uid, gid). Caller must ensure the user
    already exists; raises InstallError on lookup failure so the install
    path can roll back."""
    rc, uid_txt = _run("id", "-u", name, check=False)
    if rc != 0:
        raise InstallError(f"user {name!r} not found after _ensure_user")
    rc, gid_txt = _run("id", "-g", name, check=False)
    if rc != 0:
        raise InstallError(f"group lookup failed for {name!r}")
    return int(uid_txt), int(gid_txt)


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
    # Thin shim over services.hooks.run_hook: callers in this module raise
    # InstallError on lifecycle failures, so translate the generic HookError.
    try:
        run_hook(manifest, install_dir, hook_name, config_values)
    except HookError as e:
        raise InstallError(str(e)) from e
