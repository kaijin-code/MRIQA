import { proxyRequest } from "../_proxy";

export async function POST(request: Request): Promise<Response> {
  return proxyRequest(request, { path: "/api/ingest" });
}
