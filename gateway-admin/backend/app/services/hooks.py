"""
Manifest hook runner — invoke a script declared in a `HooksSpec` field.

Shared between `app_installer` (install / uninstall lifecycle) and `backup`
(pre/post-backup quiesce). The hook script receives:

    env: APP_ID, APP_VERSION, INSTALL_DIR, DATA_DIR, plus every key from
         the merged user config.
    cwd: install_dir
    argv: just the script path

A non-zero exit raises `HookError`. Callers are expected to catch and
re-raise in their domain's exception (`InstallError`, `BackupError`, …).
"""

import os
import subprocess
from pathlib import Path

from app.models.app_manifest import AppManifest


class HookError(Exception):
    pass


def run_hook(
    manifest: AppManifest,
    install_dir: Path,
    hook_name: str,
    config_values: dict,
) -> None:
    rel = getattr(manifest.hooks, hook_name)
    if not rel:
        return

    hook_path = install_dir / rel
    if not hook_path.exists():
        raise HookError(f"hook {hook_name} script not found: {hook_path}")
    hook_path.chmod(0o755)

    env = os.environ.copy()
    env.update({
        "APP_ID": manifest.id,
        "APP_VERSION": manifest.version,
        "INSTALL_DIR": str(install_dir),
        "DATA_DIR": str(install_dir),
    })
    for k, v in config_values.items():
        env[k] = str(v)

    result = subprocess.run(
        [str(hook_path)],
        cwd=install_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HookError(
            f"hook {hook_name} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
