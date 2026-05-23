"""
Render systemd `.mount` and `.automount` units (plus an SMB credentials file)
for a NasMount entry. Mount paths are constrained by the schema to /mnt/<id>;
the unit basename is `mnt-<escaped-id>` per systemd's path-to-unit rules.
"""

from app.models.schemas import NasMount

DEFAULT_OPTIONS = "vers=3.0,iocharset=utf8,nofail,_netdev,noperm"


def path_to_unit(path: str) -> str:
    """Encode a filesystem path as a systemd unit basename.

    Each path component has '-' escaped to '\\x2d' (because '-' is the
    component separator in unit names); components are then joined by '-'.
    e.g. /mnt/music -> mnt-music; /mnt/foo-bar -> mnt-foo\\x2dbar
    """
    parts = [p for p in path.split("/") if p]
    escaped = ["".join("\\x2d" if c == "-" else c for c in p) for p in parts]
    return "-".join(escaped) if escaped else "-"


def unit_basename(mount: NasMount) -> str:
    return path_to_unit(mount.mount_path)


def credentials_content(mount: NasMount) -> str | None:
    if not mount.username and not mount.password:
        return None
    return f"username={mount.username}\npassword={mount.password}\n"


def options_string(mount: NasMount, credentials_path: str | None) -> str:
    opts = [DEFAULT_OPTIONS]
    if credentials_path:
        opts.append(f"credentials={credentials_path}")
    else:
        opts.append("guest")
    if mount.extra_options.strip():
        opts.append(mount.extra_options.strip())
    return ",".join(opts)


def generate_mount_unit(mount: NasMount, credentials_path: str | None) -> str:
    what = f"//{mount.server}/{mount.share}"
    options = options_string(mount, credentials_path)
    lines = [
        "[Unit]",
        f"Description=NAS mount {mount.id} ({what})",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Mount]",
        f"What={what}",
        f"Where={mount.mount_path}",
        "Type=cifs",
        f"Options={options}",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(lines)


def generate_automount_unit(mount: NasMount) -> str:
    lines = [
        "[Unit]",
        f"Description=NAS automount {mount.id}",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Automount]",
        f"Where={mount.mount_path}",
        "TimeoutIdleSec=600",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]
    return "\n".join(lines)
