import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { recarregarQuandoAVersaoNovaAssumir } from "./dados/novaVersao";
import { iniciarSessao } from "./login";
import "./estilo.css";

void iniciarSessao();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  recarregarQuandoAVersaoNovaAssumir(navigator.serviceWorker);
  void navigator.serviceWorker.register("/service-worker.js");
}
