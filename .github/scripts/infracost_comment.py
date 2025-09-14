#!/usr/bin/env python3
import json, os, sys, pathlib, re

# ---------- CLI args ----------
argv_out   = sys.argv[1] if len(sys.argv) > 1 else ""         # infracost.out.json (diff)
argv_md    = sys.argv[2] if len(sys.argv) > 2 else ""         # output markdown path

# ---------- Env / inputs ----------
AUTHOR   = os.getenv("PR_AUTHOR", "").strip()
MENTIONS = os.getenv("MENTION_HANDLES", "").strip()
MARKER   = os.getenv("INPUT_COMMENT_MARKER", "<!-- infracost-comment -->").strip()

# Currency flag used only in the delta headline
CURRENCY = os.getenv("INFRACOST_CURRENCY", os.getenv("CURRENCY", "USD")).upper().strip()
FLAG_MAP = {
    "USD":"🇺🇸","EUR":"🇪🇺","GBP":"🇬🇧","INR":"🇮🇳","AUD":"🇦🇺","CAD":"🇨🇦",
    "JPY":"🇯🇵","NZD":"🇳🇿","CHF":"🇨🇭","SEK":"🇸🇪",
}
CURRENCY_FLAG = os.getenv("CURRENCY_FLAG", FLAG_MAP.get(CURRENCY, "💱")).strip()

WS = os.getenv("GITHUB_WORKSPACE", "").rstrip("/")

# Where the action saved files
WD   = os.getenv("INFRACOST_WD", os.path.join(WS, ".github/fixtures/terraform") if WS else ".")
PR_J = os.path.join(WD, ".infracost-pr.json")
BA_J = os.path.join(WD, ".infracost-base.json")

# Resolve diff JSON (optional but nice to have)
candidates_out = [
    argv_out,
    os.getenv("INFRACOST_OUT_PATH", "").strip(),
    os.path.join(WD, "infracost.out.json"),
    "infracost.out.json",
]
def first_file(paths):
    for p in paths:
        if p and os.path.isfile(p): return p
    return None

OUT_PATH = first_file(candidates_out)

# Resolve output MD path
COMMENT_PATH = argv_md or os.getenv("INFRACOST_COMMENT_PATH", "").strip()
if not COMMENT_PATH:
    COMMENT_PATH = os.path.join(WD, "infracost_comment.md")

# ---------- Helpers ----------
def to_float(x):
    try:
        if x in (None, "", "-", "null"): return 0.0
        return float(x)
    except Exception:
        s = re.sub(r"[^\d\.\-eE]", "", str(x))
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

def sum_total_monthly_cost(infracost_json_path):
    """Sum projects[].breakdown.totalMonthlyCost (Infracost breakdown output)."""
    if not infracost_json_path or not os.path.isfile(infracost_json_path):
        return None
    with open(infracost_json_path) as f:
        data = json.load(f)
    total = 0.0
    for p in data.get("projects", []):
        # Breakdown JSON has projects[].breakdown.totalMonthlyCost
        b = p.get("breakdown") or {}
        total += to_float(b.get("totalMonthlyCost"))
    return total

def read_diff_totals(diff_json_path):
    """Read Current/Future/Delta from a diff JSON if it actually contains them."""
    if not diff_json_path or not os.path.isfile(diff_json_path):
        return None
    with open(diff_json_path) as f:
        data = json.load(f)
    cur = fut = dlt = 0.0
    found_any = False
    for p in data.get("projects", []):
        d = p.get("diff") or {}
        if d:
            found_any = True
            cur += to_float(d.get("pastTotalMonthlyCost"))
            fut += to_float(d.get("totalMonthlyCost"))
            dlt += to_float(d.get("diffTotalMonthlyCost"))
    if not found_any:
        return None
    return (cur, fut, dlt)

# ---------- Compute current/future/delta ----------
# 1) Try to get all three from diff JSON (best case)
totals = read_diff_totals(OUT_PATH)

# 2) If diff lacks past/future, compute Current/Future from the two breakdown files
if totals is None or (totals[0] == 0.0 and os.path.isfile(BA_J)):
    current = sum_total_monthly_cost(BA_J)
    future  = sum_total_monthly_cost(PR_J)
    if current is None or future is None:
        # Last resort: if we still can't read, fall back to zeros to avoid crashing
        current = current or 0.0
        future  = future  or 0.0
    delta = future - current
else:
    current, future, delta = totals

# ---------- Derive per-day/hour ----------
daily_current,  daily_future,  daily_delta  = current/30.0,  future/30.0,  delta/30.0
hourly_current, hourly_future, hourly_delta = current/730.0, future/730.0, delta/730.0
arr = arrow(delta)

# ---------- Markdown ----------
lines = []
if AUTHOR:   lines.append(f"@{AUTHOR}")
if MENTIONS: lines.append(MENTIONS)
if lines:    lines.append("")

lines.append("### 💸 Infracost Report\n")
lines.append(f"{arr} Monthly delta: {CURRENCY_FLAG} {money(delta)}\n")
lines.append("| Period | Current 🟦 | Future 🟨 | Δ |")
lines.append("|--------|-----------:|-----------:|---:|")
lines.append(f"| Monthly | {money(current)} | {money(future)} | {arr} {money(delta)} |")
lines.append(f"| Daily   | {money(daily_current)} | {money(daily_future)} | {arr} {money(daily_delta)} |")
lines.append(f"| Hourly  | {money_hr(hourly_current)} | {money_hr(hourly_future)} | {arr} {money_hr(hourly_delta)} |")
lines.append(f"\n{MARKER}")

pathlib.Path(os.path.dirname(COMMENT_PATH) or ".").mkdir(parents=True, exist_ok=True)
with open(COMMENT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ Wrote cost report → {COMMENT_PATH}")
print(f"ℹ️ Current(FROM base breakdown) = {money(current)}")
print(f"ℹ️ Future (FROM PR breakdown)   = {money(future)}")
if OUT_PATH:
    print(f"ℹ️ Also checked diff JSON       = {OUT_PATH}")
else:
    print("ℹ️ No diff JSON provided; used breakdown files only.")