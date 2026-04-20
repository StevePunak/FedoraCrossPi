from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import dhcp, dns, network, services, system

app = FastAPI(title="Gateway Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(network.router)
app.include_router(dhcp.router)
app.include_router(dns.router)
app.include_router(services.router)
app.include_router(system.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
