import { proxyRequest } from "../../../_proxy";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params;
  return proxyRequest(request, { path: `/api/documents/${id}/download` });
}
