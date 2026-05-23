"""Runtime status queries for NAS mounts."""

import subprocess
from pathlib import Path

from app.models.schemas import NasConfig, NasMountStatus
from app.services.generators import nas as nas_gen


def _run(cmd: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as e:
        return 1, str(e)


def _is_mounted(mount_path: str) -> bool:
    rc, _ = _run(["findmnt", "-n", mount_path])
    return rc == 0


def _automount_active(unit: str) -> bool:
    rc, _ = _run(["systemctl", "is-active", unit])
    return rc == 0


def _last_error(unit: str) -> str:
    """Pull the most recent error line from the unit's journal."""
    rc, out = _run(
        ["journalctl", "-u", unit, "-n", "20", "--no-pager", "-o", "cat"],
        timeout=5,
    )
    if rc != 0 or not out:
        return ""
    error_lines = [
        line for line in out.splitlines()
        if any(kw in line.lower() for kw in ("error", "fail", "denied", "refused"))
    ]
    return error_lines[-1] if error_lines else ""


def get_statuses(config: NasConfig) -> list[NasMountStatus]:
    statuses: list[NasMountStatus] = []
    for mount in config.mounts:
        base = nas_gen.unit_basename(mount)
        mount_unit = f"{base}.mount"
        automount_unit = f"{base}.automount"
        mounted = _is_mounted(mount.mount_path)
        automount_active = _automount_active(automount_unit)
        last_error = ""
        if mount.enabled and not mounted:
            last_error = _last_error(mount_unit) or _last_error(automount_unit)
        statuses.append(NasMountStatus(
            id=mount.id,
            mount_path=mount.mount_path,
            enabled=mount.enabled,
            mounted=mounted,
            automount_active=automount_active,
            last_error=last_error,
        ))
    return statuses


def test_mount(mount, timeout: int = 15) -> tuple[bool, str]:
    """Try mounting `mount` to a temp location, then unmount.

    Returns (ok, message). Used by the UI's "Test" button so the operator
    sees credential/share failures before persisting the config.
    """
    import tempfile

    tmp_root = Path(tempfile.mkdtemp(prefix="nas-test-"))
    creds_path: Path | None = None
    creds_content = nas_gen.credentials_content(mount)
    if creds_content is not None:
        creds_path = tmp_root / "creds"
        creds_path.write_text(creds_content)
        creds_path.chmod(0o600)

    options = nas_gen.options_string(
        mount, str(creds_path) if creds_path else None
    )
    what = f"//{mount.server}/{mount.share}"
    target = tmp_root / "mnt"
    target.mkdir()

    try:
        rc, out = _run(
            ["mount", "-t", "cifs", what, str(target), "-o", options],
            timeout=timeout,
        )
        if rc != 0:
            return False, out or f"mount failed (rc={rc})"
        # Sanity: verify we can stat the mount point.
        rc2, out2 = _run(["ls", "-la", str(target)], timeout=5)
        return True, "mounted ok" + (f"; {out2.splitlines()[0]}" if out2 else "")
    finally:
        _run(["umount", str(target)], timeout=10)
        if creds_path and creds_path.exists():
            creds_path.unlink()
        try:
            target.rmdir()
            tmp_root.rmdir()
        except OSError:
            pass
