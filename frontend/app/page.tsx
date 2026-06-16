"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/app/contexts/AuthContext";
import { authFetch } from "@/app/lib/api";

type RoleId = "user" | "customer_service" | "technical_support" | "product_manager";

type Citation = {
  document_id: string;
  chunk_id: string;
  source?: string | null;
  score: number;
};

type ConversationSummary = {
  id: string;
  title?: string | null;
  created_at: string;
  last_message_at?: string | null;
  message_count: number;
};

type ConversationHistory = {
  id: string;
  title?: string | null;
  created_at: string;
  messages: Array<{
    id: string;
    role: RoleId;
    content: string;
    sources?: Citation[] | null;
    created_at: string;
  }>;
};

type ChatMessage = {
  id: string;
  role: RoleId;
  content: string;
  citations?: Citation[];
  createdAt?: string;
};

const ROLE_LABELS: Record<Exclude<RoleId, "user">, string> = {
  customer_service: "客服",
  technical_support: "技术支持",
  product_manager: "产品经理",
};

const ROLE_STYLES: Record<Exclude<RoleId, "user">, string> = {
  customer_service: "bg-emerald-100 text-emerald-800",
  technical_support: "bg-amber-100 text-amber-900",
  product_manager: "bg-sky-100 text-sky-900",
};

function getRoleLabel(role: RoleId): string {
  if (role === "user") return "你";
  return ROLE_LABELS[role];
}

function getRoleStyle(role: RoleId): string {
  if (role === "user") return "bg-slate-900 text-white";
  return ROLE_STYLES[role];
}

function formatTime(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatScore(score?: number): string {
  if (typeof score !== "number") return "";
  const percent = Math.round(score * 1000) / 10;
  return `${percent}%`;
}

export default function Home() {
  const { user, logout, isLoading: isAuthLoading } = useAuth();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [openCitations, setOpenCitations] = useState<Record<string, boolean>>({});
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [hasReceivedToken, setHasReceivedToken] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const streamingRef = useRef<{
    currentRoleId: string | null;
    currentMsgId: string | null;
    accumulated: string;
  }>({ currentRoleId: null, currentMsgId: null, accumulated: "" });

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeId) ?? null,
    [conversations, activeId]
  );

  useEffect(() => {
    void loadConversations();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  useEffect(() => {
    if (!uploadMessage) return;
    const timer = setTimeout(() => setUploadMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [uploadMessage]);

  const canSend = draft.trim().length > 0 && !isSending;

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-[var(--muted)]">
        Loading...
      </div>
    );
  }

  async function loadConversations(): Promise<void> {
    setIsLoadingList(true);
    setListError(null);

    try {
      const response = await authFetch("/api/conversations?limit=50", {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("failed");
      }
      const data = (await response.json()) as { conversations: ConversationSummary[] };
      setConversations(data.conversations ?? []);
    } catch {
      setListError("会话列表加载失败，请稍后重试。");
    } finally {
      setIsLoadingList(false);
    }
  }

  async function loadConversation(conversationId: string): Promise<void> {
    setIsLoadingHistory(true);
    setChatError(null);

    try {
      const response = await authFetch(`/api/conversations/${conversationId}?limit=200`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("failed");
      }
      const data = (await response.json()) as ConversationHistory;
      const mapped = data.messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        citations: message.sources ?? undefined,
        createdAt: message.created_at,
      }));
      setMessages(mapped);
    } catch {
      setChatError("会话加载失败，请稍后重试。");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  function handleNewConversation(): void {
    setActiveId(null);
    setMessages([]);
    setChatError(null);
  }

  async function handleSelectConversation(conversationId: string): Promise<void> {
    setActiveId(conversationId);
    await loadConversation(conversationId);
  }

  async function handleDeleteConversation(conversationId: string): Promise<void> {
    if (!confirm("Delete this conversation? This action cannot be undone.")) return;

    setDeletingId(conversationId);
    try {
      const response = await authFetch(`/api/conversations/${conversationId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("failed");

      if (conversationId === activeId) {
        setActiveId(null);
        setMessages([]);
      }
      await loadConversations();
    } catch {
      setListError("Failed to delete conversation.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleUploadFiles(files: FileList | null): Promise<void> {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadMessage(null);

    try {
      const documents: Array<{ title: string; source: string; text: string }> = [];

      for (const file of Array.from(files)) {
        const text = await file.text();
        if (!text.trim()) continue;
        documents.push({ title: file.name, source: file.name, text: text.trim() });
      }

      if (documents.length === 0) {
        setUploadMessage({ type: "error", text: "所选文件为空或无法读取。" });
        return;
      }

      const response = await authFetch("/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ documents }),
      });

      if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(detail || `HTTP ${response.status}`);
      }

      const result = (await response.json()) as { documents: number; chunks: number };
      setUploadMessage({
        type: "success",
        text: `成功上传 ${result.documents} 个文档，生成 ${result.chunks} 个片段。`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      setUploadMessage({ type: "error", text: `上传失败: ${message}` });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleSend(): Promise<void> {
    if (!canSend) return;

    const content = draft.trim();
    const tempId = `local-user-${Date.now()}`;
    setDraft("");
    setChatError(null);
    setHasReceivedToken(false);
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: "user",
        content,
        createdAt: new Date().toISOString(),
      },
    ]);
    setIsSending(true);

    try {
      const response = await authFetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: activeId,
          message: content,
          metadata: null,
        }),
      });

      if (!response.ok) throw new Error("failed");
      if (!response.body) throw new Error("no body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr) as Record<string, unknown>;
              handleSSEEvent(currentEvent, data);
            } catch {
              // skip malformed events
            }
          }
        }
      }

      await loadConversations();
    } catch {
      setChatError("发送失败，请稍后重试。");
    } finally {
      setIsSending(false);
      streamingRef.current = { currentRoleId: null, currentMsgId: null, accumulated: "" };
    }
  }

  function handleSSEEvent(event: string, data: Record<string, unknown>): void {
    switch (event) {
      case "start": {
        const convId = data.conversation_id as string;
        if (convId && !activeId) {
          setActiveId(convId);
        }
        break;
      }
      case "role_start": {
        const role = data.role as RoleId;
        const msgId = `stream-${role}-${Date.now()}`;
        streamingRef.current = { currentRoleId: role, currentMsgId: msgId, accumulated: "" };
        setHasReceivedToken(true);
        setMessages((prev) => [
          ...prev,
          {
            id: msgId,
            role,
            content: "",
            citations: [],
            createdAt: new Date().toISOString(),
          },
        ]);
        break;
      }
      case "token": {
        const token = data.content as string;
        if (!token) break;
        streamingRef.current.accumulated += token;
        const msgId = streamingRef.current.currentMsgId;
        const accumulated = streamingRef.current.accumulated;
        setMessages((prev) =>
          prev.map((msg) => (msg.id === msgId ? { ...msg, content: accumulated } : msg))
        );
        break;
      }
      case "citations": {
        const citations = data.citations as Citation[];
        const msgId = streamingRef.current.currentMsgId;
        if (msgId && citations?.length) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === msgId ? { ...msg, citations } : msg
            )
          );
        }
        break;
      }
      case "role_end": {
        streamingRef.current = { currentRoleId: null, currentMsgId: null, accumulated: "" };
        break;
      }
      case "error": {
        setChatError((data.error as string) || "流式响应出错");
        break;
      }
    }
  }

  function handleToggleCitations(messageId: string): void {
    setOpenCitations((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_#efe6d8_0,_#f6f1e8_45%,_#f9f7f2_100%)]">
      <div className="absolute right-6 top-5 z-10 flex items-center gap-3 text-sm">
        <span className="text-[var(--muted)]">{user?.username}</span>
        <button
          type="button"
          onClick={logout}
          className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1 text-xs text-[var(--muted)] backdrop-blur transition hover:border-rose-300 hover:text-rose-600"
        >
          Logout
        </button>
      </div>
      <div className="pointer-events-none absolute -left-32 top-16 h-72 w-72 rounded-full bg-emerald-200/40 blur-[120px]" />
      <div className="pointer-events-none absolute right-0 top-40 h-80 w-80 rounded-full bg-amber-200/50 blur-[130px]" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-sky-200/40 blur-[120px]" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-4 py-6 md:flex-row md:items-stretch">
        <aside className="flex w-full flex-col rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5 shadow-[var(--shadow)] backdrop-blur md:w-72">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">多角色协作</p>
              <h1 className="mt-2 font-[var(--font-display)] text-2xl text-[var(--foreground)]">
                智能对话台
              </h1>
            </div>
            <button
              type="button"
              onClick={handleNewConversation}
              className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-xs text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
            >
              新建会话
            </button>
          </div>

          <div className="mt-4 rounded-2xl border border-dashed border-[var(--border)] bg-white/50 p-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.markdown,.text"
              multiple
              className="hidden"
              onChange={(e) => void handleUploadFiles(e.target.files)}
            />
            <button
              type="button"
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
                  上传中...
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  上传文档
                </>
              )}
            </button>
            <p className="mt-1.5 text-center text-[10px] text-[var(--muted)]">
              支持 .txt / .md 格式
            </p>
            {uploadMessage ? (
              <div
                className={`mt-2 flex items-start justify-between gap-1 rounded-xl px-2.5 py-1.5 text-xs ${
                  uploadMessage.type === "success"
                    ? "border border-emerald-200 bg-emerald-50 text-emerald-700"
                    : "border border-rose-200 bg-rose-50 text-rose-700"
                }`}
              >
                <span>{uploadMessage.text}</span>
                <button
                  type="button"
                  onClick={() => setUploadMessage(null)}
                  className="shrink-0 text-current opacity-60 hover:opacity-100"
                >
                  x
                </button>
              </div>
            ) : null}
          </div>

          <div className="mt-3 flex items-center justify-between text-xs text-[var(--muted)]">
            <span>会话列表</span>
            {isLoadingList ? <span>加载中...</span> : <span>{conversations.length} 个</span>}
          </div>

          <div className="mt-3 flex-1 space-y-2 overflow-y-auto pr-1">
            {listError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                {listError}
              </div>
            ) : null}

            {!isLoadingList && conversations.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[var(--border)] px-3 py-4 text-xs text-[var(--muted)]">
                暂无会话，点击“新建会话”开始。
              </div>
            ) : null}

            {conversations.map((conversation) => {
              const isActive = conversation.id === activeId;
              const displayTitle = conversation.title?.trim() || "新会话";
              return (
                  <div key={conversation.id} className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleSelectConversation(conversation.id)}
                      className={`flex-1 rounded-2xl border px-3 py-3 text-left transition ${
                        isActive
                          ? "border-[var(--accent)] bg-white text-[var(--foreground)]"
                          : "border-transparent bg-white/50 text-[var(--muted)] hover:border-[var(--border)] hover:bg-white"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium text-[var(--foreground)]">
                          {displayTitle}
                        </span>
                        <span className="shrink-0 text-xs text-[var(--muted)]">
                          {conversation.message_count}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        {formatTime(conversation.last_message_at ?? conversation.created_at)}
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteConversation(conversation.id)}
                      disabled={deletingId === conversation.id}
                      className="shrink-0 rounded-xl border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-600 transition hover:bg-rose-100 hover:border-rose-300 disabled:opacity-50"
                    >
                      {deletingId === conversation.id ? "..." : "删除"}
                    </button>
                  </div>
              );
            })}
          </div>
        </aside>

        <section className="flex min-h-[70vh] flex-1 flex-col rounded-3xl border border-[var(--border)] bg-[var(--panel-strong)] shadow-[var(--shadow)]">
          <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] px-6 py-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">当前会话</p>
              <h2 className="mt-2 text-xl font-semibold">
                {activeConversation?.title?.trim() || "未命名会话"}
              </h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
              {isLoadingHistory ? "正在读取消息..." : "随时输入你的问题"}
            </div>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
            {chatError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {chatError}
              </div>
            ) : null}

            {messages.length === 0 && !isLoadingHistory ? (
              <div className="rounded-2xl border border-dashed border-[var(--border)] bg-white/70 px-5 py-6 text-sm text-[var(--muted)]">
                这里会显示多角色的协作回答。先发送一条问题试试吧。
              </div>
            ) : null}

            {messages.map((message) => {
              const isUser = message.role === "user";
              const roleLabel = getRoleLabel(message.role);
              const roleStyle = getRoleStyle(message.role);
              const hasCitations = (message.citations?.length ?? 0) > 0;

              return (
                <div
                  key={message.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[78%] rounded-3xl px-4 py-3 text-sm shadow-sm ${
                      isUser
                        ? "bg-[var(--accent)] text-white"
                        : "bg-white text-[var(--foreground)]"
                    }`}
                  >
                    <div className="flex items-center gap-2 text-xs">
                      <span className={`rounded-full px-2 py-0.5 font-medium ${roleStyle}`}>
                        {roleLabel}
                      </span>
                      {message.createdAt ? (
                        <span className="text-[var(--muted)]">
                          {formatTime(message.createdAt)}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap leading-6">
                      {message.content}
                      {isSending && message.id === streamingRef.current.currentMsgId ? (
                        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-[var(--accent)] align-text-bottom" />
                      ) : null}
                    </p>

                    {hasCitations ? (
                      <div className="mt-3 rounded-2xl border border-[var(--border)] bg-emerald-50/40 px-3 py-2 text-xs text-[var(--muted)]">
                        <button
                          type="button"
                          onClick={() => handleToggleCitations(message.id)}
                          className="flex w-full items-center justify-between font-medium text-[var(--accent)]"
                        >
                          <span>引用来源（{message.citations?.length}）</span>
                          <span>{openCitations[message.id] ? "收起" : "展开"}</span>
                        </button>
                        {openCitations[message.id] ? (
                          <ul className="mt-2 space-y-2">
                            {message.citations?.map((citation, index) => {
                              const sourceLabel =
                                citation.source?.trim() ||
                                `文档 ${citation.document_id.slice(0, 8)} / 片段 ${citation.chunk_id.slice(0, 8)}`;
                              const score = formatScore(citation.score);
                              return (
                                <li
                                  key={`${message.id}-citation-${index}`}
                                  className="rounded-xl border border-[var(--border)] bg-white px-3 py-2"
                                >
                                  <p className="text-[var(--foreground)]">{sourceLabel}</p>
                                  {score ? (
                                    <p className="mt-1 text-[var(--muted)]">相似度 {score}</p>
                                  ) : null}
                                </li>
                              );
                            })}
                          </ul>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}

            {isSending && !hasReceivedToken ? (
              <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
                <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-[var(--accent)]" />
                正在思考...
              </div>
            ) : null}
            <div ref={bottomRef} />
          </div>

          <form
            className="border-t border-[var(--border)] px-6 py-4"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSend();
            }}
          >
            <div className="flex flex-col gap-3">
              <textarea
                rows={3}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void handleSend();
                  }
                }}
                placeholder="请输入问题，回车发送，Shift+Enter 换行"
                className="w-full resize-none rounded-2xl border border-[var(--border)] bg-white px-4 py-3 text-sm outline-none transition focus:border-[var(--accent)]"
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-[var(--muted)]">
                  角色将根据问题自动协作回答。
                </p>
                <button
                  type="submit"
                  disabled={!canSend}
                  className={`rounded-full px-5 py-2 text-sm font-medium text-white transition ${
                    canSend
                      ? "bg-[var(--accent)] hover:bg-[var(--accent-strong)]"
                      : "bg-slate-300"
                  }`}
                >
                  发送
                </button>
              </div>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
