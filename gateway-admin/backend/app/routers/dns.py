from fastapi import APIRouter

from app.models.schemas import DnsConfig, HostEntry
from app.services import applier, config_store
from app.services.generators import dns as dns_gen

router = APIRouter(prefix="/api/dns", tags=["dns"])


def _apply_current() -> dict:
    return applier.apply_dns(
        config_store.get_dns_config(),
        config_store.get_host_entries(),
    )


@router.get("", response_model=DnsConfig)
def get_dns():
    return config_store.get_dns_config()


@router.put("")
def update_dns(config: DnsConfig):
    config_store.save_dns_config(config)
    return {"status": "ok", **_apply_current()}


@router.get("/hosts", response_model=list[HostEntry])
def get_hosts():
    return config_store.get_host_entries()


@router.put("/hosts")
def update_hosts(entries: list[HostEntry]):
    config_store.save_host_entries(entries)
    return {"status": "ok", **_apply_current()}


from pydantic import BaseModel


class DnsPreviewBody(BaseModel):
    config: DnsConfig
    hosts: list[HostEntry]


@router.post("/preview")
def preview_dns(body: DnsPreviewBody):
    return {
        "dns": dns_gen.generate_dns(body.config),
        "hosts": dns_gen.generate_hosts(body.hosts),
    }
