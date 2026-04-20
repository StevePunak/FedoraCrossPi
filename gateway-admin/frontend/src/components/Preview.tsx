interface PreviewProps {
  label: string;
  content: string;
  path?: string;
}

export default function Preview({ label, content, path }: PreviewProps) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "#636e72",
          marginBottom: 4,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span>{label}</span>
        {path && <code style={{ color: "#b2bec3", fontWeight: 400 }}>{path}</code>}
      </div>
      <pre
        style={{
          background: "#2d3436",
          color: "#dfe6e9",
          padding: 14,
          borderRadius: 4,
          fontSize: 13,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          overflow: "auto",
          margin: 0,
          lineHeight: 1.5,
          whiteSpace: "pre-wrap",
        }}
      >
        {content || "# (empty)"}
      </pre>
    </div>
  );
}
