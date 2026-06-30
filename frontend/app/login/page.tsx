"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function sha256Hex(value: string): Promise<string> {
    const buf = new TextEncoder().encode(value);
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const passwordDigest = await sha256Hex(password);
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password: passwordDigest }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? "Login failed");
      }

      const data = await res.json();
      login(data.access_token, data.user);
      window.location.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#efe6d8_0,_#f6f1e8_45%,_#f9f7f2_100%)]">
      <div className="w-full max-w-sm rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-8 shadow-[var(--shadow)]">
        <h1 className="text-center text-2xl font-semibold text-[var(--foreground)]">
          Login
        </h1>
        <p className="mt-1 text-center text-sm text-[var(--muted)]">
          Enter your credentials to continue
        </p>

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="text-sm text-[var(--muted)]">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="mt-1 w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label className="text-sm text-[var(--muted)]">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full rounded-full py-2.5 text-sm font-medium text-white transition ${
              isSubmitting ? "bg-slate-300" : "bg-[var(--accent)] hover:bg-[var(--accent-strong)]"
            }`}
          >
            {isSubmitting ? "Logging in..." : "Login"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-[var(--muted)]">
          No account?{" "}
          <Link href="/register" className="font-medium text-[var(--accent)] hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
