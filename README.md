# Claude Code Handoff Bundle: Internal Policy RAG

This ZIP contains a PRD/implementation handoff for finishing the internal-policy RAG MVP in Claude Code.

## Contents

- `PRD.md` — complete product requirements and implementation plan
- `docs/composio-notion-setup.md` — Composio/Notion OAuth setup notes
- `docs/open-notebook-setup.md` — Open Notebook model setup notes
- `docs/parser-layer.md` — LLMParse/LiteParse parser layer notes
- `.env.example` — environment variable template without secrets

## Target repo

```text
/opt/data/workspace/internal-policy-rag-chatbot
```

## First Claude Code prompt

```text
Read PRD.md in this handoff bundle. Then inspect /opt/data/workspace/internal-policy-rag-chatbot. Implement the tasks sequentially with tests. Do not hard-code or print secrets. Start by verifying Composio tool execution for Notion using env vars, then implement scripts/import_composio_notion_docs.py.
```
