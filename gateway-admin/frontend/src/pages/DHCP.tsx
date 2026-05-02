import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { DhcpConfig, StaticLease } from "../api/client";
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

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 14,
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
  verticalAlign: "top",
};

const emptyLease: StaticLease = { mac: "", ip: "", hostname: "", comment: "", enabled: true };

export default function DHCP() {
  const [config, setConfig] = useState<DhcpConfig | null>(null);
  const [leases, setLeases] = useState<StaticLease[]>([]);
  const [saved, setSaved] = useState(false);
  const [newLease, setNewLease] = useState<StaticLease>({ ...emptyLease });
  const [preview, setPreview] = useState<{ dhcp: string; static_leases: string }>({ dhcp: "", static_leases: "" });

  const formState = useMemo(() => ({ config, leases }), [config, leases]);
  const debounced = useDebounced(formState);

  useEffect(() => {
    api.getDhcp().then(setConfig);
    api.getLeases().then(setLeases);
  }, []);

  useEffect(() => {
    if (debounced.config) api.previewDhcp(debounced.config, debounced.leases).then(setPreview);
  }, [debounced]);

  if (!config) return <p>Loading...</p>;

  const updateConfig = <K extends keyof DhcpConfig>(field: K, value: DhcpConfig[K]) => {
    setConfig({ ...config, [field]: value });
    setSaved(false);
  };

  const updateLease = (idx: number, field: keyof StaticLease, value: string | boolean) => {
    const next = [...leases];
    next[idx] = { ...next[idx], [field]: value };
    setLeases(next);
    setSaved(false);
  };

  const save = async () => {
    await api.updateDhcp(config);
    await api.updateLeases(leases);
    setSaved(true);
  };

  const addLease = () => {
    if (newLease.mac && newLease.ip && newLease.hostname) {
      setLeases([...leases, { ...newLease }]);
      setNewLease({ ...emptyLease });
      setSaved(false);
    }
  };

  const removeLease = (idx: number) => {
    setLeases(leases.filter((_, i) => i !== idx));
    setSaved(false);
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>DHCP Configuration</h1>

      <Card title="DHCP Server">
        <FormField label="Enabled">
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={config.enabled} onChange={(e) => updateConfig("enabled", e.target.checked)} />
            {config.enabled ? "Active" : "Disabled"}
          </label>
        </FormField>
        <FormField label="Authoritative">
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={config.authoritative} onChange={(e) => updateConfig("authoritative", e.target.checked)} />
            Respond to requests for unknown clients
          </label>
        </FormField>
      </Card>

      <Card title="Address Pool">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <FormField label="Range Start">
            <input style={inputStyle} value={config.range_start} onChange={(e) => updateConfig("range_start", e.target.value)} />
          </FormField>
          <FormField label="Range End">
            <input style={inputStyle} value={config.range_end} onChange={(e) => updateConfig("range_end", e.target.value)} />
          </FormField>
          <FormField label="Netmask">
            <input style={inputStyle} value={config.netmask} onChange={(e) => updateConfig("netmask", e.target.value)} />
          </FormField>
          <FormField label="Lease Time">
            <input style={inputStyle} value={config.lease_time} onChange={(e) => updateConfig("lease_time", e.target.value)} />
          </FormField>
        </div>
      </Card>

      <Card title="DHCP Options Advertised to Clients">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <FormField label="Router (Gateway)">
            <input style={inputStyle} value={config.router} onChange={(e) => updateConfig("router", e.target.value)} />
          </FormField>
          <FormField label="DNS Servers (comma-separated; first is primary)">
            <input
              style={inputStyle}
              value={config.dns_servers.join(", ")}
              onChange={(e) => updateConfig("dns_servers", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
            />
          </FormField>
          <FormField label="Domain Name">
            <input style={inputStyle} value={config.domain} onChange={(e) => updateConfig("domain", e.target.value)} />
          </FormField>
          <FormField label="Domain Search (comma-separated)">
            <input
              style={inputStyle}
              value={config.domain_search.join(", ")}
              onChange={(e) => updateConfig("domain_search", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
            />
          </FormField>
          <FormField label="NTP Servers (comma-separated)">
            <input
              style={inputStyle}
              value={config.ntp_servers.join(", ")}
              onChange={(e) => updateConfig("ntp_servers", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
            />
          </FormField>
          <FormField label="MTU">
            <input
              style={inputStyle}
              type="number"
              value={config.mtu ?? ""}
              onChange={(e) => updateConfig("mtu", e.target.value ? parseInt(e.target.value, 10) : null)}
              placeholder="1500"
            />
          </FormField>
        </div>
      </Card>

      <Card title="PXE / Network Boot (optional)">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <FormField label="TFTP Server">
            <input style={inputStyle} value={config.tftp_server} onChange={(e) => updateConfig("tftp_server", e.target.value)} placeholder="192.168.0.51" />
          </FormField>
          <FormField label="Boot Filename">
            <input style={inputStyle} value={config.boot_filename} onChange={(e) => updateConfig("boot_filename", e.target.value)} placeholder="pxelinux.0" />
          </FormField>
        </div>
      </Card>

      <Card title="Static Leases">
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={{ ...thStyle, width: 60 }}>On</th>
              <th style={thStyle}>MAC Address</th>
              <th style={thStyle}>IP Address</th>
              <th style={thStyle}>Hostname</th>
              <th style={thStyle}>Comment</th>
              <th style={{ ...thStyle, width: 100, textAlign: "right" }}></th>
            </tr>
          </thead>
          <tbody>
            {leases.map((lease, idx) => (
              <tr key={idx} style={{ opacity: lease.enabled ? 1 : 0.5 }}>
                <td style={tdStyle}>
                  <input
                    type="checkbox"
                    checked={lease.enabled}
                    onChange={(e) => updateLease(idx, "enabled", e.target.checked)}
                  />
                </td>
                <td style={tdStyle}>
                  <input style={inputStyle} value={lease.mac} onChange={(e) => updateLease(idx, "mac", e.target.value)} />
                </td>
                <td style={tdStyle}>
                  <input style={inputStyle} value={lease.ip} onChange={(e) => updateLease(idx, "ip", e.target.value)} />
                </td>
                <td style={tdStyle}>
                  <input style={inputStyle} value={lease.hostname} onChange={(e) => updateLease(idx, "hostname", e.target.value)} />
                </td>
                <td style={tdStyle}>
                  <input style={inputStyle} value={lease.comment} onChange={(e) => updateLease(idx, "comment", e.target.value)} placeholder="optional" />
                </td>
                <td style={{ ...tdStyle, textAlign: "right" }}>
                  <button style={dangerBtn} onClick={() => removeLease(idx)}>Remove</button>
                </td>
              </tr>
            ))}
            <tr style={{ background: "#f5f6fa" }}>
              <td style={tdStyle}>
                <input
                  type="checkbox"
                  checked={newLease.enabled}
                  onChange={(e) => setNewLease({ ...newLease, enabled: e.target.checked })}
                />
              </td>
              <td style={tdStyle}>
                <input style={inputStyle} placeholder="AA:BB:CC:DD:EE:FF" value={newLease.mac} onChange={(e) => setNewLease({ ...newLease, mac: e.target.value })} />
              </td>
              <td style={tdStyle}>
                <input style={inputStyle} placeholder="192.168.0.100" value={newLease.ip} onChange={(e) => setNewLease({ ...newLease, ip: e.target.value })} />
              </td>
              <td style={tdStyle}>
                <input style={inputStyle} placeholder="hostname" value={newLease.hostname} onChange={(e) => setNewLease({ ...newLease, hostname: e.target.value })} />
              </td>
              <td style={tdStyle}>
                <input style={inputStyle} placeholder="optional" value={newLease.comment} onChange={(e) => setNewLease({ ...newLease, comment: e.target.value })} />
              </td>
              <td style={tdStyle}>
                <button style={{ ...btnStyle, padding: "4px 12px", fontSize: 13, background: "#00b894" }} onClick={addLease}>
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
        <Preview label="dnsmasq DHCP" path="/etc/dnsmasq.d/02-dhcp.conf" content={preview.dhcp} />
        <Preview label="dnsmasq static leases" path="/etc/dnsmasq.d/03-static-leases.conf" content={preview.static_leases} />
      </Card>
    </>
  );
}
