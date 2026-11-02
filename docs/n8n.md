# Run it in n8n

[`n8n/firmographic-icp.json`](../n8n/firmographic-icp.json) builds the same ICP from an n8n form, when you prefer a form to a chat. `n8n/build_workflow.py` regenerates it.

## What runs

1. **Your won and lost accounts** (form): paste the `ACCOUNTS.md` table.
2. **Accounts** (Code): reads the table and checks there are at least 3 won and 3 lost accounts.
3. **Review the cost** (form): 1 Evaboot credit per account. Nothing is spent until you choose *Read the firmographics*.
4. **One search per account** (Code) and **Export one row each** (Evaboot MCP): one Sales Navigator search per account, its CXOs, exported with `max_results` 1. That row carries the company's firmographics.
5. **Wait 60 s**, **Check the exports** (Evaboot MCP) and **All done?** (Code): waits until every export has finished.
6. **Compare won and lost** (Code): the win rate of each value, the same rule as `icp.py`, and the Sales Navigator account search.
7. **Your ICP** (form): the ICP and a link to the account search.

## Set it up

1. **Import** the JSON: *Workflows > Import from file*.
2. **Add one credential:** **Bearer Auth** named `Evaboot MCP (Bearer)`, with your key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/). Select it on the two Evaboot MCP nodes.
3. **Publish** the workflow and open the form URL of **Your won and lost accounts**.
4. **Test:** paste 3 won and 3 lost accounts first (6 credits).

An unknown industry or country shows on the last page: add its LinkedIn id to `INDUSTRY` or `COUNTRY` in **Compare won and lost**.

Back to the [README](../README.md).
