import { proxyRequest } from "../../_proxy";

export async function GET(request: Request): Promise<Response> {
  return proxyRequest(request, { path: "/api/auth/me" });
}
