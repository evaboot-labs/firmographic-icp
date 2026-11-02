#!/usr/bin/env python3
"""Firmographic ICP: compare the companies you won with the ones you lost, keep what separates them.

  python3 icp.py urls ACCOUNTS.md                      -> one Sales Navigator search per account (to export 1 row each)
  python3 icp.py compare data/rows.json ACCOUNTS.md    -> win rate per firmographic value, written to ICP.md
  python3 icp.py filters ICP.md                        -> the Sales Navigator account search for your ICP

Standard library only. The Evaboot work happens in your AI agent through the Evaboot MCP server.
"""
import json
import re
import sys
from collections import defaultdict
from urllib.parse import quote

# Sales Navigator company headcount codes.
HEADCOUNT = {
    "1 to 10": "B", "11 to 50": "C", "51 to 200": "D", "201 to 500": "E",
    "501 to 1000": "F", "1001 to 5000": "G", "5001 to 10000": "H", "10001+": "I",
}
# LinkedIn industry ids. Add yours: pick the industry in a Sales Navigator search and read
# the id in the INDUSTRY filter of the URL.
INDUSTRY = {
    "Software Development": 4,
    "Technology, Information and Internet": 6,
    "Financial Services": 43,
    "IT Services and IT Consulting": 96,
    "Business Consulting and Services": 11,
    "Advertising Services": 80,
    "Computer Games": 109,
    "Retail": 27,
    "Hospitals and Health Care": 14,
}
# LinkedIn geo ids for a company headquarters country. Add yours the same way (REGION filter).
COUNTRY = {
    "France": 105015875, "United States": 103644278, "United Kingdom": 101165590,
    "Germany": 101282230, "Spain": 105646813, "Netherlands": 102890719,
    "Belgium": 100565514, "Switzerland": 106693272, "Canada": 101174742,
}
# Firmographic fields of an Evaboot export row, and how each value is grouped.
GROWTH_BANDS = [(-1000, 0, "shrinking (below 0%)"), (0, 10, "flat (0 to 9%)"),
                (10, 25, "growing (10 to 24%)"), (25, 100000, "fast (25% and more)")]
FOUNDED_BANDS = [(0, 2000, "before 2000"), (2000, 2010, "2000 to 2009"),
                 (2010, 2015, "2010 to 2014"), (2015, 3000, "2015 or later")]


def band(value, bands):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    return next((name for lo, hi, name in bands if lo <= v < hi), "")


def revenue(row):
    lo, hi = row.get("Company Revenue Min (Millions USD)"), row.get("Company Revenue Max (Millions USD)")
    if lo in (None, "") and hi in (None, ""):
        return ""
    open_ended = hi in (None, "") or float(hi) >= 1_000_000  # LinkedIn's top band has no real maximum
    return f"${lo}M and more" if open_ended else f"${lo}M to ${hi}M"


ATTRIBUTES = {
    "Industry": lambda r: r.get("Company Industry", ""),
    "Employees": lambda r: r.get("Company Employee Range", ""),
    "HQ country": lambda r: str(r.get("Company Headquarters (Full Address)") or "").split(",")[-1].strip(),
    "Headcount growth (1 year)": lambda r: band(r.get("Company Employee Growth 1 Year (%)"), GROWTH_BANDS),
    "Company type": lambda r: r.get("Company Type", ""),
    # LinkedIn leaves the founding year empty on some pages; Evaboot writes 0 then.
    "Founded": lambda r: band(r.get("Company Year Founded"), FOUNDED_BANDS) if str(r.get("Company Year Founded") or "0") != "0" else "",
    "Revenue (LinkedIn estimate)": revenue,
}


def read_accounts(path):
    """The table in ACCOUNTS.md: | Company | LinkedIn id | Outcome |, outcome won or lost."""
    rows = []
    for line in open(path, encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("Company", "") or set(cells[0]) <= set("-: "):
            continue
        outcome = cells[2].lower()
        if outcome not in ("won", "lost"):
            sys.exit(f"{path}: outcome of {cells[0]} must be won or lost, not '{cells[2]}'.")
        cid = re.sub(r"\D", "", cells[1])
        if not cid:
            sys.exit(f"{path}: {cells[0]} needs a LinkedIn company id (the number in linkedin.com/company/<id>).")
        rows.append({"name": cells[0], "id": cid, "outcome": outcome})
    won = sum(r["outcome"] == "won" for r in rows)
    if won < 3 or len(rows) - won < 3:
        sys.exit(f"{path}: list at least 3 won and 3 lost accounts (20 of each gives a real signal).")
    return rows


def cmd_urls(accounts_path):
    """A people search per account: the account's CXOs. One exported row carries all the company fields."""
    for a in read_accounts(accounts_path):
        urn = quote(quote(f"urn:li:organization:{a['id']}", safe=""), safe="")
        print(a["id"], "https://www.linkedin.com/sales/search/people?query=(filters%3AList("
              f"(type%3ACURRENT_COMPANY%2Cvalues%3AList((id%3A{urn}%2CselectionType%3AINCLUDED)))%2C"
              "(type%3ASENIORITY_LEVEL%2Cvalues%3AList((id%3A310%2CselectionType%3AINCLUDED)))))")


def load_rows(path):
    data = json.load(open(path, encoding="utf-8"))
    rows = []
    # Accept flat export rows, or whole get_export results that hold them in "prospects".
    for item in data if isinstance(data, list) else [data]:
        if "prospects" in item or "result" in item:
            rows += item.get("prospects") or item.get("result", {}).get("prospects") or []
        else:
            rows.append(item)
    by_id = {}
    for r in rows:
        cid = re.sub(r"\D", "", str(r.get("Company Linkedin URL Unique ID") or "").rsplit("/", 1)[-1])
        if cid and cid not in by_id:
            by_id[cid] = r
    return by_id


def compare(accounts, rows):
    found = [dict(a, row=rows[a["id"]]) for a in accounts if a["id"] in rows]
    missing = [a["name"] for a in accounts if a["id"] not in rows]
    won = [a for a in found if a["outcome"] == "won"]
    base = len(won) / len(found) if found else 0
    table = {}
    for attr, read in ATTRIBUTES.items():
        counts = defaultdict(lambda: {"won": 0, "lost": 0})
        for a in found:
            counts[read(a["row"]) or "unknown"][a["outcome"]] += 1
        values = []
        for value, c in counts.items():
            rate = c["won"] / (c["won"] + c["lost"])
            # In the ICP: wins more often than average, and at least 2 wins (one win is luck).
            keep = value != "unknown" and c["won"] >= 2 and rate > base
            values.append({"value": value, **c, "win_rate": rate, "icp": keep})
        values.sort(key=lambda v: (-v["win_rate"], -v["won"]))
        table[attr] = values
    return found, missing, base, table


def pct(x):
    return f"{round(100 * x)}%"


def write_icp(found, missing, base, table):
    won = sum(a["outcome"] == "won" for a in found)
    out = ["# ICP: firmographics of the accounts you win", "",
           f"Built by `icp.py compare` from {won} won and {len(found) - won} lost accounts "
           f"(average win rate {pct(base)}).", ""]
    if missing:
        out += [f"No Evaboot row for: {', '.join(missing)}. They are left out.", ""]
    out += ["## Your ICP", ""]
    for attr, values in table.items():
        keep = [v["value"] for v in values if v["icp"]]
        # "; " because some LinkedIn industries hold a comma ("Technology, Information and Internet").
        out.append(f"- **{attr}:** {'; '.join(keep) if keep else 'no difference between won and lost'}")
    out += ["", "## Won vs lost, value by value", "",
            "| Attribute | Value | Won | Lost | Win rate | In ICP |", "|---|---|---|---|---|---|"]
    for attr, values in table.items():
        for v in values:
            out.append(f"| {attr} | {v['value']} | {v['won']} | {v['lost']} | {pct(v['win_rate'])} | "
                       f"{'yes' if v['icp'] else ''} |")
    out += ["", "## Accounts", "", "| Company | Outcome | " + " | ".join(ATTRIBUTES) + " |",
            "|---|---|" + "---|" * len(ATTRIBUTES)]
    for a in found:
        cells = [read(a["row"]) or "" for read in ATTRIBUTES.values()]
        out.append(f"| {a['row'].get('Company Name') or a['name']} | {a['outcome']} | " + " | ".join(map(str, cells)) + " |")
    return "\n".join(out) + "\n"


def cmd_compare(rows_path, accounts_path, out_path="ICP.md"):
    found, missing, base, table = compare(read_accounts(accounts_path), load_rows(rows_path))
    if not found:
        sys.exit(f"{rows_path}: no row matches a LinkedIn id in {accounts_path}.")
    open(out_path, "w", encoding="utf-8").write(write_icp(found, missing, base, table))
    won = sum(a["outcome"] == "won" for a in found)
    print(f"{len(found)} accounts with firmographics ({won} won, {len(found) - won} lost), average win rate {pct(base)}.")
    if missing:
        print(f"No row for: {', '.join(missing)}")
    for attr, values in table.items():
        keep = [f"{v['value']} ({v['won']}/{v['won'] + v['lost']})" for v in values if v["icp"]]
        print(f"  {attr}: {'; '.join(keep) if keep else '-'}")
    print(f"Written to {out_path}.")


def read_icp(path):
    icp = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"- \*\*(.+?):\*\* (.+)", line.strip())
        if m and not m.group(2).startswith("no difference"):
            icp[m.group(1)] = [v.strip() for v in m.group(2).split(";") if v.strip()]
    return icp


def cmd_filters(icp_path):
    icp = read_icp(icp_path)
    lst = lambda type_, vals: (f"(type%3A{type_}%2Cvalues%3AList("
                               + "%2C".join(f"(id%3A{v}%2CselectionType%3AINCLUDED)" for v in vals) + "))")
    parts, unknown, skipped = [], [], []
    if "Industry" in icp:
        unknown += [i for i in icp["Industry"] if i not in INDUSTRY]
        ids = [INDUSTRY[i] for i in icp["Industry"] if i in INDUSTRY]
        if ids:
            parts.append(lst("INDUSTRY", ids))
    if "Employees" in icp:
        unknown += [e for e in icp["Employees"] if e not in HEADCOUNT]
        codes = sorted(HEADCOUNT[e] for e in icp["Employees"] if e in HEADCOUNT)
        if codes:
            parts.append(lst("COMPANY_HEADCOUNT", codes))
    if "HQ country" in icp:
        unknown += [c for c in icp["HQ country"] if c not in COUNTRY]
        ids = [COUNTRY[c] for c in icp["HQ country"] if c in COUNTRY]
        if ids:
            parts.append(lst("REGION", ids))
    if "Headcount growth (1 year)" in icp:
        picked = [(lo, hi) for lo, hi, name in GROWTH_BANDS if name in icp["Headcount growth (1 year)"]]
        if picked:
            lo, hi = min(p[0] for p in picked), max(p[1] for p in picked)
            rng = ([f"min%3A{lo}"] if lo > -1000 else []) + ([f"max%3A{hi - 1}"] if hi < 100000 else [])
            if rng:
                parts.append(f"(type%3ACOMPANY_HEADCOUNT_GROWTH%2CrangeValue%3A({'%2C'.join(rng)}))")
    skipped = [a for a in icp if a not in ("Industry", "Employees", "HQ country", "Headcount growth (1 year)")]
    if unknown:
        print(f"Unknown LinkedIn id, add it to INDUSTRY, COUNTRY or HEADCOUNT in icp.py: {', '.join(unknown)}", file=sys.stderr)
    if skipped:
        print(f"No Sales Navigator account filter for: {', '.join(skipped)}. Check them on the list.", file=sys.stderr)
    if not parts:
        sys.exit("No ICP value maps to a Sales Navigator filter.")
    print("https://www.linkedin.com/sales/search/company?query=(filters%3AList(" + "%2C".join(parts) + "))")


if __name__ == "__main__":
    a = sys.argv
    if len(a) == 3 and a[1] == "urls":
        cmd_urls(a[2])
    elif len(a) in (4, 5) and a[1] == "compare":
        cmd_compare(*a[2:])
    elif len(a) == 3 and a[1] == "filters":
        cmd_filters(a[2])
    else:
        sys.exit(__doc__)
