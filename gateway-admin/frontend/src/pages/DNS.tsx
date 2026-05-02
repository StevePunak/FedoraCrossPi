import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { DnsConfig, HostEntry } from "../api/client";
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

const dangerBtn: React.CSSProperties = {
  ...btnStyle,
  background: "#d63031",
  padding: "4px 12px",
  fontSize: 13,
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  borderBottom: "2px solid #dfe6e9",
  color: "#636e72",
  fontSize: 13,
  fontWeight: 600,
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #f0f0f0",
};

export default function DNS() {
  const [config, setConfig] = useState<DnsConfig | null>(null);
  const [hosts, setHosts] = useState<HostEntry[]>([]);
  const [saved, setSaved] = useState(false);
  const [newHost, setNewHost] = useState<HostEntry>({ ip: "", hostnames: [""] });
  const [preview, setPreview] = useState<{ dns: string; hosts: string }>({ dns: "", hosts: "" });

  const formState = useMemo(() => ({ config, hosts }), [config, hosts]);
  const debounced = useDebounced(formState);

  useEffect(() => {
    api.getDns().then(setConfig);
    api.getHosts().then(setHosts);
  }, []);

  useEffect(() => {
    if (debounced.config) api.previewDns(debounced.config, debounced.hosts).then(setPreview);
  }, [debounced]);

  if (!config) return <p>Loading...</p>;

  const updateConfig = (field: keyof DnsConfig, value: string | string[] | boolean) => {
    setConfig({ ...config, [field]: value });
    setSaved(false);
  };

  const save = async () => {
    await api.updateDns(config);
    await api.updateHosts(hosts);
    setSaved(true);
  };

  const addHost = () => {
    if (newHost.ip && newHost.hostnames[0]) {
      setHosts([...hosts, { ...newHost }]);
      setNewHost({ ip: "", hostnames: [""] });
      setSaved(false);
    }
  };

  const removeHost = (idx: number) => {
    setHosts(hosts.filter((_, i) => i !== idx));
    setSaved(false);
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>DNS Configuration</h1>
      <Card title="DNS Settings">
        <FormField label="Local Domain">
          <input style={inputStyle} value={config.domain} onChange={(e) => updateConfig("domain", e.target.value)} />
        </FormField>
        <FormField label="Upstream Servers (comma-separated)">
          <input
            style={inputStyle}
            value={config.upstream_servers.join(", ")}
            onChange={(e) =>
              updateConfig("upstream_servers", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
            }
          />
        </FormField>
        <FormField label="Expand Hosts">
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={config.expand_hosts}
              onChange={(e) => updateConfig("expand_hosts", e.target.checked)}
            />
            Append domain to DHCP hostnames
          </label>
        </FormField>
      </Card>

      <Card title="Host Entries">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr>
              <th style={{ ...thStyle, width: 150 }}>IP Address</th>
              <th style={thStyle}>Hostnames</th>
              <th style={{ ...thStyle, width: 100, textAlign: "right" }}></th>
            </tr>
          </thead>
          <tbody>
            {hosts.map((entry, idx) => (
              <tr key={idx}>
                <td style={tdStyle}>{entry.ip}</td>
                <td style={tdStyle}><code>{entry.hostnames.join(", ")}</code></td>
                <td style={{ ...tdStyle, textAlign: "right" }}>
                  <button style={dangerBtn} onClick={() => removeHost(idx)}>Remove</button>
                </td>
              </tr>
            ))}
            <tr>
              <td style={tdStyle}>
                <input
                  style={inputStyle}
                  placeholder="192.168.0.100"
                  value={newHost.ip}
                  onChange={(e) => setNewHost({ ...newHost, ip: e.target.value })}
                />
              </td>
              <td style={tdStyle}>
                <input
                  style={inputStyle}
                  placeholder="host.example.com"
                  value={newHost.hostnames[0]}
                  onChange={(e) => setNewHost({ ...newHost, hostnames: [e.target.value] })}
                />
              </td>
              <td style={tdStyle}>
                <button style={{ ...btnStyle, padding: "4px 12px", fontSize: 13, background: "#00b894" }} onClick={addHost}>
                  Add
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </Card>

      <div style={{ marginBottom: 24 }}>
        <button style={btnStyle} onClick={save}>Save &amp; Apply</button>
        {saved && <span style={{ marginLeft: 12, color: "#00b894" }}>Saved</span>}
      </div>

      <Card title="Generated Configuration">
        <Preview label="dnsmasq DNS" path="/etc/dnsmasq.d/01-dns.conf" content={preview.dns} />
        <Preview label="dnsmasq hosts" path="/etc/dnsmasq.d/04-hosts.conf" content={preview.hosts} />
      </Card>
    </>
  );
}
