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
