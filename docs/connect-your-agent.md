# Connect your AI Agent

The ICP builder needs one MCP server: Evaboot.

## 1. Accounts

- An [Evaboot account](https://dash.evaboot.com/accounts/signup/?last_click_origin=firmographic-icp-repo) with credits, and a Sales Navigator seat connected to it.

## 2. Get the repo

```bash
git clone https://github.com/evaboot-labs/firmographic-icp
cd firmographic-icp
cp .env.example .env
```

## 3. Connect the MCP server

**Claude Code:** write your key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/) into `.env` as `EVABOOT_API_KEY`, run `set -a; . ./.env; set +a`, then start Claude Code from this folder. The repo's `.mcp.json` connects Evaboot.

**Claude (web and desktop app):** *Settings > Connectors > Add custom connector*: name `Evaboot`, URL `https://mcp.evaboot.com/mcp`. Sign in to Evaboot and approve. Upload `ACCOUNTS.md` and `icp.py` to the chat, or paste the skill.

**Codex, Cursor:** add `https://mcp.evaboot.com/mcp` as an HTTP MCP server with the header `Authorization: Bearer <your key>`.

## 4. Check

Ask your AI Agent: "Check my Evaboot quota and whether my Sales Navigator is connected." A quota and `has_valid_salesnav: true` mean you are ready.

Back to the [README](../README.md).
