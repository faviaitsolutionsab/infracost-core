#!/usr/bin/env python3
import json, os, sys, pathlib

# ---------- CLI args & env ----------
argv_out   = sys.argv[1] if len(sys.argv) > 1 else ""
argv_md    = sys.argv[2] if len(sys.argv) > 2 else ""

OUT_PATH     = (argv_out or os.getenv("INFRACOST_OUT_PATH", "")).strip()
COMMENT_PATH = (argv_md  or os.getenv("INFRACOST_COMMENT_PATH", "")).strip()
AUTHOR       = os.getenv("PR_AUTHOR", "").strip()
MENTIONS     = os.getenv("MENTION_HANDLES", "").strip()
MARKER       = os.getenv("INPUT_COMMENT_MARKER", "<!-- infracost-comment -->").strip()

# Currency & flag handling
CURRENCY     = os.getenv("INFRACOST_CURRENCY", os.getenv("CURRENCY", "USD")).upper().strip()
FLAG_MAP = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "INR": "🇮🇳", "AUD": "🇦🇺",
    "CAD": "🇨🇦", "JPY": "🇯🇵", "NZD": "🇳🇿", "CHF": "🇨🇭", "SEK": "🇸🇪",
}
CURRENCY_FLAG = os.getenv("CURRENCY_FLAG", FLAG_MAP.get(CURRENCY, "💱")).strip()

# ---------- Path resolution helpers ----------
def first_existing(paths):
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None

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

# ---------- Formatting helpers ----------
def to_float(x):
    try:
        if x in (None, "", "-", "null"):
            return 0.0
        return float(x)
    except Exception:
        # Some Infracost strings might include currency symbols; strip non-numeric
        try:
            import re
            s = re.sub(r"[^\d\.\-eE]", "", str(x))
            return float(s) if s else 0.0
        except Exception:
            return 0.0

def money(x):    return f"${x:,.2f}"
def money_hr(x): return f"${x:.4f}"

def arrow(x):
    if x > 0: return "🔴 ↑"
    if x < 0: return "🟢 ↓"
    return "⚪ ↔️"

# ---------- Load and aggregate ----------
with open(OUT_PATH) as f:
    data = json.load(f)

projects = data.get("projects", [])
# Support both "diff" (from infracost diff) and "summary" keys if present
past   = 0.0
future = 0.0
delta  = 0.0

for p in projects:
    d = p.get("diff") or {}
    if d:
        past   += to_float(d.get("pastTotalMonthlyCost"))
        future += to_float(d.get("totalMonthlyCost"))
        delta  += to_float(d.get("diffTotalMonthlyCost"))
    else:
        # Fallback: use summary if diff missing (rare)
        s = p.get("summary") or {}
        past   += to_float(s.get("pastTotalMonthlyCost"))
        future += to_float(s.get("totalMonthlyCost"))
        delta  += to_float(s.get("diffTotalMonthlyCost"))

daily_past,  daily_future,  daily_delta  = past/30.0,  future/30.0,  delta/30.0
hourly_past, hourly_future, hourly_delta = past/730.0, future/730.0, delta/730.0
arr = arrow(delta)

# ---------- Markdown ----------
md = []
if AUTHOR:
    md.append(f"@{AUTHOR}")
if MENTIONS:
    md.append(MENTIONS)
if md:
    md.append("")  # blank line before title

md.append("### 💸 Infracost Report")
md.append(f"\n{arr} Monthly delta: {CURRENCY_FLAG} {money(delta)}\n")
md.append("| Period | Current 🟦 | Future 🟨 | Δ |")
md.append("|--------|-----------:|-----------:|---:|")
md.append(f"| Monthly | {CURRENCY_FLAG} {money(past)} | {CURRENCY_FLAG} {money(future)} | {arr} {CURRENCY_FLAG} {money(delta)} |")
md.append(f"| Daily   | {CURRENCY_FLAG} {money(daily_past)} | {CURRENCY_FLAG} {money(daily_future)} | {arr} {CURRENCY_FLAG} {money(daily_delta)} |")
md.append(f"| Hourly  | {CURRENCY_FLAG} {money_hr(hourly_past)} | {CURRENCY_FLAG} {money_hr(hourly_future)} | {arr} {CURRENCY_FLAG} {money_hr(hourly_delta)} |")
md.append(f"\n{MARKER}")

pathlib.Path(os.path.dirname(COMMENT_PATH) or ".").mkdir(parents=True, exist_ok=True)
with open(COMMENT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"✅ Wrote cost report to {COMMENT_PATH}")
print(f"ℹ️ Read diff JSON from {OUT_PATH}")
print(f"ℹ️ Currency: {CURRENCY} {CURRENCY_FLAG}")