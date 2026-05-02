// Both prod (nginx reverse proxy) and dev (Vite proxy) serve /api on the
// same origin as the UI, so this can always be relative.
const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  // 401s on non-auth endpoints mean the session expired — signal a redirect.
  if (res.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

export interface NetworkConfig {
  mode: string;
  address: string;
  netmask: string;
  gateway: string;
  dns: string[];
  hostname: string;
}

export interface DhcpConfig {
  enabled: boolean;
  authoritative: boolean;
  range_start: string;
  range_end: string;
  netmask: string;
  lease_time: string;
  router: string;
  dns_servers: string[];
  domain: string;
  domain_search: string[];
  ntp_servers: string[];
  mtu: number | null;
  tftp_server: string;
  boot_filename: string;
}

export interface StaticLease {
  mac: string;
  ip: string;
  hostname: string;
  comment: string;
  enabled: boolean;
}

export interface DnsConfig {
  upstream_servers: string[];
  domain: string;
  expand_hosts: boolean;
}

export interface HostEntry {
  ip: string;
  hostnames: string[];
}

export interface ServiceStatus {
  name: string;
  active: boolean;
  enabled: boolean;
  status: string;
}

export interface SystemInfo {
  hostname: string;
  uptime: string;
  ip_address: string;
  kernel: string;
  memory_total: string;
  memory_used: string;
  disk_total: string;
  disk_used: string;
}

export interface AuthStatus {
  authenticated: boolean;
  bootstrap: boolean;
  username: string | null;
  dev_bypass: boolean;
}

export const api = {
  getAuthStatus: () => request<AuthStatus>("/auth/status"),
  bootstrap: (username: string, password: string) =>
    request<{ status: string; username: string }>("/auth/bootstrap", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<{ status: string; username: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  changePassword: (current_password: string, new_password: string) =>
    request("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
  getSystem: () => request<SystemInfo>("/system"),
  getNetwork: () => request<NetworkConfig>("/network"),
  updateNetwork: (c: NetworkConfig) =>
    request("/network", { method: "PUT", body: JSON.stringify(c) }),
  getDhcp: () => request<DhcpConfig>("/dhcp"),
  updateDhcp: (c: DhcpConfig) =>
    request("/dhcp", { method: "PUT", body: JSON.stringify(c) }),
  getLeases: () => request<StaticLease[]>("/dhcp/leases"),
  updateLeases: (l: StaticLease[]) =>
    request("/dhcp/leases", { method: "PUT", body: JSON.stringify(l) }),
  getDns: () => request<DnsConfig>("/dns"),
  updateDns: (c: DnsConfig) =>
    request("/dns", { method: "PUT", body: JSON.stringify(c) }),
  getHosts: () => request<HostEntry[]>("/dns/hosts"),
  updateHosts: (h: HostEntry[]) =>
    request("/dns/hosts", { method: "PUT", body: JSON.stringify(h) }),
  getServices: () => request<ServiceStatus[]>("/services"),
  controlService: (name: string, action: string) =>
    request(`/services/${name}/${action}`, { method: "POST" }),
  previewNetwork: (config: NetworkConfig) =>
    request<{ generated: string }>("/network/preview", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  previewDhcp: (config: DhcpConfig, leases: StaticLease[]) =>
    request<{ dhcp: string; static_leases: string }>("/dhcp/preview", {
      method: "POST",
      body: JSON.stringify({ config, leases }),
    }),
  previewDns: (config: DnsConfig, hosts: HostEntry[]) =>
    request<{ dns: string; hosts: string }>("/dns/preview", {
      method: "POST",
      body: JSON.stringify({ config, hosts }),
    }),
  downloadBackup: async (includeSecrets: boolean, passphrase: string) => {
    const form = new FormData();
    form.append("include_secrets", String(includeSecrets));
    if (passphrase) form.append("passphrase", passphrase);
    const res = await fetch("/api/backup", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.blob();
  },
  restoreBackup: async (file: File, passphrase: string) => {
    const form = new FormData();
    form.append("file", file);
    if (passphrase) form.append("passphrase", passphrase);
    const res = await fetch("/api/backup/restore", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json() as Promise<{ status: string; restored: number; files: string[] }>;
  },
};
