from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api import routes
from app.models import Chunk, Conversation, Document, Message
from app.rag import ingest, retriever
from app.agents.base import BaseRoleAgent
from app.schemas import ChunkCitation
from app.schemas import DocumentInput


class Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class Session:
    def __init__(self, objects=(), results=()):
        self.objects = {(type(obj), obj.id): obj for obj in objects}
        self.results = list(results)
        self.added = []
        self.commit = AsyncMock()

    async def get(self, model, identifier):
        return self.objects.get((model, identifier))

    async def execute(self, statement):
        return Result(self.results.pop(0))

    def add(self, obj):
        self.added.append(obj)


class CitationRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=uuid4())
        self.conversation = Conversation(id=uuid4(), user_id=self.user.id, created_at=datetime.now(UTC))
        self.document = Document(id=uuid4(), source="guide.md", title="guide")
        self.document.content = "PRIVATE FIRST LINE\n\nshared excerpt\nPRIVATE LAST LINE"
        self.chunk = Chunk(id=uuid4(), document_id=self.document.id, chunk_index=0, content="shared excerpt")
        self.message = Message(id=uuid4(), conversation_id=self.conversation.id, role="technical_support", content="answer",
                               sources=[{"chunk_id": str(self.chunk.id), "document_id": str(self.document.id), "score": 0.8}],
                               created_at=datetime.now(UTC))

    async def preview(self, session):
        self.assertTrue(hasattr(routes, "get_citation_excerpt"), "Citation preview endpoint is not implemented")
        return await routes.get_citation_excerpt(self.conversation.id, self.chunk.id, session=session, current_user=self.user)

    async def test_cited_chunk_preview_contains_only_the_cited_excerpt(self):
        session = Session([self.conversation], [[self.message], [self.document], [self.chunk]])
        result = await self.preview(session)
        self.assertEqual(result.content, "shared excerpt")
        self.assertEqual((result.start_line, result.end_line, result.line_number_kind), (3, 3, "original"))
        self.assertEqual(result.source, "guide.md")
        self.assertNotIn("PRIVATE", result.model_dump_json())

    async def test_another_users_conversation_cannot_authorize_preview(self):
        self.conversation.user_id = uuid4()
        with self.assertRaises(HTTPException) as raised:
            await self.preview(Session([self.conversation]))
        self.assertEqual(raised.exception.status_code, 404)

    async def test_deleted_conversation_cannot_authorize_preview(self):
        self.conversation.deleted_at = datetime.now(UTC)
        with self.assertRaises(HTTPException) as raised:
            await self.preview(Session([self.conversation]))
        self.assertEqual(raised.exception.status_code, 404)

    async def test_uncited_chunk_cannot_be_read_even_if_it_exists(self):
        self.message.sources = []
        with self.assertRaises(HTTPException) as raised:
            await self.preview(Session([self.conversation, self.chunk], [[self.message]]))
        self.assertEqual(raised.exception.status_code, 404)

    async def test_deleted_message_cannot_authorize_preview(self):
        self.message.deleted_at = datetime.now(UTC)
        with self.assertRaises(HTTPException) as raised:
            await self.preview(Session([self.conversation], [[self.message]]))
        self.assertEqual(raised.exception.status_code, 404)

    async def test_history_enriches_legacy_sources_without_rewriting_them(self):
        original_sources = [dict(source) for source in self.message.sources]
        session = Session([self.conversation], [[self.message], [self.document], [self.chunk]])
        result = await routes.get_conversation_history(self.conversation.id, limit=200, offset=0,
                                                       session=session, current_user=self.user)
        self.assertEqual(result.messages[0].sources[0]["start_line"], 3)
        self.assertEqual(result.messages[0].sources[0]["line_number_kind"], "original")
        self.assertEqual(result.messages[0].sources[0]["score"], 0.8)
        self.assertEqual(self.message.sources, original_sources)

    async def test_new_retrieval_exposes_line_metadata_in_the_chat_citation_contract(self):
        session = Session(results=[[(self.chunk, self.document.source, 0.2)], [self.document], [self.chunk]])
        qwen = SimpleNamespace(embed_query=AsyncMock(return_value=[0.1]))
        with patch.object(retriever, "get_qwen_client", return_value=qwen):
            retrieved = await retriever.retrieve_chunks("question", session)
        citation = ChunkCitation.model_validate(BaseRoleAgent._build_citations(retrieved)[0])
        self.assertEqual((citation.start_line, citation.end_line, citation.line_number_kind), (3, 3, "original"))
        self.assertEqual(citation.chunk_id, self.chunk.id)

    async def test_deleted_document_preview_returns_not_found(self):
        with self.assertRaises(HTTPException) as raised:
            await self.preview(Session([self.conversation], [[self.message], []]))
        self.assertEqual(raised.exception.status_code, 404)

    async def test_history_preserves_stale_citations_with_unknown_lines(self):
        session = Session([self.conversation], [[self.message], []])
        result = await routes.get_conversation_history(self.conversation.id, limit=200, offset=0,
                                                       session=session, current_user=self.user)
        source = result.messages[0].sources[0]
        self.assertEqual(source["chunk_id"], str(self.chunk.id))
        self.assertIsNone(source["start_line"])
        self.assertIsNone(source["line_number_kind"])

    async def test_ingestion_retains_the_unmodified_decoded_text(self):
        text = "\n\n# Heading\r\n\r\nparagraph\r\n"
        session = Session()
        with patch.object(ingest, "get_qwen_client", return_value=SimpleNamespace(embed_texts=AsyncMock(return_value=[[0.1]]))):
            await ingest.ingest_documents([DocumentInput(source="guide.md", text=text)], session)
        document = next(obj for obj in session.added if isinstance(obj, Document))
        self.assertEqual(getattr(document, "content", None), text)


if __name__ == "__main__":
    unittest.main()
