"""
Render systemd .mount (and optional .automount) units for a MountSpec.

systemd derives the unit name from the absolute mount point — `/mnt/movies`
becomes `mnt-movies.mount`. The escape rules are not a plain slash swap
(hyphens and other characters need escaping), so we shell out to
`systemd-escape --path` and let systemd answer authoritatively.

Credentials referenced in the options string (e.g.
`credentials=/data/nas/credentials/movies`) are assumed to exist as a
pre-provisioned host resource. The installer does not create or manage
them — that's an operator concern handled out-of-band.
"""

import subprocess

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


def effective_options(spec: MountSpec) -> str:
    """Final `Options=` value. Auto-appends `_netdev` for cifs/nfs so
    systemd doesn't block boot waiting on a network mount."""
    parts = [p.strip() for p in spec.options.split(",") if p.strip()]
    if spec.type in ("cifs", "nfs", "nfs4") and "_netdev" not in parts:
        parts.append("_netdev")
    return ",".join(parts)


def generate_mount(app: InstalledApp, spec: MountSpec) -> str:
    options = effective_options(spec)

    sections = [
        "[Unit]",
        f"Description={app.manifest.name} mount: {spec.name}",
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
    ]
    if spec.type in ("cifs", "nfs", "nfs4"):
        sections += [
            "After=network-online.target",
            "Wants=network-online.target",
        ]
    sections += [
        "",
        "[Automount]",
        f"Where={spec.where}",
    ]
    if spec.idle_timeout_seconds is not None:
        sections.append(f"TimeoutIdleSec={spec.idle_timeout_seconds}")
    sections += [
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(sections)


def required_unit_name(spec: MountSpec) -> str:
    """The unit a dependent service should Require= and After=. When
    automount is true the service depends on the .automount so it
    triggers a lazy mount; otherwise the .mount itself."""
    return automount_unit_name(spec.where) if spec.automount else mount_unit_name(spec.where)
