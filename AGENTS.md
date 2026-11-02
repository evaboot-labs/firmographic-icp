# Agent instructions

This repo defines a B2B ideal customer profile (ICP) from firmographic data. Your AI Agent reads the industry, headcount, headquarters, headcount growth, company type, founding year and revenue of the accounts the user won and lost through Evaboot, compares them value by value, writes the values that win more often into `ICP.md`, and turns them into a LinkedIn Sales Navigator account search.

1. Follow the skill in `skills/firmographic-icp/SKILL.md` step by step.
2. The accounts go in `ACCOUNTS.md`. If it says `Status: EXAMPLE`, ask the user for their own won and lost deals and rewrite the table.
3. `icp.py` builds the searches, compares the accounts and writes the Sales Navigator account search. Python 3, no packages.
4. If the Evaboot MCP tools are missing, follow `docs/connect-your-agent.md`.
5. If the user wants it in n8n instead, follow `docs/n8n.md` with them one step at a time.

Confirm with the user before the exports (1 Evaboot credit per account). Never guess whether an account was won or lost: the outcome comes from the user's CRM or the user. Never ask for or handle an API key: the user writes it into `.env`. Never commit `.env` or `data/`: they hold real people's data and secrets.
