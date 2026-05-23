from fastapi import APIRouter

from app.models.schemas import NasConfig, NasMount, NasMountStatus, NasTestResult
from app.services import applier, config_store, nas_status
from app.services.generators import nas as nas_gen

router = APIRouter(prefix="/api/nas", tags=["nas"])


@router.get("", response_model=NasConfig)
def get_nas():
    return config_store.get_nas_config()


@router.put("")
def update_nas(config: NasConfig):
    config_store.save_nas_config(config)
    result = applier.apply_nas(config)
    return {"status": "ok", **result}


@router.get("/status", response_model=list[NasMountStatus])
def get_status():
    return nas_status.get_statuses(config_store.get_nas_config())


@router.post("/preview")
def preview_nas(config: NasConfig):
    units = {}
    for mount in config.mounts:
        base = nas_gen.unit_basename(mount)
        creds = nas_gen.credentials_content(mount)
        creds_path = f"/data/nas/credentials/{mount.id}" if creds else None
        units[f"{base}.mount"] = nas_gen.generate_mount_unit(mount, creds_path)
        units[f"{base}.automount"] = nas_gen.generate_automount_unit(mount)
    return units


@router.post("/test", response_model=NasTestResult)
def test_nas(mount: NasMount):
    ok, message = nas_status.test_mount(mount)
    return NasTestResult(ok=ok, message=message)
