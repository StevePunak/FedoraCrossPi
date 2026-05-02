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
    # v1: always true. Field exists so future installs can opt out per-app.
    requires_admin: bool = True

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


class HooksSpec(BaseModel):
    # Each value is a path inside the archive to an executable script.
    # Hooks run with env: APP_ID, APP_VERSION, INSTALL_DIR, DATA_DIR,
    # plus the merged user config. Working dir is the extracted archive root.
    pre_install: str | None = None
    post_install: str | None = None
    pre_uninstall: str | None = None


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

    # Subpaths created under /data/apps/<id>/. Must be relative, no ".." segments.
    data_dirs: list[str] = []
    config: list[ConfigField] = []
    hooks: HooksSpec = HooksSpec()
    health: HealthSpec | None = None

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not SEMVER_PATTERN.match(v):
            raise ValueError(f"not a valid semver: {v!r}")
        return v

    @field_validator("data_dirs")
    @classmethod
    def _no_traversal(cls, v: list[str]) -> list[str]:
        for d in v:
            if not d or d.startswith("/") or ".." in d.split("/"):
                raise ValueError(f"data_dirs entries must be relative, non-empty, and free of '..': {d!r}")
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

        return self
