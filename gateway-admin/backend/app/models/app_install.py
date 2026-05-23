"""
InstalledApp record — what gateway-admin tracks for each installed app.

The full AppManifest from the archive is snapshotted into this record so
uninstall/reconcile can run without the original archive on disk
(e.g. after a reflash that preserves /data but loses any upload tmpdir).
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.app_manifest import AppManifest

ConfigValue = str | int | bool


class InstalledApp(BaseModel):
    id: str
    version: str
    manifest: AppManifest
    config_values: dict[str, ConfigValue] = {}
    installed_at: datetime
    enabled: bool = True
    archive_sha256: str
    # POSIX uid/gid the install_dir is chown'd to. Persisted so a
    # post-reflash reconcile can re-create the app's system user with
    # the *same* numeric IDs (the rootfs got wiped, /data didn't), keeping
    # existing file ownership intact. Optional for records written before
    # this field was added; reconcile re-captures the live ids in that
    # case and writes them back.
    uid: int | None = None
    gid: int | None = None
