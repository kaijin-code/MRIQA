import { proxyRequest } from "../../../../_proxy";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ conversationId: string; chunkId: string }> },
): Promise<Response> {
  const { conversationId, chunkId } = await params;
  return proxyRequest(request, {
    path: `/api/conversations/${conversationId}/citations/${chunkId}`,
  });
}
