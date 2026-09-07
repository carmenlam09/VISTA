import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { setActor, type Role } from "./api/client";
import { EntityDetailPage } from "./pages/EntityDetailPage";
import { EntityListPage } from "./pages/EntityListPage";

export function App() {
  const [role, setRole] = useState<Role>("reviewer");

  function onRoleChange(next: Role) {
    setRole(next);
    setActor(next === "admin" ? "demo-admin" : "demo-reviewer", next);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">
          <span className="app-brand">VISTA</span>
          <span className="app-subtitle">Screening Intelligence Hub</span>
        </div>
        <label className="role-switch">
          Viewing as
          <select value={role} onChange={(e) => onRoleChange(e.target.value as Role)}>
            <option value="reviewer">Reviewer</option>
            <option value="admin">Admin</option>
          </select>
        </label>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<EntityListPage />} />
          <Route path="/entities/:entityId" element={<EntityDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
