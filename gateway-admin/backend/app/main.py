from fastapi import Depends, FastAPI

from app.routers import auth, dhcp, dns, network, services, system
from app.routers.auth import require_auth

app = FastAPI(title="Gateway Admin API")

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
