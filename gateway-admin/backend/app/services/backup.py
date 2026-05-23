"""
Backup / restore the gateway's persistent configuration.

The "source of truth" lives in /data:
    *.json              user-editable configs (network, dhcp, dns, hosts, ...)
    auth.json           bcrypt admin password (excluded if include_secrets=False)
    ssl/                self-signed cert + key (excluded if include_secrets=False)
    network/            generated systemd-networkd unit (regenerated on reconcile)
    dnsmasq.d/          generated dnsmasq drop-ins (regenerated on reconcile)
    hostname            persisted hostname

A backup is a gzip-compressed tarball of those files. If a passphrase is
given, the tarball is encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
using PBKDF2-derived key.
"""

import base64
import io
import json
import logging
import os
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.models.app_install import InstalledApp
from app.services import app_store
from app.services.hooks import HookError, run_hook

log = logging.getLogger("gateway-admin")

# Marker bytes prefix on encrypted backups so we can tell them apart
ENCRYPTED_HEADER = b"GWADMIN-ENC-V1\n"

# Files to exclude when include_secrets is False
SECRET_PATHS = {"auth.json", "ssl"}


class BackupError(Exception):
    """Raised when a backup cannot proceed (e.g. an app's pre_backup hook
    failed to quiesce it). Distinct from the existing `ValueError` paths
    (missing /data, decryption failure) so the route handler can map
    quiesce failures to a clearly-worded HTTP error."""


def _data_dir() -> Path:
    return Path(os.environ.get("GATEWAY_DATA_DIR", "/data"))


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _encrypt(blob: bytes, passphrase: str) -> bytes:
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(blob)
    return ENCRYPTED_HEADER + salt + token


def _decrypt(blob: bytes, passphrase: str) -> bytes:
    if not blob.startswith(ENCRYPTED_HEADER):
        raise ValueError("file is not an encrypted gateway backup")
    body = blob[len(ENCRYPTED_HEADER):]
    salt, token = body[:16], body[16:]
    key = _derive_key(passphrase, salt)
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken:
        raise ValueError("incorrect passphrase or corrupted backup")


def _should_skip(arcname: str, include_secrets: bool) -> bool:
    if include_secrets:
        return False
    head = arcname.split("/", 1)[0]
    return head in SECRET_PATHS


def _app_path_filter():
    """Return a predicate `keep(arcname)`. Skips per-app paths (under
    `apps/<id>/`) that are reproducible from the archive — bin, lib,
    plugins, web .venv, etc. — and keeps only `manifest.json`,
    `config.env`, and the subtrees the manifest declares as
    `backup_paths` (falling back to `data_dirs`). Everything outside
    `apps/<id>/` (gateway config JSON, ssl, etc.) is left to the
    existing `_should_skip` to decide.
    """
    installed_json = _data_dir() / "apps" / "installed.json"
    try:
        records = json.loads(installed_json.read_text())
    except FileNotFoundError:
        return lambda _: True
    except (OSError, json.JSONDecodeError):
        # Best-effort: if the registry is unreadable, fall back to the
        # old behavior (everything included) rather than blocking a
        # backup.
        return lambda _: True

    # Per-app keep-prefixes derived from manifest.backup_paths (None →
    # fall back to data_dirs).
    keep_under: dict[str, list[str]] = {}
    for rec in records:
        app_id = rec.get("id")
        if not app_id:
            continue
        manifest = rec.get("manifest", {})
        bp = manifest.get("backup_paths")
        if bp is None:
            bp = manifest.get("data_dirs", [])
        keep_under[app_id] = [p.strip("/") for p in (bp or []) if p.strip("/")]

    def keep(arcname: str) -> bool:
        parts = arcname.split("/", 2)
        if parts[0] != "apps" or len(parts) < 2:
            return True  # Non-app path; let _should_skip have the call.
        if parts[1] not in keep_under:
            # apps/installed.json or unknown subdir — keep.
            return True
        if len(parts) < 3:
            # An apps/<id> entry that is itself a file (no `rest`).
            # Shouldn't happen in practice; default to keeping.
            return True
        rest = parts[2]
        if rest in ("manifest.json", "config.env"):
            return True
        for kp in keep_under[parts[1]]:
            if rest == kp or rest.startswith(kp + "/"):
                return True
        return False

    return keep


def _app_install_dir(app_id: str) -> Path:
    """Match app_installer.APPS_DIR (`/data/apps/<id>`), but respect
    GATEWAY_DATA_DIR so tests pointing at a tmpdir resolve correctly."""
    return _data_dir() / "apps" / app_id


def _run_pre_backup_hooks() -> list[InstalledApp]:
    """Quiesce every installed app that declares `pre_backup`. On any
    failure, restart already-quiesced apps (best-effort rollback) and raise
    `BackupError` so the caller aborts the backup before opening the tar.

    Returns the list of apps whose pre_backup actually ran — caller passes
    the same list to `_run_post_backup_hooks` so only quiesced apps get
    restarted.
    """
    try:
        apps = app_store.get_all()
    except Exception as e:
        # Strict mode: if we can't read the installed-app registry, we
        # can't know which apps need quiescing, so we can't safely back up
        # whatever's on disk. Fail loud instead of silently producing
        # another torn-page SQLite (the hazard this whole pipeline exists
        # to prevent — see project_gateway_wal_backup_hazard.md).
        raise BackupError(f"unable to read installed-app registry: {e}") from e
    fired: list[InstalledApp] = []
    for record in apps:
        if not record.manifest.hooks.pre_backup:
            continue
        try:
            run_hook(record.manifest, _app_install_dir(record.id),
                     "pre_backup", record.config_values)
            fired.append(record)
        except HookError as e:
            # Strict rollback: restart everything we already quiesced so a
            # failed quiesce doesn't leave the appliance half-down.
            for r in fired:
                if not r.manifest.hooks.post_backup:
                    continue
                try:
                    run_hook(r.manifest, _app_install_dir(r.id),
                             "post_backup", r.config_values)
                except HookError:
                    log.exception(
                        "rollback: post_backup failed for %s after %s pre_backup failure",
                        r.id, record.id,
                    )
            raise BackupError(
                f"pre_backup failed for {record.id}: {e}"
            ) from e
    return fired


def _run_post_backup_hooks(records: list[InstalledApp]) -> None:
    """Run `post_backup` on every record returned by `_run_pre_backup_hooks`.
    Best-effort: data is already captured at this point, so a failure logs
    but does NOT raise — surfacing it would mask the successful backup."""
    for r in records:
        if not r.manifest.hooks.post_backup:
            continue
        try:
            run_hook(r.manifest, _app_install_dir(r.id),
                     "post_backup", r.config_values)
        except HookError:
            log.exception("post_backup failed for %s", r.id)


def create_backup(include_secrets: bool = True, passphrase: str | None = None) -> bytes:
    """Return a gzipped tarball (optionally encrypted) of /data.

    Buffered variant — used for encrypted backups (Fernet needs the whole
    plaintext input) and as a synchronous helper for tests. For unencrypted
    downloads prefer `stream_backup` which yields chunks as gzip produces
    them, so the HTTP response can begin in milliseconds rather than after
    the full tarball has been built.

    Quiesces every app declaring `pre_backup` before the tar walk and
    restarts them via `post_backup` in a `finally` so a mid-build exception
    doesn't leave services down. `pre_backup` failure raises `BackupError`
    before any file is touched.
    """
    data = _data_dir()
    if not data.exists():
        raise ValueError(f"data dir {data} does not exist")

    fired = _run_pre_backup_hooks()
    try:
        keep = _app_path_filter()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for path in sorted(data.rglob("*")):
                if path.is_dir():
                    continue
                arcname = str(path.relative_to(data))
                if _should_skip(arcname, include_secrets):
                    continue
                if not keep(arcname):
                    continue
                tar.add(str(path), arcname=arcname)

        blob = buf.getvalue()
        if passphrase:
            blob = _encrypt(blob, passphrase)
        return blob
    finally:
        _run_post_backup_hooks(fired)


class _ChunkBuffer:
    """Writable buffer used as `tarfile.open(fileobj=...)` target. Each
    `tar.add()` causes gzip to write some bytes; the generator drains and
    yields them after every file."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, b: bytes) -> int:
        if b:
            self._chunks.append(bytes(b))
        return len(b)

    def drain(self) -> bytes:
        if not self._chunks:
            return b""
        out = b"".join(self._chunks)
        self._chunks.clear()
        return out


# Module-global progress for the in-flight streaming backup, polled by
# `GET /api/backup/progress`. Single-user gateway so a single slot is fine;
# concurrent backups would conflate progress, but we never expect two.
_progress: dict[str, object] = {
    "phase": "idle",     # idle | streaming | done
    "files_done": 0,
    "files_total": 0,
}


def get_progress() -> dict:
    """Snapshot of the streaming backup's progress for the polling endpoint."""
    return dict(_progress)


def stream_backup(include_secrets: bool = True):
    """Set up `_progress` synchronously, then return a generator yielding
    gzipped tarball chunks as files are added.

    No passphrase variant — Fernet can't encrypt incrementally, so
    encrypted backups go through `create_backup` instead. Used by the
    `/api/backup` route to flip first-byte time from ~75s (full
    in-memory build) to ~0s, which sidesteps nginx's `proxy_read_timeout`
    on slow appliances.

    Pre-walks `/data` to count files so a poll arriving immediately after
    the route handler returns sees the correct `files_total`.

    Quiesce ordering: `_run_pre_backup_hooks` fires BEFORE the pre-walk so
    the file list reflects post-quiesce on-disk state (otherwise the
    walker can observe paths whose content is still being written). The
    matching `_run_post_backup_hooks` lives in `_stream_files_gen`'s
    `finally`, so a client that drops the stream mid-flight still gets
    services restarted when the generator is garbage-collected.
    """
    data = _data_dir()
    if not data.exists():
        raise ValueError(f"data dir {data} does not exist")

    fired = _run_pre_backup_hooks()
    try:
        keep = _app_path_filter()
        files: list[tuple[Path, str]] = []
        for path in sorted(data.rglob("*")):
            if path.is_dir():
                continue
            arcname = str(path.relative_to(data))
            if _should_skip(arcname, include_secrets):
                continue
            if not keep(arcname):
                continue
            files.append((path, arcname))

        _progress.update(phase="streaming", files_done=0, files_total=len(files))
    except BaseException:
        # If anything between pre_backup and the generator construction
        # fails, we own the responsibility to bring services back up.
        _run_post_backup_hooks(fired)
        raise

    return _stream_files_gen(files, fired)


def _stream_files_gen(files: list[tuple[Path, str]], fired: list[InstalledApp]):
    buf = _ChunkBuffer()
    # `mode='w|gz'` opens the tarfile in streaming mode (no seeks), which
    # works against a non-seekable writable like our chunk buffer.
    try:
        with tarfile.open(fileobj=buf, mode="w|gz") as tar:
            for path, arcname in files:
                tar.add(str(path), arcname=arcname)
                _progress["files_done"] = int(_progress["files_done"]) + 1  # type: ignore[arg-type]
                chunk = buf.drain()
                if chunk:
                    yield chunk
        final = buf.drain()
        if final:
            yield final
    finally:
        # Last poll after the response ends should see "done" so the UI
        # can switch out of the progress display cleanly.
        _progress["phase"] = "done"
        # Restart any apps we quiesced. Fires even when the client drops
        # the response and Python GCs the generator (via close()'s
        # injected GeneratorExit, which propagates through this finally).
        _run_post_backup_hooks(fired)


def restore_backup(blob: bytes, passphrase: str | None = None) -> dict:
    """Replace /data contents with the backup tarball.

    Returns a summary of restored files.
    """
    if blob.startswith(ENCRYPTED_HEADER):
        if not passphrase:
            raise ValueError("backup is encrypted — passphrase required")
        blob = _decrypt(blob, passphrase)
    elif passphrase:
        raise ValueError("backup is not encrypted; remove the passphrase")

    data = _data_dir()
    data.mkdir(parents=True, exist_ok=True)

    files_restored: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        members = tar.getmembers()
        # Defence: refuse path traversal
        for m in members:
            if m.name.startswith("/") or ".." in m.name.split("/"):
                raise ValueError(f"unsafe path in backup: {m.name}")
        for m in members:
            if m.isfile():
                tar.extract(m, path=str(data), filter="data")
                files_restored.append(m.name)

    return {"restored": len(files_restored), "files": files_restored}
