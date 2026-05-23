import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Apps from "./pages/Apps";
import Backup from "./pages/Backup";
import Bootstrap from "./pages/Bootstrap";
import DHCP from "./pages/DHCP";
import DNS from "./pages/DNS";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import NAS from "./pages/NAS";
import Network from "./pages/Network";
import Services from "./pages/Services";

function Gate({ children }: { children: React.ReactNode }) {
  const { status, loading } = useAuth();

  if (loading) {
    return <div style={{ padding: 40, color: "#636e72" }}>Loading…</div>;
  }
  if (!status) {
    return <div style={{ padding: 40, color: "#d63031" }}>Cannot reach API.</div>;
  }
  if (status.bootstrap) {
    return <Navigate to="/setup" replace />;
  }
  if (!status.authenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { status, loading } = useAuth();
  if (loading) return null;
  if (status?.authenticated && !status.bootstrap) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/setup" element={<PublicOnly><Bootstrap /></PublicOnly>} />
        <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
        <Route element={<Gate><Layout /></Gate>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/network" element={<Network />} />
          <Route path="/dhcp" element={<DHCP />} />
          <Route path="/dns" element={<DNS />} />
          <Route path="/services" element={<Services />} />
          <Route path="/apps" element={<Apps />} />
          <Route path="/nas" element={<NAS />} />
          <Route path="/backup" element={<Backup />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
