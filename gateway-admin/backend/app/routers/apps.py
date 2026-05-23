"""
HTTP API for installable apps.

Endpoints (all require admin auth via the protected dependency in main.py):

    GET    /api/apps                  list installed apps
    GET    /api/apps/{id}             detail (record + per-service status)
    POST   /api/apps/preflight        validate archive, return its manifest
    POST   /api/apps                  install (multipart: file=archive, config=JSON)
    DELETE /api/apps/{id}             uninstall (purges /data/apps/<id>/)
    PUT    /api/apps/{id}/config      update config values + restart services
    POST   /api/apps/{id}/{action}    start | stop | restart all services
    GET    /api/apps/{id}/status      per-service is-active state

The unauthenticated manifest JSON Schema lives in `routers/docs.py` so
build pipelines can fetch it without a session cookie.
"""

import json

from fastapi import APIRouter, File, Form, HTTPException, Path, UploadFile

from app.models.app_install import InstalledApp
from app.models.app_manifest import AppManifest
from app.services import app_installer, app_store

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("", response_model=list[InstalledApp])
def list_apps():
    return app_store.get_all()


@router.get("/{app_id}")
def get_app(app_id: str = Path(pattern=r"^[a-z][a-z0-9-]{1,30}$")):
    record = app_store.get(app_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"app {app_id!r} not installed")
    try:
        svc_status = app_installer.status(app_id)
    except app_installer.InstallError:
        svc_status = {}
    return {
        "app": record.model_dump(mode="json"),
        "status": svc_status,
    }


@router.post("/preflight", response_model=AppManifest)
async def preflight(file: UploadFile = File(...)):
    archive_bytes = await file.read()
    try:
        return app_installer.preflight(archive_bytes)
    except app_installer.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=InstalledApp)
async def install(
    file: UploadFile = File(...),
    config: str = Form(default="{}"),
):
    try:
        config_values = json.loads(config) if config else {}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"config is not valid JSON: {e}")
    if not isinstance(config_values, dict):
        raise HTTPException(status_code=400, detail="config must be a JSON object")

    archive_bytes = await file.read()
    try:
        return app_installer.install(archive_bytes, config_values)
    except app_installer.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{app_id}")
def uninstall(app_id: str = Path(pattern=r"^[a-z][a-z0-9-]{1,30}$")):
    try:
        app_installer.uninstall(app_id)
    except app_installer.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@router.put("/{app_id}/config", response_model=InstalledApp)
def update_config(
    config_values: dict,
    app_id: str = Path(pattern=r"^[a-z][a-z0-9-]{1,30}$"),
):
    try:
        return app_installer.update_config(app_id, config_values)
    except app_installer.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{app_id}/{action}")
def control(
    app_id: str = Path(pattern=r"^[a-z][a-z0-9-]{1,30}$"),
    action: str = Path(pattern=r"^(start|stop|restart)$"),
):
    try:
        app_installer.control(app_id, action)
    except app_installer.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@router.get("/{app_id}/status")
def get_status(app_id: str = Path(pattern=r"^[a-z][a-z0-9-]{1,30}$")):
    try:
        return app_installer.status(app_id)
    except app_installer.InstallError as e:
        raise HTTPException(status_code=404, detail=str(e))
