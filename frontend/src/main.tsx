import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import Dashboard from "./pages/Dashboard";
import NewProject from "./pages/NewProject";
import ProjectPage from "./pages/ProjectPage";
import ExperimentDetail from "./pages/ExperimentDetail";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewProject />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/experiments/:experimentId" element={<ExperimentDetail />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
