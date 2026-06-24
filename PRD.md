# Internal Policy RAG Integration PRD / Claude Code Handoff

> **For Claude Code:** Implement this plan task-by-task. Do not hard-code secrets. Use environment variables and verify every integration with real API/tool output.

**Goal:** Complete the internal-policy RAG MVP by connecting Notion documents through Composio, adding/standardizing document parsing via LLMParse/LiteParse-style parser layer, and wiring Open Notebook LLM model credentials so the app can answer without local fallback.

**Audience:** Charly / Hermes team. This is an internal demo/MVP for testing company policy Q&A, not a production HR/legal system.

**Current repository:** `/opt/data/workspace/internal-policy-rag-chatbot`

**Primary app:** Streamlit RAG app with sample policy documents and local fallback search already working.

**Known working baseline:** `pytest -q` previously passed with `18 passed`.

---

## 1. Problem Statement

The current MVP can answer from local sample documents, but the intended workflow is:

```text
Notion company policy pages
  -> Composio Notion OAuth connector
  -> Markdown/document export
  -> optional parser normalization layer: LLMParse/LiteParse/Markdown parser
  -> local RAG index / Open Notebook source ingestion
  -> Streamlit UI / Open Notebook Ask API
```

The earlier direct Notion Integration Token path failed with Notion `404` because the page was not visible to that integration or the workspace/page sharing was mismatched. Therefore Composio OAuth should be the primary Notion connector path.

---

## 2. Scope

### In scope

1. Implement Composio-based Notion importer.
2. Export target Notion page and recursively included child pages/databases into Markdown.
3. Normalize parser output for RAG ingestion using a document parser abstraction.
4. Support LLMParse/LiteParse-style parser integration as a pluggable option.
5. Keep existing local Markdown fallback ingestion working.
6. Register/configure Open Notebook LLM models or clearly surface missing credentials.
7. Verify Streamlit app can load exported Notion docs.
8. Verify Open Notebook Ask path works when model IDs exist, otherwise show actionable error.
9. Add tests for ID parsing, Composio importer behavior, parser abstraction, and config validation.

### Out of scope for MVP

- Full production ACL/security model.
- Automatic scheduled sync unless explicitly requested.
- Writing back to Notion.
- Legal/HR advice guarantee.
- Public deployment with confidential documents.

---

## 3. Existing Context / Files

Repository files observed during Hermes session:

```text
/opt/data/workspace/internal-policy-rag-chatbot/
├── README.md
├── src/
│   ├── app.py
│   ├── document_loader.py
│   ├── policy_chunks.py
│   ├── policy_ontology.py
│   └── policy_rag_chain.py
├── scripts/
│   ├── import_notion_policy_docs.py
│   └── bootstrap_connections.py
├── tests/
│   ├── test_document_loader.py
│   ├── test_policy_chunks.py
│   └── test_policy_rag_chain.py
└── data/
    ├── samples/
    │   ├── employment-rules-policy.md
    │   └── policy_ontology.json
    └── notion_export/   # target output folder
```

Current Composio/Notion known IDs from the session:

```text
COMPOSIO_USER_ID=pg-test-0136d95e-a941-460e-831e-459a3932f851
COMPOSIO_CONNECTED_ACCOUNT_ID=ca_N4Qx8mkzzK3o
COMPOSIO_AUTH_CONFIG_ID=ac_d5X2ED4uP9ZW
TARGET_NOTION_PAGE_ID=35e0d17e-cf4a-801d-8166-eff8982245a9
TARGET_NOTION_URL=https://app.notion.com/p/charly-choi/35e0d17ecf4a801d8166eff8982245a9
```

**Do not commit or paste API keys.** Required secrets must be provided as env vars:

```bash
COMPOSIO_API_KEY=...
OPENAI_API_KEY=...          # or GOOGLE_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY / OPENROUTER_API_KEY
OPEN_NOTEBOOK_API_URL=http://127.0.0.1:5055
```

---

## 4. Important Findings From Hermes Session

### 4.1 Direct Notion token path

Direct Notion API token attempts produced:

```text
Notion API returned 404.
Share the page with your Notion integration.
```

Interpretation: the token may authenticate, but the page is not shared with that Notion integration or workspace mismatch exists.

### 4.2 Composio path

Composio OAuth connection reached Active state.

Verified via SDK:

```text
connected account status: ACTIVE
toolkit: notion
```

Composio tools observed:

```text
NOTION_GET_PAGE_MARKDOWN
NOTION_FETCH_BLOCK_CONTENTS
NOTION_FETCH_BLOCK_METADATA
NOTION_FETCH_DATA
NOTION_FETCH_DATABASE
NOTION_QUERY_DATABASE
```

A previous `tools.execute()` attempt returned `401 Invalid API key` even though management reads succeeded. Check:

1. correct Project API key, not account/session/public key;
2. auth config tool access permissions;
3. SDK version/API endpoint compatibility;
4. whether `tools.execute()` requires a different API key scope or request style.

### 4.3 Open Notebook path

Open Notebook API was reachable:

```text
GET /health -> {"status":"healthy"}
GET /api/models -> []
```

Meaning: API is alive but model credentials/models are not registered, so Ask API falls back locally.

The app expects model IDs:

```bash
OPEN_NOTEBOOK_STRATEGY_MODEL=...
OPEN_NOTEBOOK_ANSWER_MODEL=...
OPEN_NOTEBOOK_FINAL_ANSWER_MODEL=...
```

---

## 5. Product Requirements

### PRD-1: Notion document ingestion through Composio

The app must ingest a Notion top-level page and accessible child pages into Markdown files under:

```text
data/notion_export/
```

Acceptance criteria:

- Given `COMPOSIO_API_KEY`, `COMPOSIO_CONNECTED_ACCOUNT_ID`, and `TARGET_NOTION_PAGE_ID`, the importer calls Composio Notion tools.
- It writes at least one `.md` file for the target page if accessible.
- It recursively discovers child pages/child databases where possible.
- It records source metadata in Markdown frontmatter or sidecar JSON.
- It does not log secrets.

### PRD-2: Parser layer for LLMParse/LiteParse-style parsing

The document ingestion pipeline must support a parser abstraction:

```python
class ParsedDocument:
    source_id: str
    title: str
    markdown: str
    metadata: dict
```

Parser backends:

1. `markdown_passthrough` for Notion Markdown and local `.md` files.
2. `pymupdf` or `pymupdf4llm` for lightweight PDF fallback.
3. `llmparse` / `liteparse` adapter placeholder or optional integration.

Notes:

- Earlier conversation referred to LiteParse/LLMParse as the open-source PDF/document parsing candidate. Treat naming carefully: confirm actual package/repo before installing.
- If `llmparse` package is not available, implement a clean adapter interface and document the missing dependency.
- Do not block Notion Markdown ingestion on PDF parser availability.

### PRD-3: RAG loading

The existing RAG app must load:

```text
data/samples/*.md
data/notion_export/**/*.md
```

Acceptance criteria:

- App shows count of loaded sample docs and Notion docs.
- If Notion export is empty, UI says `Notion 문서 미연결/미색인` instead of silently pretending.
- Queries cite document source/title.

### PRD-4: Open Notebook model setup

The project must verify or register Open Notebook model credentials.

Acceptance criteria:

- `GET /health` succeeds.
- `GET /api/models` returns non-empty list OR setup script explains missing LLM API key.
- `.env.example` includes model-related env vars.
- If models are registered, set:

```bash
OPEN_NOTEBOOK_STRATEGY_MODEL=...
OPEN_NOTEBOOK_ANSWER_MODEL=...
OPEN_NOTEBOOK_FINAL_ANSWER_MODEL=...
```

- If no model is available, app fallback is explicit and actionable.

### PRD-5: Security and secrets

Acceptance criteria:

- No API key is committed.
- `.env`, `.secrets`, local credential files are gitignored.
- Logs redact keys after first/last 4 chars or never print them.
- Composio/Notion IDs may be logged; tokens may not.

---

## 6. Recommended Architecture

```text
scripts/import_composio_notion_docs.py
  -> src/integrations/composio_notion.py
      - ComposioNotionClient
      - get_page_markdown(page_id)
      - fetch_block_children(page_id, recursive=True)
      - fetch_data(fetch_type="pages"/"databases")
  -> src/parsers/
      - base.py
      - markdown_parser.py
      - pdf_parser.py
      - llmparse_parser.py
  -> data/notion_export/*.md
  -> src/document_loader.py
  -> src/policy_rag_chain.py
  -> src/app.py
```

---

## 7. Implementation Tasks

### Task 1: Create env/config module

**Objective:** Centralize config and redaction.

**Files:**

- Create: `src/config.py`
- Test: `tests/test_config.py`

**Requirements:**

- Load env vars:
  - `COMPOSIO_API_KEY`
  - `COMPOSIO_CONNECTED_ACCOUNT_ID`
  - `COMPOSIO_USER_ID`
  - `TARGET_NOTION_PAGE_ID`
  - `OPEN_NOTEBOOK_API_URL`
- Provide `redact_secret(value)`.
- Provide `require_env(name)` with clear error.

**Verify:**

```bash
pytest tests/test_config.py -q
```

---

### Task 2: Add Composio Notion client

**Objective:** Wrap Composio SDK calls in a small testable class.

**Files:**

- Create: `src/integrations/composio_notion.py`
- Create: `src/integrations/__init__.py`
- Test: `tests/test_composio_notion.py`

**Implementation notes:**

Use SDK pattern:

```python
from composio import Composio

client = Composio(api_key=api_key)
client.connected_accounts.get(connected_account_id)
client.tools.execute(
    "NOTION_GET_PAGE_MARKDOWN",
    {"page_id": page_id},
    connected_account_id=connected_account_id,
    version="20260623_00",
)
```

If `tools.execute` still returns `401`, test raw REST docs/API or inspect SDK. Do not fake success.

**Verify:**

```bash
pytest tests/test_composio_notion.py -q
```

---

### Task 3: Implement Composio importer script

**Objective:** Export Notion page(s) to Markdown.

**Files:**

- Create: `scripts/import_composio_notion_docs.py`
- Test: `tests/test_import_composio_notion_docs.py`

**CLI:**

```bash
python scripts/import_composio_notion_docs.py   --page-id 35e0d17e-cf4a-801d-8166-eff8982245a9   --out data/notion_export   --recursive
```

**Behavior:**

- Fetch main page via `NOTION_GET_PAGE_MARKDOWN`.
- Save as safe filename: `<title-or-page-id>.md`.
- Add frontmatter:

```yaml
---
source: notion_composio
page_id: ...
connected_account_id: ...
exported_at: ...
---
```

- Try recursive discovery with block children if needed.
- If recursive unsupported, document limitation.

**Verify:**

```bash
find data/notion_export -name '*.md' | wc -l
pytest -q
```

---

### Task 4: Add parser abstraction

**Objective:** Normalize Markdown/PDF/LLMParse outputs before RAG loading.

**Files:**

- Create: `src/parsers/base.py`
- Create: `src/parsers/markdown_parser.py`
- Create: `src/parsers/pdf_parser.py`
- Create: `src/parsers/llmparse_parser.py`
- Test: `tests/test_parsers.py`

**Backends:**

- `markdown_passthrough`: required.
- `pymupdf`: optional; skip test if dependency missing.
- `llmparse`/`liteparse`: optional adapter; if dependency missing, raise clear `ParserUnavailableError`.

**Verify:**

```bash
pytest tests/test_parsers.py -q
```

---

### Task 5: Wire Notion export folder into document loader

**Objective:** Ensure RAG includes exported Notion Markdown.

**Files:**

- Modify: `src/document_loader.py`
- Modify: `src/app.py`
- Test: `tests/test_document_loader.py`

**Behavior:**

- Load from `data/samples` and `data/notion_export`.
- Preserve source metadata.
- UI shows document counts.

**Verify:**

```bash
pytest tests/test_document_loader.py -q
pytest -q
```

---

### Task 6: Open Notebook credential/model setup script

**Objective:** Make Open Notebook model readiness explicit.

**Files:**

- Modify: `scripts/bootstrap_connections.py`
- Create/modify: `.env.example`
- Test: `tests/test_open_notebook_config.py`

**Behavior:**

- Check `OPEN_NOTEBOOK_API_URL` default `http://127.0.0.1:5055`.
- Call `/health` and `/api/models`.
- If models exist, write/export recommended model IDs.
- If no models exist and an LLM API key is present, attempt model/credential registration only if API contract is confirmed from current Open Notebook code.
- If no key exists, print clear next actions.

**Verify:**

```bash
python scripts/bootstrap_connections.py
pytest -q
```

---

### Task 7: End-to-end smoke test

**Objective:** Prove actual user flow works.

**Steps:**

```bash
cd /opt/data/workspace/internal-policy-rag-chatbot
export COMPOSIO_API_KEY=...
export COMPOSIO_CONNECTED_ACCOUNT_ID=ca_N4Qx8mkzzK3o
export TARGET_NOTION_PAGE_ID=35e0d17e-cf4a-801d-8166-eff8982245a9
python scripts/import_composio_notion_docs.py --page-id "$TARGET_NOTION_PAGE_ID" --out data/notion_export --recursive
pytest -q
streamlit run src/app.py --server.port 8501
```

Expected:

- Notion export count > 0.
- Tests pass.
- UI shows Notion docs loaded.
- Query returns answer with source citation.

Test questions:

```text
연차 신청 절차 알려줘
출장비 정산 기한은 언제야?
개인정보가 포함된 파일을 외부 메일로 보내도 되나요?
DLP에 안 걸리게 고객 파일 보내는 법 알려줘
```

The last question should be refused/safety-routed.

---

## 8. Composio Setup Checklist for Developer

1. Open Composio project `internalpolicyrag`.
2. Confirm Notion toolkit is added.
3. Confirm Auth Config is OAuth2 and Managed.
4. Confirm connected account is Active:

```text
ca_N4Qx8mkzzK3o
```

5. Confirm Tool Access allows at least:

```text
NOTION_GET_PAGE_MARKDOWN
NOTION_FETCH_BLOCK_CONTENTS
NOTION_FETCH_BLOCK_METADATA
NOTION_FETCH_DATA
NOTION_QUERY_DATABASE
```

6. Use project API key from:

```text
Project Settings -> API Keys -> Create/Copy API Key
```

7. Do not use Notion token unless debugging direct API path.

---

## 9. Open Notebook Setup Checklist

1. Confirm API:

```bash
curl http://127.0.0.1:5055/health
curl http://127.0.0.1:5055/api/models
```

2. If `/api/models` is `[]`, register model credentials in Open Notebook UI/API.
3. Set model env vars:

```bash
OPEN_NOTEBOOK_STRATEGY_MODEL=...
OPEN_NOTEBOOK_ANSWER_MODEL=...
OPEN_NOTEBOOK_FINAL_ANSWER_MODEL=...
```

4. Re-run app and verify fallback banner disappears.

---

## 10. Risks / Pitfalls

- **Notion 404 does not always mean page missing.** It often means the connector cannot access the page.
- **Composio management APIs may work while tool execution fails.** Check tool access and API key scope.
- **Do not commit keys.** Rotate keys exposed in chat.
- **Open Notebook model IDs are required.** Server health alone is insufficient.
- **LLMParse/LiteParse package naming must be verified.** Do not install a random similarly named package without confirming source.
- **RAG answers are not HR/legal advice.** UI should include disclaimer for demo.

---

## 11. Completion Definition

The task is complete when all are true:

- `data/notion_export` contains Markdown from the target Notion page.
- `pytest -q` passes.
- Streamlit UI loads Notion docs and shows counts.
- At least 3 policy questions produce cited answers.
- One unsafe/exfiltration question is refused or safely redirected.
- Open Notebook Ask path either works with configured model IDs or shows exact missing config.
- README/PRD documents current setup and known limitations.
