import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { NasConfig, NasMount, NasMountStatus, NasTestResult } from "../api/client";
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

const smallBtn: React.CSSProperties = {
  ...btnStyle,
  padding: "4px 12px",
  fontSize: 13,
};

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;

function newMount(): NasMount {
  return {
    id: "",
    server: "",
    share: "",
    username: "",
    password: "",
    extra_options: "",
    enabled: true,
  };
}

function statusBadge(s: NasMountStatus): { label: string; color: string } {
  if (!s.enabled) return { label: "disabled", color: "#b2bec3" };
  if (s.mounted) return { label: "mounted", color: "#00b894" };
  if (s.automount_active) return { label: "idle (automount armed)", color: "#fdcb6e" };
  return { label: "not mounted", color: "#d63031" };
}

export default function NAS() {
  const [config, setConfig] = useState<NasConfig | null>(null);
  const [statuses, setStatuses] = useState<NasMountStatus[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [testResults, setTestResults] = useState<Record<string, NasTestResult>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [preview, setPreview] = useState<Record<string, string>>({});

  const debounced = useDebounced(config);

  useEffect(() => {
    api.getNas().then(setConfig);
    api.getNasStatus().then(setStatuses).catch(() => setStatuses([]));
  }, []);

  useEffect(() => {
    if (!debounced) return;
    api.previewNas(debounced).then(setPreview).catch(() => setPreview({}));
  }, [debounced]);

  if (!config) return <p>Loading...</p>;

  const updateMount = (idx: number, patch: Partial<NasMount>) => {
    const next = [...config.mounts];
    next[idx] = { ...next[idx], ...patch };
    setConfig({ ...config, mounts: next });
    setSaved(false);
    setError("");
    // Stale test result for this row no longer applies once the user edits.
    const oldKey = config.mounts[idx].id || `__row${idx}`;
    if (testResults[oldKey]) {
      const { [oldKey]: _, ...rest } = testResults;
      setTestResults(rest);
    }
  };

  const removeMount = (idx: number) => {
    setConfig({ ...config, mounts: config.mounts.filter((_, i) => i !== idx) });
    setSaved(false);
  };

  const addMount = () => {
    setConfig({ ...config, mounts: [...config.mounts, newMount()] });
    setSaved(false);
  };

  const validate = (): string => {
    const ids = new Set<string>();
    for (const m of config.mounts) {
      if (!SLUG_RE.test(m.id)) {
        return `mount id "${m.id || "(empty)"}" is invalid (lowercase, digits, hyphen; alphanumeric ends)`;
      }
      if (ids.has(m.id)) return `duplicate mount id: ${m.id}`;
      ids.add(m.id);
      if (!m.server.trim()) return `mount "${m.id}" needs a server`;
      if (!m.share.trim()) return `mount "${m.id}" needs a share name`;
    }
    return "";
  };

  const save = async () => {
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    try {
      await api.updateNas(config);
      setSaved(true);
      setError("");
      api.getNasStatus().then(setStatuses).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const refreshStatus = () => {
    api.getNasStatus().then(setStatuses).catch(() => {});
  };

  const validateMount = (m: NasMount): string => {
    if (!SLUG_RE.test(m.id)) {
      return "id must be lowercase letters, digits, hyphens (alphanumeric at ends)";
    }
    if (!m.server.trim()) return "server is required";
    if (!m.share.trim()) return "share is required";
    return "";
  };

  const testMount = async (idx: number) => {
    const m = config.mounts[idx];
    const key = m.id || `__row${idx}`;
    const fieldErr = validateMount(m);
    if (fieldErr) {
      setTestResults({ ...testResults, [key]: { ok: false, message: fieldErr } });
      return;
    }
    setTesting({ ...testing, [key]: true });
    try {
      const result = await api.testNas(m);
      setTestResults({ ...testResults, [key]: result });
    } catch (e) {
      setTestResults({
        ...testResults,
        [key]: { ok: false, message: e instanceof Error ? e.message : String(e) },
      });
    } finally {
      setTesting({ ...testing, [key]: false });
    }
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>NAS Mounts</h1>

      <Card title="Status">
        {statuses.length === 0 && (
          <p style={{ color: "#636e72", margin: 0 }}>No mounts configured.</p>
        )}
        {statuses.length > 0 && (
          <div style={tableWrapperStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>ID</th>
                <th style={thStyle}>Path</th>
                <th style={thStyle}>State</th>
                <th style={thStyle}>Last Error</th>
              </tr>
            </thead>
            <tbody>
              {statuses.map((s) => {
                const badge = statusBadge(s);
                return (
                  <tr key={s.id}>
                    <td style={tdStyle}><code>{s.id}</code></td>
                    <td style={tdStyle}><code>{s.mount_path}</code></td>
                    <td style={tdStyle}>
                      <span style={{ color: badge.color, fontWeight: 600 }}>{badge.label}</span>
                    </td>
                    <td style={{ ...tdStyle, color: "#d63031", fontSize: 12 }}>
                      {s.last_error}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          <button style={smallBtn} onClick={refreshStatus}>Refresh</button>
        </div>
      </Card>

      {config.mounts.map((mount, idx) => {
        const key = mount.id || `__row${idx}`;
        const result = testResults[key];
        const isTesting = testing[key];
        return (
          <Card key={idx} title={`Mount ${idx + 1}${mount.id ? `: ${mount.id}` : ""}`}>
            <div style={formGridStyle}>
              <FormField label="ID (slug)">
                <input
                  style={inputStyle}
                  placeholder="music"
                  value={mount.id}
                  onChange={(e) => updateMount(idx, { id: e.target.value })}
                />
                <small style={{ color: "#636e72" }}>
                  Mount path will be <code>/mnt/{mount.id || "<id>"}</code>
                </small>
              </FormField>
              <FormField label="Enabled">
                <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={mount.enabled}
                    onChange={(e) => updateMount(idx, { enabled: e.target.checked })}
                  />
                  Mount on boot (automount on first access)
                </label>
              </FormField>
              <FormField label="Server (host or IP)">
                <input
                  style={inputStyle}
                  placeholder="media-02"
                  value={mount.server}
                  onChange={(e) => updateMount(idx, { server: e.target.value })}
                />
              </FormField>
              <FormField label="Share">
                <input
                  style={inputStyle}
                  placeholder="Curated Music"
                  value={mount.share}
                  onChange={(e) => updateMount(idx, { share: e.target.value })}
                />
              </FormField>
              <FormField label="Username (blank = guest)">
                <input
                  style={inputStyle}
                  value={mount.username}
                  onChange={(e) => updateMount(idx, { username: e.target.value })}
                />
              </FormField>
              <FormField label="Password">
                <input
                  type="password"
                  style={inputStyle}
                  value={mount.password}
                  onChange={(e) => updateMount(idx, { password: e.target.value })}
                />
              </FormField>
              <FormField label="Extra mount options (optional)">
                <input
                  style={inputStyle}
                  placeholder="uid=1000,gid=1000"
                  value={mount.extra_options}
                  onChange={(e) => updateMount(idx, { extra_options: e.target.value })}
                />
                <small style={{ color: "#636e72" }}>
                  Defaults: <code>vers=3.0,iocharset=utf8,nofail,_netdev,noperm</code>
                </small>
              </FormField>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
              <button style={smallBtn} onClick={() => testMount(idx)} disabled={isTesting}>
                {isTesting ? "Testing..." : "Test mount"}
              </button>
              <button style={dangerBtn} onClick={() => removeMount(idx)}>Remove</button>
              {result && (
                <span style={{
                  fontSize: 13,
                  color: result.ok ? "#00b894" : "#d63031",
                  fontFamily: "ui-monospace, monospace",
                }}>
                  {result.ok ? "✓" : "✗"} {result.message}
                </span>
              )}
            </div>
          </Card>
        );
      })}

      <div style={{ marginBottom: 24, display: "flex", gap: 8, alignItems: "center" }}>
        <button style={btnStyle} onClick={addMount}>Add mount</button>
        <button style={btnStyle} onClick={save}>Save &amp; Apply</button>
        {saved && <span style={{ color: "#00b894" }}>Saved</span>}
        {error && <span style={{ color: "#d63031" }}>{error}</span>}
      </div>

      {Object.keys(preview).length > 0 && (
        <Card title="Generated systemd units">
          {Object.entries(preview).map(([name, content]) => (
            <Preview
              key={name}
              label={name}
              path={`/etc/systemd/system/${name}`}
              content={content}
            />
          ))}
        </Card>
      )}
    </>
  );
}

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

const tableStyle: React.CSSProperties = {
  width: "100%",
  // Floor so the Last Error column isn't crushed off-screen on a phone-width card.
  minWidth: 520,
  borderCollapse: "collapse",
  fontSize: 14,
};

const tableWrapperStyle: React.CSSProperties = {
  overflowX: "auto",
};

// Two-up form grid that collapses to one column on narrow viewports without
// needing a JS isMobile flag — auto-fit drops the second column whenever
// 2×280 + gap won't fit.
const formGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: 14,
};
