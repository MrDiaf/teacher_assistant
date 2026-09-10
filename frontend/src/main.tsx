import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./platform/styles.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
