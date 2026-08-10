#!/usr/bin/env python3
"""Build /spinouts-capsule/index.html and /ai-capsule/index.html from the
existing /health-capsule/index.html template.

Each capsule replaces the Biorce spotlight with its own tail card:
  * Spin-off capsule → Floodwaive spotlight (pitch-battle winner)
  * AI capsule       → Top AI breakouts list

The investor leaderboards use the Health-excluded variant so ranking isn't
dominated by health-focused investors like EIT Health, with a footnote noting
the exclusion.
"""
import base64, json, pathlib, re
from datetime import datetime

REPO = pathlib.Path("/Users/orla/Projects/4YFN")
SRC = REPO / "health-capsule" / "index.html"
DATA = pathlib.Path("/private/tmp/claude-501/-Users-orla-Projects-4YFN/7a2b42f9-03d9-4bda-904d-d0291688f68b/scratchpad/capsule_data.json")

data = json.loads(DATA.read_text())
template = SRC.read_text()

today = datetime.now()
day_of_year = today.timetuple().tm_yday if today.year == 2026 else 141

# ---- Formatting helpers ----
def fmt_amount_short_usd(v):
    if v is None: return "—"
    if v >= 1e9: return f"${v/1e9:.1f}B"
    if v >= 1e6: return f"${round(v/1e6)}M"
    if v >= 1e3: return f"${round(v/1e3)}K"
    return f"${int(v)}"

def fmt_amount_short_eur(v):
    if v is None: return "—"
    if v >= 1e9: return f"€{v/1e9:.1f}B"
    if v >= 1e6: return f"€{round(v/1e6)}M"
    if v >= 1e3: return f"€{round(v/1e3)}K"
    return f"€{int(v)}"

def js_array(nums):
    return "[" + ",".join(str(int(n)) for n in nums) + "]"

# ---- Spotlight card (Biorce-style shape, filled in per capsule) ----
def spotlight_card_html(
    *, title, subtitle, name, tagline, meta_line, logo_data_uri, stats, about, footer_svgs,
):
    """Render a spotlight card. stats is a list of dicts with keys:
    num, num_class (empty, coral, blue, violet, small, with-icon), label, sub,
    optional card_class ('award'), optional prefix_svg."""
    stat_blocks = []
    for s in stats:
        card_cls = f' {s["card_class"]}' if s.get("card_class") else ""
        num_cls = f' {s["num_class"]}' if s.get("num_class") else ""
        prefix = s.get("prefix_svg", "")
        stat_blocks.append(f'''\
      <div class="spot-stat{card_cls}">
        <div class="spot-stat-num{num_cls}">{prefix}{s["num"]}</div>
        <div class="spot-stat-label">{s["label"]}</div>
        <div class="spot-stat-sub">{s["sub"]}</div>
      </div>''')
    stats_html = "\n".join(stat_blocks)

    return f'''\
  <!-- ════════════════════════════════════════════════════════════════
       CHART 5: Company spotlight
       ════════════════════════════════════════════════════════════════ -->
  <div class="card">
    <button class="download-btn" aria-label="Download chart as PNG" title="Download as PNG">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
    </button>
    <h1 class="title">{title}</h1>
    <div class="subtitle">{subtitle}</div>

    <div class="spot-hero">
      <div class="spot-logo">
        <img src="{logo_data_uri}" alt="{name} logo" />
      </div>
      <div class="spot-id">
        <div class="spot-name">{name}</div>
        <div class="spot-tagline">{tagline}</div>
        <div class="spot-meta">{meta_line}</div>
      </div>
    </div>

    <div class="spot-stats">
{stats_html}
    </div>

    <div class="spot-about">
      {about}
    </div>

    <div class="footer">
      <span class="source">Source: Dealroom.co</span>
      <div class="logos">
        {footer_svgs}
      </div>
    </div>
  </div>'''

# ---- Breakouts list card (bespoke to AI capsule) ----
def breakouts_card_html(companies, footer_svgs):
    rows = []
    for i, c in enumerate(companies, start=1):
        funding = fmt_amount_short_eur(c["total_funding_eur"]) if c.get("total_funding_eur") else "—"
        signal = f'{c["signal"]:.1f}' if c.get("signal") is not None else "—"
        hq = ", ".join(x for x in [c.get("hq_city"), c.get("hq_country")] if x)
        meta = f'{hq}' + (f' · Founded {c["launch_year"]}' if c.get("launch_year") else "")
        tagline = (c.get("tagline") or "").replace("&", "&amp;").replace("<", "&lt;")
        rows.append(f'''\
      <div class="bo-row">
        <div class="bo-rank">{i}</div>
        <div class="bo-info">
          <div class="bo-name">{c["name"]}</div>
          <div class="bo-tagline">{tagline}</div>
          <div class="bo-meta">{meta}</div>
        </div>
        <div class="bo-metric bo-funding">{funding}</div>
        <div class="bo-metric bo-signal">{signal}</div>
      </div>''')
    rows_html = "\n".join(rows)
    return f'''\
  <!-- ════════════════════════════════════════════════════════════════
       CHART 5: Top AI breakouts from 4YFN26
       ════════════════════════════════════════════════════════════════ -->
  <div class="card">
    <button class="download-btn" aria-label="Download chart as PNG" title="Download as PNG">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
    </button>
    <h1 class="title">Breakout AI startups from 4YFN26</h1>
    <div class="subtitle">4YFN 2026 AI exhibitors with a Dealroom Signal ≥ 80, founded 2015+, and €13M–€90M raised — sorted by Signal</div>

    <div class="bo-list">
      <div class="bo-head">
        <div></div>
        <div>Company</div>
        <div class="bo-metric-label">Total raised</div>
        <div class="bo-metric-label">Signal</div>
      </div>
{rows_html}
    </div>

    <div class="footer">
      <span class="source">Source: Dealroom.co</span>
      <div class="logos">
        {footer_svgs}
      </div>
    </div>
  </div>'''

# CSS to append (inside <style>) for the breakouts list.
BREAKOUTS_CSS = """
    /* ── AI breakouts list ─────────────────────────────── */
    .bo-list {
      margin-top: 22px;
      display: flex;
      flex-direction: column;
    }
    .bo-head, .bo-row {
      display: grid;
      grid-template-columns: 32px 1fr 100px 70px;
      gap: 16px;
      align-items: center;
    }
    .bo-head {
      padding: 0 0 10px;
      border-bottom: 1px solid var(--border);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
    }
    .bo-metric-label { text-align: right; }
    .bo-row {
      padding: 14px 0;
      border-bottom: 1px solid var(--border);
    }
    .bo-row:last-child { border-bottom: none; }
    .bo-rank {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 15px;
      font-weight: 700;
      color: var(--text-muted);
      text-align: right;
    }
    .bo-info { min-width: 0; }
    .bo-name {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 15px;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -0.01em;
    }
    .bo-tagline {
      font-size: 12px;
      color: var(--text-secondary);
      margin-top: 2px;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    .bo-meta {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-top: 4px;
    }
    .bo-metric {
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      text-align: right;
    }
    .bo-funding { font-size: 15px; color: var(--text); }
    .bo-signal { font-size: 15px; color: var(--uv); }

    /* Leaderboard footnote about Health exclusion */
    .lb-note {
      margin-top: 12px;
      font-size: 11px;
      font-style: italic;
      color: var(--text-muted);
    }
"""

# ---- Existing helpers ----
def build_leaderboard_data(top_investors):
    lines = []
    for row in top_investors:
        name = row["name"].replace("'", "\\'")
        lines.append(f"      {{ name: '{name}', count: {int(row['count'])} }},")
    return "\n".join(lines)

# ---- Extract Dealroom + 4YFN partner logo SVGs from the template so we can
# reuse them inside injected cards.
DEALROOM_SVG_MATCH = re.search(
    r'<svg xmlns="http://www\.w3\.org/2000/svg" viewBox="0 0 222\.15 53\.28" width="110" height="26">.*?</svg>',
    template, re.DOTALL,
)
YFN_SVG_MATCH = re.search(
    r'<svg class="partner-logo"[^>]*aria-label="4YFN"[^>]*>.*?</svg>',
    template, re.DOTALL,
)
DEALROOM_SVG = DEALROOM_SVG_MATCH.group(0)
YFN_SVG = YFN_SVG_MATCH.group(0)
FOOTER_LOGOS_HTML = f'{YFN_SVG}\n        <span class="logo-divider"></span>\n        {DEALROOM_SVG}'

TROPHY_SVG = '<svg class="award-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" clip-rule="evenodd" d="M5.166 2.621v.858c-1.035.148-2.059.33-3.071.543a.75.75 0 0 0-.584.859 6.753 6.753 0 0 0 6.138 5.6 6.73 6.73 0 0 0 2.743 1.346A6.707 6.707 0 0 1 9.279 15H8.54c-1.036 0-1.875.84-1.875 1.875V19.5h-.75a2.25 2.25 0 0 0-2.25 2.25c0 .414.336.75.75.75h15a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-2.25-2.25h-.75v-2.625c0-1.036-.84-1.875-1.875-1.875h-.739a6.706 6.706 0 0 1-1.112-3.173 6.73 6.73 0 0 0 2.743-1.347 6.753 6.753 0 0 0 6.139-5.6.75.75 0 0 0-.585-.858 47.077 47.077 0 0 0-3.07-.543V2.62a.75.75 0 0 0-.658-.744 49.22 49.22 0 0 0-6.093-.377c-2.063 0-4.096.128-6.093.377a.75.75 0 0 0-.657.744ZM5.166 5.25c0 1.196.312 2.32.857 3.294A5.266 5.266 0 0 1 3.16 5.337c.663-.128 1.335-.243 2.006-.343V5.25Zm13.5 0v-.256c.674.1 1.343.214 2.006.343a5.265 5.265 0 0 1-2.863 3.207 6.72 6.72 0 0 0 .857-3.294Z"/></svg>'

def delete_spotlight_html(html):
    """Delete just the spotlight card HTML (chart 5). Keeps the .spot-* CSS in
    place so subsequently-injected spotlight cards still render."""
    pattern = re.compile(
        r"\n\n  <!--\s*═+\s*\n"
        r" +CHART 5:[^\n]*\n"
        r" +═+\s*-->\s*\n"
        r"  <div class=\"card\">.*?\n  </div>",
        re.DOTALL,
    )
    new_html, n = pattern.subn("", html)
    if n != 1:
        raise RuntimeError(f"expected exactly 1 spotlight-card match, got {n}")
    return new_html

def inject_card(html, card_html):
    """Insert a card immediately before the closing </div> of the .outer container."""
    marker = "\n\n</div>\n\n<script>"
    if marker not in html:
        raise RuntimeError("could not find outer/script boundary")
    return html.replace(marker, f"\n\n{card_html}\n\n</div>\n\n<script>", 1)

def inject_css(html, css):
    """Append CSS just before </style>."""
    return html.replace("\n  </style>", f"{css}\n  </style>", 1)

def build(slug, config):
    label = config["label"]
    label_lc = config["label_lc"]
    industry_word = config["industry_word"]
    sector_adj = config["sector_adj"]
    cap = data["capsules"][config["data_key"]]
    annual = [r["amount"] for r in cap["annual_vc"]]
    annual_ai = [r["amount"] for r in cap["annual_ai_amount"]]
    stats = cap["stats"]
    lb_ex_health = cap["leaderboard_ex_health"]
    stats_ex_health = cap["stats_ex_health"]

    # 2026 projection
    ytd = annual[-1]
    projected = ytd * (365 / day_of_year)

    ai_share = cap["ai_share"]
    def pct_at(year):
        for r in ai_share:
            if r["year"] == year: return int(round(r["share"] * 100))
        return None
    start_pct = pct_at(2010)
    latest_pct = pct_at(2026)

    if config["data_key"] == "ai":
        share_headline = f"AI has grown from {start_pct}% to {latest_pct}% of all global VC in 2026"
        share_subtitle = "AI-tagged companies' share of global venture capital funding"
        share_legend = "AI share of global VC"
    else:
        share_headline = f"AI share of {sector_adj} VC has surged from {start_pct}% to a projected {latest_pct}% in 2026"
        share_subtitle = f"AI-enabled {industry_word} companies' share of global {industry_word} venture capital funding"
        share_legend = f"AI share of {sector_adj} VC"

    proj_str = fmt_amount_short_usd(projected)
    if config["data_key"] == "ai":
        chart1_headline = f"Global AI VC set to hit {proj_str} in 2026"
    else:
        chart1_headline = f"Global {sector_adj} VC on track to {proj_str} in 2026"
    chart1_subtitle = f"Annual venture capital invested in {industry_word} companies worldwide, with 2026 figures annualised from year-to-date"

    # Chart 3 bubbles (still use full cohort — not Health-excluded)
    b1 = stats["exhibitors"]
    b2 = stats["cross_count"]
    b3 = stats["rounds"]
    b4 = fmt_amount_short_usd(stats["total_raised_usd"])
    b2_label = stats["cross_label"]
    bubbles_footnote = None
    if config["data_key"] == "spinout":
        b2_label = "Spin-offs × AI"
        # Combined value with Akamai in the mix is misleading — Akamai is a
        # public NASDAQ company and dominates the sum. Show the ex-Akamai
        # figure with a footnote flagging the exclusion.
        if stats.get("combined_value_ex_akamai_usd") and stats.get("akamai_valuation_usd"):
            b5 = fmt_amount_short_usd(stats["combined_value_ex_akamai_usd"]) + "*"
            akamai_val_str = fmt_amount_short_usd(stats["akamai_valuation_usd"])
            bubbles_footnote = (
                f"*Excludes Akamai, an MIT spin-off with a valuation of "
                f"~{akamai_val_str}"
            )
        else:
            b5 = fmt_amount_short_usd(stats["combined_value_usd"])
    else:
        b5 = fmt_amount_short_usd(stats["combined_value_usd"])

    # Chart 4 uses Health-excluded data
    top_name = lb_ex_health[0]["name"]
    top_count = lb_ex_health[0]["count"]
    ex_rounds = stats_ex_health["rounds"]
    ex_cohort = stats_ex_health["exhibitors"]
    chart4_headline = (
        f"{top_name} tops the leaderboard, involved in {top_count} of {ex_rounds} "
        f"rounds raised by the 4YFN 2026 {sector_adj} cohort*"
    )
    if config["data_key"] == "ai":
        chart4_subtitle = (
            f"Most active investors across 4YFN 2026 AI startups, "
            f"excluding the AI × Healthtech overlap"
        )
        chart4_footnote = f"*Excludes 4YFN 2026 AI × Healthtech companies. {ex_cohort} companies included."
    else:
        chart4_subtitle = (
            f"Most active investors across 4YFN 2026 {sector_adj} startups, "
            f"excluding Healthtech spin-offs"
        )
        chart4_footnote = f"*Excludes 4YFN 2026 Healthtech {industry_word}s. {ex_cohort} companies included."

    # ---- Substitutions ----
    html = template

    # 1. Delete spotlight HTML
    html = delete_spotlight_html(html)

    # 2. Titles
    html = html.replace(
        "<title>4YFN Health Capsule — Dealroom</title>",
        f"<title>4YFN26 {label} Capsule — Dealroom</title>",
    )
    html = html.replace(
        '<h1 class="capsule-title">4YFN26 Healthtech data capsule</h1>',
        f'<h1 class="capsule-title">4YFN26 {label} data capsule</h1>',
    )
    html = html.replace(
        '<h1 class="pdf-cover-title">4YFN26 Healthtech<br/>data capsule</h1>',
        f'<h1 class="pdf-cover-title">4YFN26 {label}<br/>data capsule</h1>',
    )
    html = html.replace(
        "Global health VC trends, 4YFN Health 2026 cohort highlights, and the most active investors backing them.",
        f"Global {industry_word} VC trends, 4YFN26 {label} cohort highlights, and the most active investors backing them.",
    )

    # 3. Chart 1
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

    # 4. Chart 2 (AI share)
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

    # 5. Chart 3 (bubbles)
    html = html.replace(
        '<h1 class="title">4YFN26 Health at a glance</h1>',
        f'<h1 class="title">4YFN26 {label} at a glance</h1>',
    )
    html = html.replace(
        "Exhibitor and funding snapshot of the 4YFN26 Healthtech cohort",
        f"Exhibitor and funding snapshot of the 4YFN26 {label} cohort",
    )
    # Bubble 1 label: for AI capsule use "Core AI"; for Spin-off use "Spin-off"
    b1_label = "Core AI" if config["data_key"] == "ai" else label_lc
    html = re.sub(
        r'<div class="bubble b1">\s*<div class="big-num">156</div>\s*<div class="label">Health<br/>exhibitors</div>',
        f'<div class="bubble b1">\n          <div class="big-num">{b1}</div>\n          <div class="label">{b1_label}<br/>exhibitors</div>',
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

    # If we have an Akamai-exclusion footnote, insert it after the bubble-stage
    # container inside the same card.
    if bubbles_footnote:
        html = html.replace(
            '<div class="bubble-inner">',
            '<div class="bubble-inner">',  # anchor no-op
        )
        # Anchor on the closing </div> of the .bubble-stage. There is only one
        # bubble-stage in the file, so a plain replace on the exact stage-close
        # sequence is unique.
        html = html.replace(
            '</div>\n    </div>\n\n    <div class="footer">',
            f'</div>\n    </div>\n\n    <div class="lb-note">{bubbles_footnote}</div>\n\n    <div class="footer">',
            1,
        )

    # 6. Chart 4 (leaderboard) — use ex-Health data + add footnote
    html = html.replace(
        '<h1 class="title">EIT Health tops the leaderboard, involved in 43 of 206 rounds raised by 4YFN 2026 Health startups</h1>',
        f'<h1 class="title">{chart4_headline}</h1>',
    )
    html = html.replace(
        "Most active investors in 4YFN 2026 Health startups, ranked by number of rounds",
        chart4_subtitle,
    )
    # Add the footnote right after the leaderboard div
    html = html.replace(
        '<div class="lb-list" id="leaderboard"></div>',
        f'<div class="lb-list" id="leaderboard"></div>\n\n    <div class="lb-note">{chart4_footnote}</div>',
    )
    # Substitute the investors const with ex-Health leaderboard
    investors_new = build_leaderboard_data(lb_ex_health)
    html = re.sub(
        r"const investors = \[\n(?:      \{[^}]+\},\n)+\s*\];",
        f"const investors = [\n{investors_new}\n    ];",
        html,
    )

    # 7. JS data arrays
    html = html.replace(
        f"const HEALTH_VC = [11569686153, 13005228269, 12251705491, 14460912830, 20562477994, 30374775283, 28917339747, 39386435786, 55711238555, 57646262236, 83231803629, 133100822224, 91858322902, 64341077110, 70034613609, 70775350767, 31704692820];",
        f"const HEALTH_VC = {js_array(annual)};",
    )
    html = html.replace(
        f"const AI_HEALTH = [246913998, 353516076, 367703045, 715220111, 1159144836, 1910621066, 3316890963, 4654670950, 6103204089, 6566119133, 9543183370, 19132278273, 11712266582, 7978929991, 11077337928, 15444457389, 9981116501];",
        f"const AI_HEALTH = {js_array(annual_ai)};",
    )

    # 8. ANNUAL_FACTOR
    html = re.sub(
        r"// 2026 annualisation factor \(today is [^)]+\)\s*\n\s*const ANNUAL_FACTOR = 365 / \d+;",
        f"// 2026 annualisation factor (today is day {day_of_year} of the year)\n  const ANNUAL_FACTOR = 365 / {day_of_year};",
        html,
    )

    # 9. AI_SHARE array override (from API-computed values)
    share_arr = "[" + ",".join(f"{r['share']:.6f}" for r in cap["ai_share"]) + "]"
    html = html.replace(
        "const AI_SHARE = HEALTH_VC.map((h, i) => AI_HEALTH[i] / h);",
        f"const AI_SHARE = {share_arr};",
    )

    # 10. Add breakouts/lb-note CSS
    html = inject_css(html, BREAKOUTS_CSS)

    # 11. Inject the tail card (spotlight for Spin-off, breakouts list for AI)
    if config["data_key"] == "spinout":
        html = inject_card(html, spinoff_spotlight_html())
    elif config["data_key"] == "ai":
        html = inject_card(html, ai_breakouts_html())

    return html

# ---- Floodwaive spotlight (Spin-off capsule) ----
FLOODWAIVE_LOGO_B64_PATH = pathlib.Path("/tmp/floodwaive-128.b64")

def spinoff_spotlight_html():
    fw = data["floodwaive"]
    logo_data = pathlib.Path(FLOODWAIVE_LOGO_B64_PATH).read_text().strip()
    logo_data_uri = f"data:image/png;base64,{logo_data}"

    signal_str = f'{fw["signal"]:.0f}' if fw.get("signal") is not None else "—"
    growth_pct = fw.get("employee_count_1y_growth")
    growth_str = f"+{growth_pct:.0f}% YoY headcount growth" if growth_pct else ""
    hq = ", ".join(x for x in [fw.get("hq_city"), fw.get("hq_country")] if x)

    return spotlight_card_html(
        title="Spotlight: Floodwaive",
        subtitle="Winner of the 4YFN26 Spin-off pitch battle — AI-powered flood forecasting from RWTH Aachen",
        name=fw["name"],
        tagline=fw["tagline"],
        meta_line=f'{hq} · Founded {fw["launch_year"]} · <a href="https://{fw["website_domain"]}">{fw["website_domain"]}</a>',
        logo_data_uri=logo_data_uri,
        stats=[
            {
                "num": fw["employee_count"],
                "label": "Team size",
                "sub": growth_str or "Rapid early hiring",
            },
            {
                "num": fw["launch_year"],
                "num_class": "coral",
                "label": "Founded",
                "sub": "Spin-off from RWTH Aachen University",
            },
            {
                "num": signal_str,
                "num_class": "blue",
                "label": "Dealroom Signal",
                "sub": "Momentum score (out of 100)",
            },
            {
                "num": "Winner",
                "num_class": "with-icon violet",
                "prefix_svg": TROPHY_SVG,
                "label": "4YFN Spin-off Pitch Battle · 2026",
                "sub": "Recognised at 4YFN26 Barcelona",
                "card_class": "award",
            },
        ],
        about=(
            "Aachen-based deeptech spinning out of RWTH Aachen University to build "
            "<strong>DeepWaive</strong> — a physics-informed AI foundation model that "
            "generates high-resolution flood forecasts up to a million times faster than "
            "traditional hydrodynamic simulations, enabling proactive climate resilience for "
            "cities, insurers and critical-infrastructure operators."
        ),
        footer_svgs=FOOTER_LOGOS_HTML,
    )

def ai_breakouts_html():
    # Client asked to drop Qilimanjaro from the breakouts — while their quantum
    # stack accelerates AI use cases, it isn't itself an AI company.
    excluded_names = {"Qilimanjaro Quantum Tech"}
    companies = [c for c in data["ai_breakouts"]["results"] if c["name"] not in excluded_names]
    return breakouts_card_html(
        companies=companies,
        footer_svgs=FOOTER_LOGOS_HTML,
    )

configs = {
    "spinouts-capsule": {
        "data_key": "spinout",
        "label": "Spin-offs",
        "label_lc": "Spin-off",
        "industry_word": "spin-off",
        "sector_adj": "Spin-off",
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
