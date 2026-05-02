import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.routers import apps, auth, backup, dhcp, dns, network, services, system
from app.routers.auth import require_auth
from app.services import app_installer, applier, config_store

log = logging.getLogger("gateway-admin")


def _reconcile_on_startup():
    """Ensure the running system matches persisted JSON configs.

    The JSON is source of truth: if the UI said DHCP is enabled, dnsmasq
    must be enabled regardless of what the image shipped with. Applies
    DHCP/DNS configs (and the network config, which is a no-op if already
    synced). Any failure is logged but never breaks app startup.
    """
    try:
        applier.apply_dhcp(
            config_store.get_dhcp_config(),
            config_store.get_static_leases(),
        )
    except Exception:
        log.exception("DHCP reconciliation failed")
    try:
        applier.apply_dns(
            config_store.get_dns_config(),
            config_store.get_host_entries(),
        )
    except Exception:
        log.exception("DNS reconciliation failed")
    try:
        applier.apply_network(config_store.get_network_config())
    except Exception:
        log.exception("network reconciliation failed")
    try:
        actions = app_installer.reconcile()
        for action in actions:
            log.info("apps: %s", action)
    except Exception:
        log.exception("app reconciliation failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _reconcile_on_startup()
    yield


app = FastAPI(title="Gateway Admin API", lifespan=lifespan)

# Public endpoints (no auth)
app.include_router(auth.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Protected endpoints
protected = [Depends(require_auth)]
app.include_router(network.router, dependencies=protected)
app.include_router(dhcp.router, dependencies=protected)
app.include_router(dns.router, dependencies=protected)
app.include_router(services.router, dependencies=protected)
app.include_router(system.router, dependencies=protected)
app.include_router(backup.router, dependencies=protected)
app.include_router(apps.router, dependencies=protected)
