const DEFAULT_BACKEND_BASE_URL = "http://localhost:8000";

type ProxyOptions = {
  path: string;
};

export async function proxyRequest(request: Request, options: ProxyOptions): Promise<Response> {
  const backendBaseUrl = process.env.BACKEND_BASE_URL ?? DEFAULT_BACKEND_BASE_URL;
  const requestUrl = new URL(request.url);
  const targetUrl = new URL(options.path, backendBaseUrl);

  targetUrl.search = requestUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const response = await fetch(targetUrl, init);
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}
