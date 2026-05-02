"""
Render a systemd service unit file for one ServiceSpec entry.

Unit naming: app-<id>-<svc>.service
Working dir: /data/apps/<id>/ (or ServiceSpec.working_dir if set)
EnvironmentFile: /data/apps/<id>/config.env (always, optional `-` prefix
so a missing file doesn't fail unit start).
"""

import shlex

from app.models.app_install import InstalledApp
from app.models.app_manifest import ServiceSpec


def install_dir(app_id: str) -> str:
    return f"/data/apps/{app_id}"


def unit_name(app_id: str, service_name: str) -> str:
    return f"app-{app_id}-{service_name}.service"


def generate_unit(app: InstalledApp, service: ServiceSpec) -> str:
    base = install_dir(app.id)
    user = service.user or f"app-{app.id}"
    working_dir = service.working_dir or base
    exec_path = f"{base}/{service.exec}"
    args_str = " ".join(shlex.quote(a) for a in service.args)
    exec_line = exec_path + ((" " + args_str) if args_str else "")

    requires_lines = []
    for req in service.requires:
        req_unit = unit_name(app.id, req)
        requires_lines.append(f"After={req_unit}")
        requires_lines.append(f"Requires={req_unit}")

    env_lines = [
        f"Environment={k}={shlex.quote(v)}"
        for k, v in sorted(service.environment.items())
    ]

    sections = [
        "[Unit]",
        f"Description={app.manifest.name} ({service.name})",
        "After=network-online.target data.mount",
        "Requires=data.mount",
        *requires_lines,
        "",
        "[Service]",
        f"Type={service.type}",
        f"User={user}",
        f"Group={user}",
        f"WorkingDirectory={working_dir}",
        f"EnvironmentFile=-{base}/config.env",
        *env_lines,
        f"ExecStart={exec_line}",
        f"Restart={service.restart}",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(sections)
