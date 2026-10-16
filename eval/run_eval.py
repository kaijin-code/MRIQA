"""MRIQA RAG 评测脚本。

用法（在仓库根目录，使用后端虚拟环境）:
    backend/.venv/Scripts/python.exe eval/run_eval.py                 # 完整评测（含 LLM 问答）
    backend/.venv/Scripts/python.exe eval/run_eval.py --retrieval-only  # 仅检索评测（不调 LLM）
    backend/.venv/Scripts/python.exe eval/run_eval.py --keep            # 评测后保留语料（默认清理）

流程：入库 eval/corpus 语料 -> 逐题检索 -> （可选）调技术支持 Agent 生成回答 -> 输出 eval/report.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.agents.technical_support import TechnicalSupportAgent  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Document  # noqa: E402
from app.rag.ingest import ingest_documents  # noqa: E402
from app.rag.retriever import retrieve_chunks  # noqa: E402
from app.schemas import DocumentInput  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
QUESTIONS_FILE = Path(__file__).resolve().parent / "questions.jsonl"
REPORT_FILE = Path(__file__).resolve().parent / "report.md"
DETAILS_FILE = Path(__file__).resolve().parent / "details.jsonl"
EVAL_DOC_PREFIX = "eval::"

# 严格拒答标记：明确指向知识库缺失，用于可答题（避免"无法"等泛化词误报）
STRICT_REFUSAL_MARKERS = [
    "知识库中未", "知识库未", "未在知识库", "不在知识库", "知识库中没有",
    "无法回答", "无法基于知识库", "未检索到相关", "没有找到相关", "未找到相关",
]
# 宽松拒答标记：用于无证据题/模糊题的判定
REFUSAL_MARKERS = STRICT_REFUSAL_MARKERS + [
    "无法", "未找到", "没有找到", "未能找到", "抱歉", "不能确认",
    "未包含", "不包含", "并未提及", "没有相关", "没有足够",
]
CLARIFY_MARKERS = [
    "澄清", "确认", "具体", "是指", "想了解", "哪个", "哪种",
    "请说明", "更详细", "指的是", "进一步说明",
]


@dataclass
class QuestionResult:
    qid: str
    qtype: str
    question: str
    retrieval_hit: bool | None = None
    keyword_covered: bool | None = None
    cited_expected: bool | None = None
    refused: bool | None = None
    clarified: bool | None = None
    passed: bool | None = None
    answer_excerpt: str = ""
    full_answer: str = ""
    error: str | None = None
    extra: dict = field(default_factory=dict)


def load_questions() -> list[dict]:
    questions = []
    with QUESTIONS_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def detect(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


async def reset_corpus(session) -> None:
    """删除上次评测残留的语料文档，保证幂等。"""
    from sqlalchemy import delete as sa_delete

    result = await session.execute(
        sa_delete(Document).where(Document.title.like(f"{EVAL_DOC_PREFIX}%"))
    )
    await session.commit()
    if result.rowcount:
        print(f"removed {result.rowcount} stale eval documents")


async def ingest_corpus(session) -> int:
    files = sorted(p for p in CORPUS_DIR.glob("*.md") if p.name not in {"NOTICE.md", "LICENSE-fastapi.md"})
    if not files:
        raise SystemExit(f"no corpus files under {CORPUS_DIR}")
    docs = [
        DocumentInput(
            title=f"{EVAL_DOC_PREFIX}{p.name}",
            source=p.name,
            text=p.read_text(encoding="utf-8"),
        )
        for p in files
    ]
    n_docs, n_chunks = await ingest_documents(docs, session)
    print(f"ingested {n_docs} documents, {n_chunks} chunks")
    return n_docs


async def cleanup_corpus(session) -> None:
    from sqlalchemy import delete as sa_delete

    await session.execute(sa_delete(Document).where(Document.title.like(f"{EVAL_DOC_PREFIX}%")))
    await session.commit()
    print("cleaned up eval corpus")


async def eval_retrieval(question: dict, session) -> tuple[list, QuestionResult]:
    result = QuestionResult(qid=question["id"], qtype=question["type"], question=question["question"])
    retrieved = await retrieve_chunks(question["question"], session)
    sources = [r.source for r in retrieved]
    if question["type"] == "answerable":
        result.retrieval_hit = question["expected_source"] in sources
        joined = "\n".join(r.content for r in retrieved)
        result.keyword_covered = any(kw in joined for kw in question["expected_keywords"])
        result.extra["retrieved_sources"] = sources
    return retrieved, result


async def eval_answer(question: dict, session, agent: TechnicalSupportAgent) -> QuestionResult:
    result = QuestionResult(qid=question["id"], qtype=question["type"], question=question["question"])
    try:
        role_result = await agent.respond(question["question"], None, session)
        answer = role_result.content
        citation_sources = {c.get("source") for c in role_result.citations}
        # 可答题用严格标记（避免正常回答含"无法"等词误报），无证据/模糊题用宽松标记
        markers = STRICT_REFUSAL_MARKERS if question["type"] == "answerable" else REFUSAL_MARKERS
        result.refused = detect(answer, markers)
        result.clarified = ("？" in answer or "?" in answer) and detect(answer, CLARIFY_MARKERS)
        result.answer_excerpt = answer[:120].replace("\n", " ")
        result.full_answer = answer
        result.extra["citation_sources"] = sorted(s for s in citation_sources if s)
        result.extra["citations"] = [
            {"source": c.get("source"), "chunk_index": c.get("chunk_index"), "score": round(c.get("score", 0), 4)}
            for c in role_result.citations
        ]
        if question["type"] == "answerable":
            result.cited_expected = question["expected_source"] in citation_sources
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)[:200]
    return result


def merge(retrieval_result: QuestionResult, answer_result: QuestionResult | None) -> QuestionResult:
    if answer_result is None:
        merged = retrieval_result
        if merged.qtype == "answerable":
            merged.passed = merged.retrieval_hit and merged.keyword_covered
        return merged
    merged = retrieval_result
    merged.cited_expected = answer_result.cited_expected
    merged.refused = answer_result.refused
    merged.clarified = answer_result.clarified
    merged.answer_excerpt = answer_result.answer_excerpt
    merged.full_answer = answer_result.full_answer
    merged.error = answer_result.error
    merged.extra.update({k: v for k, v in answer_result.extra.items() if k not in merged.extra})
    if merged.qtype == "answerable":
        merged.passed = bool(merged.retrieval_hit and merged.keyword_covered and merged.cited_expected and not merged.refused)
    elif merged.qtype == "no_evidence":
        merged.passed = bool(merged.refused)
    else:
        merged.passed = bool(merged.clarified or merged.refused)
    return merged


def write_report(results: list[QuestionResult], retrieval_only: bool, elapsed: float) -> None:
    settings = get_settings()
    answerable = [r for r in results if r.qtype == "answerable"]
    no_evidence = [r for r in results if r.qtype == "no_evidence"]
    ambiguous = [r for r in results if r.qtype == "ambiguous"]

    def rate(items, attr):
        vals = [getattr(r, attr) for r in items if getattr(r, attr) is not None]
        return (sum(vals) / len(vals) * 100) if vals else None

    lines = []
    lines.append("# RAG 评测报告")
    lines.append("")
    lines.append(f"- 时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 模式：{'仅检索' if retrieval_only else '检索 + LLM 问答'}")
    lines.append(f"- 模型：`{settings.qwen_model}` / 嵌入 `{settings.qwen_embedding_model}`")
    lines.append(f"- 检索参数：top_k={settings.rag_top_k}, min_similarity={settings.rag_min_similarity}")
    lines.append(f"- 语料：FastAPI 中文文档 10 章（MIT），评测后默认清理")
    lines.append(f"- 总耗时：{elapsed:.0f}s")
    lines.append("")
    lines.append("## 汇总指标")
    lines.append("")
    lines.append("| 指标 | 定义 | 结果 |")
    lines.append("| --- | --- | --- |")
    hit = rate(answerable, "retrieval_hit")
    lines.append(f"| 检索命中率 Hit@{settings.rag_top_k} | 期望文档出现在召回结果（可答题） | {f'{hit:.1f}%' if hit is not None else '-'} |")
    cov = rate(answerable, "keyword_covered")
    lines.append(f"| 关键词覆盖率 | 期望关键词出现在召回内容（可答题） | {f'{cov:.1f}%' if cov is not None else '-'} |")
    if not retrieval_only:
        cited = rate(answerable, "cited_expected")
        lines.append(f"| 引用准确率 | 回答引用含期望文档（可答题） | {f'{cited:.1f}%' if cited is not None else '-'} |")
        refused = rate(no_evidence, "refused")
        lines.append(f"| 拒答正确率 | 无证据题给出拒答 | {f'{refused:.1f}%' if refused is not None else '-'} |")
        clarified = rate(ambiguous, "clarified")
        lines.append(f"| 澄清率 | 模糊题给出澄清追问 | {f'{clarified:.1f}%' if clarified is not None else '-'} |")
    overall = rate([r for r in results if r.passed is not None], "passed")
    lines.append(f"| 综合通过率 | 各题型按判定标准全部通过 | {f'{overall:.1f}%' if overall is not None else '-'} |")
    lines.append("")

    lines.append("## 逐题明细")
    lines.append("")
    if retrieval_only:
        lines.append("| ID | 类型 | 问题 | 检索命中 | 关键词 | 通过 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for r in results:
            q = r.question[:38].replace("|", "\\|")
            lines.append(
                f"| {r.qid} | {r.qtype} | {q} | {fmt_bool(r.retrieval_hit)} | {fmt_bool(r.keyword_covered)} | {fmt_bool(r.passed)} |"
            )
    else:
        lines.append("| ID | 类型 | 问题 | 命中 | 关键词 | 引用 | 拒答 | 澄清 | 通过 | 回答摘录 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in results:
            q = r.question[:30].replace("|", "\\|")
            excerpt = (r.answer_excerpt or r.error or "").replace("|", "\\|")[:40]
            lines.append(
                f"| {r.qid} | {r.qtype} | {q} | {fmt_bool(r.retrieval_hit)} | {fmt_bool(r.keyword_covered)} "
                f"| {fmt_bool(r.cited_expected)} | {fmt_bool(r.refused)} | {fmt_bool(r.clarified)} "
                f"| {fmt_bool(r.passed)} | {excerpt} |"
            )
    lines.append("")
    lines.append("> 判定标准：answerable = 检索命中 + 关键词覆盖 + 引用期望文档 + 未拒答（严格拒答标记）；")
    lines.append("> no_evidence = 回答命中拒答标记（宽松）；ambiguous = 回答包含澄清追问（或拒答）。")
    lines.append("> 完整回答与引用明细见 `eval/details.jsonl`。")
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"report written to {REPORT_FILE}")

    if not retrieval_only:
        with DETAILS_FILE.open("w", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps({
                    "id": r.qid,
                    "type": r.qtype,
                    "question": r.question,
                    "passed": r.passed,
                    "retrieval_hit": r.retrieval_hit,
                    "keyword_covered": r.keyword_covered,
                    "cited_expected": r.cited_expected,
                    "refused": r.refused,
                    "clarified": r.clarified,
                    "citations": r.extra.get("citations", []),
                    "retrieved_sources": r.extra.get("retrieved_sources", []),
                    "answer": r.full_answer,
                    "error": r.error,
                }, ensure_ascii=False) + "\n")
        print(f"details written to {DETAILS_FILE}")


def fmt_bool(value: bool | None) -> str:
    if value is None:
        return "-"
    return "✓" if value else "✗"


async def main() -> None:
    parser = argparse.ArgumentParser(description="MRIQA RAG evaluation")
    parser.add_argument("--retrieval-only", action="store_true", help="skip LLM answer phase")
    parser.add_argument("--keep", action="store_true", help="keep eval corpus in DB after run")
    parser.add_argument("--limit", type=int, default=0, help="only run first N questions")
    args = parser.parse_args()

    questions = load_questions()
    if args.limit:
        questions = questions[: args.limit]
    print(f"loaded {len(questions)} questions (answerable="
          f"{sum(1 for q in questions if q['type'] == 'answerable')}, "
          f"no_evidence={sum(1 for q in questions if q['type'] == 'no_evidence')}, "
          f"ambiguous={sum(1 for q in questions if q['type'] == 'ambiguous')})")

    started = time.time()
    await init_db()

    async with SessionLocal() as session:
        await reset_corpus(session)
        await ingest_corpus(session)

        agent = None if args.retrieval_only else TechnicalSupportAgent()
        results: list[QuestionResult] = []
        for idx, question in enumerate(questions, 1):
            _, retrieval_result = await eval_retrieval(question, session)
            answer_result = None
            if not args.retrieval_only:
                answer_result = await eval_answer(question, session, agent)
            merged = merge(retrieval_result, answer_result)
            results.append(merged)
            if merged.passed is None:
                status = "N/A"
            else:
                status = "PASS" if merged.passed else "FAIL"
            print(f"[{idx}/{len(questions)}] {question['id']} {status}")

        if not args.keep:
            await cleanup_corpus(session)

    write_report(results, args.retrieval_only, time.time() - started)


if __name__ == "__main__":
    asyncio.run(main())
