import logging

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.services import applier, backup, config_store

log = logging.getLogger("gateway-admin")
router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post("")
def download_backup(
    include_secrets: bool = Form(True),
    passphrase: str | None = Form(None),
):
    try:
        blob = backup.create_backup(include_secrets=include_secrets, passphrase=passphrase or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    suffix = ".tar.gz.enc" if passphrase else ".tar.gz"
    filename = f"gateway-backup{suffix}"
    media_type = "application/octet-stream" if passphrase else "application/gzip"
    return Response(
        content=blob,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    passphrase: str | None = Form(None),
):
    blob = await file.read()
    try:
        result = backup.restore_backup(blob, passphrase=passphrase or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Re-apply restored config so services pick up the new state
    try:
        applier.apply_dhcp(
            config_store.get_dhcp_config(),
            config_store.get_static_leases(),
        )
    except Exception:
        log.exception("post-restore DHCP reconciliation failed")
    try:
        applier.apply_dns(
            config_store.get_dns_config(),
            config_store.get_host_entries(),
        )
    except Exception:
        log.exception("post-restore DNS reconciliation failed")
    try:
        applier.apply_network(config_store.get_network_config())
    except Exception:
        log.exception("post-restore network reconciliation failed")

    return {"status": "ok", **result}
