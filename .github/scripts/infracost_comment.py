#!/usr/bin/env python3
import json, os, sys, pathlib, re

# =========================
# Inputs (args/env)
# =========================
argv_out   = sys.argv[1] if len(sys.argv) > 1 else ""
argv_md    = sys.argv[2] if len(sys.argv) > 2 else ""

OUT_PATH     = (argv_out or os.getenv("INFRACOST_OUT_PATH", "")).strip()
COMMENT_PATH = (argv_md  or os.getenv("INFRACOST_COMMENT_PATH", "")).strip()
AUTHOR       = os.getenv("PR_AUTHOR", "").strip()
MENTIONS     = os.getenv("MENTION_HANDLES", "").strip()
MARKER       = os.getenv("INPUT_COMMENT_MARKER", "<!-- infracost-comment -->").strip()

# Currency & flag (flag appears ONCE in the delta line)
CURRENCY     = os.getenv("INFRACOST_CURRENCY", os.getenv("CURRENCY", "USD")).upper().strip()
FLAG_MAP = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "INR": "🇮🇳", "AUD": "🇦🇺",
    "CAD": "🇨🇦", "JPY": "🇯🇵", "NZD": "🇳🇿", "CHF": "🇨🇭", "SEK": "🇸🇪",
}
CURRENCY_FLAG = os.getenv("CURRENCY_FLAG", FLAG_MAP.get(CURRENCY, "💱")).strip()

# =========================
# Helpers
# =========================
def first_existing(paths):
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None

def to_float(x):
    if x in (None, "", "-", "null"):
        return 0.0
    try:
        return float(x)
    except Exception:
        s = re.sub(r"[^\d\.\-eE]", "", str(x))
        return float(s) if s else 0.0

def money(x):    return f"${x:,.2f}"
def money_hr(x): return f"${x:.4f}"

def arrow(x):
    if x > 0: return "🔴 ↑"
    if x < 0: return "🟢 ↓"
    return "⚪ ↔️"

# =========================
# Resolve OUT_PATH & COMMENT_PATH
# =========================
ws = os.getenv("GITHUB_WORKSPACE", "").rstrip("/")

candidates_out = [
    OUT_PATH,
    "infracost.out.json",
    os.path.join(".github", "fixtures", "terraform", "infracost.out.json"),
    os.path.join(ws, ".github", "fixtures", "terraform", "infracost.out.json") if ws else "",
]
OUT_PATH = first_existing(candidates_out)
if not OUT_PATH:
    tried = [p for p in candidates_out if p]
    print("ERROR: Could not find infracost.out.json. Paths tried:\n- " + "\n- ".join(tried), file=sys.stderr)
    sys.exit(1)

if not COMMENT_PATH:
    out_dir = os.path.dirname(OUT_PATH) or "."
    COMMENT_PATH = os.path.join(out_dir, "infracost_comment.md")

# =========================
# Load & Aggregate (works for both diff modes)
# =========================
with open(OUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

def totals_from_top_summary(d):
    s = d.get("summary") or {}
    past   = to_float(s.get("pastTotalMonthlyCost"))
    future = to_float(s.get("totalMonthlyCost"))
    delta  = to_float(s.get("diffTotalMonthlyCost"))
    if any(v != 0.0 for v in (past, future, delta)):
        return past, future, delta
    return None

def totals_from_projects(d):
    past = future = delta = 0.0
    for p in d.get("projects", []):
        # Prefer per-project diff
        diff = p.get("diff")
        if diff:
            past   += to_float(diff.get("pastTotalMonthlyCost"))
            future += to_float(diff.get("totalMonthlyCost"))
            delta  += to_float(diff.get("diffTotalMonthlyCost"))
        else:
            # Fallback to per-project summary if diff missing
            s = p.get("summary") or {}
            past   += to_float(s.get("pastTotalMonthlyCost"))
            future += to_float(s.get("totalMonthlyCost"))
            delta  += to_float(s.get("diffTotalMonthlyCost"))
    return past, future, delta

totals = totals_from_top_summary(data)
if totals is None:
    totals = totals_from_projects(data)

past, future, delta = totals

# Derived periods
daily_past,  daily_future,  daily_delta  = past/30.0,  future/30.0,  delta/30.0
hourly_past, hourly_future, hourly_delta = past/730.0, future/730.0, delta/730.0
arr = arrow(delta)

# =========================
# Markdown (flag ONCE in delta line; table shows plain $)
# =========================
md = []
if AUTHOR:
    md.append(f"@{AUTHOR}")
if MENTIONS:
    md.append(MENTIONS)
if md:
    md.append("")

md.append("### 💸 Infracost Report")
md.append(f"\n{arr} Monthly delta: {CURRENCY_FLAG} {money(delta)}\n")
md.append("| Period | Current 🟦 | Future 🟨 | Δ |")
md.append("|--------|-----------:|-----------:|---:|")
md.append(f"| Monthly | {money(past)} | {money(future)} | {arr} {money(delta)} |")
md.append(f"| Daily   | {money(daily_past)} | {money(daily_future)} | {arr} {money(daily_delta)} |")
md.append(f"| Hourly  | {money_hr(hourly_past)} | {money_hr(hourly_future)} | {arr} {money_hr(hourly_delta)} |")
md.append(f"\n{MARKER}")

pathlib.Path(os.path.dirname(COMMENT_PATH) or ".").mkdir(parents=True, exist_ok=True)
with open(COMMENT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"✅ Wrote cost report to {COMMENT_PATH}")
print(f"ℹ️ Read diff JSON from {OUT_PATH}")
print(f"ℹ️ Currency: {CURRENCY} {CURRENCY_FLAG}")