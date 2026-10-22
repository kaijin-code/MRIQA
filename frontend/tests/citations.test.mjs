import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";
const filename = fileURLToPath(new URL("../app/lib/citations.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017 },
});
const loaded = new Module(filename);
loaded._compile(compiled.outputText, filename);
const { groupCitations, formatCitationLocation } = loaded.exports;

test("groups by document and removes duplicate chunks without changing answer reference numbers", () => {
  const groups = groupCitations([
    { document_id: "doc-a", chunk_id: "a1", source: "same.txt", score: 0.7 },
    { document_id: "doc-b", chunk_id: "b1", source: "same.txt", score: 0.6 },
    { document_id: "doc-a", chunk_id: "a2", source: "same.txt", score: 0.5 },
    { document_id: "doc-a", chunk_id: "a1", source: "same.txt", score: 0.7 },
  ]);
  assert.equal(groups.length, 2);
  assert.equal(groups[0].entries.length, 2);
  assert.deepEqual(groups[0].entries.map((entry) => entry.numbers), [[1, 4], [3]]);
  assert.deepEqual(groups[1].entries[0].numbers, [2]);
});

test("distinguishes exact original lines, reconstructed preview lines, and unknown locations", () => {
  assert.equal(formatCitationLocation({ start_line: 12, end_line: 18, line_number_kind: "original" }), "第 12–18 行");
  assert.equal(formatCitationLocation({ start_line: 8, end_line: 8, line_number_kind: "reconstructed" }), "预览第 8 行");
  assert.equal(formatCitationLocation({ chunk_index: 2 }), "片段 3 · 行号不可用");
  assert.equal(formatCitationLocation({ start_line: 0, end_line: 4 }), "行号不可用");
  assert.equal(formatCitationLocation({ start_line: 8, end_line: 2 }), "行号不可用");
});
