# Composio -> Notion Setup Notes

Known IDs:

```text
COMPOSIO_USER_ID=pg-test-0136d95e-a941-460e-831e-459a3932f851
COMPOSIO_CONNECTED_ACCOUNT_ID=ca_N4Qx8mkzzK3o
COMPOSIO_AUTH_CONFIG_ID=ac_d5X2ED4uP9ZW
TARGET_NOTION_PAGE_ID=35e0d17e-cf4a-801d-8166-eff8982245a9
```

Required env var:

```bash
export COMPOSIO_API_KEY="..."
```

Required enabled tools:

```text
NOTION_GET_PAGE_MARKDOWN
NOTION_FETCH_BLOCK_CONTENTS
NOTION_FETCH_BLOCK_METADATA
NOTION_FETCH_DATA
NOTION_QUERY_DATABASE
```

SDK check:

```bash
uv run --with composio python - <<'PY'
import os
from composio import Composio
c = Composio(api_key=os.environ['COMPOSIO_API_KEY'])
print(c.connected_accounts.get(os.environ['COMPOSIO_CONNECTED_ACCOUNT_ID']))
PY
```

Tool execution check:

```bash
uv run --with composio python - <<'PY'
import os
from composio import Composio
c = Composio(api_key=os.environ['COMPOSIO_API_KEY'])
res = c.tools.execute(
    'NOTION_GET_PAGE_MARKDOWN',
    {'page_id': os.environ['TARGET_NOTION_PAGE_ID']},
    connected_account_id=os.environ['COMPOSIO_CONNECTED_ACCOUNT_ID'],
    version='20260623_00',
)
print(res)
PY
```

If management reads work but tool execution returns `401 Invalid API key`, check Project API Key scope and Auth Config Tool Access.
