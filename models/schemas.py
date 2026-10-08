"""Pydantic-style schemas using dataclasses (no hard dependency on pydantic).

Keeps structures flexible: generic documents carry open metadata dicts,
so question papers, reports, manuals, etc. all fit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PageContent:
    page_number: int
    text: str
    heading: str = ""
    section: str = ""


@dataclass
class ParsedDocument:
    document_id: str
    file_name: str
    file_type: str  # e.g. 'pdf', 'docx', 'txt'
    pages: List[PageContent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    page_number: int = 0
    section: str = ""
    heading: str = ""
    topic: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "page_number": self.page_number,
            "section": self.section,
            "heading": self.heading,
            "topic": self.topic,
            **self.extra,
        }


@dataclass
class RequirementSpec:
    """LLM's interpretation of what the user wants."""

    intent: str = "custom"  # summarize | extract | classify | retrieve | generate | custom
    target: str = ""
    scope: str = "current document"
    output_format: str = "markdown"
    constraints: List[str] = field(default_factory=list)
    rewritten_query: str = ""


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    checks: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    relevance: int = 0
    consistency: int = 0
    factuality: int = 0
    completeness: int = 0
    format_compliance: int = 0
    notes: str = ""

    @property
    def overall(self) -> int:
        scores = [
            self.relevance,
            self.consistency,
            self.factuality,
            self.completeness,
            self.format_compliance,
        ]
        return int(round(sum(scores) / len(scores))) if scores else 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "relevance": self.relevance,
            "consistency": self.consistency,
            "factuality": self.factuality,
            "completeness": self.completeness,
            "format_compliance": self.format_compliance,
            "overall": self.overall,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------
# Multi-chat workspace: one document/RAG index, many independent chats.
# Stored as plain dicts in st.session_state (session-level only).
# ---------------------------------------------------------------------

@dataclass
class ChatMessage:
    """One message. Assistant messages carry their own RAG evidence."""

    role: str  # 'user' | 'assistant'
    content: str
    task: str = "custom"
    spec: Dict[str, Any] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    quality: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    model: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role, "content": self.content, "task": self.task,
            "spec": self.spec, "sources": self.sources,
            "quality": self.quality, "validation": self.validation,
            "model": self.model,
        }


@dataclass
class ChatSession:
    """One conversation about one document. Histories never mix."""

    chat_id: str
    document_id: str
    title: str = "New Chat"
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "chat_id": self.chat_id, "document_id": self.document_id,
            "title": self.title, "messages": self.messages,
            "created_at": self.created_at,
        }
