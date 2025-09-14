#!/usr/bin/env python3
import json, os

# ---- Inputs (override with env vars) ----
OUT_PATH      = os.getenv("INFRACOST_OUT_PATH", "infracost.out.json")
COMMENT_PATH  = os.getenv("INFRACOST_COMMENT_PATH", "infracost_comment.md")
AUTHOR        = os.getenv("PR_AUTHOR", "")
MENTIONS      = os.getenv("MENTION_HANDLES", "")
CURRENCY_FLAG = os.getenv("CURRENCY_FLAG", "🇺🇸")

# ---- Helpers ----
def to_float(x):
    try:
        return float(x) if x not in (None, "", "-", "null") else 0.0
    except Exception:
        return 0.0

def money(x):    return f"${x:,.2f}"
def money_hr(x): return f"${x:.4f}"

def arrow(x):
    if x > 0: return "🔴 ↑"
    if x < 0: return "🟢 ↓"
    return "⚪ ↔️"

# ---- Load diff JSON ----
with open(OUT_PATH) as f:
    data = json.load(f)

projects = data.get("projects", [])

past   = sum(to_float(p.get("diff", {}).get("pastTotalMonthlyCost")) for p in projects)
future = sum(to_float(p.get("diff", {}).get("totalMonthlyCost"))     for p in projects)
delta  = sum(to_float(p.get("diff", {}).get("diffTotalMonthlyCost")) for p in projects)

# ---- Derived values ----
daily_past,  daily_future,  daily_delta  = past/30.0,  future/30.0,  delta/30.0
hourly_past, hourly_future, hourly_delta = past/730.0, future/730.0, delta/730.0
arr = arrow(delta)

# ---- Markdown ----
md = []
if AUTHOR:
    md.append(f"@{AUTHOR}")
md.append("")
md.append("### 💸 Infracost Report")
if AUTHOR:
    md.append(f"@{AUTHOR}")
if MENTIONS:
    md.append(MENTIONS)

md.append(f"\n{arr} Monthly delta: {CURRENCY_FLAG} {money(delta)}\n")
md.append("| Period | Current 🟦 | Future 🟨 | Δ |")
md.append("|--------|-----------:|-----------:|---:|")
md.append(f"| Monthly | {CURRENCY_FLAG} {money(past)} | {CURRENCY_FLAG} {money(future)} | {arr} {CURRENCY_FLAG} {money(delta)} |")
md.append(f"| Daily   | {CURRENCY_FLAG} {money(daily_past)} | {CURRENCY_FLAG} {money(daily_future)} | {arr} {CURRENCY_FLAG} {money(daily_delta)} |")
md.append(f"| Hourly  | {CURRENCY_FLAG} {money_hr(hourly_past)} | {CURRENCY_FLAG} {money_hr(hourly_future)} | {arr} {CURRENCY_FLAG} {money_hr(hourly_delta)} |")
md.append("\n<!-- infracost-comment -->")

os.makedirs(os.path.dirname(COMMENT_PATH) or ".", exist_ok=True)
with open(COMMENT_PATH, "w") as f:
    f.write("\n".join(md))

print(f"✅ Wrote cost report to {COMMENT_PATH}")