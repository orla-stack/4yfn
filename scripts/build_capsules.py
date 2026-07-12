#!/usr/bin/env python3
"""Build /spinouts-capsule/index.html and /ai-capsule/index.html from the
existing /health-capsule/index.html template, using the JSON pulled by
fetch_capsules.py. Removes the Biorce spotlight card and rewrites all the
text/data specific to Health.
"""
import json, pathlib, re, time
from datetime import datetime

REPO = pathlib.Path("/Users/orla/Projects/4YFN")
SRC = REPO / "health-capsule" / "index.html"
DATA = pathlib.Path("/private/tmp/claude-501/-Users-orla-Projects-4YFN/7a2b42f9-03d9-4bda-904d-d0291688f68b/scratchpad/capsule_data.json")

data = json.loads(DATA.read_text())
template = SRC.read_text()

# ---- Day-of-year for the 2026 projection factor ----
today = datetime.now()
day_of_year = today.timetuple().tm_yday if today.year == 2026 else 141  # fallback to Health capsule's value

# ---- Helpers ----
def fmt_amount_short_usd(cents_or_usd, integer=True):
    """Format e.g. 61400000 -> $61M, 850000000 -> $850M, 1355333306 -> $1.4B."""
    v = cents_or_usd
    if v is None: return "—"
    if v >= 1e9: return f"${v/1e9:.1f}B"
    if v >= 1e6: return f"${round(v/1e6)}M"
    if v >= 1e3: return f"${round(v/1e3)}K"
    return f"${int(v)}"

def js_array(nums):
    return "[" + ",".join(str(int(n)) for n in nums) + "]"

def delete_spotlight(html):
    """Remove the Biorce spotlight card (Chart 5). The card is a <div class="card">
    block that starts after the CHART 5 comment and ends at its closing </div>."""
    # Match the CHART 5 banner comment through its closing </div>\n\n  (before the outer </div>).
    pattern = re.compile(
        r"\s*<!--\s*═+\s*\n"
        r"\s*CHART 5:[^\n]*\n"
        r"\s*═+\s*-->\s*\n"
        r"\s*<div class=\"card\">.*?</div>\s*\n\s*</div>",
        re.DOTALL,
    )
    m = pattern.search(html)
    if not m:
        raise RuntimeError("could not find spotlight card boundaries")
    # Preserve the outer </div> that follows
    return html[:m.start()] + "\n</div>" + html[m.end():]

def build_leaderboard_data(top_investors):
    """Return JS-object-array text for the leaderboard `investors` const."""
    lines = []
    for row in top_investors:
        name = row["name"].replace("'", "\\'")
        lines.append(f"      {{ name: '{name}', count: {int(row['count'])} }},")
    return "\n".join(lines)

def build(slug, config):
    label = config["label"]                  # 'Spinouts', 'AI'
    label_lc = config["label_lc"]            # 'spinouts', 'AI'
    industry_word = config["industry_word"]  # 'spinout', 'AI'
    cap = data["capsules"][config["data_key"]]
    annual = [r["amount"] for r in cap["annual_vc"]]
    annual_ai = [r["amount"] for r in cap["annual_ai_amount"]]
    stats = cap["stats"]
    lb = cap["leaderboard"]

    # Compute the 2026 projected total (same math as the Health capsule) so we
    # can put a real number in the chart 1 headline.
    ytd = annual[-1]
    projected = ytd * (365 / day_of_year)

    # Build 2020-vs-2026 share % for the chart 2 headline
    ai_share = cap["ai_share"]
    def pct_at(year):
        for r in ai_share:
            if r["year"] == year: return int(round(r["share"] * 100))
        return None
    start_pct = pct_at(2010)
    latest_pct = pct_at(2026)
    sector_adj = config["sector_adj"]
    # For the AI capsule the story is AI's share of *all VC*; label copy differs
    if config["data_key"] == "ai":
        share_headline = f"AI has grown from {start_pct}% to {latest_pct}% of all global VC in 2026"
        share_subtitle = "AI-tagged companies' share of global venture capital funding"
        share_legend = "AI share of global VC"
    else:
        share_headline = f"AI share of {sector_adj} VC has surged from {start_pct}% to a projected {latest_pct}% in 2026"
        share_subtitle = f"AI-enabled {industry_word} companies' share of global {industry_word} venture capital funding"
        share_legend = f"AI share of {sector_adj} VC"

    # Chart 1 headline: e.g. "Global AI VC set to hit $780B in 2026"
    proj_str = fmt_amount_short_usd(projected)
    if config["data_key"] == "ai":
        chart1_headline = f"Global AI VC set to hit {proj_str} in 2026"
    else:
        chart1_headline = f"Global {sector_adj} VC on track to {proj_str} in 2026"
    chart1_subtitle = f"Annual venture capital invested in {industry_word} companies worldwide, with 2026 figures annualised from year-to-date"

    # Chart 3 (bubbles) — pick the 5 headline numbers
    b1 = stats["exhibitors"]
    b2 = stats["cross_count"]
    b3 = stats["rounds"]
    b4 = fmt_amount_short_usd(stats["total_raised_usd"])
    b5 = fmt_amount_short_usd(stats["combined_value_usd"])
    b2_label = stats["cross_label"]

    # Chart 4 headline: "<top> is the runaway leader, backing X of N 4YFN26 <sector_adj> rounds"
    top_name = lb[0]["name"]; top_count = lb[0]["count"]
    chart4_headline = f"{top_name} tops the leaderboard, backing {top_count} of {stats['rounds']} 4YFN26 {sector_adj} rounds"
    chart4_subtitle = f"Most active investors in 4YFN26 {sector_adj} portfolio companies, ranked by rounds participated in"

    # ---- Do the substitutions ----
    html = template

    # 1. Delete the spotlight card
    html = delete_spotlight(html)

    # 2. <title>
    html = html.replace(
        "<title>4YFN Health Capsule — Dealroom</title>",
        f"<title>4YFN26 {label} Capsule — Dealroom</title>",
    )

    # 3. capsule-title on page
    html = html.replace(
        '<h1 class="capsule-title">4YFN26 Healthtech data capsule</h1>',
        f'<h1 class="capsule-title">4YFN26 {label} data capsule</h1>',
    )

    # 4. PDF cover title + sub
    html = html.replace(
        '<h1 class="pdf-cover-title">4YFN26 Healthtech<br/>data capsule</h1>',
        f'<h1 class="pdf-cover-title">4YFN26 {label}<br/>data capsule</h1>',
    )
    html = html.replace(
        "Global health VC trends, 4YFN Health 2026 cohort highlights, and the most active investors backing them.",
        f"Global {industry_word} VC trends, 4YFN26 {label} cohort highlights, and the most active investors backing them.",
    )

    # 5. Chart 1
    html = html.replace(
        "CHART 1: Global Health VC with 2026 projection",
        f"CHART 1: Global {label} VC with 2026 projection",
    )
    html = html.replace(
        '<h1 class="title">Global Health VC on track to rebound to $82B in 2026</h1>',
        f'<h1 class="title">{chart1_headline}</h1>',
    )
    html = html.replace(
        "Annual venture capital invested in health companies worldwide, with 2026 figures annualised from year-to-date",
        chart1_subtitle,
    )

    # 6. Chart 2 (AI share)
    html = html.replace(
        "CHART 2: AI share of Health VC over time",
        "CHART 2: AI share over time",
    )
    html = html.replace(
        '<h1 class="title">AI share of Health VC has surged from 2% to a projected 31% in 2026</h1>',
        f'<h1 class="title">{share_headline}</h1>',
    )
    html = html.replace(
        "AI-enabled health companies' share of global health venture capital funding",
        share_subtitle,
    )
    html = html.replace(
        "<span>AI share of Health VC</span>",
        f"<span>{share_legend}</span>",
    )

    # 7. Chart 3 (bubbles)
    html = html.replace(
        '<h1 class="title">4YFN26 Health at a glance</h1>',
        f'<h1 class="title">4YFN26 {label} at a glance</h1>',
    )
    html = html.replace(
        "Exhibitor and funding snapshot of the 4YFN26 Healthtech cohort",
        f"Exhibitor and funding snapshot of the 4YFN26 {label} cohort",
    )
    # bubble stats: b1..b5 numbers and their labels
    html = re.sub(
        r'<div class="bubble b1">\s*<div class="big-num">156</div>\s*<div class="label">Health<br/>exhibitors</div>',
        f'<div class="bubble b1">\n          <div class="big-num">{b1}</div>\n          <div class="label">{label_lc}<br/>exhibitors</div>',
        html,
    )
    html = re.sub(
        r'<div class="bubble b2">\s*<div class="big-num">40</div>\s*<div class="label">Health × AI</div>',
        f'<div class="bubble b2">\n          <div class="big-num">{b2}</div>\n          <div class="label">{b2_label}</div>',
        html,
    )
    html = re.sub(
        r'<div class="bubble b3">\s*<div class="big-num">206</div>\s*<div class="label">Funding<br/>rounds</div>',
        f'<div class="bubble b3">\n          <div class="big-num">{b3}</div>\n          <div class="label">Funding<br/>rounds</div>',
        html,
    )
    html = re.sub(
        r'<div class="bubble b4">\s*<div class="big-num">€168M</div>\s*<div class="label">VC raised</div>',
        f'<div class="bubble b4">\n          <div class="big-num">{b4}</div>\n          <div class="label">VC raised</div>',
        html,
    )
    html = re.sub(
        r'<div class="bubble b5">\s*<div class="big-num">€850M</div>\s*<div class="label">Combined<br/>value</div>',
        f'<div class="bubble b5">\n          <div class="big-num">{b5}</div>\n          <div class="label">Combined<br/>value</div>',
        html,
    )

    # 8. Chart 4 (leaderboard)
    html = html.replace(
        '<h1 class="title">EIT Health is the runaway leader, backing 43 of 206 4YFN Health rounds</h1>',
        f'<h1 class="title">{chart4_headline}</h1>',
    )
    html = html.replace(
        "Most active investors in 4YFN Health portfolio companies, ranked by rounds participated in",
        chart4_subtitle,
    )
    # Substitute the investors const in JS
    investors_new = build_leaderboard_data(lb)
    html = re.sub(
        r"const investors = \[\n(?:      \{[^}]+\},\n)+\s*\];",
        f"const investors = [\n{investors_new}\n    ];",
        html,
    )

    # 9. JS data arrays: HEALTH_VC and AI_HEALTH become <SLUG>_VC and AI_<SLUG>
    html = html.replace(
        f"const HEALTH_VC = [11569686153, 13005228269, 12251705491, 14460912830, 20562477994, 30374775283, 28917339747, 39386435786, 55711238555, 57646262236, 83231803629, 133100822224, 91858322902, 64341077110, 70034613609, 70775350767, 31704692820];",
        f"const HEALTH_VC = {js_array(annual)};",
    )
    html = html.replace(
        f"const AI_HEALTH = [246913998, 353516076, 367703045, 715220111, 1159144836, 1910621066, 3316890963, 4654670950, 6103204089, 6566119133, 9543183370, 19132278273, 11712266582, 7978929991, 11077337928, 15444457389, 9981116501];",
        f"const AI_HEALTH = {js_array(annual_ai)};",
    )

    # 10. Update the ANNUAL_FACTOR comment + value to reflect the actual day of year
    html = re.sub(
        r"// 2026 annualisation factor \(today is [^)]+\)\s*\n\s*const ANNUAL_FACTOR = 365 / \d+;",
        f"// 2026 annualisation factor (today is day {day_of_year} of the year)\n  const ANNUAL_FACTOR = 365 / {day_of_year};",
        html,
    )

    # 11. Replace the client-side AI_SHARE derivation with a hardcoded array (using
    #     the correctly-computed share values from the API). This is critical for
    #     the AI capsule, where AI_HEALTH == HEALTH_VC would otherwise produce a
    #     flat 100% line.
    share_arr = "[" + ",".join(f"{r['share']:.6f}" for r in cap["ai_share"]) + "]"
    html = html.replace(
        "const AI_SHARE = HEALTH_VC.map((h, i) => AI_HEALTH[i] / h);",
        f"const AI_SHARE = {share_arr};",
    )

    return html

configs = {
    "spinouts-capsule": {
        "data_key": "spinout",
        "label": "Spinouts",           # cohort name (plural) — e.g. "4YFN26 Spinouts at a glance"
        "label_lc": "Spinout",          # bubble label (singular adjective)
        "industry_word": "spinout",     # noun form — e.g. "spinout companies"
        "sector_adj": "Spinout",        # adjective form — e.g. "Spinout VC"
    },
    "ai-capsule": {
        "data_key": "ai",
        "label": "AI",
        "label_lc": "AI",
        "industry_word": "AI",
        "sector_adj": "AI",
    },
}

for folder, cfg in configs.items():
    out_dir = REPO / folder
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(build(folder, cfg))
    print(f"wrote {out} ({len(out.read_text())} bytes)")
