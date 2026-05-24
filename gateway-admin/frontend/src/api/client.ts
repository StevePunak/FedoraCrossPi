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
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI/Pydantic 422 returns [{loc, msg, type}, ...]
        detail = body.detail
          .map((e: { loc?: (string | number)[]; msg?: string }) => {
            const field = e.loc?.filter((p) => p !== "body").join(".") || "body";
            return `${field}: ${e.msg ?? "invalid"}`;
          })
          .join("; ");
      }
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
  domain: string;
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

export interface ActiveLease {
  // Unix epoch when the lease expires; 0 means never-expiring (static).
  expires_at: number;
  mac: string;
  ip: string;
  hostname: string;
  client_id: string;
  // Manufacturer short name from the MAC's OUI prefix (Wireshark `manuf`).
  // `null` when the prefix is unknown or the lookup table is unavailable.
  vendor: string | null;
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

export interface NasMount {
  id: string;
  server: string;
  share: string;
  username: string;
  password: string;
  extra_options: string;
  enabled: boolean;
}

export interface NasConfig {
  mounts: NasMount[];
}

export interface NasMountStatus {
  id: string;
  mount_path: string;
  enabled: boolean;
  mounted: boolean;
  automount_active: boolean;
  last_error: string;
}

export interface NasTestResult {
  ok: boolean;
  message: string;
}

export interface AuthStatus {
  authenticated: boolean;
  bootstrap: boolean;
  username: string | null;
  dev_bypass: boolean;
}

// ---- Apps ----

export interface CompatibilitySpec {
  target_arch: "aarch64";
  min_appliance_version: string;
}

export interface AppServiceSpec {
  name: string;
  exec: string;
  args: string[];
  working_dir: string | null;
  user: string | null;
  requires: string[];
  restart: "no" | "on-failure" | "always";
  type: "simple" | "forking" | "notify";
  environment: Record<string, string>;
}

export interface AppWebUiSpec {
  service: string;
  port: number;
  path: string | null;
  strip_prefix: boolean;
  // "none" (default) — no gateway gate; app handles its own auth.
  // "admin"            — nginx auth_request gates on gateway-admin session.
  gateway_auth: "none" | "admin";
}

export interface AppConfigField {
  key: string;
  label: string;
  type: "string" | "int" | "bool" | "select" | "password" | "path";
  default: string | number | boolean | null;
  required: boolean;
  description: string | null;
  choices: string[] | null;
  min: number | null;
  max: number | null;
  secret: boolean;
}

export interface AppHooksSpec {
  pre_install: string | null;
  post_install: string | null;
  pre_uninstall: string | null;
}

export interface AppHealthSpec {
  service: string;
  url: string;
  expected_status: number;
  interval_seconds: number;
}

export interface AppManifest {
  schema_version: 1;
  id: string;
  name: string;
  version: string;
  description: string | null;
  vendor: string | null;
  compatibility: CompatibilitySpec;
  services: AppServiceSpec[];
  web_ui: AppWebUiSpec | null;
  data_dirs: string[];
  config: AppConfigField[];
  hooks: AppHooksSpec;
  health: AppHealthSpec | null;
}

export interface InstalledApp {
  id: string;
  version: string;
  manifest: AppManifest;
  config_values: Record<string, string | number | boolean>;
  installed_at: string;
  enabled: boolean;
  archive_sha256: string;
}

export interface AppDetail {
  app: InstalledApp;
  status: Record<string, string>;
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
  getActiveLeases: () => request<ActiveLease[]>("/dhcp/leases/active"),
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
  downloadBackup: async (
    includeSecrets: boolean,
    passphrase: string,
    onProgress?: (received: number) => void,
  ) => {
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
    // The backend streams unencrypted backups; we read in chunks and
    // count bytes for a fallback display. The richer progress (file
    // count + percent) comes from polling /api/backup/progress, which
    // the caller drives separately.
    if (!res.body || !onProgress) {
      return res.blob();
    }
    const reader = res.body.getReader();
    // BlobPart accepts BufferSource; the reader yields generic
    // Uint8Array<ArrayBufferLike> which TS narrows away from BlobPart,
    // so collect as the looser type and cast at construction.
    const chunks: BlobPart[] = [];
    let received = 0;
    onProgress(0);
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value as BlobPart);
      received += value.length;
      onProgress(received);
    }
    return new Blob(chunks);
  },
  getBackupProgress: () =>
    request<{ phase: "idle" | "streaming" | "done"; files_done: number; files_total: number }>(
      "/backup/progress",
    ),
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
  listApps: () => request<InstalledApp[]>("/apps"),
  getApp: (id: string) => request<AppDetail>(`/apps/${id}`),
  preflightApp: async (file: File): Promise<AppManifest> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/apps/preflight", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  },
  installApp: async (file: File, configValues: Record<string, unknown>): Promise<InstalledApp> => {
    const form = new FormData();
    form.append("file", file);
    form.append("config", JSON.stringify(configValues));
    const res = await fetch("/api/apps", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  },
  uninstallApp: (id: string) =>
    request<{ status: string }>(`/apps/${id}`, { method: "DELETE" }),
  updateAppConfig: (id: string, configValues: Record<string, unknown>) =>
    request<InstalledApp>(`/apps/${id}/config`, {
      method: "PUT",
      body: JSON.stringify(configValues),
    }),
  controlApp: (id: string, action: "start" | "stop" | "restart") =>
    request<{ status: string }>(`/apps/${id}/${action}`, { method: "POST" }),
  getAppStatus: (id: string) =>
    request<Record<string, string>>(`/apps/${id}/status`),
  getNas: () => request<NasConfig>("/nas"),
  updateNas: (c: NasConfig) =>
    request("/nas", { method: "PUT", body: JSON.stringify(c) }),
  getNasStatus: () => request<NasMountStatus[]>("/nas/status"),
  previewNas: (c: NasConfig) =>
    request<Record<string, string>>("/nas/preview", {
      method: "POST",
      body: JSON.stringify(c),
    }),
  testNas: (m: NasMount) =>
    request<NasTestResult>("/nas/test", {
      method: "POST",
      body: JSON.stringify(m),
    }),
};
