import os

from fastapi import APIRouter

from app.models.schemas import ServiceStatus

router = APIRouter(prefix="/api/services", tags=["services"])

MANAGED_SERVICES = ["dnsmasq", "nginx", "avahi-daemon", "sshd", "certbot-renew.timer"]


def _stub_status(name: str) -> ServiceStatus:
    """Return stubbed service status for dev mode."""
    defaults = {
        "dnsmasq": (False, False, "inactive"),
        "nginx": (True, True, "running"),
        "avahi-daemon": (True, True, "running"),
        "sshd": (True, True, "running"),
        "certbot-renew.timer": (True, True, "active"),
    }
    active, enabled, status = defaults.get(name, (False, False, "unknown"))
    return ServiceStatus(name=name, active=active, enabled=enabled, status=status)


def _get_service_status(name: str) -> ServiceStatus:
    if os.environ.get("GATEWAY_DATA_DIR"):
        # Production: query systemd
        import subprocess
        is_active = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True,
        ).stdout.strip()
        is_enabled = subprocess.run(
            ["systemctl", "is-enabled", name],
            capture_output=True, text=True,
        ).stdout.strip()
        return ServiceStatus(
            name=name,
            active=is_active == "active",
            enabled=is_enabled == "enabled",
            status=is_active,
        )
    return _stub_status(name)


@router.get("", response_model=list[ServiceStatus])
def list_services():
    return [_get_service_status(name) for name in MANAGED_SERVICES]


@router.post("/{name}/{action}")
def control_service(name: str, action: str):
    if name not in MANAGED_SERVICES:
        return {"status": "error", "message": f"Unknown service: {name}"}
    if action not in ("start", "stop", "restart", "enable", "disable"):
        return {"status": "error", "message": f"Unknown action: {action}"}

    if os.environ.get("GATEWAY_DATA_DIR"):
        import subprocess
        subprocess.run(["systemctl", action, name], check=True)

    return {"status": "ok", "service": name, "action": action}
