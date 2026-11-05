import { onRequestPost as __ms_chat_lead_js_onRequestPost } from "/home/corillo-adm/Proyectos/.ms-astro7/functions/ms-chat/lead.js"
import { onRequest as __ms_chat_lead_js_onRequest } from "/home/corillo-adm/Proyectos/.ms-astro7/functions/ms-chat/lead.js"

export const routes = [
    {
      routePath: "/ms-chat/lead",
      mountPath: "/ms-chat",
      method: "POST",
      middlewares: [],
      modules: [__ms_chat_lead_js_onRequestPost],
    },
  {
      routePath: "/ms-chat/lead",
      mountPath: "/ms-chat",
      method: "",
      middlewares: [],
      modules: [__ms_chat_lead_js_onRequest],
    },
  ]