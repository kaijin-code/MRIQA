"use client";

import { useEffect, useId, useRef, useState } from "react";
import { authFetch } from "@/app/lib/api";
import { type Citation, formatCitationLocation, groupCitations } from "@/app/lib/citations";

type CitationPreview = Pick<Citation,
  "document_id" | "chunk_id" | "source" | "start_line" | "end_line" | "line_number_kind"
> & { content: string };

type Props = {
  content: string;
  citations?: Citation[];
  conversationId: string | null;
  isStreaming: boolean;
  isPending?: boolean;
};

export function CitedMessage({ content, citations = [], conversationId, isStreaming, isPending = false }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<Citation | null>(null);
  const [preview, setPreview] = useState<CitationPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const previewTitleId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const firstLineRef = useRef<HTMLDivElement>(null);
  const groups = groupCitations(citations);
  const citationCount = groups.reduce((total, group) => total + group.entries.length, 0);

  useEffect(() => {
    if (!selected || !conversationId) return;
    const controller = new AbortController();
    authFetch(`/api/conversations/${conversationId}/citations/${selected.chunk_id}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(response.status === 404
            ? "此引用已不可用，文档可能已删除。"
            : "引用加载失败，请稍后重试。");
        }
        const data = await response.json() as CitationPreview;
        if (!controller.signal.aborted) setPreview(data);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "引用加载失败，请稍后重试。");
        }
      });
    return () => controller.abort();
  }, [selected, conversationId, retry]);

  useEffect(() => {
    if (preview) firstLineRef.current?.scrollIntoView({ block: "center" });
  }, [preview]);

  function openCitation(citation: Citation) {
    setPreview(null);
    setError(null);
    setSelected(citation);
    dialogRef.current?.showModal();
  }

  function closePreview() {
    dialogRef.current?.close();
    setSelected(null);
    setPreview(null);
    setError(null);
  }

  return (
    <>
      <p className="mt-2 whitespace-pre-wrap leading-6">
        {content.split(/(\[\d+\])/g).map((part, index) => {
          const match = /^\[(\d+)\]$/.exec(part);
          const citation = match ? citations[Number(match[1]) - 1] : undefined;
          return citation ? (
            <button
              key={index}
              type="button"
              onClick={() => openCitation(citation)}
              disabled={!conversationId || isPending}
              aria-label={`查看引用 ${match![1]}：${citation.source || "文档"}，${formatCitationLocation(citation)}`}
              className="cursor-pointer rounded px-0.5 font-medium text-[var(--accent)] underline decoration-dotted underline-offset-4 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:cursor-wait"
            >
              {part}
            </button>
          ) : part;
        })}
        {isStreaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-[var(--accent)] align-text-bottom" /> : null}
      </p>

      {citationCount > 0 ? (
        <div className="mt-3 rounded-2xl border border-[var(--border)] bg-emerald-50/40 px-3 py-2 text-xs text-[var(--muted)]">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            className="flex w-full cursor-pointer items-center justify-between gap-3 font-medium text-[var(--accent)]"
          >
            <span>引用来源（{groups.length} 个文件 · {citationCount} 处）</span>
            <span>{expanded ? "收起" : "展开"}</span>
          </button>
          {expanded ? (
            <ul className="mt-2 space-y-2">
              {groups.map((group) => (
                <li key={group.documentId} className="overflow-hidden rounded-xl border border-[var(--border)] bg-white">
                  <p className="break-all px-3 pb-1 pt-2 font-medium text-[var(--foreground)]">{group.source}</p>
                  <ul className="divide-y divide-[var(--border)]">
                    {group.entries.map(({ citation, numbers }) => (
                      <li key={citation.chunk_id}>
                        <button
                          type="button"
                          disabled={!conversationId || isPending}
                          onClick={() => openCitation(citation)}
                          className="flex w-full cursor-pointer flex-wrap items-center justify-between gap-x-4 gap-y-1 px-3 py-2 text-left transition hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:cursor-wait disabled:opacity-60"
                        >
                          <span className="font-medium text-[var(--accent)]">
                            <span className="mr-2">{numbers.map((number) => `[${number}]`).join(" ")}</span>
                            {formatCitationLocation(citation)}
                          </span>
                          <span className="text-[var(--muted)]">
                            {Number.isFinite(citation.score) ? `相似度 ${(citation.score * 100).toFixed(1)}% · ` : ""}查看 ↗
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <dialog
        ref={dialogRef}
        onCancel={closePreview}
        onClose={() => setSelected(null)}
        aria-labelledby={previewTitleId}
        className="fixed inset-0 m-auto max-h-[85vh] w-[min(56rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-[var(--border)] bg-white p-0 text-[var(--foreground)] shadow-xl backdrop:bg-slate-900/35"
      >
        <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] px-5 py-4">
          <div className="min-w-0">
            <h3 id={previewTitleId} className="break-all font-semibold">{preview?.source || selected?.source || "引用片段"}</h3>
            <p className="mt-1 text-xs text-[var(--muted)]">{formatCitationLocation(preview || selected || {})}</p>
          </div>
          <button type="button" autoFocus onClick={closePreview} className="shrink-0 cursor-pointer rounded-lg border border-[var(--border)] px-3 py-1 text-sm hover:bg-slate-50">关闭</button>
        </div>
        <div className="max-h-[65vh] overflow-auto p-4">
          {error ? (
            <div role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">
              {error}
              <button type="button" onClick={() => { setError(null); setRetry(retry + 1); }} className="ml-3 cursor-pointer underline">重试</button>
            </div>
          ) : preview ? (
            <>
              {preview.line_number_kind === "reconstructed" ? <p className="mb-3 text-xs text-[var(--muted)]">以下行号对应知识库片段还原的预览文本，可能与原文件行号不同。</p> : null}
              <div className="font-mono text-xs leading-6">
                {preview.content.replace(/\r\n?/g, "\n").split("\n").map((line, index) => (
                  <div key={index} ref={index === 0 ? firstLineRef : undefined} className="flex bg-amber-50">
                    <span aria-hidden="true" className="w-14 shrink-0 select-none border-r border-amber-200 pr-3 text-right text-[var(--muted)]">{(preview.start_line ?? 1) + index}</span>
                    <span className="min-w-0 whitespace-pre-wrap break-words px-3">{line || "\u00a0"}</span>
                  </div>
                ))}
              </div>
            </>
          ) : <p role="status" className="p-4 text-sm text-[var(--muted)]">正在定位引用...</p>}
        </div>
      </dialog>
    </>
  );
}
