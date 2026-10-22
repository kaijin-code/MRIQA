export type Citation = {
  document_id: string;
  chunk_id: string;
  chunk_index?: number;
  source?: string | null;
  score: number;
  start_line?: number | null;
  end_line?: number | null;
  line_number_kind?: "original" | "reconstructed" | null;
};

export type CitationEntry = { citation: Citation; numbers: number[] };
export type CitationGroup = {
  documentId: string;
  source: string;
  entries: CitationEntry[];
};

export function groupCitations(citations: Citation[]): CitationGroup[] {
  const groups = new Map<string, CitationGroup>();
  citations.forEach((citation, index) => {
    let group = groups.get(citation.document_id);
    if (!group) {
      group = {
        documentId: citation.document_id,
        source: citation.source?.trim() || `文档 ${citation.document_id.slice(0, 8)}`,
        entries: [],
      };
      groups.set(citation.document_id, group);
    }
    const entry = group.entries.find((item) => item.citation.chunk_id === citation.chunk_id);
    if (entry) entry.numbers.push(index + 1);
    else group.entries.push({ citation, numbers: [index + 1] });
  });
  return [...groups.values()];
}

export function formatCitationLocation(citation: Partial<Citation>): string {
  const { start_line: start, end_line: end } = citation;
  if (Number.isInteger(start) && Number.isInteger(end) && start! > 0 && end! >= start!) {
    const prefix = citation.line_number_kind === "reconstructed" ? "预览第" : "第";
    return `${prefix} ${start}${start === end ? "" : `–${end}`} 行`;
  }
  return typeof citation.chunk_index === "number"
    ? `片段 ${citation.chunk_index + 1} · 行号不可用`
    : "行号不可用";
}
