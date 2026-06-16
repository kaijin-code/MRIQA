import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = ["/"];
const authPaths = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;

  const isProtected = protectedPaths.some((p) => path === p);
  const isAuthPage = authPaths.some((p) => path.startsWith(p));

  const hasAuth = request.cookies.get("auth_token_check")?.value;

  if (isProtected && !hasAuth) {
    return NextResponse.redirect(new URL("/login", request.nextUrl));
  }

  if (isAuthPage && hasAuth) {
    return NextResponse.redirect(new URL("/", request.nextUrl));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
