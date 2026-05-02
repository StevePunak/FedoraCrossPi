"""
JSON-backed store for installed app records.

Persists at $GATEWAY_DATA_DIR/apps/installed.json (production:
/data/apps/installed.json). The directory layout mirrors what
app_installer expects on the appliance: each installed app's tree
lives at /data/apps/<id>/.
"""

import json
import os
import tempfile
from pathlib import Path

from app.models.app_install import InstalledApp

_apps_dir: Path | None = None


def _get_apps_dir() -> Path:
    global _apps_dir
    if _apps_dir is not None:
        return _apps_dir

    env_dir = os.environ.get("GATEWAY_DATA_DIR")
    if env_dir:
        _apps_dir = Path(env_dir) / "apps"
    else:
        _apps_dir = Path(tempfile.mkdtemp(prefix="gateway-apps-"))
        print(f"Dev mode: app records stored in {_apps_dir}")

    _apps_dir.mkdir(parents=True, exist_ok=True)
    return _apps_dir


def _installed_path() -> Path:
    return _get_apps_dir() / "installed.json"


def _read_all() -> list[InstalledApp]:
    path = _installed_path()
    if not path.exists():
        return []
    with path.open() as f:
        data = json.load(f)
    return [InstalledApp.model_validate(item) for item in data]


def _write_all(apps: list[InstalledApp]) -> None:
    path = _installed_path()
    payload = [app.model_dump(mode="json") for app in apps]
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(path)


def get_all() -> list[InstalledApp]:
    return _read_all()


def get(app_id: str) -> InstalledApp | None:
    for app in _read_all():
        if app.id == app_id:
            return app
    return None


def upsert(app: InstalledApp) -> None:
    apps = [a for a in _read_all() if a.id != app.id]
    apps.append(app)
    _write_all(apps)


def delete(app_id: str) -> None:
    apps = [a for a in _read_all() if a.id != app_id]
    _write_all(apps)
