"""
Backup / restore the gateway's persistent configuration.

The "source of truth" lives in /data:
    *.json              user-editable configs (network, dhcp, dns, hosts, ...)
    auth.json           bcrypt admin password (excluded if include_secrets=False)
    ssl/                self-signed cert + key (excluded if include_secrets=False)
    network/            generated systemd-networkd unit (regenerated on reconcile)
    dnsmasq.d/          generated dnsmasq drop-ins (regenerated on reconcile)
    hostname            persisted hostname

A backup is a gzip-compressed tarball of those files. If a passphrase is
given, the tarball is encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
using PBKDF2-derived key.
"""

import base64
import io
import os
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Marker bytes prefix on encrypted backups so we can tell them apart
ENCRYPTED_HEADER = b"GWADMIN-ENC-V1\n"

# Files to exclude when include_secrets is False
SECRET_PATHS = {"auth.json", "ssl"}


def _data_dir() -> Path:
    return Path(os.environ.get("GATEWAY_DATA_DIR", "/data"))


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _encrypt(blob: bytes, passphrase: str) -> bytes:
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(blob)
    return ENCRYPTED_HEADER + salt + token


def _decrypt(blob: bytes, passphrase: str) -> bytes:
    if not blob.startswith(ENCRYPTED_HEADER):
        raise ValueError("file is not an encrypted gateway backup")
    body = blob[len(ENCRYPTED_HEADER):]
    salt, token = body[:16], body[16:]
    key = _derive_key(passphrase, salt)
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken:
        raise ValueError("incorrect passphrase or corrupted backup")


def _should_skip(arcname: str, include_secrets: bool) -> bool:
    if include_secrets:
        return False
    head = arcname.split("/", 1)[0]
    return head in SECRET_PATHS


def create_backup(include_secrets: bool = True, passphrase: str | None = None) -> bytes:
    """Return a gzipped tarball (optionally encrypted) of /data."""
    data = _data_dir()
    if not data.exists():
        raise ValueError(f"data dir {data} does not exist")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in sorted(data.rglob("*")):
            if path.is_dir():
                continue
            arcname = str(path.relative_to(data))
            if _should_skip(arcname, include_secrets):
                continue
            tar.add(str(path), arcname=arcname)

    blob = buf.getvalue()
    if passphrase:
        blob = _encrypt(blob, passphrase)
    return blob


def restore_backup(blob: bytes, passphrase: str | None = None) -> dict:
    """Replace /data contents with the backup tarball.

    Returns a summary of restored files.
    """
    if blob.startswith(ENCRYPTED_HEADER):
        if not passphrase:
            raise ValueError("backup is encrypted — passphrase required")
        blob = _decrypt(blob, passphrase)
    elif passphrase:
        raise ValueError("backup is not encrypted; remove the passphrase")

    data = _data_dir()
    data.mkdir(parents=True, exist_ok=True)

    files_restored: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        members = tar.getmembers()
        # Defence: refuse path traversal
        for m in members:
            if m.name.startswith("/") or ".." in m.name.split("/"):
                raise ValueError(f"unsafe path in backup: {m.name}")
        for m in members:
            if m.isfile():
                tar.extract(m, path=str(data), filter="data")
                files_restored.append(m.name)

    return {"restored": len(files_restored), "files": files_restored}
