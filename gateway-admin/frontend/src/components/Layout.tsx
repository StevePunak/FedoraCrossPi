import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useMediaQuery, MOBILE_QUERY } from "../hooks/useMediaQuery";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/network", label: "Network" },
  { to: "/dhcp", label: "DHCP" },
  { to: "/dns", label: "DNS" },
  { to: "/services", label: "Services" },
  { to: "/apps", label: "Apps" },
  { to: "/nas", label: "NAS" },
  { to: "/backup", label: "Backup" },
];

const HamburgerIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="3" y1="6" x2="21" y2="6" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);

const CloseIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="6" y1="6" x2="18" y2="18" />
    <line x1="18" y1="6" x2="6" y2="18" />
  </svg>
);

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
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Lock background scroll while the drawer is open on mobile.
  useEffect(() => {
    if (!isMobile) return;
    const orig = document.body.style.overflow;
    if (drawerOpen) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = orig;
    };
  }, [isMobile, drawerOpen]);

  // If the viewport crosses up into desktop range, force the drawer closed
  // so it doesn't strand state where the mobile UI is hidden.
  useEffect(() => {
    if (!isMobile && drawerOpen) setDrawerOpen(false);
  }, [isMobile, drawerOpen]);

  const navStyle: React.CSSProperties = {
    width: 220,
    background: "#2d3436",
    color: "#dfe6e9",
    padding: "24px 0",
    display: "flex",
    flexDirection: "column",
    overflowY: "auto",
    ...(isMobile
      ? {
          position: "fixed",
          top: 0,
          left: 0,
          height: "100vh",
          zIndex: 100,
          transform: drawerOpen ? "translateX(0)" : "translateX(-100%)",
          transition: "transform 200ms ease",
          boxShadow: drawerOpen ? "2px 0 12px rgba(0,0,0,0.4)" : undefined,
        }
      : {
          height: "100vh",
          position: "sticky",
          top: 0,
          alignSelf: "flex-start",
        }),
  };

  const headerBarStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "10px 14px",
    background: "#2d3436",
    color: "#fff",
    position: "sticky",
    top: 0,
    zIndex: 50,
  };

  const iconButtonStyle: React.CSSProperties = {
    background: "transparent",
    border: "none",
    color: "inherit",
    padding: 6,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  const backdropStyle: React.CSSProperties = {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.45)",
    zIndex: 90,
  };

  return (
    <div style={{ display: "flex", flexDirection: isMobile ? "column" : "row", minHeight: "100vh" }}>
      {isMobile && (
        <header style={headerBarStyle}>
          <button
            aria-label="Open menu"
            onClick={() => setDrawerOpen(true)}
            style={iconButtonStyle}
          >
            <HamburgerIcon />
          </button>
          <span style={{ fontSize: 18, fontWeight: 700 }}>Gateway</span>
        </header>
      )}

      {isMobile && drawerOpen && (
        <div aria-hidden onClick={() => setDrawerOpen(false)} style={backdropStyle} />
      )}

      <nav style={navStyle} aria-hidden={isMobile && !drawerOpen}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 24px 24px",
            fontSize: 20,
            fontWeight: 700,
            color: "#fff",
          }}
        >
          <span>Gateway</span>
          {isMobile && (
            <button
              aria-label="Close menu"
              onClick={() => setDrawerOpen(false)}
              style={{ ...iconButtonStyle, color: "#dfe6e9" }}
            >
              <CloseIcon />
            </button>
          )}
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={() => isMobile && setDrawerOpen(false)}
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

      <main style={{ flex: 1, padding: isMobile ? 16 : 32, minWidth: 0 }}>
        <Outlet />
      </main>
    </div>
  );
}
