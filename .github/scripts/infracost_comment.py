#!/usr/bin/env python3
import json, sys, re, math, os

def money_to_float(s):
    if not s:
        return 0.0
    # strip everything except digits, dot, minus
    t = re.sub(r'[^0-9.\-]', '', s)
    try:
        return float(t) if t else 0.0
    except ValueError:
        return 0.0

def sum_totals(data):
    currency = data.get("currency") or "USD"
    curr = currency
    total_past = 0.0
    total_prop = 0.0
    total_delta = 0.0
    for p in data.get("projects", []):
        d = p.get("diff")
        if d:
            total_past   += money_to_float(d.get("pastTotalMonthlyCost"))
            total_prop   += money_to_float(d.get("proposedTotalMonthlyCost"))
            total_delta  += money_to_float(d.get("totalMonthlyCost"))
        else:
            b = p.get("breakdown") or {}
            total_prop += money_to_float(b.get("totalMonthlyCost"))
    if total_delta == 0.0 and total_past and total_prop:
        total_delta = total_prop - total_past
    return curr, total_past, total_prop, total_delta

def per_day(x):  return x/30.0
def per_hour(x): return x/730.0

def flag_for(currency):
    m = {
        "USD":"🇺🇸","EUR":"🇪🇺","GBP":"🇬🇧","SEK":"🇸🇪","NOK":"🇳🇴","DKK":"🇩🇰",
        "INR":"🇮🇳","AUD":"🇦🇺","CAD":"🇨🇦","JPY":"🇯🇵","CHF":"🇨🇭","CNY":"🇨🇳"
    }
    return m.get(currency.upper(), "🏳️")

def sym_for(currency):
    m = {"USD":"$","EUR":"€","GBP":"£","SEK":"kr","NOK":"kr","DKK":"kr","INR":"₹","AUD":"$","CAD":"$","JPY":"¥","CHF":"CHF","CNY":"¥"}
    return m.get(currency.upper(), currency.upper()+" ")

def fmt_money(cur, x, places=2, pad=False):
    sym = sym_for(cur)
    s = f"{sym}{x:,.{places}f}"
    return s.rjust(12) if pad else s

def trend(delta):
    if delta > 0.0005:  return "🔴 ↑"
    if delta < -0.0005: return "🟢 ↓"
    return "⚪ ↔️"

def main(inp, outp):
    with open(inp) as f:
        data = json.load(f)
    cur, past_m, prop_m, d_m = sum_totals(data)
    d_d = per_day(d_m); d_h = per_hour(d_m)
    past_d = per_day(past_m); prop_d = per_day(prop_m)
    past_h = per_hour(past_m); prop_h = per_hour(prop_m)

    flag = flag_for(cur)
    T = trend(d_m)

    author = os.getenv("PR_AUTHOR") or ""
    mentions = (os.getenv("MENTION_HANDLES") or "").strip()
    header_ping = (f"@{author}\n\n" if author else "")
    if mentions:
        header_ping += mentions + "\n\n"

    lines = []
    lines.append("### 💸 Infracost Report")
    if header_ping.strip():
        lines.append(header_ping.strip())
        lines.append("")
    if abs(d_m) < 0.0005:
        lines.append("⚪ No cost change.")
    else:
        lines.append(f"{T} Monthly delta: {flag} {fmt_money(cur, d_m)}")
    lines.append("")
    lines.append("| Period | Current 🟦 | Future 🟨 | Δ |")
    lines.append("|--------|-----------:|-----------:|---:|")
    lines.append(f"| Monthly | {flag} {fmt_money(cur, past_m)} | {flag} {fmt_money(cur, prop_m)} | {T} {flag} {fmt_money(cur, d_m)} |")
    lines.append(f"| Daily   | {flag} {fmt_money(cur, past_d)} | {flag} {fmt_money(cur, prop_d)} | {T} {flag} {fmt_money(cur, d_d)} |")
    lines.append(f"| Hourly  | {flag} {fmt_money(cur, past_h,4)} | {flag} {fmt_money(cur, prop_h,4)} | {T} {flag} {fmt_money(cur, d_h,4)} |")
    lines.append("")
    lines.append(os.getenv("INPUT_COMMENT_MARKER") or "<!-- infracost-comment -->")

    with open(outp, "w") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: infracost_comment.py <infracost.out.json> <out.md>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])