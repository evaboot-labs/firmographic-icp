---
name: firmographic-icp
description: Define a B2B ideal customer profile (ICP) from firmographic data - read the industry, headcount, headquarters, headcount growth, company type, founding year and revenue of the accounts you won and the accounts you lost through Evaboot, compare them value by value, write the values that win more often into ICP.md, and turn them into a LinkedIn Sales Navigator account search. Use when the user asks to define or update their ideal customer profile, find which companies they win, compare won and lost deals, or turn closed deals into Sales Navigator filters.
---

# Firmographic ICP

This skill runs inside a clone of https://github.com/evaboot-labs/firmographic-icp: it uses the repo's `icp.py`, `ACCOUNTS.md` and `docs/`. If `icp.py` is not in the working directory, clone the repo and work from there.

You do the Sales Navigator and Evaboot work through the Evaboot MCP server (`https://mcp.evaboot.com/mcp`). `icp.py` builds the searches, compares won and lost accounts and writes the account search. It needs Python 3 and nothing else.

## Rules

- Confirm with the user before the exports. Show the number of accounts and the cost (1 Evaboot credit per account, one row each), then wait for a yes.
- The outcomes come from the user's CRM or the user. Never guess whether an account was won or lost.
- Never ask for or paste an API key. The user writes `EVABOOT_API_KEY` into `.env` (`docs/connect-your-agent.md`).
- Print every Sales Navigator URL as a Markdown link with the URL in angle brackets: `[Open in Sales Navigator](<url>)`.
- Say how many accounts the ICP rests on. Under 20 won and 20 lost, call it a first guess.

## Step 0: check the setup

1. If the Evaboot MCP tools are missing, walk the user through `docs/connect-your-agent.md`, then ask them to restart the agent from this folder.
2. Call `get_daily_export_quota`. If `has_valid_salesnav` is false, ask the user to sign in to Evaboot in Chrome, open any Sales Navigator search with the Evaboot extension, and click **Export with Evaboot**, then call it again.
3. Run `mkdir -p data`.

## Step 1: the accounts

1. Ask for the deals closed in the last 12 to 24 months: won and lost, 20 of each if they have them. Read them from the user's CRM connector if there is one (closed-won and closed-lost deals with their company), else ask for a list.
2. For each account, fill one row of the `ACCOUNTS.md` table: the company, its LinkedIn company id (the number in `linkedin.com/company/<id>` or in the Sales Navigator company URL) and `won` or `lost`. Ask the user for the LinkedIn URL when you cannot read it. Set `Status: yours`.
3. Leave out deals lost for a reason that is not the company (no budget this year, champion left) only if the user says so. Ask once.

## Step 2: the firmographics

1. Print one search per account, the account's CXOs:

```bash
python3 icp.py urls ACCOUNTS.md
```

2. On the user's yes, call `export_sn_search_or_list` for each line with `search_url` = the URL, `name` "ICP <LinkedIn id>" and `max_results: 1`. One exported row carries all the company fields. Run them in parallel; poll each with `get_export` and `limit: 0` until `EXECUTED`.
3. Call `get_export` for each and write every row into one JSON list in `data/rows.json`. An account with 0 rows has no CXO on Sales Navigator: tell the user, `icp.py` leaves it out.

## Step 3: compare won and lost

```bash
python3 icp.py compare data/rows.json ACCOUNTS.md
```

It writes `ICP.md`: for each attribute (industry, employees, HQ country, headcount growth over 1 year, company type, founding year, revenue), the won and lost count and the win rate of each value. A value is in the ICP when it wins more often than the average and has at least 2 wins.

Show the user the "Your ICP" list and the table. Ask about each value they want to drop or add: they know deals the data does not. Edit the "Your ICP" list in `ICP.md` to match; values are separated by `;`.

## Step 4: the Sales Navigator account search

```bash
python3 icp.py filters ICP.md
```

1. Show the account search as a link. It holds industry, company headcount, headquarters and headcount growth. Company type, founding year and revenue have no account filter here: they stay in `ICP.md` as checks for the list.
2. If it prints an unknown industry or country, ask the user to pick it in a Sales Navigator search, read its id in the URL, and add it to `INDUSTRY`, `COUNTRY` or `HEADCOUNT` in `icp.py`.
3. The user saves the search in Sales Navigator. To find the people inside those accounts and export them, see https://github.com/evaboot-labs/lookalike-prospect-list. To score a list against `ICP.md`, see https://evaboot.com/blog/ai-powered-fit-scoring-for-icp-lead-list.

To run it from n8n instead, follow `docs/n8n.md`.
