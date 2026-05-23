"""
Render systemd .mount (and optional .automount) units for a MountSpec.

systemd derives the unit name from the absolute mount point — `/data/nas/tv`
becomes `data-nas-tv.mount`. The escape rules are not a plain slash swap
(hyphens and other characters need escaping), so we shell out to
`systemd-escape --path` and let systemd answer authoritatively.

The installer is responsible for any credentials file referenced by the
unit; we just embed the path in the options string.
"""

import subprocess
from pathlib import Path

from app.models.app_install import InstalledApp
from app.models.app_manifest import MountSpec


def _escape(path: str, suffix: str) -> str:
    result = subprocess.run(
        ["systemd-escape", "--path", f"--suffix={suffix}", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def mount_unit_name(where: str) -> str:
    return _escape(where, "mount")


def automount_unit_name(where: str) -> str:
    return _escape(where, "automount")


def cred_path(app_id: str, mount_name: str) -> Path:
    return Path(f"/data/apps/{app_id}/state/{mount_name}.creds")


def effective_options(app_id: str, spec: MountSpec) -> str:
    """Build the final options string for `Options=` in the .mount unit.
    Appends `credentials=<path>` automatically when the spec declares a
    credentials block. _netdev is appended for cifs/nfs so systemd
    doesn't block boot on a missing network."""
    parts = [p.strip() for p in spec.options.split(",") if p.strip()]
    if spec.credentials is not None:
        parts.append(f"credentials={cred_path(app_id, spec.name)}")
    if spec.type in ("cifs", "nfs", "nfs4") and "_netdev" not in parts:
        parts.append("_netdev")
    return ",".join(parts)


def generate_mount(app: InstalledApp, spec: MountSpec) -> str:
    options = effective_options(app.id, spec)

    sections = [
        "[Unit]",
        f"Description={app.manifest.name} mount: {spec.name}",
        "After=data.mount",
        "Requires=data.mount",
    ]
    if spec.type in ("cifs", "nfs", "nfs4"):
        sections += [
            "After=network-online.target",
            "Wants=network-online.target",
        ]
    sections += [
        "",
        "[Mount]",
        f"What={spec.what}",
        f"Where={spec.where}",
        f"Type={spec.type}",
    ]
    if options:
        sections.append(f"Options={options}")
    sections += [
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(sections)


def generate_automount(app: InstalledApp, spec: MountSpec) -> str:
    sections = [
        "[Unit]",
        f"Description={app.manifest.name} automount: {spec.name}",
        "After=data.mount",
        "Requires=data.mount",
        "",
        "[Automount]",
        f"Where={spec.where}",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(sections)


def required_unit_name(spec: MountSpec) -> str:
    """The unit a dependent service should Require= and After=. When
    automount is true the service should depend on the .automount so it
    triggers a lazy mount; otherwise the .mount itself."""
    return automount_unit_name(spec.where) if spec.automount else mount_unit_name(spec.where)


def generate_credentials_file(
    spec: MountSpec, config_values: dict
) -> str | None:
    """Render the contents of the credentials= file. Returns None if no
    credentials block is declared. Missing values become empty strings —
    a guest CIFS share is a valid use case."""
    if spec.credentials is None:
        return None
    creds = spec.credentials
    username = str(config_values.get(creds.username_field, ""))
    password = str(config_values.get(creds.password_field, ""))
    lines = [f"username={username}", f"password={password}"]
    if creds.domain_field is not None:
        domain = str(config_values.get(creds.domain_field, ""))
        lines.append(f"domain={domain}")
    return "\n".join(lines) + "\n"
