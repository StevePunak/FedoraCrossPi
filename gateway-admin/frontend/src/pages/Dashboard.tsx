import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SystemInfo } from "../api/client";
import Card from "../components/Card";

export default function Dashboard() {
  const [info, setInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    api.getSystem().then(setInfo);
  }, []);

  if (!info) return <p>Loading...</p>;

  const items = [
    ["Hostname", info.hostname],
    ["IP Address", info.ip_address],
    ["Uptime", info.uptime],
    ["Kernel", info.kernel],
    ["Memory", `${info.memory_used} / ${info.memory_total}`],
    ["Disk", `${info.disk_used} / ${info.disk_total}`],
  ];

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Dashboard</h1>
      <Card title="System Information">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <tbody>
            {items.map(([label, value]) => (
              <tr key={label}>
                <td style={{ padding: "8px 16px 8px 0", fontWeight: 600, color: "#636e72", width: 160 }}>
                  {label}
                </td>
                <td style={{ padding: "8px 0" }}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
