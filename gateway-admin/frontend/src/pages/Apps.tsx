import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AppConfigField, AppManifest, InstalledApp } from "../api/client";
import Card from "../components/Card";
import FormField, { inputStyle } from "../components/FormField";

const btnStyle: React.CSSProperties = {
  padding: "8px 20px",
  background: "#0984e3",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  fontSize: 14,
  cursor: "pointer",
};

const smallBtn: React.CSSProperties = {
  ...btnStyle,
  padding: "4px 12px",
  fontSize: 13,
  background: "#636e72",
};

const dangerBtn: React.CSSProperties = {
  ...smallBtn,
  background: "#d63031",
};

const successBg = "#00b894";
const partialBg = "#fdcb6e";
const inactiveBg = "#636e72";

type ConfigValues = Record<string, string | number | boolean | null>;

export default function Apps() {
  const [apps, setApps] = useState<InstalledApp[]>([]);
  const [statuses, setStatuses] = useState<Record<string, Record<string, string>>>({});
  const [refreshKey, setRefreshKey] = useState(0);

  // Per-app edit state
  const [editing, setEditing] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<ConfigValues>({});

  // Install flow state
  const [installFile, setInstallFile] = useState<File | null>(null);
  const [installManifest, setInstallManifest] = useState<AppManifest | null>(null);
  const [installValues, setInstallValues] = useState<ConfigValues>({});
  const [installError, setInstallError] = useState("");
  const [installBusy, setInstallBusy] = useState(false);

  useEffect(() => {
    api.listApps().then(setApps).catch(() => setApps([]));
  }, [refreshKey]);

  useEffect(() => {
    apps.forEach((app) => {
      api.getAppStatus(app.id)
        .then((s) => setStatuses((prev) => ({ ...prev, [app.id]: s })))
        .catch(() => { /* ignore */ });
    });
  }, [apps]);

  const onFileSelected = async (file: File) => {
    setInstallFile(file);
    setInstallError("");
    setInstallManifest(null);
    try {
      const manifest = await api.preflightApp(file);
      setInstallManifest(manifest);
      const defaults: ConfigValues = {};
      manifest.config.forEach((f) => {
        if (f.default !== null && f.default !== undefined) defaults[f.key] = f.default as string | number | boolean;
      });
      setInstallValues(defaults);
    } catch (e) {
      setInstallError(e instanceof Error ? e.message : String(e));
    }
  };

  const performInstall = async () => {
    if (!installFile || !installManifest) return;
    setInstallBusy(true);
    setInstallError("");
    try {
      await api.installApp(installFile, installValues);
      setInstallFile(null);
      setInstallManifest(null);
      setInstallValues({});
      setRefreshKey((k) => k + 1);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setInstallError(msg);
      alert(`Install failed: ${msg}`);
    } finally {
      setInstallBusy(false);
    }
  };

  const performUninstall = async (id: string) => {
    if (!confirm(`Uninstall ${id}? This removes everything under /data/apps/${id}/ — back up first if you care.`)) return;
    try {
      await api.uninstallApp(id);
      setRefreshKey((k) => k + 1);
    } catch (e) {
      alert(`Uninstall failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const performControl = async (id: string, action: "start" | "stop" | "restart") => {
    try {
      await api.controlApp(id, action);
      // Give systemd a moment, then refresh statuses.
      setTimeout(() => setRefreshKey((k) => k + 1), 500);
    } catch (e) {
      alert(`${action} failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const startEdit = (app: InstalledApp) => {
    setEditing(app.id);
    setEditValues({ ...app.config_values });
  };

  const saveEdit = async (id: string) => {
    try {
      await api.updateAppConfig(id, editValues);
      setEditing(null);
      setRefreshKey((k) => k + 1);
    } catch (e) {
      alert(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Apps</h1>

      <Card title="Installed Apps">
        {apps.length === 0 ? (
          <p style={{ color: "#636e72", fontSize: 13 }}>No apps installed.</p>
        ) : (
          apps.map((app) => (
            <AppRow
              key={app.id}
              app={app}
              statuses={statuses[app.id] || {}}
              isEditing={editing === app.id}
              editValues={editValues}
              onEditValueChange={(k, v) => setEditValues((prev) => ({ ...prev, [k]: v }))}
              onStartEdit={() => startEdit(app)}
              onCancelEdit={() => setEditing(null)}
              onSaveEdit={() => saveEdit(app.id)}
              onUninstall={() => performUninstall(app.id)}
              onControl={(action) => performControl(app.id, action)}
            />
          ))
        )}
      </Card>

      <Card title="Install App">
        <FormField label="App archive (.tar.gz)">
          <input
            type="file"
            accept=".tar.gz,.tgz,application/gzip,application/x-gzip"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFileSelected(f);
            }}
            style={{ fontSize: 14 }}
          />
        </FormField>
        {installError && (
          <div style={{ color: "#d63031", fontSize: 13, marginBottom: 12 }}>{installError}</div>
        )}
        {installManifest && (
          <>
            <div style={{ background: "#f5f6fa", padding: 12, borderRadius: 4, marginBottom: 16, fontSize: 13 }}>
              <strong>{installManifest.name}</strong>
              <span style={{ color: "#636e72" }}> v{installManifest.version} (id: {installManifest.id})</span>
              {installManifest.description && <div style={{ marginTop: 4 }}>{installManifest.description}</div>}
            </div>
            {installManifest.config.length > 0 && (
              <ConfigForm
                fields={installManifest.config}
                values={installValues}
                onChange={(k, v) => setInstallValues((prev) => ({ ...prev, [k]: v }))}
              />
            )}
            <button style={btnStyle} onClick={performInstall} disabled={installBusy}>
              {installBusy ? "Installing…" : `Install ${installManifest.name}`}
            </button>
          </>
        )}
      </Card>
    </>
  );
}

interface AppRowProps {
  app: InstalledApp;
  statuses: Record<string, string>;
  isEditing: boolean;
  editValues: ConfigValues;
  onEditValueChange: (key: string, value: string | number | boolean) => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onUninstall: () => void;
  onControl: (action: "start" | "stop" | "restart") => void;
}

function AppRow({
  app,
  statuses,
  isEditing,
  editValues,
  onEditValueChange,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onUninstall,
  onControl,
}: AppRowProps) {
  const svcStates = app.manifest.services.map((s) => statuses[s.name] || "unknown");
  const allActive = svcStates.length > 0 && svcStates.every((s) => s === "active");
  const anyActive = svcStates.some((s) => s === "active");
  const overall = allActive ? "ACTIVE" : anyActive ? "PARTIAL" : "INACTIVE";
  const badgeBg = allActive ? successBg : anyActive ? partialBg : inactiveBg;

  const webPath = app.manifest.web_ui?.path || `/apps/${app.id}/`;

  return (
    <div style={{ borderTop: "1px solid #f0f0f0", padding: "16px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 16 }}>{app.manifest.name}</strong>
        <span style={{ color: "#636e72", fontSize: 13 }}>v{app.version}</span>
        <span style={{
          padding: "2px 10px",
          borderRadius: 12,
          fontSize: 11,
          fontWeight: 600,
          background: badgeBg,
          color: "#fff",
          letterSpacing: 0.5,
        }}>{overall}</span>
        {app.manifest.web_ui && (
          <a
            href={webPath}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 13, color: "#0984e3", textDecoration: "underline" }}
          >
            Open ↗
          </a>
        )}
      </div>

      <div style={{ fontSize: 12, color: "#636e72", marginBottom: 12 }}>
        {app.manifest.services.map((s, i) => (
          <span key={s.name}>
            {i > 0 && " · "}
            <code>{s.name}</code>: {statuses[s.name] || "?"}
          </span>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <button style={smallBtn} onClick={() => onControl("start")}>Start</button>
        <button style={smallBtn} onClick={() => onControl("stop")}>Stop</button>
        <button style={smallBtn} onClick={() => onControl("restart")}>Restart</button>
        {!isEditing && app.manifest.config.length > 0 && (
          <button style={{ ...smallBtn, background: "#0984e3" }} onClick={onStartEdit}>
            Configure
          </button>
        )}
        <button style={dangerBtn} onClick={onUninstall}>Uninstall</button>
      </div>

      {isEditing && (
        <div style={{ background: "#f5f6fa", padding: 16, borderRadius: 4, marginTop: 8 }}>
          <ConfigForm
            fields={app.manifest.config}
            values={editValues}
            onChange={onEditValueChange}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btnStyle} onClick={onSaveEdit}>Save &amp; Restart</button>
            <button style={smallBtn} onClick={onCancelEdit}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

interface ConfigFormProps {
  fields: AppConfigField[];
  values: ConfigValues;
  onChange: (key: string, value: string | number | boolean) => void;
}

function ConfigForm({ fields, values, onChange }: ConfigFormProps) {
  return (
    <>
      {fields.map((f) => (
        <FormField key={f.key} label={f.label + (f.required ? " *" : "")}>
          <ConfigInput field={f} value={values[f.key]} onChange={(v) => onChange(f.key, v)} />
          {f.description && f.type !== "bool" && (
            <small style={{ color: "#636e72", display: "block", marginTop: 4, fontSize: 12 }}>
              {f.description}
            </small>
          )}
        </FormField>
      ))}
    </>
  );
}

interface ConfigInputProps {
  field: AppConfigField;
  value: string | number | boolean | null | undefined;
  onChange: (value: string | number | boolean) => void;
}

function ConfigInput({ field, value, onChange }: ConfigInputProps) {
  if (field.type === "bool") {
    return (
      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        {field.description || field.label}
      </label>
    );
  }
  if (field.type === "select") {
    return (
      <select
        style={inputStyle}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="" disabled>— choose —</option>
        {(field.choices || []).map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
    );
  }
  if (field.type === "int") {
    return (
      <input
        style={inputStyle}
        type="number"
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        value={value != null && value !== "" ? String(value) : ""}
        onChange={(e) => onChange(e.target.value === "" ? 0 : parseInt(e.target.value, 10))}
      />
    );
  }
  return (
    <input
      style={inputStyle}
      type={field.type === "password" ? "password" : "text"}
      value={value != null ? String(value) : ""}
      onChange={(e) => onChange(e.target.value)}
      autoComplete={field.type === "password" ? "new-password" : undefined}
    />
  );
}
