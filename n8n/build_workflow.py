"""Builds n8n/firmographic-icp.json. Run: python3 n8n/build_workflow.py

A form takes your won and lost accounts (the ACCOUNTS.md table). A review page shows the cost; on your yes Evaboot
exports one row per account (its CXOs' search, 1 row), which carries the company's firmographics. A Code node
compares won and lost value by value, the same way as icp.py, and the last page shows your ICP and the
Sales Navigator account search.
"""
import json
import uuid
from pathlib import Path

MCP = "https://mcp.evaboot.com/mcp"
EVABOOT_CRED = {"httpBearerAuth": {"id": "", "name": "Evaboot MCP (Bearer)"}}
FORM = "Your won and lost accounts"
FIELD = "Accounts (the ACCOUNTS.md table)"
HEADCOUNT = {"1 to 10": "B", "11 to 50": "C", "51 to 200": "D", "201 to 500": "E", "501 to 1000": "F",
             "1001 to 5000": "G", "5001 to 10000": "H", "10001+": "I"}
INDUSTRY = {"Software Development": 4, "Technology, Information and Internet": 6, "Financial Services": 43,
            "IT Services and IT Consulting": 96, "Business Consulting and Services": 11, "Advertising Services": 80,
            "Computer Games": 109, "Retail": 27, "Hospitals and Health Care": 14}
COUNTRY = {"France": 105015875, "United States": 103644278, "United Kingdom": 101165590, "Germany": 101282230,
           "Spain": 105646813, "Netherlands": 102890719, "Belgium": 100565514, "Switzerland": 106693272,
           "Canada": 101174742}

nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b, out=0):
    connections.setdefault(a, {}).setdefault("main", [])
    while len(connections[a]["main"]) <= out:
        connections[a]["main"].append([])
    connections[a]["main"][out].append({"node": b, "type": "main", "index": 0})


def mcp_call(name, tool, json_expr, pos):
    node(name, "@n8n/n8n-nodes-langchain.mcpClient", 1.1, {
        "endpointUrl": MCP, "authentication": "bearerAuth",
        "tool": {"__rl": True, "mode": "list", "value": tool, "cachedResultName": tool},
        "inputMode": "json", "jsonInput": json_expr, "options": {"timeout": 120000},
    }, pos, EVABOOT_CRED)


def code(name, js, pos, mode=None):
    params = {"jsCode": js}
    if mode:
        params["mode"] = mode
    node(name, "n8n-nodes-base.code", 2, params, pos)


def is_true(name, left, pos):
    node(name, "n8n-nodes-base.if", 2.2, {"conditions": {
        "options": {"caseSensitive": True, "typeValidation": "loose", "version": 2},
        "conditions": [{"id": str(uuid.uuid4()), "leftValue": left, "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "options": {}}, pos)


ACCOUNTS_JS = r"""
// Same as icp.py read_accounts: | Company | LinkedIn id | Outcome |, outcome won or lost.
const accounts = String($('__FORM__').first().json['__FIELD__']).split('\n')
  .map(l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()))
  .filter(c => c.length >= 3 && c[0] && c[0] !== 'Company' && !/^[-: ]+$/.test(c[0]))
  .map(c => ({ name: c[0], id: c[1].replace(/\D/g, ''), outcome: c[2].toLowerCase() }));
const bad = accounts.filter(a => !['won', 'lost'].includes(a.outcome) || !a.id);
if (bad.length) throw new Error('Each row needs a LinkedIn id and won or lost: ' + bad.map(a => a.name).join(', '));
const won = accounts.filter(a => a.outcome === 'won').length;
if (won < 3 || accounts.length - won < 3) throw new Error('List at least 3 won and 3 lost accounts (20 of each gives a real signal).');
return [{ json: { accounts, summary: `${won} won and ${accounts.length - won} lost accounts` } }];
""".replace("__FORM__", FORM).replace("__FIELD__", FIELD)

SPLIT_JS = r"""
// Same as icp.py urls: one search per account, its CXOs. One exported row carries the company fields.
return $('Accounts').first().json.accounts.map(a => {
  const urn = encodeURIComponent(encodeURIComponent('urn:li:organization:' + a.id));
  return { json: { ...a, url: 'https://www.linkedin.com/sales/search/people?query=(filters%3AList('
    + `(type%3ACURRENT_COMPANY%2Cvalues%3AList((id%3A${urn}%2CselectionType%3AINCLUDED)))%2C`
    + '(type%3ASENIORITY_LEVEL%2Cvalues%3AList((id%3A310%2CselectionType%3AINCLUDED)))))' } };
});
"""

DONE_JS = r"""
// Every account's export must be finished before the comparison; otherwise all go back to the wait.
const items = $input.all();
for (const i of items) {
  const r = i.json.structuredContent?.result || {};
  if (r.failure_reason || /FAIL|ERROR|CANCEL/i.test(r.status || '')) throw new Error(`An export stopped: ${r.search_name} ${r.status} ${r.failure_reason || ''}`);
}
const allDone = items.every(i => i.json.structuredContent?.result?.status === 'EXECUTED');
const polls = (items[0].json.polls || 0) + 1;
if (!allDone && polls > 60) throw new Error('Exports still not finished after an hour: ' + items.filter(i => i.json.structuredContent?.result?.status !== 'EXECUTED').map(i => i.json.structuredContent?.result?.search_name).join(', '));
return items.map(i => ({ json: { ...i.json, allDone, polls } }));
"""

COMPARE_JS = r"""
// Same as icp.py compare + filters: win rate per firmographic value; a value is in the ICP when it wins more
// often than the average and has at least 2 wins. Then the Sales Navigator account search.
const HEADCOUNT = __HEADCOUNT__, INDUSTRY = __INDUSTRY__, COUNTRY = __COUNTRY__;
const GROWTH = [[-1000, 0, 'shrinking (below 0%)'], [0, 10, 'flat (0 to 9%)'], [10, 25, 'growing (10 to 24%)'], [25, 100000, 'fast (25% and more)']];
const FOUNDED = [[0, 2000, 'before 2000'], [2000, 2010, '2000 to 2009'], [2010, 2015, '2010 to 2014'], [2015, 3000, '2015 or later']];
const band = (v, bands) => { const n = parseFloat(v); if (isNaN(n)) return ''; const b = bands.find(([lo, hi]) => lo <= n && n < hi); return b ? b[2] : ''; };
const ATTR = {
  'Industry': r => r['Company Industry'] || '',
  'Employees': r => r['Company Employee Range'] || '',
  'HQ country': r => String(r['Company Headquarters (Full Address)'] || '').split(',').pop().trim(),
  'Headcount growth (1 year)': r => band(r['Company Employee Growth 1 Year (%)'], GROWTH),
  'Company type': r => r['Company Type'] || '',
  'Founded': r => String(r['Company Year Founded'] || '0') === '0' ? '' : band(r['Company Year Founded'], FOUNDED),
  'Revenue (LinkedIn estimate)': r => { const lo = r['Company Revenue Min (Millions USD)'], hi = r['Company Revenue Max (Millions USD)'];
    return (lo === undefined || lo === null || lo === '') ? '' : (hi === undefined || hi === null || hi === '' || Number(hi) >= 1000000 ? `$${lo}M and more` : `$${lo}M to $${hi}M`); },
};
const rows = {};
for (const i of $input.all()) for (const p of i.json.structuredContent?.result?.prospects || []) {
  const id = String(p['Company Linkedin URL Unique ID'] || '').split('/').pop().replace(/\D/g, '');
  if (id && !rows[id]) rows[id] = p;
}
const accounts = $('Accounts').first().json.accounts;
const found = accounts.filter(a => rows[a.id]).map(a => ({ ...a, row: rows[a.id] }));
const missing = accounts.filter(a => !rows[a.id]).map(a => a.name);
const base = found.filter(a => a.outcome === 'won').length / found.length;
const icp = {}, table = [];
for (const [attr, read] of Object.entries(ATTR)) {
  const c = {};
  for (const a of found) { const v = read(a.row) || 'unknown'; c[v] = c[v] || { won: 0, lost: 0 }; c[v][a.outcome]++; }
  icp[attr] = [];
  for (const [value, n] of Object.entries(c).sort((x, y) => y[1].won / (y[1].won + y[1].lost) - x[1].won / (x[1].won + x[1].lost))) {
    const rate = n.won / (n.won + n.lost), keep = value !== 'unknown' && n.won >= 2 && rate > base;
    if (keep) icp[attr].push(value);
    table.push({ attr, value, ...n, rate: Math.round(100 * rate), keep });
  }
}
const list = (type, vals) => `(type%3A${type}%2Cvalues%3AList(${vals.map(v => `(id%3A${v}%2CselectionType%3AINCLUDED)`).join('%2C')}))`;
const parts = [], unknown = [];
const ind = icp['Industry'].filter(i => INDUSTRY[i]); unknown.push(...icp['Industry'].filter(i => !INDUSTRY[i]));
if (ind.length) parts.push(list('INDUSTRY', ind.map(i => INDUSTRY[i])));
const hc = icp['Employees'].filter(e => HEADCOUNT[e]).map(e => HEADCOUNT[e]).sort();
if (hc.length) parts.push(list('COMPANY_HEADCOUNT', hc));
const ctry = icp['HQ country'].filter(c => COUNTRY[c]); unknown.push(...icp['HQ country'].filter(c => !COUNTRY[c]));
if (ctry.length) parts.push(list('REGION', ctry.map(c => COUNTRY[c])));
const picked = GROWTH.filter(g => icp['Headcount growth (1 year)'].includes(g[2]));
if (picked.length) {
  const lo = Math.min(...picked.map(g => g[0])), hi = Math.max(...picked.map(g => g[1]));
  const rng = [...(lo > -1000 ? [`min%3A${lo}`] : []), ...(hi < 100000 ? [`max%3A${hi - 1}`] : [])];
  if (rng.length) parts.push(`(type%3ACOMPANY_HEADCOUNT_GROWTH%2CrangeValue%3A(${rng.join('%2C')}))`);
}
const url = parts.length ? 'https://www.linkedin.com/sales/search/company?query=(filters%3AList(' + parts.join('%2C') + '))' : '';
const lines = Object.entries(icp).map(([k, v]) => `<li><b>${k}:</b> ${v.length ? v.join(', ') : 'no difference between won and lost'}</li>`).join('');
const html = `<p>${found.length} accounts with firmographics, average win rate ${Math.round(100 * base)}%.`
  + (missing.length ? ` No Evaboot row for ${missing.join(', ')}.` : '') + `</p><ul>${lines}</ul>`
  + (url ? `<p><a href="${url}" target="_blank">Open the ICP account search in Sales Navigator</a></p>` : '<p>No ICP value maps to a Sales Navigator filter.</p>')
  + (unknown.length ? `<p>Add the LinkedIn id of: ${unknown.join(', ')} to this node.</p>` : '');
return [{ json: { icp, table, url, missing, base, html } }];
""".replace("__HEADCOUNT__", json.dumps(HEADCOUNT)).replace("__INDUSTRY__", json.dumps(INDUSTRY)) \
   .replace("__COUNTRY__", json.dumps(COUNTRY))

node(FORM, "n8n-nodes-base.formTrigger", 2.2, {
    "formTitle": "Define your ICP from won and lost deals",
    "formDescription": "Paste the accounts you won and lost. Evaboot reads each company's firmographics, and you see which values win more often. Nothing is spent before you confirm.",
    "formFields": {"values": [
        {"fieldLabel": FIELD, "fieldType": "textarea", "requiredField": True,
         "placeholder": "| lemlist | 18342604 | won |\n| Capgemini | 157240 | lost |"},
    ]},
    "responseMode": "lastNode", "options": {},
}, [0, 0])
code("Accounts", ACCOUNTS_JS, [220, 0])
node("Review the cost", "n8n-nodes-base.form", 2.3, {
    "formFields": {"values": [{"fieldLabel": "What next?", "fieldType": "dropdown", "requiredField": True,
                               "fieldOptions": {"values": [{"option": "Read the firmographics"}, {"option": "Stop here"}]}}]},
    "options": {"formTitle": "={{ $json.summary }}",
                "formDescription": "=Evaboot exports one row per account: {{ $json.accounts.length }} credits."},
}, [440, 0])
node("Go?", "n8n-nodes-base.if", 2.2, {"conditions": {
    "options": {"caseSensitive": True, "typeValidation": "loose", "version": 2},
    "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json['What next?'] }}", "rightValue": "Read the firmographics",
                    "operator": {"type": "string", "operation": "equals"}}],
    "combinator": "and"}, "options": {}}, [660, 0])
code("One search per account", SPLIT_JS, [880, 0])
mcp_call("Export one row each", "export_sn_search_or_list",
         "={{ JSON.stringify({ search_url: $json.url, max_results: 1, name: 'ICP ' + $json.id }) }}", [1100, 0])
node("Wait 60 s", "n8n-nodes-base.wait", 1.1, {"amount": 60}, [1320, 0])
mcp_call("Check the exports", "get_export",
         "={{ JSON.stringify({ extraction_id: $json.structuredContent.result.extraction_id || $json.structuredContent.result.search_id }) }}",
         [1540, 0])
code("All done?", DONE_JS, [1760, 0])
is_true("Finished?", "={{ $json.allDone }}", [1980, 0])
code("Compare won and lost", COMPARE_JS, [2200, 0])
node("Your ICP", "n8n-nodes-base.form", 2.3, {
    "operation": "completion", "respondWith": "showText", "responseText": "={{ $json.html }}", "options": {}},
    [2420, 0])
node("Stopped", "n8n-nodes-base.form", 2.3, {
    "operation": "completion", "completionTitle": "Nothing exported",
    "completionMessage": "No credit was spent.", "options": {}}, [880, 200])

for a, b in [(FORM, "Accounts"), ("Accounts", "Review the cost"), ("Review the cost", "Go?"),
             ("One search per account", "Export one row each"), ("Export one row each", "Wait 60 s"),
             ("Wait 60 s", "Check the exports"), ("Check the exports", "All done?"), ("All done?", "Finished?"),
             ("Compare won and lost", "Your ICP")]:
    link(a, b)
link("Go?", "One search per account", out=0)
link("Go?", "Stopped", out=1)
link("Finished?", "Compare won and lost", out=0)
link("Finished?", "Wait 60 s", out=1)

wf = {"name": "Firmographic ICP (Evaboot)", "nodes": nodes, "connections": connections,
      "settings": {"executionOrder": "v1"}, "pinData": {}}
out = Path(__file__).with_name("firmographic-icp.json")
out.write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n")
print(f"Wrote {out}")
