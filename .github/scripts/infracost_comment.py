#!/usr/bin/env python3
import json, os, sys, pathlib, re

# --------------------------- CLI & ENV ---------------------------
argv_out = sys.argv[1] if len(sys.argv) > 1 else ""
argv_md  = sys.argv[2] if len(sys.argv) > 2 else ""

OUT_PATH     = (argv_out or os.getenv("INFRACOST_OUT_PATH", "")).strip()
COMMENT_PATH = (argv_md  or os.getenv("INFRACOST_COMMENT_PATH", "")).strip()
AUTHOR       = os.getenv("PR_AUTHOR", "").strip()
MENTIONS     = os.getenv("MENTION_HANDLES", "").strip()
MARKER       = os.getenv("INPUT_COMMENT_MARKER", "<!-- infracost-comment -->").strip()

# Optional: pass these so we can compute Current/Future when diff JSON lacks per-project numbers
BASE_BREAKDOWN_PATH = os.getenv("BASE_BREAKDOWN_PATH", "").strip()
PR_BREAKDOWN_PATH   = os.getenv("PR_BREAKDOWN_PATH", "").strip()

# Currency handling: show flag ONCE (not inside the table)
CURRENCY = os.getenv("INFRACOST_CURRENCY", os.getenv("CURRENCY", "USD")).upper().strip()
FLAG_MAP = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "INR": "🇮🇳", "AUD": "🇦🇺",
    "CAD": "🇨🇦", "JPY": "🇯🇵", "NZD": "🇳🇿", "CHF": "🇨🇭", "SEK": "🇸🇪",
}
CURRENCY_FLAG = os.getenv("CURRENCY_FLAG", FLAG_MAP.get(CURRENCY, "💱")).strip()

# --------------------------- Path helpers ---------------------------
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

# --------------------------- Formatting helpers ---------------------------
NUM_RE = re.compile(r"[^\d\.\-eE]")

def to_float(x):
    if x in (None, "", "-", "null"):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = NUM_RE.sub("", str(x))
    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0

def money(x):    return f"${x:,.2f}"
def money_hr(x): return f"${x:.4f}"

def arrow(x):
    if x > 0: return "🔴 ↑"
    if x < 0: return "🟢 ↓"
    return "⚪ ↔️"

# --------------------------- Load helpers ---------------------------
def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_breakdown_total(path):
    """Read totalMonthlyCost from a breakdown JSON (infracost breakdown --format json)."""
    if not path or not os.path.isfile(path):
        return 0.0
    try:
        data = read_json(path)
    except Exception:
        return 0.0
    summ = data.get("summary") or {}
    # Newer/older formats both map here
    total = to_float(summ.get("totalMonthlyCost"))
    if total == 0.0:
        # Rare alt keys (defensive)
        total = to_float(summ.get("monthlyCost") or summ.get("totalCost"))
    return total

# --------------------------- Aggregate current/future/delta ---------------------------
data = read_json(OUT_PATH)

projects = data.get("projects", [])
past   = 0.0  # Current (baseline)
future = 0.0  # Future (PR)
delta  = 0.0  # Difference

# 1) Prefer per-project diffs when present (from `infracost diff` on plan JSON files)
for p in projects:
    d = p.get("diff") or {}
    past   += to_float(d.get("pastTotalMonthlyCost"))
    future += to_float(d.get("totalMonthlyCost"))
    delta  += to_float(d.get("diffTotalMonthlyCost"))

# 2) If still zero, try top-level summary (common when diffing two *breakdown* JSONs)
if past == 0.0 and future == 0.0 and delta == 0.0:
    top = data.get("summary") or {}
    if top:
        past   = to_float(top.get("pastTotalMonthlyCost"))
        future = to_float(top.get("totalMonthlyCost"))
        delta  = to_float(top.get("diffTotalMonthlyCost"))

# 3) Final fallback: read the two breakdown files directly
if past == 0.0 and future == 0.0 and delta == 0.0:
    base_total = read_breakdown_total(BASE_BREAKDOWN_PATH)
    pr_total   = read_breakdown_total(PR_BREAKDOWN_PATH)
    past, future, delta = base_total, pr_total, (pr_total - base_total)

# Derive daily/hourly
daily_past,  daily_future,  daily_delta  = past/30.0,  future/30.0,  delta/30.0
hourly_past, hourly_future, hourly_delta = past/730.0, future/730.0, delta/730.0
arr = arrow(delta)

# --------------------------- Markdown ---------------------------
md = []
# Optional mentions at the very top
if AUTHOR:   md.append(f"@{AUTHOR}")
if MENTIONS: md.append(MENTIONS)
if md: md.append("")

md.append("### 💸 Infracost Report")
md.append(f"\n{arr} Monthly delta: {CURRENCY_FLAG} {money(delta)}\n")

# Table uses plain $ amounts; the flag is shown only above once
md.append("| Period | Current 🟦 | Future 🟨 | Δ |")
md.append("|--------|-----------:|-----------:|---:|")
md.append(f"| Monthly | {money(past)} | {money(future)} | {arr} {money(delta)} |")
md.append(f"| Daily   | {money(daily_past)} | {money(daily_future)} | {arr} {money(daily_delta)} |")
md.append(f"| Hourly  | {money_hr(hourly_past)} | {money_hr(hourly_future)} | {arr} {money_hr(hourly_delta)} |")
md.append(f"\n{MARKER}")

# Write file
pathlib.Path(os.path.dirname(COMMENT_PATH) or ".").mkdir(parents=True, exist_ok=True)
with open(COMMENT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"✅ Wrote cost report to {COMMENT_PATH}")
print(f"ℹ️ Read diff JSON from {OUT_PATH}")
if BASE_BREAKDOWN_PATH or PR_BREAKDOWN_PATH:
    print(f"ℹ️ Breakdown fallbacks: base='{BASE_BREAKDOWN_PATH or '-'}', pr='{PR_BREAKDOWN_PATH or '-'}'")
print(f"ℹ️ Currency: {CURRENCY} ({CURRENCY_FLAG})")