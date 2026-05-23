import os

from fastapi import APIRouter

from app.models.schemas import SystemInfo

router = APIRouter(prefix="/api/system", tags=["system"])


def _stub_system_info() -> SystemInfo:
    return SystemInfo(
        hostname="gateway",
        uptime="0 days, 1:23:45",
        ip_address="192.168.0.2",
        kernel="6.12.0-yocto-standard",
        memory_total="1.8 GB",
        memory_used="256 MB",
        disk_total="29.1 GB",
        disk_used="806 MB",
    )


def _primary_ip() -> str:
    """Return the IP on the default route's interface, or 'unknown'."""
    import socket
    try:
        # Doesn't actually send any packets; just picks the outbound interface.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"


def _real_system_info() -> SystemInfo:
    import subprocess

    hostname = subprocess.run(
        ["hostname"], capture_output=True, text=True,
    ).stdout.strip()

    uptime = subprocess.run(
        ["uptime", "-p"], capture_output=True, text=True,
    ).stdout.strip().removeprefix("up ")

    ip = _primary_ip()

    kernel = subprocess.run(
        ["uname", "-r"], capture_output=True, text=True,
    ).stdout.strip()

    meminfo = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split(":")
            if len(parts) == 2:
                meminfo[parts[0].strip()] = parts[1].strip()

    mem_total = meminfo.get("MemTotal", "unknown")
    mem_avail = meminfo.get("MemAvailable", "0 kB")
    total_kb = int(mem_total.split()[0]) if mem_total != "unknown" else 0
    avail_kb = int(mem_avail.split()[0])
    used_kb = total_kb - avail_kb

    df = subprocess.run(
        ["df", "-h", "/"], capture_output=True, text=True,
    ).stdout.strip().split("\n")[-1].split()

    return SystemInfo(
        hostname=hostname,
        uptime=uptime,
        ip_address=ip,
        kernel=kernel,
        memory_total=f"{total_kb // 1024} MB",
        memory_used=f"{used_kb // 1024} MB",
        disk_total=df[1] if len(df) > 1 else "unknown",
        disk_used=df[2] if len(df) > 2 else "unknown",
    )


@router.get("", response_model=SystemInfo)
def get_system_info():
    if os.environ.get("GATEWAY_DATA_DIR"):
        return _real_system_info()
    return _stub_system_info()
