import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ServiceStatus } from "../api/client";
import Card from "../components/Card";

const btnStyle: React.CSSProperties = {
  padding: "4px 14px",
  border: "none",
  borderRadius: 4,
  fontSize: 13,
  cursor: "pointer",
  marginRight: 6,
};

export default function Services() {
  const [services, setServices] = useState<ServiceStatus[]>([]);

  const refresh = () => api.getServices().then(setServices);

  useEffect(() => {
    refresh();
  }, []);

  const control = async (name: string, action: string) => {
    await api.controlService(name, action);
    refresh();
  };

  return (
    <>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Services</h1>
      <Card title="Managed Services">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr>
              {["Service", "Status", "Enabled", "Actions"].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: "8px 12px",
                    borderBottom: "2px solid #dfe6e9",
                    color: "#636e72",
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {services.map((svc) => (
              <tr key={svc.name}>
                <td style={{ padding: "10px 12px", borderBottom: "1px solid #f0f0f0", fontWeight: 500 }}>
                  {svc.name}
                </td>
                <td style={{ padding: "10px 12px", borderBottom: "1px solid #f0f0f0" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 10px",
                      borderRadius: 12,
                      fontSize: 12,
                      fontWeight: 600,
                      background: svc.active ? "#00b89422" : "#d6303122",
                      color: svc.active ? "#00b894" : "#d63031",
                    }}
                  >
                    {svc.status}
                  </span>
                </td>
                <td style={{ padding: "10px 12px", borderBottom: "1px solid #f0f0f0" }}>
                  {svc.enabled ? "yes" : "no"}
                </td>
                <td style={{ padding: "10px 12px", borderBottom: "1px solid #f0f0f0" }}>
                  {svc.active ? (
                    <>
                      <button style={{ ...btnStyle, background: "#d63031", color: "#fff" }} onClick={() => control(svc.name, "stop")}>
                        Stop
                      </button>
                      <button style={{ ...btnStyle, background: "#fdcb6e", color: "#2d3436" }} onClick={() => control(svc.name, "restart")}>
                        Restart
                      </button>
                    </>
                  ) : (
                    <button style={{ ...btnStyle, background: "#00b894", color: "#fff" }} onClick={() => control(svc.name, "start")}>
                      Start
                    </button>
                  )}
                  {svc.enabled ? (
                    <button style={{ ...btnStyle, background: "#636e72", color: "#fff" }} onClick={() => control(svc.name, "disable")}>
                      Disable
                    </button>
                  ) : (
                    <button style={{ ...btnStyle, background: "#0984e3", color: "#fff" }} onClick={() => control(svc.name, "enable")}>
                      Enable
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
