// In production, nginx serves the UI and proxies /api/* to the backend.
// In dev (Vite on :5173), point at the FastAPI server on :8000.
const API_BASE = import.meta.env.DEV
  ? `http://${window.location.hostname}:8000/api`
  : "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
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
  dns_server: string;
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

export const api = {
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
};
