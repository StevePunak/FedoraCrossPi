import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/network", label: "Network" },
  { to: "/dhcp", label: "DHCP" },
  { to: "/dns", label: "DNS" },
  { to: "/services", label: "Services" },
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

export default function Layout() {
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
      </nav>
      <main style={{ flex: 1, padding: 32 }}>
        <Outlet />
      </main>
    </div>
  );
}
