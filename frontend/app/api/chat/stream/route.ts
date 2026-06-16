export const dynamic = "force-dynamic";

const DEFAULT_BACKEND_BASE_URL = "http://localhost:8000";

export async function POST(request: Request): Promise<Response> {
  const backendBaseUrl = process.env.BACKEND_BASE_URL ?? DEFAULT_BACKEND_BASE_URL;
  const targetUrl = new URL("/api/chat/stream", backendBaseUrl);

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const response = await fetch(targetUrl, {
    method: "POST",
    headers,
    body: await request.arrayBuffer(),
    cache: "no-store",
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}
