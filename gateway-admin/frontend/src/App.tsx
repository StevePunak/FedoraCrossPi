import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Network from "./pages/Network";
import DHCP from "./pages/DHCP";
import DNS from "./pages/DNS";
import Services from "./pages/Services";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/network" element={<Network />} />
        <Route path="/dhcp" element={<DHCP />} />
        <Route path="/dns" element={<DNS />} />
        <Route path="/services" element={<Services />} />
      </Route>
    </Routes>
  );
}
