import { useRef, useState } from "react";
import { api } from "../api/client";
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

const dangerBtn: React.CSSProperties = {
  ...btnStyle,
  background: "#d63031",
};

export default function Backup() {
  // Download form state
  const [includeSecrets, setIncludeSecrets] = useState(true);
  const [downloadPassphrase, setDownloadPassphrase] = useState("");
  const [downloadConfirm, setDownloadConfirm] = useState("");
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  // Restore form state
  const fileRef = useRef<HTMLInputElement>(null);
  const [restorePassphrase, setRestorePassphrase] = useState("");
  const [restoreBusy, setRestoreBusy] = useState(false);
  const [restoreMessage, setRestoreMessage] = useState("");
  const [restoreError, setRestoreError] = useState("");

  const downloadFile = async () => {
    setDownloadError("");
    if (downloadPassphrase && downloadPassphrase !== downloadConfirm) {
      setDownloadError("Passphrases do not match.");
      return;
    }
    setDownloadBusy(true);
    try {
      const blob = await api.downloadBackup(includeSecrets, downloadPassphrase);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const ext = downloadPassphrase ? "tar.gz.enc" : "tar.gz";
      a.download = `gateway-backup-${stamp}.${ext}`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "download failed";
      setDownloadError(msg);
      alert(`Download failed: ${msg}`);
    } finally {
      setDownloadBusy(false);
    }
  };

  const restoreFile = async () => {
    setRestoreError("");
    setRestoreMessage("");
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setRestoreError("Choose a backup file first.");
      return;
    }
    if (!confirm(`Restore from ${file.name}? This will overwrite current configuration.`)) {
      return;
    }
    setRestoreBusy(true);
    try {
      const result = await api.restoreBackup(file, restorePassphrase);
      setRestoreMessage(`Restored ${result.restored} files. Configuration reapplied.`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "restore failed";
      setRestoreError(msg);
      alert(`Restore failed: ${msg}`);
    } finally {
      setRestoreBusy(false);
    }
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Backup &amp; Restore</h1>

      <Card title="Download Backup">
        <p style={{ fontSize: 13, color: "#636e72", marginBottom: 16 }}>
          Downloads a tarball of all gateway configuration in <code>/data</code>.
        </p>
        <FormField label="Include secrets (admin password hash + TLS certificate)">
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={includeSecrets}
              onChange={(e) => setIncludeSecrets(e.target.checked)}
            />
            {includeSecrets
              ? "Yes — backup is sensitive, protect it like a password file"
              : "No — backup excludes auth.json and ssl/; recipient must set their own"}
          </label>
        </FormField>
        <FormField label="Passphrase (optional, for encryption)">
          <input
            style={inputStyle}
            type="password"
            value={downloadPassphrase}
            onChange={(e) => setDownloadPassphrase(e.target.value)}
            placeholder="leave blank for unencrypted"
            autoComplete="new-password"
          />
        </FormField>
        {downloadPassphrase && (
          <FormField label="Confirm Passphrase">
            <input
              style={inputStyle}
              type="password"
              value={downloadConfirm}
              onChange={(e) => setDownloadConfirm(e.target.value)}
              autoComplete="new-password"
            />
          </FormField>
        )}
        {downloadError && (
          <div style={{ color: "#d63031", fontSize: 13, marginBottom: 12 }}>{downloadError}</div>
        )}
        <button style={btnStyle} onClick={downloadFile} disabled={downloadBusy}>
          {downloadBusy ? "Building…" : "Download Backup"}
        </button>
      </Card>

      <Card title="Restore from Backup">
        <p style={{ fontSize: 13, color: "#636e72", marginBottom: 16 }}>
          Upload a previously-saved backup. <strong>Current configuration will be overwritten</strong> and
          services will reload automatically. If the backup contains a different IP, your session may drop.
        </p>
        <FormField label="Backup file">
          <input
            ref={fileRef}
            type="file"
            accept=".tar.gz,.tgz,.gz,.enc,application/gzip,application/octet-stream"
            style={{ fontSize: 14 }}
          />
        </FormField>
        <FormField label="Passphrase (only if backup is encrypted)">
          <input
            style={inputStyle}
            type="password"
            value={restorePassphrase}
            onChange={(e) => setRestorePassphrase(e.target.value)}
            autoComplete="off"
          />
        </FormField>
        {restoreError && (
          <div style={{ color: "#d63031", fontSize: 13, marginBottom: 12 }}>{restoreError}</div>
        )}
        {restoreMessage && (
          <div style={{ color: "#00b894", fontSize: 13, marginBottom: 12 }}>{restoreMessage}</div>
        )}
        <button style={dangerBtn} onClick={restoreFile} disabled={restoreBusy}>
          {restoreBusy ? "Restoring…" : "Restore"}
        </button>
      </Card>
    </>
  );
}
