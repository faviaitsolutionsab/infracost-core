#!/usr/bin/env python3
import json, os, sys

infile = sys.argv[1] if len(sys.argv) > 1 else "infracost.out.json"
outfile = sys.argv[2] if len(sys.argv) > 2 else "infracost_comment.md"

author = os.getenv("PR_AUTHOR", "")
mentions = os.getenv("MENTION_HANDLES", "")
mention_line = " ".join([
    f"@{author}" if author and not author.startswith("@") else author,
    mentions
]).strip()

with open(infile) as f:
    data = json.load(f)

s = data.get("summary", {})
currency = s.get("currency", data.get("currency", "INR"))

future = float(s.get("totalMonthlyCost") or 0.0)
current = float(s.get("pastTotalMonthlyCost") or 0.0)
delta = float(s.get("diffTotalMonthlyCost") or (future - current))

dcur, dfut, ddel = current/30, future/30, delta/30
hcur, hfut, hdel = current/730, future/730, delta/730

def f(x, p=2): return f"{x:.{p}f}"

currency_map = {
    "USD": ("$", "🇺🇸"),
    "EUR": ("€", "🇪🇺"),
    "GBP": ("£", "🇬🇧"),
    "JPY": ("¥", "🇯🇵"),
    "SEK": ("kr","🇸🇪"),
    "INR": ("₹","🇮🇳"),
    "AUD": ("A$","🇦🇺"),
    "CAD": ("C$","🇨🇦"),
    "CHF": ("CHF","🇨🇭"),
}
symbol, flag = currency_map.get(currency, ("₹","🇮🇳"))

arrow, diff_emoji, sign = "↔️","⚪",""
if delta > 0: arrow, diff_emoji, sign = "⬆️","🔴","+"
elif delta < 0: arrow, diff_emoji, sign = "⬇️","🟢",""

banner = "⚪ No cost change."
if delta > 0:
    banner = f"🚨 Costs increased by {flag} {symbol}{sign}{f(delta)}"
elif delta < 0:
    banner = f"✅ Costs decreased by {flag} {symbol}{f(delta)}"

rows = []
rows.append("### 💸 Infracost Report\n")
if mention_line:
    rows.append(f"{mention_line}\n\n")
rows.append(f"{banner}\n\n")
rows.append("| Period | Current 🟦 | Future 🟨 | Δ |\n")
rows.append("|--------|-----------:|-----------:|---:|\n")
rows.append(f"| Monthly | {flag} {symbol}{f(current)} | {flag} {symbol}{f(future)} | {diff_emoji} {arrow} {flag} {symbol}{sign}{f(delta)} |\n")
rows.append(f"| Daily   | {flag} {symbol}{f(dcur)} | {flag} {symbol}{f(dfut)} | {diff_emoji} {arrow} {flag} {symbol}{sign}{f(ddel)} |\n")
rows.append(f"| Hourly  | {flag} {symbol}{f(hcur,4)} | {flag} {symbol}{f(hfut,4)} | {diff_emoji} {arrow} {flag} {symbol}{sign}{f(hdel,4)} |\n")
rows.append("\n<!-- infracost-comment -->\n")

with open(outfile, "w") as out:
    out.write("".join(rows))