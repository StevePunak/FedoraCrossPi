"""
Render the nginx location-include drop-in for an InstalledApp's web_ui.

The drop-in is included from inside the main 443 server{} block via:

    include /etc/nginx/locations.d/apps/*.conf;

Each app gets exactly one file at /etc/nginx/locations.d/apps/<id>.conf.
Auth gating is controlled by `web_ui.gateway_auth`: `"admin"` adds
`auth_request /api/auth/check` so only a logged-in gateway admin can
reach the proxy. `"none"` (the default) leaves the location open and
delegates access control to the app.
"""

from app.models.app_install import InstalledApp


def conf_path(app_id: str) -> str:
    return f"/etc/nginx/locations.d/apps/{app_id}.conf"


def generate(app: InstalledApp) -> str | None:
    if app.manifest.web_ui is None:
        return None

    web = app.manifest.web_ui
    path = web.path or f"/apps/{app.id}/"
    if not path.endswith("/"):
        path += "/"
    upstream = f"http://127.0.0.1:{web.port}"
    proxy_target = f"{upstream}/" if web.strip_prefix else upstream

    auth_lines: list[str] = []
    if web.gateway_auth == "admin":
        # Tailnet (100.64.0.0/10, fd7a:115c:a1e0::/48) skips the
        # auth_request — Tailscale device identity is the auth. Non-tailnet
        # sources fall through to the admin session check; 401s bounce to
        # /login via the @to_login named location in default.conf.
        auth_lines = [
            "    satisfy any;",
            "    allow 100.64.0.0/10;",
            "    allow fd7a:115c:a1e0::/48;",
            "    deny all;",
            "    auth_request /api/auth/check;",
            "    error_page 401 = @to_login;",
            "",
        ]

    lines = [
        f"# Auto-generated for app: {app.id}",
        f"location {path} {{",
        *auth_lines,
        f"    proxy_pass {proxy_target};",
        "    proxy_set_header Host $host;",
        "    proxy_set_header X-Real-IP $remote_addr;",
        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "    proxy_set_header X-Forwarded-Proto $scheme;",
        "    proxy_http_version 1.1;",
        "    proxy_set_header Upgrade $http_upgrade;",
        '    proxy_set_header Connection "upgrade";',
        "    proxy_read_timeout 300s;",
        "}",
        "",
    ]
    return "\n".join(lines)
