import { proxyRequest } from "../../_proxy";

export async function GET(
  request: Request,
  context: { params: Promise<{ conversationId: string }> }
): Promise<Response> {
  const { conversationId } = await context.params;
  return proxyRequest(request, { path: `/api/conversations/${conversationId}` });
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ conversationId: string }> }
): Promise<Response> {
  const { conversationId } = await context.params;
  return proxyRequest(request, { path: `/api/conversations/${conversationId}` });
}
