from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import UUID

import importlib.util


class CitationLineTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('app.utils.citation_lines'), 'Citation line lookup is not implemented')
        global citation_lines
        citation_lines = importlib.import_module('app.utils.citation_lines')
        self.first = SimpleNamespace(id=UUID(int=1), chunk_index=0, content="alpha\nbeta")
        self.second = SimpleNamespace(id=UUID(int=2), chunk_index=1, content="gamma")

    def test_original_line_numbers_preserve_blank_lines_and_crlf(self):
        result = citation_lines.build_citation_excerpts("intro\r\n\r\nalpha\r\nbeta\r\n\r\ngamma", [self.first, self.second])
        self.assertEqual((result[self.first.id]["start_line"], result[self.first.id]["end_line"]), (3, 4))
        self.assertEqual(result[self.first.id]["line_number_kind"], "original")
        self.assertEqual(result[self.second.id]["start_line"], 6)
        self.assertEqual(result[self.first.id]["content"], "alpha\nbeta")

    def test_normalized_whitespace_mapping_returns_original_excerpt(self):
        self.first.content = "alpha\n\nbeta"
        result = citation_lines.build_citation_excerpts("intro\n\nalpha   beta\nnext", [self.first])
        self.assertEqual(result[self.first.id]["line_number_kind"], "original")
        self.assertEqual(result[self.first.id]["content"], "alpha   beta")
        self.assertEqual((result[self.first.id]["start_line"], result[self.first.id]["end_line"]), (3, 3))

    def test_legacy_line_numbers_use_stable_chunk_order(self):
        result = citation_lines.build_citation_excerpts(None, [self.second, self.first])
        self.assertEqual((result[self.first.id]["start_line"], result[self.first.id]["end_line"]), (1, 2))
        self.assertEqual((result[self.second.id]["start_line"], result[self.second.id]["end_line"]), (4, 4))
        self.assertEqual(result[self.second.id]["line_number_kind"], "reconstructed")

    def test_requested_chunk_keeps_legacy_positions_without_returning_other_excerpts(self):
        result = citation_lines.build_citation_excerpts(None, [self.first, self.second], {self.second.id})
        self.assertEqual(set(result), {self.second.id})
        self.assertEqual(result[self.second.id]["start_line"], 4)

    def test_transformed_markdown_does_not_claim_original_lines(self):
        self.first.content = "# Heading\n\nsecond paragraph"
        result = citation_lines.build_citation_excerpts("# Heading\n\nfirst paragraph\n\nsecond paragraph", [self.first])
        self.assertEqual(result[self.first.id]["line_number_kind"], "reconstructed")
        self.assertEqual(result[self.first.id]["start_line"], 1)

    def test_ambiguous_repeated_text_does_not_guess_original_lines(self):
        self.first.content = "repeat"
        result = citation_lines.build_citation_excerpts("repeat\n\nrepeat", [self.first])
        self.assertEqual(result[self.first.id]["line_number_kind"], "reconstructed")

    def test_trailing_newline_does_not_extend_highlight_to_empty_line(self):
        self.first.content = "alpha\nbeta\n"
        result = citation_lines.build_citation_excerpts("alpha\nbeta\n", [self.first])
        self.assertEqual(result[self.first.id]["end_line"], 2)


if __name__ == "__main__":
    unittest.main()
