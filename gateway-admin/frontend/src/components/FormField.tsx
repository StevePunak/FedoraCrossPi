interface FormFieldProps {
  label: string;
  children: React.ReactNode;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 12px",
  border: "1px solid #dfe6e9",
  borderRadius: 4,
  fontSize: 14,
  fontFamily: "inherit",
};

export { inputStyle };

export default function FormField({ label, children }: FormFieldProps) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4, color: "#636e72" }}>
        {label}
      </label>
      {children}
    </div>
  );
}
