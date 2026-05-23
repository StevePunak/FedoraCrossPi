"""
App manifest schema (v1).

Each installable app archive contains a `manifest.json` at its root that conforms
to `AppManifest`. The installer validates this on upload, renders config forms
from `config[]`, materializes systemd units from `services[]`, and writes the
nginx drop-in from `web_ui`.

Archive layout
--------------
The app archive is a `.tar.gz` whose root is the install tree. `manifest.json`
must live at the archive root. Everything else is up to the app — common
conventions:

    manifest.json
    bin/<exec-name>        (referenced by ServiceSpec.exec, e.g. "bin/qbit-nox")
    lib/...
    share/...

The installer extracts the archive verbatim into the install dir below.

Runtime layout
--------------
All app state lives under `/data/apps/<id>/` so it survives a reflash:

    /data/apps/<id>/                extracted archive contents (binaries + libs)
    /data/apps/<id>/manifest.json   the manifest
    /data/apps/<id>/config.env      user-edited config (sourced by every unit)
    /data/apps/<id>/<data_dir>/     subdirs created from `data_dirs[]`

Service units default to `WorkingDirectory=/data/apps/<id>/` and
`EnvironmentFile=/data/apps/<id>/config.env`. The `exec` field in each
ServiceSpec is resolved relative to the install dir.

Naming
------
systemd units: `app-<id>-<svc>.service`
nginx mount:   `/apps/<id>/` (default; overridable via `web_ui.path`)
system user:   `app-<id>` (created at install time if `ServiceSpec.user` unset)
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ID_PATTERN = r"^[a-z][a-z0-9-]{1,30}$"
SVC_PATTERN = r"^[a-z][a-z0-9-]{0,30}$"
ENV_PATTERN = r"^[A-Z][A-Z0-9_]*$"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")


class CompatibilitySpec(BaseModel):
    target_arch: Literal["aarch64"]
    min_appliance_version: str

    @field_validator("min_appliance_version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not SEMVER_PATTERN.match(v):
            raise ValueError(f"not a valid semver: {v!r}")
        return v


class ServiceSpec(BaseModel):
    name: str = Field(pattern=SVC_PATTERN)
    # Path inside the archive, relative to its root.
    # Becomes /opt/apps/<id>/<exec> at install time.
    exec: str
    args: list[str] = []
    # Defaults to /opt/apps/<id>/ if unset.
    working_dir: str | None = None
    # Defaults to a per-app system user (app-<id>) created at install time.
    user: str | None = None
    # Names of other services in this manifest. Translates to
    # After= and Requires= in the systemd unit.
    requires: list[str] = []
    restart: Literal["no", "on-failure", "always"] = "on-failure"
    type: Literal["simple", "forking", "notify"] = "simple"
    # Inline Environment= entries. Merged with the user-config env file
    # (which always wins, since it's sourced after these are set).
    environment: dict[str, str] = {}


class WebUiSpec(BaseModel):
    # Must reference a services[].name.
    service: str
    port: int = Field(ge=1, le=65535)
    # Defaults to /apps/<id>/ at install time.
    path: str | None = None
    # If true, nginx strips `path` before forwarding (the app sees clean URLs).
    strip_prefix: bool = True
    # Who's allowed to reach this app's web UI through the gateway:
    #   "none"  — no gateway-level gate. The app is reachable from the LAN.
    #             Auth (if the app wants it) is the app's own concern.
    #   "admin" — nginx auth_request gates the proxy on a valid
    #             gateway-admin session cookie. Suited to ops-only tools.
    # Defaults to "none" because admin gating is the *wrong* layer for
    # most apps — users of a torrent UI / media player aren't appliance
    # admins. Apps with their own user model build it themselves.
    gateway_auth: Literal["none", "admin"] = "none"

    @model_validator(mode="before")
    @classmethod
    def _migrate_requires_admin(cls, data):
        # Existing installed.json records (pre-2026-05-10) carry
        # `requires_admin: bool`. Convert on read so persisted state
        # doesn't reject parse after the schema rename.
        if isinstance(data, dict) and "requires_admin" in data and "gateway_auth" not in data:
            data = dict(data)
            data["gateway_auth"] = "admin" if data.pop("requires_admin") else "none"
        return data

    @field_validator("path")
    @classmethod
    def _abs_path(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("/"):
            raise ValueError("path must start with /")
        return v


class ConfigField(BaseModel):
    # Env var name written into /data/apps/<id>/config.env.
    key: str = Field(pattern=ENV_PATTERN)
    label: str
    type: Literal["string", "int", "bool", "select", "password", "path"]
    default: Any = None
    required: bool = False
    description: str | None = None
    # Required only when type="select".
    choices: list[str] | None = None
    # Bounds for type="int".
    min: int | None = None
    max: int | None = None
    # Suppress in API responses and UI display (not encryption).
    secret: bool = False

    @model_validator(mode="after")
    def _check_type_constraints(self):
        if self.type == "select" and not self.choices:
            raise ValueError("type=select requires choices")
        if self.type != "select" and self.choices is not None:
            raise ValueError("choices is only valid when type=select")
        if (self.min is not None or self.max is not None) and self.type != "int":
            raise ValueError("min/max only valid when type=int")
        return self


class MountSpec(BaseModel):
    name: str = Field(pattern=SVC_PATTERN)
    # Source. CIFS: //host/share. NFS: host:/export. bind: an existing path.
    what: str
    # Mount point. Absolute path; must not be "/" and must not contain "..".
    where: str
    type: Literal["cifs", "nfs", "nfs4", "bind", "tmpfs", "ext4"] = "cifs"
    # Mount options, comma-separated. CIFS authors put their
    # `credentials=/data/nas/credentials/<name>` here directly — credentials
    # files are infrastructure the operator manages out-of-band, not
    # installer-provisioned.
    options: str = ""
    # When true (the default), the installer pairs the .mount with a
    # .automount that watches the path and triggers the actual mount
    # on first access. Lets the daemon boot even when the NAS is down;
    # the mountpoint just looks empty until the share comes up.
    automount: bool = True
    # When set, emitted as `TimeoutIdleSec=` in the .automount section so
    # systemd unmounts the share after the configured idle period and
    # remounts on next access. Only meaningful when `automount` is true.
    idle_timeout_seconds: int | None = Field(default=None, ge=1)

    @field_validator("where")
    @classmethod
    def _where_abs(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("where must be an absolute path")
        if v == "/":
            raise ValueError("where cannot be /")
        if ".." in v.split("/"):
            raise ValueError("where must not contain '..'")
        return v


class HooksSpec(BaseModel):
    # Each value is a path inside the archive to an executable script.
    # Hooks run with env: APP_ID, APP_VERSION, INSTALL_DIR, DATA_DIR,
    # plus the merged user config. Working dir is the extracted archive root.
    pre_install: str | None = None
    post_install: str | None = None
    pre_uninstall: str | None = None
    # Backup hooks: pre_backup quiesces the app before the gateway tars
    # /data (e.g. stop the daemon so a SQLite-in-WAL file is consistent on
    # disk); post_backup brings it back afterwards. pre_backup failure
    # aborts the whole backup; post_backup is best-effort. See
    # services/backup.py for the orchestration.
    pre_backup: str | None = None
    post_backup: str | None = None


class HealthSpec(BaseModel):
    service: str
    url: str  # relative URL queried against the service's upstream port
    expected_status: int = 200
    interval_seconds: int = Field(default=30, ge=5, le=3600)

    @field_validator("url")
    @classmethod
    def _starts_with_slash(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("url must start with /")
        return v


class AppManifest(BaseModel):
    schema_version: Literal[1] = 1

    id: str = Field(pattern=ID_PATTERN)
    name: str
    version: str
    description: str | None = None
    vendor: str | None = None

    compatibility: CompatibilitySpec

    services: list[ServiceSpec] = Field(min_length=1)
    web_ui: WebUiSpec | None = None
    # Filesystem mounts the app needs. Each entry materializes a systemd
    # .mount unit (and a paired .automount if MountSpec.automount=true).
    # Service units in this manifest get auto-injected Requires=/After=
    # against these mounts, so the daemon never starts against an empty
    # mountpoint. Mount-point conflicts across apps are rejected at install.
    mounts: list[MountSpec] = []

    # Subpaths created under /data/apps/<id>/. Must be relative, no ".." segments.
    data_dirs: list[str] = []
    # Subpaths inside /data/apps/<id>/ preserved by the gateway backup +
    # by install-over-existing (the update path). `None` (the default)
    # means fall back to `data_dirs` — that's what app authors usually
    # want and existing manifests get sensible behavior for free. An
    # empty list is an explicit opt-out (nothing app-specific in the
    # backup, app is fully rebuildable from the archive). A non-empty
    # list overrides data_dirs (e.g. a subset of data_dirs that excludes
    # large reproducible caches).
    backup_paths: list[str] | None = None
    config: list[ConfigField] = []
    hooks: HooksSpec = HooksSpec()
    health: HealthSpec | None = None

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not SEMVER_PATTERN.match(v):
            raise ValueError(f"not a valid semver: {v!r}")
        return v

    @field_validator("data_dirs", "backup_paths")
    @classmethod
    def _no_traversal(cls, v):
        if v is None:
            return v
        for d in v:
            if not d or d.startswith("/") or ".." in d.split("/"):
                raise ValueError(f"entries must be relative, non-empty, and free of '..': {d!r}")
        return v

    @model_validator(mode="after")
    def _cross_refs(self):
        names = {s.name for s in self.services}
        if len(names) != len(self.services):
            raise ValueError("services[].name values must be unique")

        for s in self.services:
            for r in s.requires:
                if r not in names:
                    raise ValueError(f"service {s.name!r} requires unknown service {r!r}")

        if self.web_ui and self.web_ui.service not in names:
            raise ValueError(f"web_ui.service {self.web_ui.service!r} not in services")

        if self.health and self.health.service not in names:
            raise ValueError(f"health.service {self.health.service!r} not in services")

        keys = [c.key for c in self.config]
        if len(keys) != len(set(keys)):
            raise ValueError("config[].key values must be unique")

        mount_names = [m.name for m in self.mounts]
        if len(mount_names) != len(set(mount_names)):
            raise ValueError("mounts[].name values must be unique")

        mount_wheres = [m.where.rstrip("/") for m in self.mounts]
        if len(mount_wheres) != len(set(mount_wheres)):
            raise ValueError("mounts[].where values must be unique within an app")

        return self
