# ✦ NEXUS AI — Document Intelligence Platform

Modular, document-type-independent **RAG platform**: upload a document (PDF / DOCX / TXT / MD),
ask in plain language, get a grounded, validated, quality-scored answer. LLM-first design —
Python orchestrates, the LLM understands.

> **Brand in UI:** `NEXUS AI / DOCUMENT INTELLIGENCE` (see `ui/sidebar.py`, `ui/styles.py`).

## Architecture

```
USER → Streamlit UI (app.py)
  → 01 Document Intake: identify → parse → ingest
  → 02 Conversation (multi-chat): understand → retrieve → generate → validate → evaluate
  → 03 Reset: Start New Task (isolated, no cross-document leakage)
```

Pipeline in code (`app.py` / `rag/pipeline.py`):

```python
document = parse_document(file)              # document/parser.py
out = pipeline.ingest(document)              # understand → preprocess → chunk → embed → store
query = understand_requirement(user_input)   # llm/requirement_understanding.py (+ chat history)
context = retrieve(query)                    # rag/retriever.py (cosine + keyword rerank, doc-filtered)
response, prompt, validation = generate_response(context, query)  # llm/generation.py + repair loop
quality = evaluate_quality(response)         # llm/evaluation.py
```

Ingest order is intentional: **embed BEFORE clearing the old index** (atomic swap), so a failed
ingest never wipes a working index. Query side **auto-selects the LLM per task** before retrieval.

## Features

- 📄 **Parsing** — PDF (`pypdf`), DOCX, TXT/MD with page numbers + metadata (`document/parser.py`, `document/identifier.py`)
- 🧠 **LLM document understanding** — type, topics, sections, entities, with offline fallback (`document/structure.py`, `llm/document_understanding.py`)
- 🧹 **Preprocessing** — cleaned text + notes (`document/preprocess.py`)
- ✂️ **Semantic chunking** — rich metadata (`chunk_id`, `page`, `section`, `heading`, `topic`) (`document/chunker.py`)
- 🔎 **RAG retrieval** — API-only embeddings (OpenRouter, auto-selected) + isolated in-memory `VectorStore` scoped per `document_id`; cosine search **filtered to active document** + keyword rerank (`rag/embeddings.py`, `rag/vector_store.py`, `rag/retriever.py`)
- 💬 **Requirement understanding** — intents: `summarize / extract / classify / retrieve / generate / custom` with task-hint buttons (SUMMARY, EXTRACT, CLASSIFY, RETRIEVE, GENERATE, CUSTOM) (`llm/requirement_understanding.py`)
- 💭 **Multi-chat conversational workspace** — one document + one shared RAG index, many independent chats; history-aware follow-ups resolve `it / this / that section` via `chat/manager.py::build_contextual_query` (last 3 turns); deterministic titles, per-chat delete, `↻ Regenerate last answer`
- 🧩 **Prompt engine** — reusable templates per task (`prompts/engine.py`, `prompts/{summarization,extraction,classification,retrieval,generation,evaluation,fragments}.py`)
- ✅ **Validation → repair/regenerate loop** — up to `MAX_RETRIES` (`validation/output_validator.py`, `llm/generation.py`)
- ⭐ **Quality evaluation** — relevance, consistency, factuality, completeness, format (`validation/quality_checker.py`, `llm/evaluation.py`)
- 🔍 **Transparency** — retrieved chunks + scores, interpreted requirement spec, full prompt, selected models + reasons visible in UI/chat expanders
- 🩹 **Self-healing index** — live index-size check, `🔄 Re-index document` one-click recovery (bytes kept in session), auto-rebuild on SEND if index was lost
- 🔄 **Start New Task reset** — clears document, chunks, embeddings, chats, results; session isolation so Doc A never leaks into Doc B (`utils/session.py`)
- 📊 **Sidebar ops** — Workspace dots (Document / Understanding / Retrieval + vector count / Generation / Validation / Evaluation), System dots (LLM / RAG Engine / Embeddings API), Retrieval Tuning (`Top-K 1–10`, `Creativity/temperature 0.0–1.0`), Conversations list
- 🩺 **Diagnostics + logging** — `diagnose.py` bypasses Streamlit for real tracebacks; `logs/` persists ingest/generate errors (`utils/logging.py`)
- ⚡ **No local models** — Streamlit starts instantly; LLM + embeddings are all API calls

## Tech Stack

Python · Streamlit · OpenRouter (LLM + embeddings, auto-selected) · pypdf · python-docx · numpy · requests · python-dotenv

`requirements.txt`: `streamlit>=1.33`, `requests>=2.31`, `python-dotenv>=1.0`, `pypdf>=4.0`, `python-docx>=1.1`, `numpy>=1.26`

## Folder Structure

```
app.py                  # Streamlit entry: intake → multi-chat → reset orchestration
diagnose.py             # Standalone ingest diagnostic (no Streamlit)
config/settings.py      # Single source of truth — all config + env parsing
document/               # identifier.py, parser.py, structure.py, preprocess.py, chunker.py
llm/                    # client.py (only OpenRouter caller), model_selector.py,
                        # requirement_understanding.py, document_understanding.py,
                        # generation.py, evaluation.py
rag/                    # pipeline.py, embeddings.py, embedding_selector.py,
                        # vector_store.py, retriever.py
prompts/                # engine.py + summarization/extraction/classification/
                        # retrieval/generation/evaluation/fragments templates
validation/             # output_validator.py, quality_checker.py
models/schemas.py       # ParsedDocument / Chunk / RequirementSpec / etc.
chat/manager.py         # Multi-chat CRUD + contextual query (no Streamlit dep)
ui/                     # sidebar.py, upload.py, chat.py, components.py, styles.py
utils/                  # session.py (task vs app state), logging.py, helpers.py
logs/                   # Persisted ingest/generate errors
```

Spec: `config/settings.py` = all config; `llm/client.py` = only OpenRouter caller;
`rag/{embeddings,vector_store,retriever,pipeline}.py` = swappable RAG layers;
`llm/model_selector.py` + `rag/embedding_selector.py` = only places that pick models.

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env   # then set OPENROUTER_API_KEY
```

Requires Python 3.10+ recommended.

## Environment Variables

| Var | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | **Required** (LLM + embeddings) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API endpoint |
| `OPENROUTER_TIMEOUT` | `60` | Request timeout (s) |
| `OPENROUTER_SITE_URL` / `OPENROUTER_APP_NAME` | `""` / `doc-intelligence-platform` | Optional OpenRouter headers |
| `AUTO_SELECT_MODELS` | `true` | Automatic LLM + embedding selection |
| `OPENROUTER_MODEL` | `""` (override only) | Pin chat model — used only when `AUTO_SELECT_MODELS=false` |
| `LLM_EFFICIENT_MODEL` | `openai/gpt-4o-mini` | Simple tasks (`classify`, `retrieve`, small docs) |
| `LLM_GENERAL_MODEL` | `openai/gpt-4o-mini` | Standard tasks (`summarize`, `extract`, `retrieve`) |
| `LLM_REASONING_MODEL` | `openai/gpt-4o` | Complex/large/reasoning tasks (`generate`, `custom`, large docs) |
| `EMBEDDING_PROVIDER` | `openrouter` | Embedding provider id |
| `EMBEDDING_MODEL` | `nvidia/nemotron-3-embed-1b:free` | Primary embedding model (2048d) |
| `EMBEDDING_FALLBACK_MODEL` | `openai/text-embedding-3-small` | Fallback embedding model (1536d) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `120` | Chunking (chars) |
| `TOP_K` | `5` | Default retrieved chunks (slider 1–10 overrides per query) |
| `MAX_RETRIES` | `3` | Validate → repair/regenerate attempts |
| `MAX_UPLOAD_MB` | `25` | Upload size guard |
| `LARGE_DOC_CHARS` | `60000` | Threshold for “large doc” → reasoning-tier LLM (>60 chunks also counts) |

Supported extensions: `.pdf`, `.docx`, `.doc`, `.txt`, `.md` (legacy binary `.doc` may not parse — prefer `.docx`).

> Normal usage needs **only** `OPENROUTER_API_KEY`. The `*_MODEL` vars are developer overrides.

## Automatic Model Selection

You never pick a model. Per task, the app runs:

```
requirement + doc stats → llm/model_selector.py::select_llm → OpenRouter chat model
document stats          → rag/embedding_selector.py         → embedding API model
```

Tiers (`TaskContext`: intent, doc_chars, chunk_count, needs_reasoning):

- **efficient** — `classify` / `retrieve` on small docs → `LLM_EFFICIENT_MODEL`
- **general** — standard `summarize` / `extract` / `retrieve` → `LLM_GENERAL_MODEL`
- **reasoning** — `generate` / `custom`, `needs_reasoning=true`, or large doc (`>= LARGE_DOC_CHARS` chars or `> 60` chunks) → `LLM_REASONING_MODEL`
- **override** — only when `AUTO_SELECT_MODELS=false` + `OPENROUTER_MODEL` / `EMBEDDING_MODEL` set (debugging)

Embeddings carry expected dimensions (`nemotron-3-embed-1b:free=2048`, `text-embedding-3-small=1536`, …) and each index is tagged with `provider:model` so vectors from different models are never mixed. The choice + reason is surfaced per answer (`model_config`) and in the UI.

## How to Run

```bash
streamlit run app.py
```

Without an API key the app still parses, chunks, and shows structure; retrieval, generation, and evaluation need the key (API-based embeddings only — no local downloads, per design).

Bypass Streamlit to debug indexing:

```bash
python diagnose.py <path-to-document.pdf>
# parse → understand → preprocess → chunk → embed (real API) → store → retrieve, with tracebacks
```

## How RAG Works Here

1. **Ingest**: `identify → parse → LLM structure → preprocess → semantic chunks → embed (before clearing old index) → atomic swap into `VectorStore` (scoped per `document_id`)`.
2. **Query**: task-hint + text → LLM `RequirementSpec` (intent/entities) → contextual query folds last 3 chat turns → embed query → cosine search **filtered to active document** → keyword rerank → top-K context.
3. **Generate**: prompt engine merges system + task + requirement + cited context → OpenRouter (`Creativity` slider = temperature) → validate → repair loop → evaluate quality → chat message with `sources / spec / quality / validation / model`.

## Using the App

1. **01 · Document Intake** — upload PDF/DOCX/TXT/MD → `Document ready: N page(s), M chunks, K vectors in index.` If the index is empty you get `⚠️ index is empty` + `🔄 Re-index document` (no re-upload needed).
2. **02 · Conversation** — pick a task (`SUMMARY / EXTRACT / CLASSIFY / RETRIEVE / GENERATE / CUSTOM`), type a question, `SEND →`. Follow-ups understand pronouns. Each answer expander shows sources (chunk_id, page, section, score), interpreted requirement, quality, validation, model.
3. **Sidebar** — switch/create/delete chats (per-document), watch Workspace/System dots, tune `Top-K sources` and `Creativity`, read `About NEXUS AI`.
4. **Reset** — `Start New Task` wipes document + RAG + all chats. Deleting one chat only deletes its history.

## Example Usage

- Question paper: *“Give me all AI-related questions asked between 2022 and 2025.”*
- Technical doc: *“Summarize the section about transformer architecture.”*
- Report: *“Extract revenue, profit, employee count and major risks.”*
- Follow-up: *“Explain it simply for a beginner.”* (resolves `it` from chat history)
- Any doc: *“Classify this document and list key entities.”*

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `LLM authentication failed / 401` | `OPENROUTER_API_KEY` missing/invalid in `.env` |
| `rate-limited / 429` | Wait + retry; check OpenRouter credits/rate limits |
| `The document index is empty` / `No relevant chunks found` | Embedding call failed — error is shown at upload; click `🔄 Re-index`, or run `python diagnose.py <file>` for the real traceback; kill duplicate `streamlit` processes and start one fresh |
| `Could not reach the LLM service / timeout` | Network issue; retry, check `OPENROUTER_BASE_URL` |
| Scanned PDF yields no text | Image-only PDF needs OCR (not included) |

Logs persist under `logs/` (`persist_error` / `persist_info`).

## Limitations

- Scanned-image PDFs (no text layer) need OCR (not included).
- In-memory vector store resets on app restart (swap in Chroma/FAISS for persistence).
- Legacy binary `.doc` may not parse; prefer `.docx`.
- Embeddings + generation require network + OpenRouter credits.

## Future Improvements

- OCR, table/figure extraction, persistent vector DB, multi-document comparison, persistent chat history, streaming output, eval harness.
