import { proxyRequest } from "../../_proxy";

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ messageId: string }> }
): Promise<Response> {
  const { messageId } = await params;
  return proxyRequest(request, { path: `/api/messages/${messageId}` });
}
