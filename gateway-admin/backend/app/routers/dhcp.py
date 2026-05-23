from fastapi import APIRouter
from pydantic import BaseModel

from app.models.schemas import ActiveLease, DhcpConfig, StaticLease
from app.services import applier, config_store, dhcp_leases
from app.services.generators import dhcp as dhcp_gen

router = APIRouter(prefix="/api/dhcp", tags=["dhcp"])


def _apply_current() -> dict:
    return applier.apply_dhcp(
        config_store.get_dhcp_config(),
        config_store.get_static_leases(),
    )


@router.get("", response_model=DhcpConfig)
def get_dhcp():
    return config_store.get_dhcp_config()


@router.put("")
def update_dhcp(config: DhcpConfig):
    config_store.save_dhcp_config(config)
    return {"status": "ok", **_apply_current()}


@router.get("/leases", response_model=list[StaticLease])
def get_leases():
    return config_store.get_static_leases()


@router.put("/leases")
def update_leases(leases: list[StaticLease]):
    config_store.save_static_leases(leases)
    return {"status": "ok", **_apply_current()}


@router.get("/leases/active", response_model=list[ActiveLease])
def get_active_leases():
    return dhcp_leases.get_active_leases()


class DhcpPreviewBody(BaseModel):
    config: DhcpConfig
    leases: list[StaticLease]


@router.post("/preview")
def preview_dhcp(body: DhcpPreviewBody):
    return {
        "dhcp": dhcp_gen.generate_dhcp(body.config),
        "static_leases": dhcp_gen.generate_static_leases(body.leases),
    }
