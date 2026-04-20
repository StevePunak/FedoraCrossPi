import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { NetworkConfig } from "../api/client";
import Card from "../components/Card";
import FormField, { inputStyle } from "../components/FormField";
import Preview from "../components/Preview";
import { useDebounced } from "../hooks/useDebounced";

const btnStyle: React.CSSProperties = {
  padding: "8px 20px",
  background: "#0984e3",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  fontSize: 14,
  cursor: "pointer",
};

type Status =
  | { kind: "idle" }
  | { kind: "saved" }
  | { kind: "redirecting"; newHost: string; attempts: number };

async function waitForHost(host: string, protocol: string, maxAttempts = 60): Promise<boolean> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${protocol}//${host}/api/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(2000),
      });
      if (res.ok) return true;
    } catch {
      // keep polling
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

export default function Network() {
  const [config, setConfig] = useState<NetworkConfig | null>(null);
  const [preview, setPreview] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const debounced = useDebounced(config);

  useEffect(() => {
    api.getNetwork().then(setConfig);
  }, []);

  useEffect(() => {
    if (debounced) api.previewNetwork(debounced).then((r) => setPreview(r.generated));
  }, [debounced]);

  if (!config) return <p>Loading...</p>;

  const update = (field: keyof NetworkConfig, value: string | string[]) => {
    setConfig({ ...config, [field]: value });
    setStatus({ kind: "idle" });
  };

  const save = async () => {
    const currentHost = window.location.hostname;
    const newHost = config.mode === "static" && config.address ? config.address : null;
    const willChangeIp = newHost && newHost !== currentHost;

    // Fire the update; we may not see the response if the IP changes mid-request.
    api.updateNetwork(config).catch(() => { /* expected on IP change */ });

    if (willChangeIp) {
      setStatus({ kind: "redirecting", newHost: newHost!, attempts: 0 });
      const protocol = window.location.protocol; // "http:" or "https:"
      const reachable = await waitForHost(newHost!, protocol);
      if (reachable) {
        window.location.href = `${protocol}//${newHost}/`;
      } else {
        alert(`New IP ${newHost} did not come online after 60s. Check the Pi.`);
      }
    } else {
      setStatus({ kind: "saved" });
    }
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Network Configuration</h1>
      <Card title="Interface Settings">
        <FormField label="Hostname">
          <input style={inputStyle} value={config.hostname} onChange={(e) => update("hostname", e.target.value)} />
        </FormField>
        <FormField label="Mode">
          <select style={inputStyle} value={config.mode} onChange={(e) => update("mode", e.target.value)}>
            <option value="dhcp">DHCP</option>
            <option value="static">Static</option>
          </select>
        </FormField>
        {config.mode === "static" && (
          <>
            <FormField label="IP Address">
              <input style={inputStyle} value={config.address} onChange={(e) => update("address", e.target.value)} />
            </FormField>
            <FormField label="Netmask">
              <input style={inputStyle} value={config.netmask} onChange={(e) => update("netmask", e.target.value)} />
            </FormField>
            <FormField label="Gateway">
              <input style={inputStyle} value={config.gateway} onChange={(e) => update("gateway", e.target.value)} />
            </FormField>
            <FormField label="DNS Servers (comma-separated)">
              <input
                style={inputStyle}
                value={config.dns.join(", ")}
                onChange={(e) => update("dns", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
              />
            </FormField>
          </>
        )}
        <div style={{ marginTop: 16 }}>
          <button
            style={btnStyle}
            onClick={save}
            disabled={status.kind === "redirecting"}
          >
            Save &amp; Apply
          </button>
          {status.kind === "saved" && (
            <span style={{ marginLeft: 12, color: "#00b894" }}>Saved</span>
          )}
          {status.kind === "redirecting" && (
            <span style={{ marginLeft: 12, color: "#e17055" }}>
              Waiting for {status.newHost} to come online…
            </span>
          )}
        </div>
      </Card>

      <Card title="Generated Configuration">
        <Preview label="systemd-networkd" path="/etc/systemd/network/10-wired-static.network" content={preview} />
      </Card>
    </>
  );
}
