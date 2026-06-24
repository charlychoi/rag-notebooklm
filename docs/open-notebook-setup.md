# Open Notebook Setup Notes

Observed baseline:

```text
GET http://127.0.0.1:5055/health -> {"status":"healthy"}
GET http://127.0.0.1:5055/api/models -> []
```

This means Open Notebook API is alive but no model is configured.

Required model env vars for fallback-free Ask:

```bash
OPEN_NOTEBOOK_API_URL=http://127.0.0.1:5055
OPEN_NOTEBOOK_STRATEGY_MODEL=...
OPEN_NOTEBOOK_ANSWER_MODEL=...
OPEN_NOTEBOOK_FINAL_ANSWER_MODEL=...
```

If `/api/models` is empty, register a credential/model using Open Notebook UI/API. Use one provider key:

```bash
OPENAI_API_KEY=...
# or GOOGLE_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY / OPENROUTER_API_KEY
```

The app should show a clear fallback banner if models are missing.
