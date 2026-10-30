import createClient from "openapi-fetch";
import { tokenDeAcesso, tokenRecusado } from "../login";
import { fetchComTempoLimite } from "../dados/rede";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "", // Só o pedido: o segundo argumento do openapi-fetch não interessa.
  fetch: (request) => fetchComTempoLimite(request) });

// Toda chamada leva o token de acesso da sessão; a API só confere o JWT.
api.use({
  async onRequest({ request }) {
    const token = await tokenDeAcesso();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ request, response }) {
    const token = request.headers.get("Authorization")?.replace(/^Bearer /, "");
    if (response.status === 401 && token) tokenRecusado(token);
    return response;
  },
});
