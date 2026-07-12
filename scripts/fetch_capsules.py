#!/usr/bin/env python3
"""Pull all data needed for the 4YFN26 AI + Spinouts capsules.

Endpoint choices (all confirmed against the beta API):
  - /api/analytics/aggregate/funding-rounds  (requires group_by; response rows
    are {dimension, sum_amount, count})
  - /api/data/transactions  (paged rounds with investors[])
  - /api/data/entities      (page.total for cohort sizes)
"""
import json, pathlib, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

ENV_PATH = "/Users/orla/Projects/4YFN/.env"
TOKEN_PATH = "/tmp/dr_token"
OUT_DIR = pathlib.Path("/private/tmp/claude-501/-Users-orla-Projects-4YFN/7a2b42f9-03d9-4bda-904d-d0291688f68b/scratchpad")
API = "https://api-next.beta.dealroom.co"

env = {}
for line in open(ENV_PATH):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

CID = env["DEALROOM_CLIENT_ID"]
TOKEN = open(TOKEN_PATH).read().strip()

TAG = {
    "ai":     202,       # technology
    "spinout":1651201,   # sector
    "yfn26":  2296201,   # sector
    "health": 125403,    # industry (used as cross-cut for the AI capsule)
}

YEARS = list(range(2010, 2027))

def call(path, params, retries=3):
    parts = []
    for k, v in params:
        parts.append(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='[](),|:+.-')}")
    url = f"{API}{path}?{'&'.join(parts)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "X-Client-Id": CID,
        "User-Agent": "4yfn-capsules@claude",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")[:300]
            if e.code in (429, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f"{e.code} for {path} {params}: {body}") from e
        except Exception:
            if attempt < retries - 1:
                time.sleep(1); continue
            raise
    raise RuntimeError("retries exhausted")

def count_entities(filt):
    r = call("/api/data/entities", [("filter", filt), ("limit", 1), ("include_total", "true")])
    return r["page"]["total"]

def annual_sums(filt, years=YEARS):
    """Return {year: sum_amount} for VC rounds matching filt, over given years."""
    filt_with_years = f"and({filt},year[gte]:{years[0]},year[lte]:{years[-1]})"
    r = call("/api/analytics/aggregate/funding-rounds", [
        ("filter", filt_with_years),
        ("metric", "sum:amount"),
        ("group_by", "year"),
    ])
    out = {int(row["dimension"]): int(row["sum_amount"] or 0) for row in r.get("data", [])}
    return [{"year": y, "amount": out.get(y, 0)} for y in years]

def cohort_total_raised(filt):
    """Sum of amount for all rounds matching filt (across all years)."""
    r = call("/api/analytics/aggregate/funding-rounds", [
        ("filter", filt),
        ("metric", "sum:amount"),
        ("group_by", "year"),  # required but we sum client-side
    ])
    return sum(int(row["sum_amount"] or 0) for row in r.get("data", []))

def cohort_combined_valuation(company_filter):
    """Sum of latest_valuation for companies matching filter. Uses the companies
    aggregate with a benign group_by then sums."""
    try:
        r = call("/api/analytics/aggregate/companies", [
            ("filter", company_filter),
            ("metric", "sum:latest_valuation"),
            ("group_by", "hq_continent"),  # benign dimension
        ])
        return sum(int(row.get("sum_latest_valuation") or 0) for row in r.get("data", []))
    except Exception as e:
        print(f"  combined val failed: {e}", file=sys.stderr)
        return None

def cohort_rounds(filt):
    return call("/api/data/transactions", [
        ("filter", filt), ("limit", 1), ("include_total", "true"),
    ])["page"]["total"]

def leaderboard(round_filter, top_n=10, page_limit=500):
    """Page through all rounds matching filter, tally investor participation."""
    tally = Counter()
    offset = 0
    total_rounds = 0
    while True:
        r = call("/api/data/transactions", [
            ("filter", round_filter),
            ("limit", page_limit),
            ("offset", offset),
        ])
        rows = r.get("data", [])
        if not rows:
            break
        for tx in rows:
            for inv in tx.get("investors") or []:
                if inv.get("name"):
                    tally[inv["name"]] += 1
        total_rounds += len(rows)
        if len(rows) < page_limit:
            break
        offset += page_limit
        if offset > 5000:  # safety cap
            print(f"  leaderboard: capping at {offset} rounds", file=sys.stderr)
            break
    top = [{"name": n, "count": c} for n, c in tally.most_common(top_n)]
    print(f"  leaderboard: {total_rounds} rounds, {len(tally)} distinct investors", file=sys.stderr)
    return top

def build_capsule(slug, tag_id, label):
    print(f"\n==== {label} ({slug}) ====", file=sys.stderr)
    cohort_company = f"and(organization_subtype[eq]:company,tag_id[in_all]:{TAG['yfn26']}|{tag_id})"
    cohort_round = f"company.tag_id[in_all]:{TAG['yfn26']}|{tag_id}"
    # Cross-cut with a complementary sector: AI capsule uses Health, others use AI
    if tag_id == TAG["ai"]:
        cross_tag = TAG["health"]; cross_label = "AI × Health"
    else:
        cross_tag = TAG["ai"]; cross_label = f"{label} × AI"
    cross_filter = f"and(organization_subtype[eq]:company,tag_id[in_all]:{TAG['yfn26']}|{tag_id}|{cross_tag})"

    print("  annual VC series...", file=sys.stderr)
    annual_vc = annual_sums(f"company.tag_id[eq]:{tag_id}")

    # AI-share series (only meaningful for sectors that aren't already "AI")
    print("  AI-share series...", file=sys.stderr)
    if tag_id == TAG["ai"]:
        # For the AI capsule: show AI as share of ALL global VC
        annual_ai = annual_vc
        annual_all = annual_sums("year[gte]:2010")  # everything
        ai_share = [
            {"year": y["year"], "share": (a["amount"] / y["amount"]) if y["amount"] else 0}
            for a, y in zip(annual_ai, annual_all)
        ]
        ai_share_label = "ai_share_of_all_vc"
    else:
        # For the Spinout capsule: AI share of Spinout VC
        annual_ai = annual_sums(f"company.tag_id[in_all]:{tag_id}|{TAG['ai']}")
        ai_share = [
            {"year": v["year"], "share": (a["amount"] / v["amount"]) if v["amount"] else 0}
            for a, v in zip(annual_ai, annual_vc)
        ]
        ai_share_label = "ai_share_of_sector_vc"

    print("  cohort stats...", file=sys.stderr)
    stats = {
        "exhibitors": count_entities(cohort_company),
        "cross_count": count_entities(cross_filter),
        "cross_label": cross_label,
        "rounds": cohort_rounds(cohort_round),
        "total_raised_usd": cohort_total_raised(cohort_round),
        "combined_value_usd": cohort_combined_valuation(cohort_company),
    }

    print("  leaderboard...", file=sys.stderr)
    lb = leaderboard(cohort_round, top_n=10)

    return {
        "annual_vc": annual_vc,
        "ai_share": ai_share,
        "ai_share_label": ai_share_label,
        "annual_ai_amount": annual_ai,
        "stats": stats,
        "leaderboard": lb,
    }

OUT = {
    "generated_at": time.strftime("%Y-%m-%d"),
    "capsules": {
        "ai":      build_capsule("ai", TAG["ai"], "AI"),
        "spinout": build_capsule("spinout", TAG["spinout"], "Spinouts"),
    },
}

out_path = OUT_DIR / "capsule_data.json"
out_path.write_text(json.dumps(OUT, indent=2))
print(f"\nwrote {out_path}", file=sys.stderr)
