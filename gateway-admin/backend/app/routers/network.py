from fastapi import APIRouter

from app.models.schemas import NetworkConfig
from app.services import applier, config_store
from app.services.generators import network as network_gen

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("", response_model=NetworkConfig)
def get_network():
    return config_store.get_network_config()


@router.put("")
def update_network(config: NetworkConfig):
    config_store.save_network_config(config)
    result = applier.apply_network(config)
    return {"status": "ok", **result}


@router.post("/preview")
def preview_network(config: NetworkConfig):
    return {"generated": network_gen.generate_network(config)}
