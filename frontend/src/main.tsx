import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import ModuleHost from "./ModuleHost";
import "./platform/styles.css";
import "./styles.css";

const moduleHostId = import.meta.env.VITE_MODULE_HOST?.trim();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {moduleHostId ? <ModuleHost moduleId={moduleHostId} /> : <App />}
  </StrictMode>,
);
