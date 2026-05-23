import logging

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.services import app_installer, applier, backup, config_store

log = logging.getLogger("gateway-admin")
router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/progress")
def get_backup_progress():
    """Polled by the UI while a streaming backup is in flight; reports
    `{phase, files_done, files_total}`. Module-global on the backend so
    concurrent backups would mix — single-user gateway so we accept that."""
    return backup.get_progress()


@router.post("")
def download_backup(
    include_secrets: bool = Form(True),
    passphrase: str | None = Form(None),
):
    suffix = ".tar.gz.enc" if passphrase else ".tar.gz"
    filename = f"gateway-backup{suffix}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    if passphrase:
        # Fernet has no incremental API, so encrypted backups still buffer
        # the full plaintext before encryption. The build is short enough
        # at /data sizes the gateway can hold that this stays under
        # nginx's bumped `proxy_read_timeout` of 600s.
        try:
            blob = backup.create_backup(include_secrets=include_secrets, passphrase=passphrase)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except backup.BackupError as e:
            # Quiesce failed — backup didn't run, no tarball produced. 500
            # reflects "gateway couldn't fulfil the request" rather than
            # "bad input"; the message names the offending app.
            raise HTTPException(status_code=500, detail=f"backup aborted: {e}")
        return Response(content=blob, media_type="application/octet-stream", headers=headers)

    try:
        return StreamingResponse(
            backup.stream_backup(include_secrets=include_secrets),
            media_type="application/gzip",
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except backup.BackupError as e:
        raise HTTPException(status_code=500, detail=f"backup aborted: {e}")


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

    # Re-apply restored config so services pick up the new state. Mirrors
    # main._reconcile_on_startup so a restore lands the appliance in the
    # same state a fresh boot would, without waiting for a reboot.
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
    try:
        applier.apply_nas(config_store.get_nas_config())
    except Exception:
        log.exception("post-restore NAS reconciliation failed")
    try:
        app_installer.reconcile()
    except Exception:
        log.exception("post-restore app reconciliation failed")

    return {"status": "ok", **result}
