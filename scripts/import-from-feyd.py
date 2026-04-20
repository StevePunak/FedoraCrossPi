#!/usr/bin/env python3
"""
Import DHCP + DNS configuration from feyd (old gateway) into stilgar (new
gateway) via the admin API.

Reads:
    /etc/dnsmasq.d/dhcp.conf       — DHCP options + static leases
    /etc/dnsmasq.d/punak.conf      — upstream DNS + cache config
    /etc/punak-hosts               — addn-hosts (local DNS overrides)

Posts to:
    https://stilgar/api/dhcp
    https://stilgar/api/dhcp/leases
    https://stilgar/api/dns
    https://stilgar/api/dns/hosts
"""

import argparse
import getpass
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
import http.cookiejar
import ssl


def ssh_read(host: str, path: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", host, f"cat {path}"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def parse_dhcp_conf(text: str) -> tuple[dict, list[dict]]:
    dhcp = {
        "enabled": False,  # leave disabled on import; flip in UI when cutting over
        "authoritative": False,
        "range_start": "",
        "range_end": "",
        "netmask": "255.255.255.0",
        "lease_time": "24h",
        "router": "",
        "dns_server": "",
        "domain": "",
        "domain_search": [],
        "ntp_servers": [],
        "mtu": None,
        "tftp_server": "",
        "boot_filename": "",
    }
    leases = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line == "dhcp-authoritative":
            dhcp["authoritative"] = True
            continue

        if line.startswith("dhcp-range="):
            parts = line.split("=", 1)[1].split(",")
            if len(parts) >= 2:
                dhcp["range_start"] = parts[0]
                dhcp["range_end"] = parts[1]
            if len(parts) >= 3:
                dhcp["netmask"] = parts[2]
            if len(parts) >= 4:
                dhcp["lease_time"] = parts[3]
            continue

        if line.startswith("dhcp-option="):
            opt = line.split("=", 1)[1]
            m = re.match(r"option:([\w-]+),(.+)", opt)
            if m:
                name, val = m.group(1), m.group(2)
                if name == "router":
                    dhcp["router"] = val
                elif name == "dns-server":
                    dhcp["dns_server"] = val
                elif name == "domain-name":
                    dhcp["domain"] = val
                elif name == "domain-search":
                    dhcp["domain_search"] = [s.strip() for s in val.split(",")]
                elif name == "ntp-server":
                    dhcp["ntp_servers"] = [s.strip() for s in val.split(",")]
                elif name == "mtu":
                    dhcp["mtu"] = int(val)
                elif name == "tftp-server":
                    dhcp["tftp_server"] = val
                elif name == "bootfile-name":
                    dhcp["boot_filename"] = val
            continue

        if line.startswith("domain="):
            dhcp["domain"] = line.split("=", 1)[1]
            continue

        if line.startswith("dhcp-host="):
            parts = line.split("=", 1)[1].split(",")
            if len(parts) >= 3:
                leases.append({
                    "mac": parts[0].upper(),
                    "ip": parts[1],
                    "hostname": parts[2],
                    "comment": "",
                    "enabled": True,
                })

    return dhcp, leases


def parse_dns_conf(text: str) -> dict:
    dns = {
        "upstream_servers": [],
        "domain": "",
        "expand_hosts": False,
    }
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("server="):
            dns["upstream_servers"].append(line.split("=", 1)[1])
        elif line == "expand-hosts":
            dns["expand_hosts"] = True
    return dns


def parse_hosts(text: str) -> list[dict]:
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        entries.append({
            "ip": parts[0],
            "hostnames": parts[1:],
        })
    return entries


class ApiClient:
    def __init__(self, base_url: str, insecure: bool = False):
        self.base_url = base_url.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        handlers = [urllib.request.HTTPCookieProcessor(self.cookies)]
        if insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        self.opener = urllib.request.build_opener(*handlers)

    def request(self, path: str, method: str = "GET", body=None):
        data = None
        headers = {"Content-Type": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method, headers=headers,
        )
        try:
            with self.opener.open(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"{method} {path} -> {e.code}: {body_text}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="https://stilgar",
                    help="Base URL of new gateway admin (default: https://stilgar)")
    ap.add_argument("--feyd", default="feyd",
                    help="SSH host for feyd (default: feyd)")
    ap.add_argument("--username", default="admin")
    ap.add_argument("-k", "--insecure", action="store_true",
                    help="Skip TLS verification (for self-signed cert)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and print, don't POST")
    args = ap.parse_args()

    print(f"Reading configs from {args.feyd}…")
    dhcp_conf = ssh_read(args.feyd, "/etc/dnsmasq.d/dhcp.conf")
    dns_conf = ssh_read(args.feyd, "/etc/dnsmasq.d/punak.conf")
    hosts = ssh_read(args.feyd, "/etc/punak-hosts")

    dhcp_cfg, leases = parse_dhcp_conf(dhcp_conf)
    dns_cfg = parse_dns_conf(dns_conf)
    host_entries = parse_hosts(hosts)

    # Merge the "domain" and "expand-hosts" from dhcp.conf into DNS config too
    if dhcp_cfg.get("domain") and not dns_cfg.get("domain"):
        dns_cfg["domain"] = dhcp_cfg["domain"]

    # Also check dhcp.conf for expand-hosts
    if "expand-hosts" in dhcp_conf:
        dns_cfg["expand_hosts"] = True

    print(f"\nParsed {len(leases)} static leases, {len(host_entries)} host entries")
    print(f"DHCP range:  {dhcp_cfg['range_start']} - {dhcp_cfg['range_end']}")
    print(f"Router:      {dhcp_cfg['router']}")
    print(f"DNS server:  {dhcp_cfg['dns_server']}  (clients will use this for DNS)")
    print(f"Domain:      {dhcp_cfg['domain']}")
    print(f"Upstream:    {', '.join(dns_cfg['upstream_servers'])}")

    if args.dry_run:
        print("\n--- DHCP config ---")
        print(json.dumps(dhcp_cfg, indent=2))
        print("\n--- DNS config ---")
        print(json.dumps(dns_cfg, indent=2))
        print("\n--- First 3 leases ---")
        print(json.dumps(leases[:3], indent=2))
        print("\n--- First 3 host entries ---")
        print(json.dumps(host_entries[:3], indent=2))
        return

    # Log in
    import os
    password = os.environ.get("GATEWAY_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass(f"Password for {args.username}@{args.target}: ")
    api = ApiClient(args.target, insecure=args.insecure)
    print(f"\nLogging in as {args.username}…")
    api.request("/api/auth/login", "POST", {
        "username": args.username, "password": password,
    })

    print("Pushing DHCP config…")
    api.request("/api/dhcp", "PUT", dhcp_cfg)

    print(f"Pushing {len(leases)} static leases…")
    api.request("/api/dhcp/leases", "PUT", leases)

    print("Pushing DNS config…")
    api.request("/api/dns", "PUT", dns_cfg)

    print(f"Pushing {len(host_entries)} host entries…")
    api.request("/api/dns/hosts", "PUT", host_entries)

    print("\nDone.")


if __name__ == "__main__":
    main()
