interface CardProps {
  title: string;
  children: React.ReactNode;
}

export default function Card({ title, children }: CardProps) {
  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 8,
        padding: 24,
        marginBottom: 20,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}
    >
      <h2 style={{ fontSize: 18, marginBottom: 16, color: "#2d3436" }}>{title}</h2>
      {children}
    </div>
  );
}
