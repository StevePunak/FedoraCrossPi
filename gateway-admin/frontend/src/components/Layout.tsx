import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/network", label: "Network" },
  { to: "/dhcp", label: "DHCP" },
  { to: "/dns", label: "DNS" },
  { to: "/services", label: "Services" },
  { to: "/apps", label: "Apps" },
  { to: "/backup", label: "Backup" },
];

const navStyle: React.CSSProperties = {
  width: 220,
  background: "#2d3436",
  color: "#dfe6e9",
  minHeight: "100vh",
  padding: "24px 0",
  display: "flex",
  flexDirection: "column",
};

const linkStyle: React.CSSProperties = {
  display: "block",
  padding: "10px 24px",
  fontSize: 15,
  transition: "background 0.15s",
};

const activeStyle: React.CSSProperties = {
  ...linkStyle,
  background: "#636e72",
  color: "#fff",
  fontWeight: 600,
};

const logoutBtnStyle: React.CSSProperties = {
  margin: "16px 24px 0",
  padding: "8px 12px",
  background: "transparent",
  border: "1px solid #636e72",
  color: "#dfe6e9",
  borderRadius: 4,
  fontSize: 13,
  cursor: "pointer",
};

export default function Layout() {
  const { status, logout } = useAuth();

  return (
    <div style={{ display: "flex" }}>
      <nav style={navStyle}>
        <div style={{ padding: "0 24px 24px", fontSize: 20, fontWeight: 700, color: "#fff" }}>
          Gateway
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            style={({ isActive }) => (isActive ? activeStyle : linkStyle)}
          >
            {item.label}
          </NavLink>
        ))}
        <div style={{ flex: 1 }} />
        {status?.username && (
          <div style={{ padding: "0 24px", fontSize: 13, color: "#b2bec3" }}>
            Signed in as <strong style={{ color: "#dfe6e9" }}>{status.username}</strong>
          </div>
        )}
        {!status?.dev_bypass && (
          <button style={logoutBtnStyle} onClick={logout}>
            Sign Out
          </button>
        )}
        <div style={{ height: 24 }} />
      </nav>
      <main style={{ flex: 1, padding: 32 }}>
        <Outlet />
      </main>
    </div>
  );
}
