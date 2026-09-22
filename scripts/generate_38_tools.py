#!/usr/bin/env python3
"""Step 5 of CalcWorker SEO overhaul: generate 38 new calculator pages via template.

Reads shared chrome (sidebar, topbar, footer, styles, adsense) VERBATIM from
tools/mortgage-calculator.html, combines with per-tool data dicts below, and
emits one self-contained page per tool. No git commit/push — files land in tools/.
"""
import json, re, os, sys, subprocess, tempfile, html as htmlmod
from html.parser import HTMLParser

BASE = os.path.expanduser('~/workspace/calcworker-seo')
TOOLS_DIR = os.path.join(BASE, 'tools')
TPL = open(os.path.join(TOOLS_DIR, 'mortgage-calculator.html'), encoding='utf-8').read()

def chunk(start, end, strip_active=False):
    i = TPL.find(start); j = TPL.find(end)
    assert i != -1 and j != -1, (start, end)
    c = TPL[i:j+len(end)]
    if strip_active:
        c = c.replace(' class="nav-link active"', ' class="nav-link"')
    return c

SIDEBAR   = chunk('<aside class="sidebar"', '</aside>', strip_active=True)
TOPBAR    = chunk('<div class="sidebar-backdrop" id="sidebarBackdrop"></div>', '</header>')
TOPBAR_TPL_TITLE = '<span class="topbar-title">🏠 Mortgage Calculator</span>'
FOOTER    = chunk('<footer style=', '</footer>')
HEAD_STYLE = chunk('<style>', '</style>')
THEME_LOCK = chunk('<!-- Zero-Flicker Instant Hardware Executable Theme Lock -->', '</script>')
ADSENSE   = chunk('<!-- Google AdSense — Auto Ads -->', '></script>')
GTAG      = chunk('<!-- Google tag (gtag.js) - Google Analytics -->', '</script>')

# sanity: adsense block must be byte-verbatim copy, untouched
assert 'ca-pub-3405098265613384' in ADSENSE and 'adsbygoogle.js' in ADSENSE

JS_PRELUDE = r"""
function fmt0(n){n=isFinite(n)?n:0;return n.toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0});}
function fmtM(n){n=isFinite(n)?n:0;return (n<0?'-$':'$')+fmt0(Math.abs(n));}
function fmtP(n,d){n=isFinite(n)?n:0;return n.toFixed(d===undefined?1:d)+'%';}
function fmtN(n,d){n=isFinite(n)?n:0;return n.toLocaleString('en-US',{minimumFractionDigits:(d===undefined?2:d),maximumFractionDigits:(d===undefined?2:d)});}
function setT(id,txt){var e=document.getElementById(id);if(e)e.textContent=txt;}
function num(id){return parseFloat(document.getElementById(id).value)||0;}
"""

SHARE_SNIPPET = """
// Copy-calculation-summary button
(function(){var b=document.getElementById('shareBtn');if(!b)return;
b.addEventListener('click',function(){
  var t='📊 CalcWorker — {NAME} Results:\\n'+document.getElementById('shareText').textContent+'\\n🔗 Free {NAME}: '+window.location.href;
  var done=function(){var bt=document.getElementById('shareBtnText');if(bt)bt.textContent='✓ Copied to Clipboard!';setTimeout(function(){if(bt)bt.textContent='📋 Copy Calculation Summary';},2500);};
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done).catch(done);}else{done();}
});})();
"""

def head(t):
    ld = json.dumps([
        {"@context": "https://schema.org", "@type": "SoftwareApplication",
         "name": t['name'], "url": f"https://calcworker.com/tools/{t['slug']}.html",
         "applicationCategory": "FinanceApplication", "operatingSystem": "All",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
        {"@context": "https://schema.org", "@type": "FAQPage",
         "mainEntity": [
             {"@type": "Question", "name": q,
              "acceptedAnswer": {"@type": "Answer", "text": a}}
             for q, a in t['faqs']]}
    ], ensure_ascii=False, indent=2)
    return f"""<!DOCTYPE html>

<html data-theme="dark" lang="en">
<head>
<link href="/manifest.json" rel="manifest"/>
<meta content="#1d4ed8" name="theme-color"/>
<meta content="yes" name="apple-mobile-web-app-capable"/>
<meta content="black-translucent" name="apple-mobile-web-app-status-bar-style"/>
<meta content="CalcWorker" name="apple-mobile-web-app-title"/>
{THEME_LOCK}
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{htmlmod.escape(t['title'])}</title>
<meta content="{htmlmod.escape(t['desc'], quote=True)}" name="description"/>
<meta content="{htmlmod.escape(t['keywords'], quote=True)}" name="keywords"/>
<meta content="index, follow" name="robots"/>
<link href="https://calcworker.com/tools/{t['slug']}.html" rel="canonical"/>
<meta content="{htmlmod.escape(t['title'])}" property="og:title"/>
<meta content="{htmlmod.escape(t['desc'], quote=True)}" property="og:description"/>
<meta content="https://calcworker.com/tools/{t['slug']}.html" property="og:url"/>
<meta content="website" property="og:type"/>
<meta content="summary_large_image" name="twitter:card"/>
<!-- Structured Data: FAQPage & WebApplication -->
<script type="application/ld+json">
{ld}
</script>
<link href="/assets/favicon.png" rel="icon" type="image/png"/>
{ADSENSE}
{GTAG}
<link href="/css/calcworker.css?v=2026-v26" rel="stylesheet"/>
<meta content="#090d16" name="theme-color"/>
<script defer="" src="../js/analytics.js"></script>
{HEAD_STYLE}
<script defer="" src="/js/sidebar.js"></script>
<link href="/assets/favicon.png" rel="icon" type="image/png"/>
<link href="/css/ai-widget.css?v=2026-v26" rel="stylesheet"/>
</head>
"""

def input_html(inp):
    if inp.get('type') == 'select':
        opts = ''.join(f'<option value="{o[0]}">{o[1]}</option>' for o in inp['options'])
        return (f'<div class="form-group"><label class="form-label">{inp["label"]}</label>'
                f'<select class="form-input" id="{inp["id"]}">{opts}</select></div>')
    pre = f'<span class="input-prefix">{inp["prefix"]}</span>' if inp.get('prefix') else ''
    suf = (f'<span style="position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--text-muted);">{inp["suffix"]}</span>'
           if inp.get('suffix') else '')
    cls = 'form-input input-with-prefix' if inp.get('prefix') else 'form-input'
    wrap = '<div class="input-prefix-wrap">' if (pre or suf) else '<div>'
    return (f'<div class="form-group"><label class="form-label">{inp["label"]}</label>'
            f'{wrap}{pre}<input class="{cls}" id="{inp["id"]}" type="number" value="{inp["value"]}"'
            f' min="{inp.get("min",0)}" max="{inp.get("max","")}" step="{inp.get("step","any")}"/>{suf}</div></div>')

def related_card(href, emoji, tag, title, blurb):
    return f'''<a class="related-tool-link" href="{href}" style="display: flex; flex-direction: column; justify-content: space-between; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; text-decoration: none; transition: all 0.2s ease;">
<div>
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
<span style="font-size: 1.35rem;">{emoji}</span>
<span style="font-size: 0.65rem; font-weight: 800; background: rgba(37,99,235,0.12); color: #60a5fa; border: 1px solid rgba(37,99,235,0.25); padding: 2px 7px; border-radius: 9999px;">{tag}</span>
</div>
<div style="font-size: 0.95rem; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">{title}</div>
<p style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.45; margin: 0 0 12px 0;">{blurb}</p>
</div>
<div style="display: flex; align-items: center; font-size: 0.8rem; font-weight: 600; color: var(--brand-primary);">
<span>Open Calculator</span> <span style="margin-left: 4px;">→</span>
</div>
</a>'''

def guide_html(t):
    faqs = ''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in t['faqs'])
    return f"""<section class="tool-guide-section" style="margin-top:48px;padding:28px;background:var(--bg-surface,#ffffff);border:1px solid var(--border-subtle,#e5e7eb);border-radius:12px;line-height:1.7;color:var(--text-main,#1f2937);">
<h2 style="color:var(--brand-primary,#2563eb);font-size:1.5rem;margin-bottom:12px;">{t['guide_h2']}</h2>
{full_guide(t)}
<h3 style="margin-top:28px;color:var(--brand-primary,#2563eb);font-size:1.3rem;">Frequently Asked Questions (FAQs)</h3>
<div class="faq-item" style="margin-top:12px;">
{faqs}
</div>
<p style="margin-top:20px;font-size:0.78rem;color:var(--text-muted);">Last updated: September 2026</p>
</section>"""

def related_html(t):
    cards = related_card(t['hub'], '📂', 'HUB', t['hub_title'], t['hub_blurb'])
    for slug, name, emoji, blurb in t['related']:
        cards += '\n' + related_card(f'/tools/{slug}.html', emoji, t['cat_label'], name, blurb)
    return f"""<section class="related-tools-section" style="margin-top: 40px; margin-bottom: 30px;">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-main); display: flex; align-items: center; gap: 8px; margin: 0;">
<span>🔗</span> Related Precision Calculators
          </h3>
<span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Recommended For You</span>
</div>
<div class="related-tools-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px;">
{cards}
</div>
</section>"""

def page(t):
    topbar = TOPBAR.replace(TOPBAR_TPL_TITLE,
        f'<span class="topbar-title">{t["icon"]} {htmlmod.escape(t["name"])}</span>')
    inputs = '\n'.join(input_html(i) for i in t['inputs'])
    extra_inputs = t.get('extra_inputs_html', '')
    guide = guide_html(t)
    rel = related_html(t)
    script = ("<script src=\"/js/calcworker-common.js?v=2026.3\"></script>\n<script>\n"
              + JS_PRELUDE + "\n" + t['js_core'] + "\n" + t['js_glue'] + "\n"
              + SHARE_SNIPPET.replace('{NAME}', t['name']) + "\n</script>\n"
              + '<script defer="" src="/js/ai-widget.js?v=2026.3"></script>')
    return (head(t) + "<body>\n<div class=\"app-shell\">\n" + SIDEBAR + "\n" + topbar + "\n"
            + '<main class="page-container">\n'
            + '<div class="tool-header-block">\n'
            + f'<h1 class="tool-header-title"><span>{t["icon"]}</span> {htmlmod.escape(t["h1"])}</h1>\n'
            + f'<p class="tool-header-desc">{t["intro"]}</p>\n</div>\n'
            + '<div class="tool-page-layout">\n'
            + '<div class="tool-form-panel">\n' + inputs + extra_inputs
            + f'\n<button class="calc-btn" id="calcBtn" onclick="recalc()" style="margin-top:8px;">{t["icon"]} Calculate</button>\n</div>\n'
            + '<div class="tool-results-panel">\n' + t['results_html'] + '\n</div>\n</div>\n'
            + guide + "\n" + rel + "\n" + FOOTER + "\n</main>\n</div>\n</div>\n"
            + script + "\n</body>\n</html>\n")

# ---------------- validation machinery ----------------
class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for k, v in attrs:
                if k == 'href':
                    self.hrefs.append(v)

def extract_inline_script(page_html):
    m = re.findall(r'<script>\n(.*?)\n</script>', page_html, re.S)
    return m[-1] if m else ''

def node_check(js_src):
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(js_src); path = f.name
    r = subprocess.run(['node', '--check', path], capture_output=True, text=True)
    os.unlink(path)
    return r.returncode == 0, r.stderr[:500]

def run_core_tests(t):
    """Execute js_core + harness in node, compare against expected values."""
    harness = t['js_core'] + "\nvar __tests=" + json.dumps(t['tests']) + """;
var __out=[];
for(var ti=0;ti<__tests.length;ti++){
  var tc=__tests[ti];
  try{var r=core(tc.inputs);__out.push({ok:true,res:r});}
  catch(e){__out.push({ok:false,err:String(e)});}
}
console.log(JSON.stringify(__out));"""
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(harness); path = f.name
    r = subprocess.run(['node', path], capture_output=True, text=True, timeout=20)
    os.unlink(path)
    if r.returncode != 0:
        return False, 'node exec failed: ' + r.stderr[:400]
    try:
        outs = json.loads(r.stdout.strip().split('\n')[-1])
    except Exception as e:
        return False, 'bad node output: ' + r.stdout[:300]
    msgs = []
    for tc, o in zip(t['tests'], outs):
        if not o.get('ok'):
            return False, f"case {tc['inputs']} threw {o.get('err')}"
        for k, exp in tc['expect'].items():
            got = o['res'].get(k)
            if got is None or not isinstance(got, (int, float)) or got != got:
                return False, f"case {tc['inputs']}: {k} not finite ({got})"
            if abs(got - exp) > max(0.02 * abs(exp), 1.0):
                return False, f"case {tc['inputs']}: {k}={got} != expected {exp}"
            msgs.append(f"{k}={got:g}")
    return True, '; '.join(msgs)

def guide_wordcount(t):
    txt = re.sub(r'<[^>]+>', ' ', full_guide(t))
    txt = htmlmod.unescape(txt)
    return len([w for w in txt.split() if w.strip()])

# ---- Guide expansions (inlined into this single script; combined guides validated 300-500 words) ----
GUIDE_EXTRA = {
'fire-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Beyond the 4% Rule</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The 4% rule assumes a 30-year retirement, ~50/50 stock-bond mix, and inflation-adjusted withdrawals. Early retirees face 50–60 year horizons, where <strong>sequence-of-returns risk</strong> — a bear market in your first five years — does the most damage. Mitigations: a larger bond tent near retirement, flexible withdrawals (cut spending 10–20% in down years), and part-time income. Variants worth knowing: <strong>Coast FIRE</strong> (save enough early that compounding alone hits your number, then work for expenses), <strong>Barista FIRE</strong> (semi-retire with benefits-providing part-time work), and <strong>Fat FIRE</strong> ($2.5M+ for higher spending). Budget healthcare explicitly — pre-Medicare insurance can run $500–$1,500/month per person. Fees and taxes are silent killers: a 1% advisory fee over 40 years can consume nearly a third of potential wealth, so prefer low-cost index funds in tax-advantaged accounts first.</p>',
'credit-score-simulator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">How Lenders Actually Use Your Score</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Mortgage pricing moves in <strong>score tiers</strong>: borrowers above ~760 get the best rates, with meaningful price hits at 700, 680, and 620 (the conventional minimum). On a $400,000 loan, the rate gap between a 620 and 760 score can exceed $300/month — over $100,000 across 30 years. Two timing facts most people miss: utilization is reported on your <strong>statement closing date</strong>, not the due date, so paying down before the statement posts is what lowers reported utilization; and most negative marks (late payments, collections) hurt less with age and fall off after seven years. Note that <strong>FICO and VantageScore</strong> differ — lenders overwhelmingly use FICO (often older versions for mortgages), so a free VantageScore from your bank is directional, not exact. Never close your oldest card before a mortgage application: it shortens average account age and can spike utilization.</p>',
'w-4-withholding-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">When and How to Update Your W-4</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Revisit your W-4 after every major life event: marriage or divorce, a new baby (worth a $2,000 Child Tax Credit), a second job, or new investment income. The form\'s <strong>Step 4</strong> is the precision toolkit: 4(a) adds other income (freelance, dividends) so withholding covers it; 4(b) claims deductions beyond the standard deduction to reduce withholding; 4(c) adds a flat extra amount per paycheck — the simplest way to fine-tune. Two earners should both check the box in Step 2 or use the multiple-jobs worksheet; otherwise the standard deduction and brackets get double-counted and you under-withhold. Aim to owe or be refunded <strong>under $1,000</strong>: within that band you avoid estimated-tax penalties via safe harbor and keep your money working all year instead of lending it to the Treasury interest-free.</p>',
'llc-tax-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">LLC Tax Planning Levers</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Three moves matter most. First, the <strong>20% qualified business income (QBI) deduction</strong> can exempt a fifth of your profit from income tax (not SE tax) — but it phases out for high-earning service businesses (SSTBs) above ~$197,300 single / $394,600 married for 2026. Second, the <strong>S-corp election</strong>: once profit reliably exceeds ~$40,000–$60,000, paying yourself a reasonable salary and taking the rest as distributions can save thousands in SE tax — model it against ~$1,500–$3,000/year in payroll admin costs. Third, retirement contributions: a <strong>Solo 401(k)</strong> lets you shelter up to ~$70,000 (2026) as both employee and employer, far more than a SEP IRA once income rises. Set aside 25–30% of profit in a separate account and pay <strong>quarterly estimates</strong> (April, June, September, January) to avoid underpayment penalties.</p>',
's-corp-tax-savings-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">The Reasonable-Salary Tripwire</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The IRS requires S-corp owners to pay themselves a <strong>"reasonable salary"</strong> before taking distributions — this is the #1 audit trigger for small S-corps. Research salary benchmarks for your role and region (BLS data, job postings) and document your reasoning; $30,000 salary on $300,000 profit invites trouble, while 50–60% of profit as salary is a common defensible zone. Weigh the real costs: payroll service (~$50–$100/month), unemployment insurance, workers\' comp, and a business tax return (1120-S, ~$800–$2,000 from a CPA) — total overhead often <strong>$1,500–$3,000/year</strong>. The election rarely pays below ~$40,000 profit. Also note the QBI interplay: S-corp distributions don\'t count as qualified business income, so the 20% QBI deduction applies to a smaller base — the net savings calculation must include that offset, which this calculator does.</p>',
'self-employment-tax-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">What Counts — and What Reduces It</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">SE tax applies to <strong>net earnings</strong> — profit after business expenses — and the 92.35% factor exists because employees split payroll tax with employers while you pay both halves. Two adjustments soften the blow: you may deduct <strong>half your SE tax</strong> from income (an above-the-line deduction), and only the Social Security portion (12.4%) stops at the wage base — Medicare\'s 2.9% has no cap, plus an extra <strong>0.9% Additional Medicare Tax</strong> above $200,000 single / $250,000 married. Retirement contributions (Solo 401(k), SEP IRA) and the HSA reduce <em>income</em> tax but generally not SE tax — only an S-corp salary/distribution split reduces SE tax itself. Because nothing is withheld, pay <strong>quarterly estimated taxes</strong> or face penalties; a common rule is to park 25–30% of each client payment in a separate tax account the day it arrives.</p>',
'quarterly-tax-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Safe Harbors That Eliminate Penalties</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">You can avoid underpayment penalties entirely with a <strong>safe harbor</strong>: pay 100% of last year\'s total tax (110% if AGI exceeded $150,000), or 90% of this year\'s tax, through withholding + timely estimates. For lumpy income (big Q4, seasonal business), the <strong>annualized income installment method</strong> (Form 2210 Schedule AI) lets you match payments to when income actually arrived instead of four equal chunks. Deadlines: April 15, June 15, September 15, January 15 — miss one and the penalty clock runs from that date even if you catch up later. Don\'t forget <strong>state estimated taxes</strong>, which have their own thresholds and are often where freelancers get blindsided. The federal penalty rate floats with interest rates (recently ~8% annually) — cheaper than credit cards, but an avoidable drag.</p>',
'bonus-tax-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Why Bonuses Feel Over-Taxed</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Employers withhold on bonuses two ways: the <strong>22% flat method</strong> (used for bonuses up to $1M; 37% above) or the <strong>aggregate method</strong> (bonus folded into regular pay, withheld at your marginal rate). The flat 22% is just withholding, not your actual tax — at filing, the bonus is taxed as ordinary income at your real marginal rate, which is why high earners often <em>owe</em> more on bonuses and moderate earners get a <em>refund</em>. States add their own supplemental rates (e.g., California ~10.23%). Smart moves: bump your <strong>401(k) contribution rate</strong> before a known bonus to shelter it, or time deductions; and if bonuses are large and regular, adjust your W-4 Step 4(a) rather than oscillating between big refunds and surprise balances due each April.</p>',
'rsu-tax-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">The Concentration Trap</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">RSUs align you with your employer — until your job, salary, and portfolio all depend on one stock. Financial planners typically advise selling vested shares on a schedule and diversifying; holding is an active bet, not a default. Note the tax mechanics: vesting creates <strong>ordinary income</strong> (no 83(b) election available for RSUs, unlike restricted stock), and any later gain is capital — short-term unless you hold a year post-vest. Withholding at vest is usually 22% federal, so high earners owe more at filing. <strong>Double-trigger RSUs</strong> (common pre-IPO) vest only after both time service and a liquidity event, creating a big tax bill in the IPO year with no cash until you can sell — plan liquidity for that April. Moving states between grant and vest can split taxation across states.</p>',
'tax-refund-estimator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">The Interest-Free Loan Problem</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">A $3,600 refund feels like a windfall, but it\'s <strong>your own money returned without interest</strong> — you overpaid $300/month all year. The optimal target is a small refund or balance due under $1,000: close enough to avoid penalties, far enough from giving the Treasury a free loan. To fix persistent large refunds, increase W-4 allowances accuracy: claim the Child Tax Credit properly in Step 3 ($2,000 per qualifying child), account for a non-working spouse, or add deductions in Step 4(b). Conversely, if you <em>owe</em> every year, add extra withholding in Step 4(c) per paycheck. Credits vs. deductions matter enormously here: a $2,000 <em>credit</em> cuts your refund swing by the full $2,000, while a $2,000 <em>deduction</em> only moves it by your marginal rate (~$440 at 22%).</p>',
'house-affordability-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">What the 28/36 Rule Misses</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The classic <strong>28/36 rule</strong> — housing under 28% of gross income, all debts under 36% — is a ceiling, not a target; in high-cost cities buyers routinely stretch to 35–40% housing ratios, which works only with strong job security and no other debt. Budget the invisible costs: maintenance (~1–2% of home value/year), homeowners insurance, HOA dues, and <strong>PMI</strong> (~0.5–1%/year) if you put down under 20%. A <strong>rate buydown</strong> (paying points) only pays off if you stay past the breakeven — roughly divide points cost by monthly savings. And remember: pre-approval amounts reflect the <em>lender\'s</em> risk tolerance, not your budget — approval at $800,000 doesn\'t mean $800,000 is wise. Run this calculator with your <em>actual</em> comfortable payment, then shop below the max.</p>',
'cash-flow-rental-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Rules of Thumb vs. Real Underwriting</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Quick screens: the <strong>1% rule</strong> (monthly rent ≥ 1% of purchase price) and the <strong>50% rule</strong> (operating expenses ≈ 50% of rent, before debt service) — useful for rejecting bad deals in seconds, not for buying. Real underwriting reserves by component: roof ($5,000–$15,000 every 20–30 years), HVAC ($5,000–$10,000 every 15 years), water heaters, appliances — amortize each into monthly capex. Vacancy assumptions should reflect asset class: 3–5% for Class A, 8–10%+ for Class C. The silent killer is <strong>rent growth vs. expense growth</strong>: taxes and insurance often rise faster than rents, compressing cash flow over time. Finally, cash flow is only one return leg — add principal paydown, appreciation, and tax benefits (depreciation) for total return, but never let projected appreciation justify negative cash flow.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Screening shortcut:</strong> if a deal fails the 1% rent-to-price test <em>and</em> the 50% expense rule, walk away in under a minute. If it passes both, graduate to full underwriting with actual tax records, insurance quotes, and contractor bids — rules of thumb open the funnel, verified numbers close the deal.</p>',
'airbnb-profit-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Occupancy Is a Strategy, Not a Stat</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Top hosts manage occupancy deliberately: <strong>dynamic pricing tools</strong> (PriceLabs, Beyond) adjust nightly rates to demand, often lifting revenue 15–30% over static pricing. Counterintuitively, slightly <em>lower</em> rates that push occupancy from 55% to 75% usually beat premium pricing — empty nights earn zero. Watch your market\'s <strong>regulations</strong>: many cities require STR permits, cap annual rental nights, or ban non-owner-occupied listings outright; fines can erase years of profit. Cleaning fees are strategic: high fees boost per-booking profit but hurt search conversion and review scores — most optimized listings keep them at or below local median. Factor <strong>seasonality</strong> honestly: a 70% annual occupancy often means 95% in summer and 45% in winter, with cash flow to match.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Design for the thumbnail:</strong> listings live or die on the first five photos. Professional photography ($150–$300) routinely pays for itself within weeks through higher click-through and nightly rates. Add the top 3 amenities guests filter for in your market (hot tub, fast wifi, EV charger) — each one expands your searchable demand pool and justifies premium pricing.</p>',
'cap-rate-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Reading Cap Rates Like an Investor</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Cap rate = return in a world without leverage — which makes it the purest <strong>comparison tool</strong> across properties and markets. Typical bands: 4–6% for core coastal multifamily, 6–8% for secondary markets, 8–12%+ for value-add or tertiary assets — higher always means higher risk, never free return. Critical: NOI must <strong>exclude debt service, income taxes, and capital expenditures</strong>; including them understates or overstates yield. Compare a property\'s cap rate to the <strong>going-in vs. stabilized</strong> distinction — value-add deals quote today\'s (low) cap and tomorrow\'s (higher) pro-forma cap; underwrite the path between them. Cap rates also set value: at a 6% market cap, every $10,000 of additional NOI is worth ~$167,000 — which is exactly why forced appreciation through NOI growth is the professional\'s game.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Cap rate compression</strong> is how markets make investors rich without lifting a finger: if you buy at an 8% cap and the market compresses to 6%, your property\'s value rises ~33% on identical income. That\'s why buying in path-of-progress neighborhoods at high going-in caps — then riding compression — is the classic wealth-building trade.</p>',
'brrrr-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Where BRRRR Deals Die</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Three failure points dominate. First, the <strong>appraisal</strong>: your refinance is capped at 70–80% of <em>appraised</em> value, not your renovation budget — if the appraisal comes in light, your capital stays trapped. Conservative investors underwrite the refi at 75% of a pessimistic ARV. Second, <strong>seasoning</strong>: most lenders require 6–12 months of ownership before refinancing on the new value; hard-money loans bridge the gap but cost 9–12% plus 2–4 points. Third, <strong>rehab overruns</strong>: budget a 15–20% contingency and verify contractor bids against the ARV math — every $10,000 over budget at 75% LTV traps $2,500 extra (plus the unrecovered 25%). The BRRRR promise of "infinite returns" is real when all capital is recovered, but the first deal\'s trapped equity is tuition — keep reserves for it.</p>',
'dscr-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">How Lenders Use DSCR</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Most investment-property lenders require <strong>DSCR ≥ 1.20–1.25</strong> — the property must generate 20–25% more income than its debt costs. <strong>DSCR loans</strong> (a popular investor product) qualify you on the property\'s ratio alone: no personal income verification, no tax returns — which is why they price ~1–2% above conventional rates. If your DSCR falls short, the levers are: larger down payment (lowers debt service directly), buying down the rate, raising rents to market, or cutting operating expenses. Lenders also compute a <strong>global DSCR</strong> across your entire portfolio for experienced investors — one weak property can constrain the next purchase. Note that lenders use <em>their</em> underwriting (often 25% expense factor, market rents, actual taxes/insurance), so your pro-forma DSCR and the lender\'s can differ meaningfully.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Rate buydowns directly raise DSCR:</strong> every 0.5% shaved off your mortgage rate cuts debt service ~5–6%, which flows straight into the ratio. On a borderline 1.18x deal, a 2-1 buydown or an extra 5% down payment is often the difference between approval and rejection — model both scenarios before you offer.</p>',
'cash-on-cash-return-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Leverage: Amplifier, Not Magic</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Cash-on-cash shines light on <strong>leverage</strong>: a $300,000 property with $60,000 down earning $6,000/year cash flow shows 10% cash-on-cash but only ~4–5% cap rate — the gap is leverage working for you. But leverage is symmetric: if rents dip or rates reset higher, cash-on-cash compresses faster than cap rate and can go negative while the property still "cash flows" on paper. Know what it hides: cash-on-cash <strong>ignores appreciation, principal paydown, and tax benefits</strong> — total return is always higher. It also ignores <em>time</em>: unlike IRR, it doesn\'t penalize capital trapped for years. Use cash-on-cash for year-one income screening and lender conversations, cap rate for comparing properties, and IRR for hold-period decisions.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Target benchmarks:</strong> most buy-and-hold investors want 8–12% cash-on-cash in year one — enough to beat passive alternatives with a risk premium. Below 6%, your capital is likely better deployed elsewhere unless appreciation or tax benefits are exceptional. Always compare against what the same down payment earns in an index fund (~10% long-run) to keep opportunity cost honest.</p>',
'real-estate-commission-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Commissions After the 2024 NAR Settlement</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The 2024 NAR settlement changed the game: sellers no longer pre-set buyer-agent compensation in the MLS, and buyers now sign <strong>written agreements</strong> with their agents before touring. Practically, commissions remain negotiable — total costs still often land near 5–6%, but every component is now explicitly negotiated rather than defaulted. Sellers: interview 3+ agents, negotiate the listing side (many accept 2–2.5%), and decide strategically what buyer-side compensation to offer — offering zero can shrink your buyer pool. Alternatives have matured: <strong>flat-fee MLS listings</strong> (~$500–$3,000), 1% listing brokerages, and FSBO (saving the full listing side but costing time and pricing expertise). On a $500,000 sale, each 1% negotiated saves $5,000 — the highest-paid hour in real estate is the commission negotiation.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Negotiation script that works:</strong> "I\'m interviewing three agents. What\'s your listing-side rate, and what buyer-side compensation do you recommend for maximum exposure?" Agents competing openly routinely drop from 3% to 2–2.5% on the listing side. Get every quote in writing — verbal commission promises evaporate at closing.</p>',
'youtube-shorts-earnings-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">The Real Shorts Strategy</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Treat Shorts as <strong>acquisition, not income</strong>. The winning playbook: use Shorts to build subscribers, then convert them to long-form viewers where RPMs are 30–50× higher — pin comments linking to full videos, and post long-form on a consistent schedule so new subscribers have somewhere valuable to land. Shorts <em>can</em> earn directly through <strong>brand deals</strong>: sponsors pay for Shorts integrations at rates far above ad revenue (often $500–$5,000+ per Short depending on audience), because they buy your distribution, not YouTube\'s RPM. Repurpose ruthlessly — one long-form video yields 3–5 Shorts for TikTok, Reels, and YouTube simultaneously. And watch the monetization thresholds: the lower YPP tier (500 subs, 3M Shorts views/90 days) unlocks Shopping and fan funding well before full ad sharing, letting small Shorts-native channels monetize early.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Viral math sanity check:</strong> a 10-million-view Short at $0.08 RPM earns about $800 — nice, but a single brand deal to that same audience can pay 10× more. Creators who treat every viral Short as a media kit entry ("10M views last month — sponsors, my DMs are open") monetize virality instead of just admiring it.</p>',
'tiktok-rpm-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Why RPM Varies So Much</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Three factors dominate your RPM. <strong>Geography</strong>: US, UK, and German audiences command the highest advertiser demand — creators with identical views report 2–3× RPM differences based on audience country mix. <strong>Content niche</strong>: finance, business, and tech content attracts premium advertisers ($0.80–$1.50+ RPM), while dance trends and memes sit at the floor. <strong>Qualified views</strong>: only views meeting TikTok\'s watch-time and authenticity thresholds count — rewatch loops, bot traffic, and paid promotion views are excluded, which is why RPM computed on <em>total</em> views understates your true qualified RPM. To join the Creativity Program you generally need 10,000 followers and 100,000 views in 30 days with 1-minute+ videos. Track RPM <strong>monthly</strong>, not per video — per-video RPM is noise; the monthly trend tells you whether your content mix and audience are moving upmarket.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Raising RPM deliberately:</strong> shift 20–30% of output toward higher-RPM niches (finance, tech, business) while keeping your core audience, and geo-target content toward US/UK viewers (trending sounds and hashtags from those regions help). Even a $0.20 RPM lift on 5M monthly views is worth $1,000/month — small content pivots compound.</p>',
'tiktok-shop-profit-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Seller vs. Affiliate: Two Different Games</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Sellers</strong> win by engineering the offer: set affiliate commissions at 15–20%+ to recruit top creators (the best affiliates promote dozens of products and pick the highest-paying), price with fees baked in, and budget for <strong>return rates</strong> — apparel and beauty can see 10–20% returns, each one erasing the margin on several good sales. <strong>Affiliates</strong> win on volume and selection: promote proven products with existing review velocity, go live (LIVE shopping converts dramatically better than shoppable videos), and stack multiple products per account. Both sides should watch the <strong>fee creep</strong>: platform fees, payment processing, and affiliate payouts compound — re-run this calculator whenever TikTok adjusts its fee schedule. The creators earning life-changing money on Shop aren\'t lucky; they treat it as a media-buying business with content as the ad creative.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>The returns blind spot:</strong> a product with 25% margin and a 15% return rate is barely profitable once return shipping, restocking labor, and refunded affiliate commissions are counted. Before scaling any hero product, sell 100 units, measure the <em>true</em> return rate, then re-run this calculator with returns modeled as a cost line — most "winning" products fail this test.</p>',
'instagram-engagement-rate-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">What the Algorithm Actually Rewards</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Not all engagement is equal: <strong>shares and saves</strong> are the strongest ranking signals because they indicate content worth redistributing or revisiting — a post with 500 saves will out-distribute one with 2,000 passive likes. Format matters enormously: <strong>carousels</strong> consistently post the highest feed ER (multiple slides = multiple chances to hook), Reels dominate reach, and single images lag both. Before a brand deal, audit for <strong>ghost followers</strong> — sudden follower spikes with flat engagement, or comment sections full of generic emoji, signal purchased audiences that crater real ER. Never use engagement pods: the inauthentic comment patterns are detectable, violate platform policy, and train the algorithm on the wrong audience. The durable ER strategy is unglamorous: niche down, post consistently, reply to comments in the first hour, and delete bot followers quarterly.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Benchmark before you pitch:</strong> screenshot your ER monthly and keep a rolling 90-day average — brands ask for it, and a documented upward trend justifies rate increases. If your ER sits below your size band\'s benchmark, pause pitching and spend 30 days on engagement repair (reels, carousels, comment replies) before quoting premium prices.</p>',
'ugc-creator-rate-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Building a UGC Business, Not Just Gig Income</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The creators earning $5,000–$10,000+/month from UGC share three habits. First, a <strong>portfolio</strong> of 10–15 spec ads (self-made ads for real brands, labeled as concepts) beats any follower count for landing deals. Second, <strong>usage renewals</strong>: structure every contract with term limits (30–90 days paid usage), then charge 50–100% of the original fee per renewal — brands that keep running your ad keep paying you, creating recurring revenue most creators never claim. Third, <strong>niches and speed</strong>: specialize (skincare, SaaS, DTC food) to command premium rates, and offer 48-hour turnaround as a paid rush tier rather than a free favor. Always use a simple contract covering deliverables, usage term and territory, revision rounds, payment terms (50% upfront is standard), and kill fees. Raise rates every 5–10 deals.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>When to raise rates:</strong> if brands accept your quotes without negotiating, you\'re underpriced — raise 15–20% immediately. If more than half push back hard, hold. The sweet spot is a ~30% negotiation rate: most say yes, some haggle, and your effective rate climbs every quarter without losing deal flow.</p>',
'newsletter-valuation-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">What Buyers Actually Diligence</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Revenue multiples get headlines; <strong>churn and engagement</strong> set the price. Buyers request 12+ months of subscriber churn, open rates (40%+ supports premium multiples; sub-30% triggers discounts), and paid conversion trends — a shrinking list at any multiple is a melting ice cube. <strong>Strategic buyers</strong> (competitors, media companies, sponsors) pay the most because your list plugs into their monetization; financial buyers pay standard 2–4× ARR. Deal structures matter: many acquisitions use <strong>earnouts</strong> (part of the price paid as future revenue materializes) to bridge valuation gaps — negotiate caps and measurement terms carefully. To maximize value before a sale: grow paid conversion (even 8% → 10% transforms ARR), diversify revenue (ads + affiliates + paid), document SOPs so the newsletter runs without you, and keep a clean, exportable list with verified consent.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Quick value wins before selling:</strong> convert 2% more free readers to paid with a limited-time annual-plan discount, add one sponsor slot per issue, and prune cold subscribers (they depress open rates that buyers diligence). These three moves can lift ARR 20–30% in a quarter — at a 3× multiple, that\'s nearly a full year of revenue added to the sale price.</p>',
'youtube-channel-valuation-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">How Channel Sales Actually Work</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Channels trade on brokerages like <strong>Flippa and Empire Flippers</strong>, which verify revenue and handle escrow — never transfer a channel on a handshake. Due diligence is forensic: buyers demand 12+ months of YouTube Analytics exports, AdSense and sponsor revenue proof, traffic-source breakdowns (search/suggested traffic is durable; viral spikes are discounted), copyright strike history, and sponsor contract assignability. What kills value: active strikes, a face-dependent brand with no transition plan, single-source revenue (AdSense-only), and declining watch time. What commands premiums: <strong>diversified revenue</strong> (sponsors + affiliates + digital products), evergreen searchable content, documented SOPs and editors in place, and an email list or community off-platform. Technically, YouTube\'s ToS restricts account transfers, but brokered asset sales with secure credential handover are the established market practice — use escrow, staged payments, and a non-compete.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Pre-sale checklist (90 days out):</strong> resolve any copyright claims, diversify revenue so no single source exceeds 50%, document your production SOPs, and secure your brand assets (domain, socials, email list) for transfer. Channels that look "turnkey" to buyers — systems, not a personality under stress — consistently fetch the top of the multiple range.</p>',
'affiliate-commission-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Picking Programs Like a Professional</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Amateurs chase commission <em>rates</em>; professionals chase <strong>EPC</strong>. A 50% commission on a product nobody buys loses to a 5% commission on a product that converts at 8% — always test and measure EPC per program. Three structural factors matter: <strong>cookie duration</strong> (24 hours at Amazon vs. 30–90 days at software companies — longer cookies capture far more delayed purchases), <strong>average order value</strong> (high-ticket programs need fewer conversions), and <strong>brand conversion strength</strong> (established brands convert 3–5× unknown ones). Diversify across 3–5 programs so one terms-change doesn\'t zero your income — networks cut rates regularly. And compliance is non-negotiable: the FTC requires <strong>clear disclosure</strong> of affiliate relationships near every link, and Amazon requires specific language; violations risk both account termination and regulatory action.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Content that converts:</strong> "best X for Y" review posts and comparison tables convert 5–10× better than informational content because readers arrive with wallets open. Update top posts quarterly — rankings decay, prices change, and programs alter terms. One refreshed money page often outperforms ten new informational posts.</p>',
'sponsorship-pricing-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Negotiating Like You Mean It</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Your first number <strong>anchors</strong> the negotiation — quote the top of your range (the CPM-based figure) and let brands negotiate toward the middle, never opening with your floor. Package deals close bigger: 3-post bundles or 90-day ambassador programs at a 10–15% volume discount beat one-off posts on total revenue and relationship depth. Charge explicit premiums: <strong>25–50% for category exclusivity</strong>, extra for whitelisting/paid amplification rights, and rush fees for sub-7-day turnarounds. Build a one-page <strong>media kit</strong> (audience demographics, average views, engagement rate, past brand results with screenshots) — proof of ROI justifies every rate increase. And track performance obsessively: creators who report back view counts, click-throughs, and conversions get renewed at higher rates; creators who go silent get replaced.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>The follow-up fortune:</strong> most creators never follow up after sending rates — yet 50%+ of brand deals close on the second or third touch. Send a polite bump after 5 business days with one new proof point (a recent viral post, a press mention). Persistence, not discounts, is what converts hesitant brands.</p>',
'openai-api-cost-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Cutting Your API Bill in Half</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Four levers, in order of impact. <strong>Model routing</strong>: send simple tasks (classification, extraction, moderation) to mini models and reserve flagships for hard reasoning — most production workloads are 80%+ routable, cutting bills 5–10×. <strong>Prompt caching</strong>: stable system-prompt prefixes get 50%+ discounts automatically once cached; design prompts with static prefixes and dynamic suffixes. <strong>Batch API</strong>: non-urgent workloads (evals, bulk classification, data processing) cost 50% less with 24-hour turnaround. <strong>Token discipline</strong>: cap max_tokens, strip verbose system prompts, summarize conversation history instead of resending full transcripts. The professional workflow: prototype on the flagship, build evals, then <strong>downgrade per endpoint</strong> until quality drops — your bill is the sum of per-endpoint optima, not one model choice.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Budget guardrails:</strong> set per-key monthly spend limits in the OpenAI dashboard, add usage alerts at 50% and 80%, and log per-endpoint token consumption from day one. Most billing surprises come from one unmonitored endpoint (usually chat history growing unbounded) — visibility is cheaper than any optimization.</p>',
'claude-api-cost-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Workload Placement Strategy</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The Claude lineup is a <strong>routing problem</strong>: Haiku (~⅓ Sonnet\'s price) for high-volume simple tasks like classification and extraction; Sonnet as the production default for chat, coding assistance, and agents; Opus reserved for the hardest reasoning with <strong>fallback routing</strong> (try Sonnet, escalate to Opus on low confidence). Prompt caching is the economic superpower — agentic loops re-sending long tool definitions and system prompts routinely hit 80–90% cache rates, making effective input costs a fraction of sticker price. Watch <strong>extended thinking</strong>: thinking tokens bill as output (the expensive kind), so long reasoning chains on simple queries waste money — set thinking budgets per task difficulty. The Batch API (50% off, slower) suits offline evals and bulk processing. Re-run this calculator per workload with realistic cache rates; sticker-price comparisons without caching mislead.</p>',
'ai-token-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Where Token Estimates Break Down</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The ÷4 rule is for <strong>English prose</strong>. Code tokenizes ~30–50% worse (whitespace and symbols fragment into more tokens), non-Latin scripts and emoji far worse — budget 2–3× for multilingual apps. <strong>Images</strong> consume tokens too: vision models tile images and charge per tile (a detailed screenshot can cost 1,000+ tokens before a word is read). The silent budget-killer is <strong>conversation history</strong>: every turn resends the full transcript, so a 20-turn chat costs roughly 20× the average turn length in input tokens — summarize or truncate history aggressively. For exact counts, run the <strong>tiktoken</strong> library (OpenAI) or each provider\'s tokenizer; for architecture decisions, this estimate is plenty. Remember the window is shared: input + output + thinking must all fit, so a "128K window" with 100K of history leaves little room to generate.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Plan for growth:</strong> prototype prompts are short; production prompts balloon with few-shot examples, tool schemas, and retrieved context (RAG). Multiply your prototype token estimate by 3–5× when budgeting production — retrieval-augmented apps routinely send 10,000+ tokens of context per request before generating a single word.</p>',
'saas-mrr-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">MRR Hygiene: Bookings vs. Billings vs. Revenue</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Founders routinely conflate three numbers: <strong>bookings</strong> (contracts signed), <strong>billings</strong> (cash invoiced), and <strong>MRR</strong> (revenue recognized monthly). Only MRR measures the business\'s run-rate — a $120,000 annual deal signed today is $10,000 MRR, not $120,000 of anything this month. Track <strong>contraction MRR</strong> (downgrades) separately from churn (cancellations); downgrades are often the bigger, quieter leak. Segment MRR by <strong>cohort</strong>: if new cohorts retain worse than old ones, aggregate NRR hides a decaying product. And pair MRR with the <strong>Rule of 40</strong> (growth rate + profit margin ≥ 40%) — hypergrowth at any cost eventually meets arithmetic. Investors prize <em>predictable</em> MRR: multi-year contracts, annual prepay, and expansion-heavy NRR above 110% command premium valuations over flat, churn-heavy revenue at the same total.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>The growth math that matters:</strong> at 100% NRR, every new customer is permanent progress; at 90% NRR, you must replace 10% of revenue yearly just to stand still — growth gets exponentially harder as you scale. This is why investors interrogate NRR before growth rate: retention is the compounding engine, acquisition is just the fuel.</p>',
'saas-churn-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Finding and Fixing Your Churn</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Split churn into <strong>voluntary</strong> (customer chose to leave) and <strong>involuntary</strong> (failed payments) — dunning management and card-updater services routinely recover 20–40% of involuntary churn, the cheapest growth you\'ll ever buy. Voluntary churn clusters in the first 90 days: <strong>onboarding</strong> that drives users to their first value moment (the "aha") within days cuts early churn dramatically. Structural retention beats persuasion: <strong>annual plans</strong> (often at 2 months free) collapse 12 monthly cancel decisions into one, typically halving logo churn. Run <strong>exit surveys</strong> on every cancellation and code the reasons — "too expensive" usually means "didn\'t get value," which is a product/onboarding problem, not a pricing one. Finally, remember expansion offsets churn: a customer who upgrades 2× before canceling contributed net-positive — optimize net revenue retention, not just logo retention.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Set churn alerts, not just reports:</strong> instrument leading indicators — login frequency drops, feature usage declines, support ticket spikes — and trigger human outreach <em>before</em> the cancellation click. Save plays (discounts, training, success calls) recover 15–30% of at-risk accounts, but only if they fire weeks before renewal, not after.</p>',
'customer-ltv-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Using LTV to Make Spending Decisions</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">LTV\'s real job is setting <strong>CAC ceilings per channel</strong>: compute LTV separately for organic, paid, and partner-acquired customers — they churn differently, and blended LTV misprices every channel. Pair LTV:CAC with the <strong>payback period</strong> (months to recover CAC): a 5:1 ratio with a 24-month payback still starves cash flow, while 3:1 with 6-month payback funds itself. Define gross margin honestly — include hosting, support, onboarding, and payment fees, not just COGS; overstated margin is the most common LTV inflation. <strong>Expansion revenue</strong> belongs in advanced LTV models: customers who upgrade over time are worth far more than ARPU × lifespan suggests. And segment ruthlessly: enterprise vs. SMB, annual vs. monthly — a single company-wide LTV is a fiction that hides your best and worst economics.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Sanity-check with payback:</strong> divide CAC by monthly gross profit per customer — if payback exceeds 12 months (18 for enterprise), growth consumes dangerous amounts of cash regardless of a healthy LTV:CAC ratio. The best businesses pair 3:1+ LTV:CAC with sub-12-month payback: profitable growth that funds itself.</p>',
'startup-runway-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">Extending Runway Without Raising</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">When runway drops below 12 months with no fundraise lined up, you have three levers: <strong>cut burn</strong> (cut once, cut deep — rolling layoffs destroy morale and still miss targets), <strong>grow revenue</strong> (annual prepay discounts convert future revenue into present cash; enterprise pilots become paid pilots), and <strong>bridge financing</strong> (extensions from existing investors, venture debt, or revenue-based financing). Know your <strong>"default alive"</strong> number: the growth rate at which current cash reaches profitability — if you\'re default alive, you negotiate from strength; if not, fundraising is existential and should start <em>now</em>. Fundraising itself takes 3–6 months, so begin at 9–12 months of runway, not 6. And model scenarios, not points: base, downside (revenue −30%), and hiring-plan cases — the downside case is the one that determines survival.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>The two-runway rule:</strong> always know both your <em>cash</em> runway (this calculator) and your <em>milestone</em> runway — the months until you hit the traction target your next fundraise requires. If milestone runway exceeds cash runway, you must cut burn, accelerate growth, or raise immediately. Running out of cash with momentum is a fundable problem; running out without it is fatal.</p>',
'stripe-fee-calculator': '\n<h3 style="margin-top:20px;font-size:1.2rem;">When the Fixed Fee Dominates</h3>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The 30¢ fixed fee is regressive: on a <strong>$5</strong> transaction the effective rate is 8.9%, on <strong>$500</strong> it\'s 2.96%. If your average ticket is under ~$10, Stripe\'s <strong>micropayment pricing</strong> (5% + 5¢) wins — the breakeven is around $7–$8 per transaction; above that, standard pricing is cheaper. International businesses: the +1.5% cross-border fee plus 1% currency conversion compounds fast — <strong>local acquiring</strong> (settling in the customer\'s currency/region) can cut it substantially at scale. Fight <strong>disputes</strong> preventively: clear descriptors, delivery confirmation, and responsive support beat representment (win rates are low and each dispute costs $15 regardless). Above ~$80,000/month in volume, <strong>negotiate</strong> — Stripe offers custom rates, and competing quotes from Adyen or Chase give leverage. Always bake fees into pricing: divide target net by (1 − rate) rather than absorbing the cut.</p>\n<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Fee-aware pricing pages:</strong> when you raise prices, remember fees scale with the increase — a $10 price hike at 2.9% + 30¢ nets only $9.41. For SaaS, annual plans are fee-efficient: one $1,188 charge costs ~$34.75 in fees versus ~$4.16 × 12 = $49.92 monthly — you save ~$15 per customer per year just on processing.</p>',
}

def full_guide(t):
    return t['guide'] + GUIDE_EXTRA.get(t['slug'], '')

# ================= PER-TOOL DATA (38 tools) =================
# Convention: js_core defines function core(p) returning numeric results.
# tests: two cases with Python-computed expected values; node must reproduce.

TOOLS = []

def R(emoji, label, rid, fmt):
    return (emoji, label, rid, fmt)

# ---------------- 1. fire-calculator (finance) ----------------
TOOLS.append({
'slug':'fire-calculator','name':'FIRE Calculator','icon':'🔥','cat':'finance','cat_label':'FINANCE',
'hub':'/finance-calculators','hub_title':'Finance Calculators',
'hub_blurb':'Browse all 60+ finance, loan, and investing calculators.',
'title':'FIRE Calculator — Years to Financial Independence & Retire Early',
'desc':'Calculate your FIRE number with the 4% rule, project investment growth, and find the exact age you can retire early. Free financial independence calculator.',
'keywords':'FIRE calculator, financial independence retire early, FIRE number calculator, 4 percent rule calculator, retire early calculator',
'h1':'FIRE Calculator',
'intro':'Find your FIRE number using the 4% rule, project your savings growth with compound returns, and discover the exact age you could reach financial independence.',
'inputs':[
 {'id':'age','label':'Current Age','value':35,'min':18,'max':80},
 {'id':'retireAge','label':'Target Retirement Age','value':60,'min':30,'max':90},
 {'id':'savings','label':'Current Savings / Investments','value':100000,'prefix':'$','min':0},
 {'id':'contrib','label':'Annual Contribution','value':20000,'prefix':'$','min':0},
 {'id':'expenses','label':'Annual Expenses in Retirement','value':60000,'prefix':'$','min':0},
 {'id':'ret','label':'Expected Annual Return (%)','value':7,'suffix':'%','min':0,'max':15,'step':0.1},
 {'id':'swr','label':'Safe Withdrawal Rate (%)','value':4,'suffix':'%','min':2,'max':6,'step':0.1},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">🎯 Your FIRE Number</div>
<div class="mort-result-big" id="resFire">$0</div>
<div id="resFireSub" style="font-size:0.82rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📈 Projected Savings at Target Age</span><span class="val" id="resProj">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Savings Gap / Surplus</span><span class="val" id="resGap">$0</span></div>
<div class="mort-row"><span class="lbl">🎂 Projected FI Age</span><span class="val" id="resAge">—</span></div>
<div class="mort-row"><span class="lbl">📊 Annual Expenses Covered</span><span class="val" id="resCov">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How the FIRE Number and the 4% Rule Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">FIRE — <strong>Financial Independence, Retire Early</strong> — is the movement built on one powerful idea: once your investments can cover your living expenses indefinitely, work becomes optional. This calculator tells you exactly how much you need and when you'll get there.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">What Is the FIRE Number?</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Your <strong>FIRE number</strong> is the portfolio size that makes you financially independent. It comes from the <strong>4% rule</strong>, based on the Trinity Study: a retiree withdrawing 4% of their portfolio per year (adjusted for inflation) historically did not run out of money over 30-year retirements. The formula is simple:</p>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">FIRE Number = Annual Expenses ÷ Safe Withdrawal Rate<br/>Example: $60,000 ÷ 0.04 = $1,500,000</div>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">A 35-year-old has <strong>$100,000</strong> invested, contributes <strong>$20,000/year</strong>, earns <strong>7%</strong> annually, and spends <strong>$60,000/year</strong>. FIRE number = $60,000 ÷ 0.04 = <strong>$1,500,000</strong>. Compound growth: FV = $100,000×(1.07)<sup>25</sup> + $20,000×[((1.07)<sup>25</sup>−1)/0.07] ≈ <strong>$1,807,700</strong> by age 60 — about <strong>$307,700</strong> past the FIRE number. Solving backwards, this saver actually crosses $1.5M at roughly <strong>age 57.6</strong>, more than two years before the target.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">How to Use This Calculator</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Enter your current age, savings, yearly contributions, and expected return. The calculator projects your portfolio with the future-value-of-annuity formula, compares it to your FIRE number, and binary-searches the exact age your savings cross the target. Raise contributions or expected return and watch your FI age drop — small increases compound enormously over 20+ years. Note the 4% rule assumes a stock-heavy portfolio and a ~30-year retirement; earlier retirees often use 3.5% for extra safety.</p>''',
'faqs':[
 ('What is the 4% rule?','The 4% rule comes from the Trinity Study (1998): withdrawing 4% of your portfolio in year one of retirement, then adjusting for inflation each year, historically survived 30-year retirements in most market scenarios. It implies you need 25× your annual expenses invested.'),
 ('What is a good FIRE number?','It depends entirely on spending. At $40,000/year expenses, your FIRE number is $1,000,000; at $80,000/year it is $2,000,000. Cutting expenses is the highest-leverage move because it shrinks the target AND speeds up savings.'),
 ('Is the 4% rule still safe in 2026?','Many planners now suggest 3.5–4% as a starting point, with flexibility to cut spending in down years. Early retirees (40+ year horizons) often target 3–3.5% for extra margin. This calculator lets you adjust the withdrawal rate.'),
 ('What return should I assume?','US stocks have returned ~10% nominal (~7% after inflation) long-term. A 7% nominal assumption is common for stock-heavy portfolios; use 5–6% to be conservative or if you hold bonds.'),
 ('What are Lean FIRE and Fat FIRE?','Lean FIRE means retiring on minimal spending (often under $40k/year); Fat FIRE targets a higher-spending lifestyle ($100k+/year) and a larger portfolio. Coast FIRE is the middle path: save enough early that compounding alone reaches your number by traditional retirement age.'),
],
'related':[
 ('compound-interest','Compound Interest Calculator','📈','Model long-term wealth growth with recurring contributions.'),
 ('retirement-401k','401(k) Retirement Savings','🏖️','Project your 401(k) balance at retirement age.'),
 ('roth-ira-calculator','Roth IRA Tax-Free Growth','📈','See how tax-free Roth growth accelerates FIRE.'),
 ('inflation-retirement-calculator','Inflation & Retirement (4% Rule)','⏳','Stress-test the 4% rule against inflation.'),
 ('net-worth-calculator','Personal Net Worth','⚖️','Track assets minus liabilities toward FI.'),
 ('emergency-fund-calculator','Emergency Fund Calculator','🛡️','Size a 3–6 month safety net first.'),
],
'js_core':'''function core(p){
  var y=Math.max(0,p.retireAge-p.age);
  var r=p.ret/100;
  var g=Math.pow(1+r,y);
  var proj=p.savings*g+(r>0?p.contrib*(g-1)/r:p.contrib*y);
  var fire=p.swr>0?p.expenses/(p.swr/100):0;
  var gap=fire-proj;
  var n=y;
  if(r>0){
    var lo=0,hi=100;
    for(var i=0;i<80;i++){var m=(lo+hi)/2;var gm=Math.pow(1+r,m);
      var v=p.savings*gm+p.contrib*(gm-1)/r;
      if(v>=fire)hi=m;else lo=m;}
    n=hi;
  }
  return {fire:fire,proj:proj,gap:gap,fiAge:p.age+n,years:y};
}''',
'js_glue':'''function recalc(){
  var p={age:num('age'),retireAge:num('retireAge'),savings:num('savings'),contrib:num('contrib'),expenses:num('expenses'),ret:num('ret'),swr:num('swr')};
  var r=core(p);
  setT('resFire',fmtM(r.fire));
  setT('resFireSub','= '+fmtM(p.expenses)+' annual expenses ÷ '+fmtP(p.swr,1)+' withdrawal rate');
  setT('resProj',fmtM(r.proj));
  setT('resGap',(r.gap>0?'-':'')+fmtM(Math.abs(r.gap))+(r.gap<=0?' surplus':' shortfall'));
  setT('resAge',r.fiAge.toFixed(1)+' years');
  setT('resCov',fmtM(r.proj*(p.swr/100))+' / yr sustainable');
  document.getElementById('shareText').textContent='FIRE number '+fmtM(r.fire)+', projected '+fmtM(r.proj)+' by age '+p.retireAge+', FI at ~'+r.fiAge.toFixed(1);
}
['age','retireAge','savings','contrib','expenses','ret','swr'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'age':35,'retireAge':60,'savings':100000,'contrib':20000,'expenses':60000,'ret':7,'swr':4},
  'expect':{'fire':1500000,'proj':1807723,'gap':-307723,'fiAge':57.65}},
 {'inputs':{'age':40,'retireAge':65,'savings':50000,'contrib':15000,'expenses':80000,'ret':6,'swr':4},
  'expect':{'fire':2000000,'proj':1037561,'gap':962439,'fiAge':74.58}},
],
})

# ---------------- 2. credit-score-simulator (finance) ----------------
TOOLS.append({
'slug':'credit-score-simulator','name':'Credit Score Simulator','icon':'💳','cat':'finance','cat_label':'FINANCE',
'hub':'/finance-calculators','hub_title':'Finance Calculators',
'hub_blurb':'Browse all 60+ finance, loan, and investing calculators.',
'title':'Credit Score Simulator — See How Actions Change Your Score',
'desc':'Simulate how paying down balances, missing payments, or opening new accounts could change your credit score. Based on published FICO score factor weights.',
'keywords':'credit score simulator, what affects credit score, FICO score factors, how to improve credit score, credit utilization impact',
'h1':'Credit Score Simulator',
'intro':'Model how utilization changes, missed payments, new accounts, and payment history could move your credit score — using the published FICO scoring factor weights.',
'inputs':[
 {'id':'score','label':'Current Credit Score','value':720,'min':300,'max':850},
 {'id':'onTime','label':'On-Time Payment History (%)','value':100,'suffix':'%','min':50,'max':100},
 {'id':'util','label':'Credit Utilization (%)','value':20,'suffix':'%','min':0,'max':100},
 {'id':'missed','label':'Missed Payments (last 12 mo)','value':0,'min':0,'max':10},
 {'id':'newAccts','label':'New Accounts Opened (last 12 mo)','value':1,'min':0,'max':10},
 {'id':'histYears','label':'Oldest Account Age (years)','value':8,'min':0,'max':40},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Simulated Credit Score</div>
<div class="mort-result-big" id="resScore">720</div>
<div id="resDelta" style="font-size:0.9rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💳 Utilization Effect</span><span class="val" id="resUtil">—</span></div>
<div class="mort-row"><span class="lbl">⏰ Payment History Effect</span><span class="val" id="resPay">—</span></div>
<div class="mort-row"><span class="lbl">🆕 New Credit Effect</span><span class="val" id="resNew">—</span></div>
<div class="mort-row"><span class="lbl">📜 Length of History Effect</span><span class="val" id="resHist">—</span></div>
<div class="mort-row"><span class="lbl">🏷️ Estimated Score Band</span><span class="val" id="resBand">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>
<p style="font-size:0.78rem;color:var(--text-muted);margin-top:10px;">⚠️ Educational estimate only — bureaus use proprietary models. Based on published FICO factor weights (35/30/15/10/10).</p>''',
'guide_h2':'How Credit Scores Are Calculated (FICO Weights)',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Your credit score is not a mystery — FICO publishes the exact weight of each factor. This simulator applies those weights so you can see, before you act, roughly how a financial move could shift your score.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Five FICO Factors</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Payment history (35%)</strong> — the single biggest factor. One 30-day late payment can drop a good score 60–110 points. <strong>Amounts owed (30%)</strong> — dominated by credit utilization: balances ÷ limits. Under 10% is ideal; over 30% hurts. <strong>Length of history (15%)</strong> — average age of accounts; keep old cards open. <strong>New credit (10%)</strong> — hard inquiries and new accounts shave a few points each. <strong>Credit mix (10%)</strong> — a blend of revolving and installment accounts helps slightly.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Take a <strong>720</strong> score with 100% on-time history, <strong>20% utilization</strong>, no missed payments, one new account, and 8 years of history. The model estimates utilization 10 points above the 10% ideal costs about <strong>−18 points</strong>, and the new account costs about <strong>−12 points</strong>, for a simulated score of <strong>690</strong>. Now change one thing: pay utilization down to 8% and the simulation rebounds to roughly <strong>712</strong> — showing why utilization is the fastest lever most people can pull (it has no memory; it resets monthly).</p>
<h3 style="margin-top:20px;font-size:1.2rem;">How to Use This Simulator</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Enter your current score and habits, then experiment: drop utilization, add a hypothetical missed payment, or open a new card. Use it for planning, not precision — real bureau models are proprietary and consider dozens of sub-factors. The directional guidance is what matters: pay on time, keep utilization low, and let accounts age.</p>''',
'faqs':[
 ('What credit score do I need for a mortgage in 2026?','Conventional loans typically want 620+, with the best rates at 740+. FHA loans allow 580 with 3.5% down (500 with 10% down). VA loans have no official minimum but lenders often want 620.'),
 ('How fast can I raise my credit score?','Utilization improvements can lift scores within one billing cycle (30–45 days) since utilization has no memory. Recovering from a missed payment takes much longer — late payments stay on reports for 7 years, though their impact fades.'),
 ('Does checking my own score hurt it?','No. Checking your own score is a soft inquiry and never affects your score. Only hard inquiries from credit applications (usually −5 to −10 points each) have an impact.'),
 ('What is a good credit utilization ratio?','Under 30% is the common guideline, but under 10% is ideal for the highest scores. Both per-card and overall utilization matter. Paying balances before the statement closing date is a legitimate way to report lower utilization.'),
 ('How long do hard inquiries affect my score?','Hard inquiries affect FICO scores for 12 months and stay visible on reports for 2 years. Rate-shopping for a mortgage or auto loan within a 14–45 day window counts as a single inquiry.'),
],
'related':[
 ('credit-card-payoff','Credit Card Payoff','💳','See how long card debt takes to clear.'),
 ('debt-payoff','Debt Snowball & Avalanche','💳','A payoff plan that protects your score.'),
 ('dti-calculator','Debt-to-Income (DTI)','⚖️','Check the DTI ratio lenders use.'),
 ('mortgage-calculator','Mortgage Calculator','🏠','See what rate your score could earn.'),
 ('auto-loan','Auto Loan Calculator','🚘','Score-driven auto loan payments.'),
],
'js_core':'''function core(p){
  var utilAdj=p.util<=10?(10-p.util)*0.8:-(p.util-10)*1.8;
  var missAdj=p.missed===0?0:(p.missed===1?-80:(p.missed===2?-120:-150));
  var payAdj=-(100-p.onTime)*4+missAdj;
  var newAdj=-p.newAccts*12;
  var histAdj=p.histYears<5?-20:(p.histYears>15?10:0);
  var est=p.score+utilAdj+payAdj+newAdj+histAdj;
  est=Math.max(300,Math.min(850,Math.round(est)));
  var band=est>=800?'Exceptional':(est>=740?'Very Good':(est>=670?'Good':(est>=580?'Fair':'Poor')));
  return {est:est,delta:est-p.score,utilAdj:Math.round(utilAdj),payAdj:Math.round(payAdj),newAdj:newAdj,histAdj:histAdj,band:band};
}''',
'js_glue':'''function sgn(n){return (n>0?'+':'')+n+' pts';}
function recalc(){
  var p={score:num('score'),onTime:num('onTime'),util:num('util'),missed:num('missed'),newAccts:num('newAccts'),histYears:num('histYears')};
  var r=core(p);
  setT('resScore',String(r.est));
  var d=document.getElementById('resDelta');
  d.textContent=(r.delta>=0?'▲ +':'▼ ')+r.delta+' points';
  d.style.color=r.delta>=0?'#34d399':'#f87171';
  setT('resUtil',sgn(r.utilAdj));setT('resPay',sgn(r.payAdj));setT('resNew',sgn(r.newAdj));setT('resHist',sgn(r.histAdj));
  setT('resBand',r.band);
  document.getElementById('shareText').textContent='Simulated score '+r.est+' ('+sgn(r.delta)+') from '+p.score;
}
['score','onTime','util','missed','newAccts','histYears'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'score':720,'onTime':100,'util':20,'missed':0,'newAccts':1,'histYears':8},
  'expect':{'est':690,'delta':-30}},
 {'inputs':{'score':680,'onTime':98,'util':45,'missed':1,'newAccts':0,'histYears':4},
  'expect':{'est':509,'delta':-171}},
],
})

# ---------------- 3. debt-to-income-calculator (finance) ----------------
TOOLS.append({
'slug':'debt-to-income-calculator','name':'Debt-to-Income Calculator','icon':'⚖️','cat':'finance','cat_label':'FINANCE',
'hub':'/finance-calculators','hub_title':'Finance Calculators',
'hub_blurb':'Browse all 60+ finance, loan, and investing calculators.',
'title':'Debt-to-Income (DTI) Calculator — Front-End & Back-End Ratios',
'desc':'Calculate your debt-to-income ratio the way mortgage lenders do. See front-end and back-end DTI, the 28/36 rule, and whether you qualify for a home loan.',
'keywords':'debt to income ratio calculator, DTI calculator mortgage, front end back end DTI, 28/36 rule, how to calculate DTI',
'h1':'Debt-to-Income Calculator',
'intro':'Lenders judge affordability with one number: your debt-to-income ratio. Enter your income and monthly debts to see your front-end and back-end DTI instantly.',
'inputs':[
 {'id':'income','label':'Gross Monthly Income','value':8000,'prefix':'$','min':0},
 {'id':'housing','label':'Housing Payment (rent/mortgage + tax + ins)','value':1800,'prefix':'$','min':0},
 {'id':'car','label':'Car Loan / Lease Payment','value':350,'prefix':'$','min':0},
 {'id':'student','label':'Student Loan Payment','value':300,'prefix':'$','min':0},
 {'id':'cards','label':'Credit Card Minimum Payments','value':150,'prefix':'$','min':0},
 {'id':'other','label':'Other Monthly Debts','value':100,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Back-End DTI Ratio</div>
<div class="mort-result-big" id="resDTI">0%</div>
<div id="resVerdict" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🏠 Front-End DTI (housing only)</span><span class="val" id="resFront">—</span></div>
<div class="mort-row"><span class="lbl">💳 Total Monthly Debt Payments</span><span class="val" id="resDebts">$0</span></div>
<div class="mort-row"><span class="lbl">💰 Monthly Income</span><span class="val" id="resInc">$0</span></div>
<div class="mort-row"><span class="lbl">🎯 Max Housing at 28%</span><span class="val" id="resMaxH">$0</span></div>
<div class="mort-row"><span class="lbl">🎯 Max Total Debt at 36%</span><span class="val" id="resMaxT">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How the Debt-to-Income Ratio Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Your debt-to-income ratio is the first filter every mortgage underwriter applies. It answers one question: of each dollar you earn, how many cents are already spoken for by debt?</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">DTI = (Total Monthly Debt Payments ÷ Gross Monthly Income) × 100</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Lenders compute two versions. <strong>Front-end DTI</strong> counts housing only (mortgage/rent + taxes + insurance + HOA). <strong>Back-end DTI</strong> counts everything: housing plus car loans, student loans, credit card minimums, child support, and any installment debt. Only minimum required payments count — not the full credit card balance.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">With <strong>$8,000</strong> gross monthly income, <strong>$1,800</strong> housing, and <strong>$900</strong> in other debts ($350 car + $300 student + $150 cards + $100 other): front-end DTI = $1,800 ÷ $8,000 = <strong>22.5%</strong>; back-end DTI = $2,700 ÷ $8,000 = <strong>33.75%</strong>. That passes the classic <strong>28/36 rule</strong> (housing ≤ 28%, all debts ≤ 36%) that conventional lenders use as their benchmark.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">How to Use This Calculator</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Enter gross (pre-tax) monthly income and every recurring minimum debt payment. If your back-end DTI is above 43% — the Qualified Mortgage cutoff — most conventional lenders will decline you; FHA loans may stretch to 50–56.9% with compensating factors. To lower DTI fast, pay off small installment loans entirely (removing a payment helps more than shrinking a balance) or increase income — the ratio rewards both.</p>''',
'faqs':[
 ('What is a good debt-to-income ratio?','Under 36% is considered healthy; 36–43% is acceptable to most lenders; above 43% you hit the Qualified Mortgage limit and conventional approval gets difficult. Under 28% housing-only (front-end) is the traditional target.'),
 ('Does DTI include utilities and groceries?','No. DTI only counts debt obligations reported or verifiable: housing, auto, student loans, credit card minimums, child support, alimony, and personal loans. Living expenses like food, utilities, and insurance (except homeowners) are excluded.'),
 ('What is the 28/36 rule?','A long-standing lending guideline: spend no more than 28% of gross income on housing and no more than 36% on all debts combined. It is a benchmark, not a law — actual limits vary by loan program.'),
 ('Can I get a mortgage with 50% DTI?','Possibly with FHA (up to 56.9% back-end with strong compensating factors like large reserves or residual income), VA (no hard cap, uses residual income), or non-QM loans. Conventional conforming loans cap around 45–50% with automated approval.'),
 ('Do I use gross or net income for DTI?','Always gross (pre-tax) income. Lenders use gross because it is standardized and verifiable via pay stubs and tax returns.'),
],
'related':[
 ('mortgage-calculator','Mortgage Calculator','🏠','Monthly PITI payment and amortization.'),
 ('dti-calculator','Debt-to-Income (DTI)','⚖️','Quick DTI check for loan qualification.'),
 ('rent-vs-buy','Rent vs Buy Decision','⚖️','Compare renting vs buying a home.'),
 ('auto-loan','Auto Loan Calculator','🚘','Car payments that feed your DTI.'),
 ('house-affordability-calculator','House Affordability Calculator','🏡','Max home price from your income.'),
 ('credit-card-payoff','Credit Card Payoff','💳','Kill minimum payments dragging DTI.'),
],
'js_core':'''function core(p){
  var debts=p.housing+p.car+p.student+p.cards+p.other;
  var front=p.income>0?p.housing/p.income*100:0;
  var back=p.income>0?debts/p.income*100:0;
  var verdict=back<=36?'✅ Excellent — within 28/36 guidelines':(back<=43?'⚠️ Acceptable — near QM 43% limit':'❌ High — above 43% QM threshold');
  return {front:front,back:back,debts:debts,verdict:verdict,maxH:p.income*0.28,maxT:p.income*0.36};
}''',
'js_glue':'''function recalc(){
  var p={income:num('income'),housing:num('housing'),car:num('car'),student:num('student'),cards:num('cards'),other:num('other')};
  var r=core(p);
  setT('resDTI',fmtP(r.back,2));
  var v=document.getElementById('resVerdict');v.textContent=r.verdict;
  v.style.color=r.back<=36?'#34d399':(r.back<=43?'#fbbf24':'#f87171');
  setT('resFront',fmtP(r.front,2));
  setT('resDebts',fmtM(r.debts));setT('resInc',fmtM(p.income));
  setT('resMaxH',fmtM(r.maxH)+'/mo');setT('resMaxT',fmtM(r.maxT)+'/mo');
  document.getElementById('shareText').textContent='Back-end DTI '+r.back.toFixed(2)+'%, front-end '+r.front.toFixed(2)+'%';
}
['income','housing','car','student','cards','other'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'income':8000,'housing':1800,'car':350,'student':300,'cards':150,'other':100},
  'expect':{'front':22.5,'back':33.75,'debts':2700}},
 {'inputs':{'income':5000,'housing':500,'car':200,'student':150,'cards':100,'other':50},
  'expect':{'front':10,'back':20,'debts':1000}},
],
})

# Shared 2026 federal brackets (single) — mirrors the site's own paycheck-calculator table
FED_BRACKETS_JS = '''function fedTax(taxable,married){
  var mult=married?2:1;
  var br=[[11925,0.10],[48475,0.12],[103350,0.22],[197300,0.24],[250525,0.32],[626350,0.35],[1e15,0.37]];
  var tax=0,prev=0;
  for(var i=0;i<br.length;i++){var cap=br[i][0]*mult,rate=br[i][1];
    if(taxable>prev){tax+= (Math.min(taxable,cap)-prev)*rate;prev=cap;}else break;}
  return tax;
}
function seTaxF(net){
  var base=net*0.9235;
  var ss=Math.min(base,176100)*0.062*2; /* 12.4% total up to 2026 wage base */
  var med=base*0.029;
  return {total:ss+med,base:base,ss:ss,med:med};
}'''
IRS_NOTE = '<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Official reference: <a href="https://www.irs.gov/" target="_blank" rel="noopener" style="color:#38bdf8;">IRS.gov</a>. This is an <strong>estimate for planning only — not tax advice</strong>. Verify with a CPA or tax professional before filing.</p>'

# ---------------- 4. w-4-withholding-calculator (tax) ----------------
TOOLS.append({
'slug':'w-4-withholding-calculator','name':'W-4 Withholding Calculator','icon':'📝','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'W-4 Withholding Calculator — Fix Your 2026 Paycheck Withholding',
'desc':'Estimate your 2026 federal income tax, see if your W-4 withholds too much or too little, and avoid a surprise tax bill or giant refund. Free W-4 checkup.',
'keywords':'W-4 calculator, tax withholding calculator 2026, how much tax withheld paycheck, adjust W-4, federal withholding estimator',
'h1':'W-4 Withholding Calculator',
'intro':'Enter your salary and current per-paycheck withholding to see whether your W-4 is on target — or setting you up for a refund or a bill.',
'inputs':[
 {'id':'salary','label':'Annual Gross Salary','value':85000,'prefix':'$','min':0},
 {'id':'fstatus','label':'Filing Status','type':'select','options':[['0','Single'],['1','Married Filing Jointly']]},
 {'id':'pretax','label':'Annual Pre-Tax Deductions (401k, HSA)','value':5000,'prefix':'$','min':0},
 {'id':'periods','label':'Pay Periods Per Year','value':26,'min':1,'max':52},
 {'id':'curwh','label':'Current Federal Withholding Per Paycheck','value':300,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Withholding Per Paycheck</div>
<div class="mort-result-big" id="resDiff">$0</div>
<div id="resDiffSub" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🧾 Est. Annual Federal Tax</span><span class="val" id="resTax">$0</span></div>
<div class="mort-row"><span class="lbl">💵 Correct Withholding / Paycheck</span><span class="val" id="resPer">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Taxable Income</span><span class="val" id="resTaxable">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Marginal Bracket</span><span class="val" id="resBracket">—</span></div>
<div class="mort-row"><span class="lbl">💸 Projected Refund / Owed</span><span class="val" id="resRefund">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How W-4 Withholding Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Your employer does not know your whole tax picture — it only withholds based on the W-4 you filed. Too little and you owe (plus possible penalties); too much and you gave the IRS an interest-free loan. This calculator benchmarks your withholding against your actual 2026 liability.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Withholding Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Taxable Income = Salary − Pre-Tax Deductions − Standard Deduction<br/>Correct / paycheck = Progressive Federal Tax ÷ Pay Periods</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The 2026 standard deduction is <strong>$15,000</strong> single / <strong>$30,000</strong> married filing jointly, and federal brackets run 10%–37%. Compare the "correct" per-paycheck figure to your actual withholding: a positive difference means you are over-withholding (refund coming); negative means under-withholding (bill coming).</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Single filer, <strong>$85,000</strong> salary, <strong>$5,000</strong> in 401(k) contributions, paid biweekly (26 periods). Taxable income = $85,000 − $5,000 − $15,000 = <strong>$65,000</strong>. Progressive tax: 10% on the first $11,925 ($1,192.50) + 12% on $11,926–$48,475 ($4,386) + 22% on $48,476–$65,000 ($3,635.50) = <strong>$9,214/year</strong>, or <strong>$354.38 per paycheck</strong>. If your W-4 currently withholds $300, you are under-withholding by about <strong>$54 per paycheck</strong> — roughly a $1,414 tax bill at filing time.</p>
'''+IRS_NOTE+'''
<h3 style="margin-top:20px;font-size:1.2rem;">How to Fix Your W-4</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Under-withheld? Add an extra dollar amount on W-4 Step 4(c), or reduce pre-tax contributions. Over-withheld? Increase allowances via Step 3 credits or adjust Step 4(b) deductions. Re-run this checkup after raises, marriage, or new dependents.</p>''',
'faqs':[
 ('How do I know if my W-4 is correct?','Compare your per-paycheck federal withholding to the "correct" figure from this calculator. Within a few dollars per paycheck is fine. Off by $50+ per paycheck means a four-figure refund or bill at tax time.'),
 ('Is a big tax refund good?','A refund means you overpaid during the year — an interest-free loan to the IRS. Ideally your refund or balance due is near zero, keeping the money in your paycheck all year.'),
 ('What triggers an underpayment penalty?','Owing more than $1,000 at filing can trigger penalties unless you paid at least 90% of the current-year tax or 100% of last year\'s tax (110% for higher incomes) through withholding or estimates.'),
 ('Should I claim 0 or 1 on my W-4?','The post-2020 W-4 has no allowances — you enter dollar amounts instead. Use Step 3 for dependents/credits and Step 4 for extra income, deductions, or extra withholding per pay period.'),
 ('When should I update my W-4?','After a raise, job change, marriage/divorce, a new child, or big changes in deductions. The IRS recommends a Paycheck Checkup at least once a year.'),
],
'related':[
 ('paycheck-calculator','Paycheck Net Take-Home (2026)','💵','Full paycheck breakdown after 2026 taxes.'),
 ('tax-withholding','Tax Withholding (2026)','🏛️','Federal withholding per paycheck.'),
 ('freelance-tax-calculator','Freelance 1099 Tax Estimator','💼','Estimate self-employment taxes.'),
 ('bonus-tax-calculator','Bonus Tax Calculator','🎁','How bonuses are withheld.'),
 ('tax-refund-estimator','Tax Refund Estimator','💸','Project your refund or balance due.'),
],
'js_core':FED_BRACKETS_JS+'''function core(p){
  var married=p.fstatus==1;
  var stdDed=married?30000:15000;
  var taxable=Math.max(0,p.salary-p.pretax-stdDed);
  var tax=fedTax(taxable,married);
  var per=p.periods>0?tax/p.periods:0;
  var diff=p.curwh-per;
  var refund=diff*p.periods;
  var br=taxable<=11925*(married?2:1)?'10%':(taxable<=48475*(married?2:1)?'12%':(taxable<=103350*(married?2:1)?'22%':(taxable<=197300*(married?2:1)?'24%':'32%+')));
  return {tax:tax,per:per,diff:diff,refund:refund,taxable:taxable,bracket:br};
}''',
'js_glue':'''function recalc(){
  var p={salary:num('salary'),fstatus:parseInt(document.getElementById('fstatus').value),pretax:num('pretax'),periods:num('periods'),curwh:num('curwh')};
  var r=core(p);
  var d=document.getElementById('resDiff');
  setT('resDiff',(r.diff>=0?'+':'\u2212')+'$'+fmt0(Math.abs(r.diff))+'/check');
  var s=document.getElementById('resDiffSub');
  s.textContent=r.diff>=0?'Over-withheld (refund coming)':'Under-withheld (bill coming)';
  s.style.color=r.diff>=0?'#34d399':'#f87171';
  setT('resTax',fmtM(r.tax));setT('resPer',fmtM(r.per)+'/check');
  setT('resTaxable',fmtM(r.taxable));setT('resBracket',r.bracket);
  setT('resRefund',(r.refund>=0?'Refund ':'Owed ')+fmtM(Math.abs(r.refund)));
  document.getElementById('shareText').textContent='Est. federal tax '+fmtM(r.tax)+', correct withholding '+fmtM(r.per)+'/paycheck';
}
['salary','pretax','periods','curwh'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('fstatus').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'salary':85000,'fstatus':0,'pretax':5000,'periods':26,'curwh':300},
  'expect':{'tax':9214,'per':354.38,'refund':-1414,'taxable':65000}},
 {'inputs':{'salary':150000,'fstatus':1,'pretax':10000,'periods':26,'curwh':500},
  'expect':{'tax':14028,'per':539.54,'taxable':110000}},
],
})

# ---------------- 5. llc-tax-calculator (tax) ----------------
TOOLS.append({
'slug':'llc-tax-calculator','name':'LLC Tax Calculator','icon':'🏢','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'LLC Tax Calculator — Self-Employment + Income Tax on Profits',
'desc':'Estimate total LLC taxes: 15.3% self-employment tax plus federal and state income tax on pass-through profits. See your effective rate for 2026.',
'keywords':'LLC tax calculator, how are LLCs taxed, LLC self employment tax, single member LLC taxes, pass through taxation',
'h1':'LLC Tax Calculator',
'intro':'LLCs are pass-through: profits flow to your personal return and face both self-employment tax and income tax. See the full bill.',
'inputs':[
 {'id':'profit','label':'Annual Net Business Profit','value':120000,'prefix':'$','min':0},
 {'id':'fstatus','label':'Filing Status','type':'select','options':[['0','Single'],['1','Married Filing Jointly']]},
 {'id':'stateRate','label':'State Income Tax Rate (%)','value':5,'suffix':'%','min':0,'max':15,'step':0.1},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Total Tax Bill</div>
<div class="mort-result-big" id="resTotal">$0</div>
<div id="resEff" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💼 Self-Employment Tax (15.3%)</span><span class="val" id="resSE">$0</span></div>
<div class="mort-row"><span class="lbl">🏛️ Federal Income Tax</span><span class="val" id="resFed">$0</span></div>
<div class="mort-row"><span class="lbl">🗺️ State Income Tax</span><span class="val" id="resState">$0</span></div>
<div class="mort-row"><span class="lbl">💰 After-Tax Profit</span><span class="val" id="resNet">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How LLC Taxation Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">A single-member LLC is a <strong>disregarded entity</strong> and a multi-member LLC is a <strong>partnership</strong> by default — either way, the IRS taxes profits on your personal return. That means two layers of tax on the same profit.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Two Layers</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>1. Self-employment tax (15.3%)</strong> — 12.4% Social Security (on earnings up to the $176,100 wage base) + 2.9% Medicare, applied to 92.35% of net profit. <strong>2. Income tax</strong> — federal progressive brackets (10%–37%) on profit minus half your SE tax minus the standard deduction ($15,000 single / $30,000 married), plus your state tax. Pass-through owners may also qualify for the <strong>20% QBI deduction</strong> (Section 199A), which this estimate excludes — a CPA can tell you if you qualify.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Single filer, <strong>$120,000</strong> LLC profit, 5% state tax. SE base = $120,000 × 92.35% = $110,820 → SE tax = <strong>$16,955</strong>. Federal taxable = $120,000 − $8,478 (half SE) − $15,000 = $96,522 → federal tax ≈ <strong>$16,149</strong>. State tax = <strong>$6,000</strong>. Total ≈ <strong>$39,104</strong> — an effective rate of about <strong>32.6%</strong>, leaving $80,896 after tax.</p>
'''+IRS_NOTE,
'faqs':[
 ('Do LLCs pay corporate tax?','No, by default. A single-member LLC is taxed as a sole proprietorship and a multi-member LLC as a partnership — profits pass through to owners\' personal returns. An LLC can elect S-corp or C-corp taxation with Form 2553 or 8832.'),
 ('What is the self-employment tax rate in 2026?','15.3% total: 12.4% Social Security on earnings up to the $176,100 wage base plus 2.9% Medicare on all earnings. It applies to 92.35% of net profit, and half is deductible against income tax.'),
 ('Can an LLC reduce self-employment tax?','Electing S-corp taxation lets you take part of the profit as distributions not subject to SE tax — you only pay payroll tax on a reasonable W-2 salary. It typically pays off around $60k–$80k+ in profit.'),
 ('Do I owe quarterly estimated taxes as an LLC owner?','Yes, if you expect to owe $1,000+ — the IRS wants pay-as-you-go via Form 1040-ES, due April, June, September, and January. Safe harbor: pay 100% of last year\'s tax (110% at higher incomes).'),
 ('What is the QBI deduction?','Section 199A lets eligible pass-through owners deduct up to 20% of qualified business income. Service businesses phase out above certain income thresholds. It can significantly cut the income-tax layer.'),
],
'related':[
 ('freelance-tax-calculator','Freelance 1099 Tax Estimator','💼','Estimate self-employment and income tax.'),
 ('llc-vs-scorp-calculator','LLC vs S-Corp Tax Savings','⚖️','Compare LLC and S-Corp tax outcomes.'),
 ('self-employment-tax-calculator','Self-Employment Tax Calculator','🧾','SE tax on any net earnings.'),
 ('quarterly-tax-calculator','Quarterly Tax Calculator','📅','Estimate your quarterly payments.'),
 ('s-corp-tax-savings-calculator','S-Corp Tax Savings Calculator','💰','Savings from an S-corp election.'),
],
'js_core':FED_BRACKETS_JS+'''function core(p){
  var married=p.fstatus==1;
  var se=seTaxF(p.profit);
  var taxable=Math.max(0,p.profit-se.total/2-(married?30000:15000));
  var fed=fedTax(taxable,married);
  var state=p.profit*p.stateRate/100;
  var total=se.total+fed+state;
  return {se:se.total,fed:fed,state:state,total:total,net:p.profit-total,eff:p.profit>0?total/p.profit*100:0};
}''',
'js_glue':'''function recalc(){
  var p={profit:num('profit'),fstatus:parseInt(document.getElementById('fstatus').value),stateRate:num('stateRate')};
  var r=core(p);
  setT('resTotal',fmtM(r.total));
  setT('resEff','Effective rate '+fmtP(r.eff,1)+' of profit');
  setT('resSE',fmtM(r.se));setT('resFed',fmtM(r.fed));setT('resState',fmtM(r.state));setT('resNet',fmtM(r.net));
  document.getElementById('shareText').textContent='LLC tax on '+fmtM(p.profit)+': '+fmtM(r.total)+' total ('+r.eff.toFixed(1)+'% effective)';
}
['profit','stateRate'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('fstatus').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'profit':120000,'fstatus':0,'stateRate':5},
  'expect':{'se':16955,'fed':16149,'state':6000,'total':39104}},
 {'inputs':{'profit':60000,'fstatus':1,'stateRate':0},
  'expect':{'se':8478,'fed':2614,'state':0,'total':11092}},
],
})

# ---------------- 6. s-corp-tax-savings-calculator (tax) ----------------
TOOLS.append({
'slug':'s-corp-tax-savings-calculator','name':'S-Corp Tax Savings Calculator','icon':'💰','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'S-Corp Tax Savings Calculator — LLC vs S-Corp Election',
'desc':'Compare LLC vs S-corp taxation: see how much self-employment tax an S-corp election could save you on a reasonable salary vs. distributions.',
'keywords':'S corp tax savings calculator, LLC vs S corp taxes, S corp election savings, reasonable salary S corp, self employment tax savings',
'h1':'S-Corp Tax Savings Calculator',
'intro':'An S-corp election splits profit into salary (payroll tax) and distributions (no SE tax). See your potential annual savings.',
'inputs':[
 {'id':'profit','label':'Annual Net Business Profit','value':150000,'prefix':'$','min':0},
 {'id':'salary','label':'Reasonable W-2 Salary','value':70000,'prefix':'$','min':0},
 {'id':'adminCost','label':'Extra Annual S-Corp Costs (payroll, CPA)','value':2000,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Annual Tax Savings</div>
<div class="mort-result-big" id="resSave">$0</div>
<div id="resWorth" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💼 LLC: SE Tax on Full Profit</span><span class="val" id="resLLC">$0</span></div>
<div class="mort-row"><span class="lbl">🏢 S-Corp: Payroll Tax on Salary</span><span class="val" id="resSCorp">$0</span></div>
<div class="mort-row"><span class="lbl">💸 Gross Tax Savings</span><span class="val" id="resGross">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Minus Extra Admin Costs</span><span class="val" id="resCost">$0</span></div>
<div class="mort-row"><span class="lbl">🛡️ Distributions (no SE tax)</span><span class="val" id="resDist">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How S-Corp Taxation Saves Money',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">As an LLC, every dollar of profit pays 15.3% self-employment tax. As an S-corp, you pay yourself a <strong>reasonable W-2 salary</strong> (payroll tax applies) and take the rest as <strong>distributions</strong> — which skip SE tax entirely. The spread is your savings.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Savings = 15.3% × (Profit − Salary) − Extra Admin Costs</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The catch: the IRS requires a <strong>reasonable salary</strong> for your role and industry — you cannot pay yourself $0. And S-corps add payroll processing, a separate tax return (Form 1120-S), and bookkeeping, typically <strong>$1,500–$3,000/year</strong>. The election usually makes sense around <strong>$60,000–$80,000</strong> in profit and up.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$150,000</strong> profit, <strong>$70,000</strong> salary. LLC SE tax on $150,000 ≈ <strong>$21,194</strong>. S-corp payroll tax (15.3% employer+employee share) on $70,000 ≈ <strong>$10,710</strong>. Gross savings = $21,194 − $10,710 = <strong>$10,484</strong>; minus $2,000 admin costs = <strong>$8,484 net annual savings</strong> — every year the election stays in place.</p>
'''+IRS_NOTE,
'faqs':[
 ('When should I elect S-corp taxation?','Common rule of thumb: consistent net profit above $60k–$80k. Below that, payroll and compliance costs often erase the SE tax savings. File Form 2553 by March 15 for the election to apply to the current year.'),
 ('What is a reasonable salary for an S-corp owner?','What you would pay an unrelated employee for the same work — check Bureau of Labor Statistics or industry salary data for your role and metro. Too-low salaries are a classic IRS audit trigger.'),
 ('Do S-corp distributions avoid all tax?','No — distributions avoid Social Security/Medicare tax but are still subject to income tax on your personal return. Only the 15.3% payroll/SE layer is saved.'),
 ('What are the downsides of an S-corp?','Payroll tax filings, Form 1120-S, stricter bookkeeping, required shareholder meetings/minutes, and less flexibility on health insurance deductions and retirement plan contributions for >2% owners.'),
 ('Can I switch back from S-corp to LLC taxation?','Yes, by revoking the election, but you generally must wait 5 years before re-electing S status. Talk to a CPA before switching.'),
],
'related':[
 ('llc-vs-scorp-calculator','LLC vs S-Corp Tax Savings','⚖️','Side-by-side entity comparison.'),
 ('llc-tax-calculator','LLC Tax Calculator','🏢','Full LLC tax bill breakdown.'),
 ('self-employment-tax-calculator','Self-Employment Tax Calculator','🧾','SE tax on any net earnings.'),
 ('paycheck-calculator','Paycheck Net Take-Home (2026)','💵','What the W-2 salary nets you.'),
 ('quarterly-tax-calculator','Quarterly Tax Calculator','📅','Estimate quarterly payments.'),
],
'js_core':FED_BRACKETS_JS+'''function core(p){
  var llc=seTaxF(p.profit).total;
  var scorpFica=p.salary*0.153;
  var gross=llc-scorpFica;
  var net=gross-p.adminCost;
  return {llc:llc,scorp:scorpFica,gross:gross,net:net,dist:Math.max(0,p.profit-p.salary),worth:net>0};
}''',
'js_glue':'''function recalc(){
  var p={profit:num('profit'),salary:num('salary'),adminCost:num('adminCost')};
  var r=core(p);
  setT('resSave',(r.net>=0?'':'−')+fmtM(Math.abs(r.net)));
  var w=document.getElementById('resWorth');
  w.textContent=r.worth?'✅ Election likely worth it':'❌ Costs outweigh savings';
  w.style.color=r.worth?'#34d399':'#f87171';
  setT('resLLC',fmtM(r.llc));setT('resSCorp',fmtM(r.scorp));setT('resGross',fmtM(r.gross));
  setT('resCost',fmtM(p.adminCost));setT('resDist',fmtM(r.dist));
  document.getElementById('shareText').textContent='S-corp savings on '+fmtM(p.profit)+': '+fmtM(r.net)+'/yr net';
}
['profit','salary','adminCost'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'profit':150000,'salary':70000,'adminCost':2000},
  'expect':{'llc':21194,'scorp':10710,'gross':10484,'net':8484}},
 {'inputs':{'profit':80000,'salary':60000,'adminCost':2500},
  'expect':{'llc':11304,'scorp':9180,'gross':2124,'net':-376}},
],
})

# ---------------- 7. self-employment-tax-calculator (tax) ----------------
TOOLS.append({
'slug':'self-employment-tax-calculator','name':'Self-Employment Tax Calculator','icon':'🧾','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'Self-Employment Tax Calculator — 15.3% SE Tax for 2026',
'desc':'Calculate 2026 self-employment tax: 15.3% on 92.35% of net earnings, Social Security wage base, and the deductible half. Free SE tax estimator.',
'keywords':'self employment tax calculator, SE tax rate 2026, 15.3 self employment tax, schedule SE calculator, freelancer tax',
'h1':'Self-Employment Tax Calculator',
'intro':'Freelancers and business owners pay both halves of Social Security and Medicare. Enter net earnings to see your SE tax and the deductible half.',
'inputs':[
 {'id':'net','label':'Net Earnings (profit after expenses)','value':80000,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Self-Employment Tax</div>
<div class="mort-result-big" id="resSE">$0</div>
<div id="resEff" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🏦 Social Security (12.4%)</span><span class="val" id="resSS">$0</span></div>
<div class="mort-row"><span class="lbl">🏥 Medicare (2.9%)</span><span class="val" id="resMed">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Taxable SE Base (92.35%)</span><span class="val" id="resBase">$0</span></div>
<div class="mort-row"><span class="lbl">✂️ Deductible Half (income tax)</span><span class="val" id="resHalf">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Self-Employment Tax Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">W-2 employees split payroll tax with their employer. When you work for yourself, you pay <strong>both halves</strong> — that is the self-employment tax, reported on Schedule SE.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">SE Tax = 15.3% × (Net Earnings × 92.35%)<br/>12.4% Social Security (up to $176,100 wage base) + 2.9% Medicare (no cap)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The 92.35% factor is the equivalent of the employer-half deduction employees get. And you may deduct <strong>half of your SE tax</strong> from income tax (an above-the-line deduction). High earners also face an extra 0.9% Medicare surtax above $200,000 single / $250,000 married.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$80,000</strong> net earnings → SE base = $80,000 × 92.35% = <strong>$73,880</strong>. Social Security = $73,880 × 12.4% = <strong>$9,161</strong>; Medicare = $73,880 × 2.9% = <strong>$2,143</strong>. Total SE tax = <strong>$11,304</strong>, and <strong>$5,652</strong> (half) is deductible against income tax. At $200,000 of earnings, the Social Security portion caps at the $176,100 wage base while Medicare keeps applying.</p>
'''+IRS_NOTE,
'faqs':[
 ('Who has to pay self-employment tax?','Anyone with $400+ in net self-employment earnings: freelancers, gig workers, sole proprietors, partners, and most LLC owners. It is separate from income tax — you owe both.'),
 ('What is the Social Security wage base for 2026?','Earnings above the annual wage base ($176,100 used in this calculator) are exempt from the 12.4% Social Security portion. The 2.9% Medicare portion has no cap.'),
 ('Can I deduct self-employment tax?','Half of your SE tax is deductible from gross income (above-the-line), lowering income tax. The SE tax itself is not reduced by the deduction.'),
 ('Do I pay SE tax on S-corp distributions?','No — that is the core S-corp advantage. Only the W-2 salary portion faces payroll tax; distributions are exempt from SE/payroll tax (but still subject to income tax).'),
 ('How do I pay SE tax during the year?','Through quarterly estimated payments (Form 1040-ES) or by increasing W-2 withholding at a day job. The annual total is reconciled on Schedule SE with your return.'),
],
'related':[
 ('freelance-tax-calculator','Freelance 1099 Tax Estimator','💼','Full freelance tax picture.'),
 ('quarterly-tax-calculator','Quarterly Tax Calculator','📅','Estimate quarterly payments.'),
 ('llc-tax-calculator','LLC Tax Calculator','🏢','LLC total tax breakdown.'),
 ('tax-refund-estimator','Tax Refund Estimator','💸','Project refund or balance due.'),
 ('s-corp-tax-savings-calculator','S-Corp Tax Savings Calculator','💰','Cut SE tax via S-corp election.'),
],
'js_core':FED_BRACKETS_JS+'''function core(p){
  var se=seTaxF(p.net);
  return {total:se.total,ss:se.ss,med:se.med,base:se.base,half:se.total/2,eff:p.net>0?se.total/p.net*100:0};
}''',
'js_glue':'''function recalc(){
  var r=core({net:num('net')});
  setT('resSE',fmtM(r.total));
  setT('resEff','Effective '+fmtP(r.eff,1)+'% of net earnings');
  setT('resSS',fmtM(r.ss));setT('resMed',fmtM(r.med));setT('resBase',fmtM(r.base));setT('resHalf',fmtM(r.half));
  document.getElementById('shareText').textContent='SE tax on '+fmtM(num('net'))+': '+fmtM(r.total);
}
document.getElementById('net').addEventListener('input',recalc);
recalc();''',
'tests':[
 {'inputs':{'net':80000},'expect':{'total':11304,'ss':9161,'med':2143,'base':73880}},
 {'inputs':{'net':200000},'expect':{'total':27193,'ss':21836,'med':5356,'base':184700}},
],
})

# ---------------- 8. quarterly-tax-calculator (tax) ----------------
TOOLS.append({
'slug':'quarterly-tax-calculator','name':'Quarterly Tax Calculator','icon':'📅','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'Quarterly Tax Calculator — Estimated Payments (1040-ES) 2026',
'desc':'Calculate 2026 quarterly estimated tax payments for freelancers and business owners, including the IRS safe harbor rule to avoid underpayment penalties.',
'keywords':'quarterly tax calculator, estimated tax payments 2026, 1040-ES calculator, safe harbor rule, freelancer quarterly taxes',
'h1':'Quarterly Tax Calculator',
'intro':'Self-employed? The IRS wants pay-as-you-go. Estimate each quarterly 1040-ES payment and check the safe harbor.',
'inputs':[
 {'id':'profit','label':'Expected Annual Net Profit','value':100000,'prefix':'$','min':0},
 {'id':'fstatus','label':'Filing Status','type':'select','options':[['0','Single'],['1','Married Filing Jointly']]},
 {'id':'priorTax','label':'Prior Year Total Tax','value':12000,'prefix':'$','min':0},
 {'id':'highAGI','label':'Prior-Year AGI Over $150k?','type':'select','options':[['0','No'],['1','Yes']]},
 {'id':'withheld','label':'Already Withheld / Paid This Year','value':8000,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Quarterly Payment</div>
<div class="mort-result-big" id="resQ">$0</div>
<div id="resDue" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;">Due Apr 15 • Jun 15 • Sep 15 • Jan 15</div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🧾 Est. Total Annual Tax</span><span class="val" id="resTotal">$0</span></div>
<div class="mort-row"><span class="lbl">🛡️ Safe Harbor Target</span><span class="val" id="resSafe">$0</span></div>
<div class="mort-row"><span class="lbl">💵 Required Annual Payments</span><span class="val" id="resReq">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Remaining After Withholding</span><span class="val" id="resRem">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Quarterly Estimated Taxes Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">The US taxes income <strong>pay-as-you-go</strong>. Without an employer withholding for you, the IRS expects four estimated payments (Form 1040-ES) — miss them and you can owe an underpayment penalty even if you pay in full at filing time.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Safe Harbor Rule</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">You avoid penalties by paying the <strong>lesser</strong> of: <strong>90% of this year\'s tax</strong>, or <strong>100% of last year\'s tax</strong> (110% if prior-year AGI exceeded $150,000). This calculator estimates your total tax (SE + income), computes both targets, and divides the smaller — minus what you have already paid — into four payments.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Single freelancer expecting <strong>$100,000</strong> profit, prior-year tax <strong>$12,000</strong>, <strong>$8,000</strong> already withheld. SE tax ≈ $14,130; income tax ≈ $12,060 → total ≈ <strong>$26,189</strong>. 90% of current = $23,570; safe harbor = 110% × $12,000 = <strong>$13,200</strong>. Pay the smaller: ($13,200 − $8,000) ÷ 4 = <strong>$1,300 per quarter</strong> — penalty-proof even though the true bill is higher.</p>
'''+IRS_NOTE,
'faqs':[
 ('When are quarterly taxes due?','Typically April 15, June 15, September 15, and January 15 of the following year. If a date falls on a weekend or holiday, the deadline shifts to the next business day.'),
 ('What is the underpayment penalty?','The IRS charges interest (the federal rate, adjusted quarterly — recently around 8%) on the shortfall for the period it was unpaid. Safe-harbor payments avoid it entirely.'),
 ('Who must pay quarterly estimated tax?','Generally anyone expecting to owe $1,000+ at filing after withholding and credits — freelancers, landlords, investors, and retirees with untaxed income.'),
 ('What if my income is uneven?','You can use the annualized income installment method (Schedule AI) to match payments to when income was actually earned — useful for seasonal businesses.'),
 ('Can I just increase W-2 withholding instead?','Yes. Withholding is treated as paid evenly all year even if increased in December — a legitimate year-end catch-up strategy if you also hold a W-2 job.'),
],
'related':[
 ('freelance-tax-calculator','Freelance 1099 Tax Estimator','💼','Full freelance tax picture.'),
 ('self-employment-tax-calculator','Self-Employment Tax Calculator','🧾','SE tax component explained.'),
 ('tax-refund-estimator','Tax Refund Estimator','💸','Project refund or balance due.'),
 ('paycheck-calculator','Paycheck Net Take-Home (2026)','💵','W-2 withholding alternative.'),
 ('llc-tax-calculator','LLC Tax Calculator','🏢','LLC total tax breakdown.'),
],
'js_core':FED_BRACKETS_JS+'''function core(p){
  var married=p.fstatus==1;
  var se=seTaxF(p.profit).total;
  var taxable=Math.max(0,p.profit-se/2-(married?30000:15000));
  var fed=fedTax(taxable,married);
  var total=se+fed;
  var safe=p.priorTax*(p.highAGI==1?1.10:1.00);
  var req=Math.min(total*0.90,safe);
  var rem=Math.max(0,req-p.withheld);
  return {total:total,safe:safe,req:req,rem:rem,q:rem/4,se:se,fed:fed};
}''',
'js_glue':'''function recalc(){
  var p={profit:num('profit'),fstatus:parseInt(document.getElementById('fstatus').value),priorTax:num('priorTax'),highAGI:parseInt(document.getElementById('highAGI').value),withheld:num('withheld')};
  var r=core(p);
  setT('resQ',fmtM(r.q));
  setT('resTotal',fmtM(r.total));setT('resSafe',fmtM(r.safe));
  setT('resReq',fmtM(r.req));setT('resRem',fmtM(r.rem));
  document.getElementById('shareText').textContent='Quarterly estimated payment '+fmtM(r.q)+' (safe harbor '+fmtM(r.safe)+')';
}
['profit','priorTax','withheld'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
['fstatus','highAGI'].forEach(function(id){document.getElementById(id).addEventListener('change',recalc);});
recalc();''',
'tests':[
 {'inputs':{'profit':100000,'fstatus':0,'priorTax':12000,'highAGI':0,'withheld':8000},
  'expect':{'total':26189,'safe':12000,'q':1000}},
 {'inputs':{'profit':100000,'fstatus':0,'priorTax':12000,'highAGI':1,'withheld':8000},
  'expect':{'safe':13200,'q':1300}},
],
})

# ---------------- 9. roth-ira-conversion-calculator (tax) ----------------
TOOLS.append({
'slug':'roth-ira-conversion-calculator','name':'Roth IRA Conversion Calculator','icon':'🔄','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'Roth IRA Conversion Calculator — Pay Tax Now or Later?',
'desc':'Compare converting a traditional IRA to Roth: upfront tax cost vs. tax-free growth. See the breakeven and which future tax rate favors conversion.',
'keywords':'Roth IRA conversion calculator, Roth conversion tax, convert traditional IRA to Roth, Roth vs traditional IRA, backdoor Roth',
'h1':'Roth IRA Conversion Calculator',
'intro':'A Roth conversion means paying income tax today for tax-free growth forever. Model the tradeoff with your own rates and timeline.',
'inputs':[
 {'id':'amount','label':'Amount to Convert','value':50000,'prefix':'$','min':0},
 {'id':'curRate','label':'Current Marginal Tax Rate (%)','value':24,'suffix':'%','min':0,'max':50,'step':1},
 {'id':'futRate','label':'Expected Tax Rate at Withdrawal (%)','value':28,'suffix':'%','min':0,'max':50,'step':1},
 {'id':'years','label':'Years Until Withdrawal','value':20,'min':1,'max':50},
 {'id':'ret','label':'Expected Annual Return (%)','value':7,'suffix':'%','min':0,'max':15,'step':0.1},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Tax Due on Conversion</div>
<div class="mort-result-big" id="resTax">$0</div>
<div id="resVerdict" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🌱 Roth Value (tax-free) in N Years</span><span class="val" id="resRoth">$0</span></div>
<div class="mort-row"><span class="lbl">🏦 Traditional Value (after tax)</span><span class="val" id="resTrad">$0</span></div>
<div class="mort-row"><span class="lbl">⚖️ Roth Advantage</span><span class="val" id="resAdv">$0</span></div>
<div class="mort-row"><span class="lbl">💡 Breakeven Future Rate</span><span class="val" id="resBE">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Roth Conversions Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Converting means moving money from a pre-tax traditional IRA to a Roth IRA and paying ordinary income tax on the converted amount this year. After that, growth and qualified withdrawals are <strong>100% tax-free</strong> — no required minimum distributions, ever.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Core Math</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">If your tax rate never changed, converting would be exactly neutral: pay 24% now on $50,000 ($12,000) and $38,000 grows tax-free, versus $50,000 growing and paying 24% at the end — identical results. Conversion <strong>wins when your future rate is higher</strong> than today\'s (common if you convert in a low-income year, early retirement gap years, or expect higher future brackets) and loses when it is lower.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Convert <strong>$50,000</strong> at a <strong>24%</strong> marginal rate → tax due <strong>$12,000</strong>. $38,000 growing at 7% for 20 years = $38,000 × (1.07)<sup>20</sup> ≈ <strong>$147,048</strong> tax-free. If left traditional and withdrawn at 28%: $50,000 × (1.07)<sup>20</sup> × (1 − 0.28) ≈ <strong>$139,308</strong>. Roth advantage ≈ <strong>$7,740</strong>. Pay the conversion tax from <strong>outside</strong> funds (not from the IRA) to maximize the benefit.</p>
'''+IRS_NOTE,
'faqs':[
 ('Is there income limit on Roth conversions?','No. Anyone can convert any amount — income limits apply to Roth contributions, not conversions. High earners use this via the "backdoor Roth" (nondeductible traditional contribution, then convert).'),
 ('When is the best time to do a Roth conversion?','Low-income years: early retirement before Social Security/RMDs, a sabbatical, a job loss year, or any year your marginal rate dips. Fill up your current bracket without spilling into the next.'),
 ('Do I pay a penalty on Roth conversions?','No 10% early-withdrawal penalty on conversions at any age (it is not a distribution). But each conversion has a 5-year clock before earnings can be withdrawn penalty-free if you are under 59½.'),
 ('Can I undo (recharacterize) a Roth conversion?','No — recharacterizations were eliminated by the 2017 Tax Cuts and Jobs Act. Conversions are irreversible, so model carefully first.'),
 ('Will a conversion affect my Medicare premiums?','Yes, potentially. The converted amount raises your MAGI, which can trigger IRMAA surcharges on Medicare Parts B and D two years later. Large conversions near age 63+ deserve extra planning.'),
],
'related':[
 ('roth-ira-calculator','Roth IRA Tax-Free Growth','📈','Project Roth contributions to retirement.'),
 ('roth-conversion-calculator','Roth Conversion Tax','🔄','Quick Roth conversion tax check.'),
 ('retirement-401k','401(k) Retirement Savings','🏖️','Project pre-tax 401(k) growth.'),
 ('capital-gains-tax-calculator','Capital Gains Tax (2026)','🏛️','Tax on taxable-account gains.'),
 ('401k-rmd-calculator','401(k) & IRA RMD (2026)','📅','RMDs conversions can reduce.'),
],
'js_core':'''function core(p){
  var tax=p.amount*p.curRate/100;
  var net=p.amount-tax;
  var g=Math.pow(1+p.ret/100,p.years);
  var roth=net*g;
  var trad=p.amount*g*(1-p.futRate/100);
  var adv=roth-trad;
  return {tax:tax,roth:roth,trad:trad,adv:adv,be:p.curRate,win:adv>0};
}''',
'js_glue':'''function recalc(){
  var p={amount:num('amount'),curRate:num('curRate'),futRate:num('futRate'),years:num('years'),ret:num('ret')};
  var r=core(p);
  setT('resTax',fmtM(r.tax));
  var v=document.getElementById('resVerdict');
  v.textContent=r.win?'✅ Conversion wins at these rates':'❌ Keeping traditional wins at these rates';
  v.style.color=r.win?'#34d399':'#f87171';
  setT('resRoth',fmtM(r.roth));setT('resTrad',fmtM(r.trad));
  setT('resAdv',(r.adv>=0?'+':'−')+fmtM(Math.abs(r.adv)));
  setT('resBE',fmtP(p.curRate,0)+' — convert if future rate is higher');
  document.getElementById('shareText').textContent='Roth conversion of '+fmtM(p.amount)+': tax '+fmtM(r.tax)+', advantage '+fmtM(r.adv);
}
['amount','curRate','futRate','years','ret'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'amount':50000,'curRate':24,'futRate':28,'years':20,'ret':7},
  'expect':{'tax':12000,'roth':147048,'trad':139308,'adv':7740}},
 {'inputs':{'amount':100000,'curRate':32,'futRate':24,'years':15,'ret':6},
  'expect':{'tax':32000,'roth':162966,'trad':182138,'adv':-19173}},
],
})

# ---------------- 10. bonus-tax-calculator (tax) ----------------
TOOLS.append({
'slug':'bonus-tax-calculator','name':'Bonus Tax Calculator','icon':'🎁','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'Bonus Tax Calculator — How Much of Your Bonus You Keep',
'desc':'Bonuses are withheld at a flat 22% federal supplemental rate. Calculate federal, Social Security, Medicare, and state tax on your bonus.',
'keywords':'bonus tax calculator, how are bonuses taxed, supplemental wage withholding 22%, bonus paycheck calculator',
'h1':'Bonus Tax Calculator',
'intro':'That $10,000 bonus is not $10,000. See exactly what federal, FICA, and state take — and what lands in your account.',
'inputs':[
 {'id':'bonus','label':'Gross Bonus Amount','value':10000,'prefix':'$','min':0},
 {'id':'stateRate','label':'State Income Tax Rate (%)','value':5,'suffix':'%','min':0,'max':15,'step':0.1},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Net Bonus (Take-Home)</div>
<div class="mort-result-big" id="resNet">$0</div>
<div id="resKeep" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🏛️ Federal (22% supplemental)</span><span class="val" id="resFed">$0</span></div>
<div class="mort-row"><span class="lbl">🏦 Social Security (6.2%)</span><span class="val" id="resSS">$0</span></div>
<div class="mort-row"><span class="lbl">🏥 Medicare (1.45%)</span><span class="val" id="resMed">$0</span></div>
<div class="mort-row"><span class="lbl">🗺️ State Income Tax</span><span class="val" id="resState">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Total Withheld</span><span class="val" id="resTot">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Bonuses Are Taxed',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">The IRS classifies bonuses as <strong>supplemental wages</strong> — taxed at the same rates as salary, but <em>withheld</em> differently. Employers usually apply the flat <strong>22% federal supplemental rate</strong> (37% on amounts over $1 million in a year) instead of your W-4 bracket rate.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Withholding Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Net = Bonus − 22% Federal − 6.2% SS − 1.45% Medicare − State Tax</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Important: 22% is just <strong>withholding</strong>, not your final tax. The bonus still joins your total income on your return — if your marginal rate is 24%, you will owe the extra 2% at filing; if it is 12%, you get the difference back as a refund.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$10,000</strong> bonus, 5% state tax: federal = <strong>$2,200</strong>, Social Security = <strong>$620</strong>, Medicare = <strong>$145</strong>, state = <strong>$500</strong>. Total withheld = $3,465 → net bonus <strong>$6,535</strong> (you keep 65.35%). High earners past the $176,100 Social Security wage base keep the 6.2% too.</p>
'''+IRS_NOTE,
'faqs':[
 ('Why is my bonus taxed at 22%?','The IRS lets employers withhold a flat 22% on supplemental wages up to $1 million instead of using your W-4 tables. It is simpler for payroll — but it is withholding, not your final tax rate.'),
 ('Are bonuses taxed higher than salary?','No. Bonus income is ordinary income taxed at your normal marginal bracket. The 22% flat withholding only determines what is taken upfront; your return reconciles the difference.'),
 ('How can I reduce tax on a bonus?','Time it into a 401(k) contribution (if your plan allows bonus deferrals), increase HSA contributions, or bunch deductions. You cannot change the withholding rate your employer uses.'),
 ('What about bonuses over $1 million?','Supplemental wages above $1 million in a calendar year must be withheld at 37% (the top bracket) — mandatory, no exceptions.'),
 ('Do bonuses count toward Social Security?','Yes, up to the annual wage base ($176,100). Bonuses paid after you have passed the cap are exempt from the 6.2% Social Security portion.'),
],
'related':[
 ('paycheck-calculator','Paycheck Net Take-Home (2026)','💵','Full paycheck after-tax breakdown.'),
 ('tax-withholding','Tax Withholding (2026)','🏛️','Federal withholding per paycheck.'),
 ('w-4-withholding-calculator','W-4 Withholding Calculator','📝','Check your W-4 accuracy.'),
 ('rsu-tax-calculator','RSU Tax Calculator','📊','Tax on vested stock grants.'),
 ('tax-refund-estimator','Tax Refund Estimator','💸','Project refund or balance due.'),
],
'js_core':'''function core(p){
  var fed=p.bonus*0.22;
  var ss=p.bonus*0.062;
  var med=p.bonus*0.0145;
  var state=p.bonus*p.stateRate/100;
  var tot=fed+ss+med+state;
  return {fed:fed,ss:ss,med:med,state:state,tot:tot,net:p.bonus-tot,keep:p.bonus>0?(p.bonus-tot)/p.bonus*100:0};
}''',
'js_glue':'''function recalc(){
  var p={bonus:num('bonus'),stateRate:num('stateRate')};
  var r=core(p);
  setT('resNet',fmtM(r.net));
  setT('resKeep','You keep '+fmtP(r.keep,1)+' of the bonus');
  setT('resFed',fmtM(r.fed));setT('resSS',fmtM(r.ss));setT('resMed',fmtM(r.med));
  setT('resState',fmtM(r.state));setT('resTot',fmtM(r.tot));
  document.getElementById('shareText').textContent='Net bonus on '+fmtM(p.bonus)+': '+fmtM(r.net);
}
['bonus','stateRate'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'bonus':10000,'stateRate':5},'expect':{'fed':2200,'ss':620,'med':145,'state':500,'net':6535}},
 {'inputs':{'bonus':25000,'stateRate':0},'expect':{'fed':5500,'ss':1550,'med':362.5,'net':17587.5}},
],
})

# ---------------- 11. rsu-tax-calculator (tax) ----------------
TOOLS.append({
'slug':'rsu-tax-calculator','name':'RSU Tax Calculator','icon':'📊','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'RSU Tax Calculator — Tax on Vested Restricted Stock Units',
'desc':'Calculate tax on vested RSUs: ordinary income at vest, supplemental withholding, and your cost basis for future capital gains. Free RSU tax estimator.',
'keywords':'RSU tax calculator, restricted stock units tax, RSU vesting tax, how are RSUs taxed, sell to cover RSU',
'h1':'RSU Tax Calculator',
'intro':'RSUs are taxed as ordinary income the moment they vest. Enter your vest details to see the tax hit and your after-tax value.',
'inputs':[
 {'id':'shares','label':'Shares Vesting','value':200,'min':0},
 {'id':'price','label':'Stock Price at Vest','value':150,'prefix':'$','min':0},
 {'id':'whRate','label':'Supplemental Withholding Rate (%)','value':22,'suffix':'%','min':0,'max':50,'step':1},
 {'id':'stateRate','label':'State Income Tax Rate (%)','value':5,'suffix':'%','min':0,'max':15,'step':0.1},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">After-Tax Vest Value</div>
<div class="mort-result-big" id="resNet">$0</div>
<div id="resKeep" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💰 Gross Vest Value</span><span class="val" id="resGross">$0</span></div>
<div class="mort-row"><span class="lbl">🏛️ Federal Withholding</span><span class="val" id="resFed">$0</span></div>
<div class="mort-row"><span class="lbl">🏦 Social Security (6.2%)</span><span class="val" id="resSS">$0</span></div>
<div class="mort-row"><span class="lbl">🏥 Medicare (1.45%)</span><span class="val" id="resMed">$0</span></div>
<div class="mort-row"><span class="lbl">🗺️ State Tax</span><span class="val" id="resState">$0</span></div>
<div class="mort-row"><span class="lbl">📏 Cost Basis / Share (for future sale)</span><span class="val" id="resBasis">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How RSUs Are Taxed',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Restricted Stock Units are a promise of future shares. Nothing is taxed at grant — the taxable event is <strong>vesting</strong>, when shares land in your account. The full market value at vest is ordinary (W-2) income, exactly like a cash bonus.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Vest Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Taxable Income = Shares × Price at Vest<br/>Net = Value − Federal − SS − Medicare − State</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Most employers <strong>sell to cover</strong>: they liquidate enough shares to cover withholding (often at the 22% supplemental rate) and deposit the rest. Crucially, your <strong>cost basis becomes the vest price</strong> — if you later sell higher, only the gain above vest price faces capital gains tax.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>200 shares</strong> vest at <strong>$150</strong> = <strong>$30,000</strong> of ordinary income. Withholding: federal 22% = <strong>$6,600</strong>, Social Security = <strong>$1,860</strong>, Medicare = <strong>$435</strong>, state 5% = <strong>$1,500</strong>. After-tax value ≈ <strong>$19,605</strong>, and each retained share carries a $150 cost basis going forward.</p>
'''+IRS_NOTE,
'faqs':[
 ('Are RSUs taxed at vest or at grant?','At vest. Grants are not taxable. When shares vest, the fair market value is taxed as ordinary income even if you do not sell a single share.'),
 ('What does "sell to cover" mean?','Your employer automatically sells enough vested shares to cover tax withholding and delivers the remaining shares to you. It is the most common RSU tax method.'),
 ('Do I owe more tax if I sell RSUs later?','Only on gains above your vest-price cost basis. Sell within a year: short-term capital gains (ordinary rates). Hold over a year: long-term rates (0/15/20%).'),
 ('What happens to RSUs if I leave the company?','Unvested RSUs are typically forfeited when you leave (some plans accelerate on acquisition or retirement). Vested shares are yours to keep.'),
 ('Are RSUs subject to Social Security tax?','Yes — RSU income counts as wages for Social Security (up to the wage base) and Medicare in the year of vesting.'),
],
'related':[
 ('capital-gains-tax-calculator','Capital Gains Tax (2026)','🏛️','Tax when you sell vested shares.'),
 ('paycheck-calculator','Paycheck Net Take-Home (2026)','💵','Full paycheck after-tax breakdown.'),
 ('bonus-tax-calculator','Bonus Tax Calculator','🎁','Supplemental wage withholding.'),
 ('freelance-tax-calculator','Freelance 1099 Tax Estimator','💼','For side income beyond salary.'),
 ('tax-refund-estimator','Tax Refund Estimator','💸','Project refund or balance due.'),
],
'js_core':'''function core(p){
  var gross=p.shares*p.price;
  var fed=gross*p.whRate/100;
  var ss=gross*0.062;
  var med=gross*0.0145;
  var state=gross*p.stateRate/100;
  var tot=fed+ss+med+state;
  return {gross:gross,fed:fed,ss:ss,med:med,state:state,tot:tot,net:gross-tot,basis:p.price,keep:gross>0?(gross-tot)/gross*100:0};
}''',
'js_glue':'''function recalc(){
  var p={shares:num('shares'),price:num('price'),whRate:num('whRate'),stateRate:num('stateRate')};
  var r=core(p);
  setT('resNet',fmtM(r.net));
  setT('resKeep','You keep '+fmtP(r.keep,1)+' of vest value');
  setT('resGross',fmtM(r.gross));setT('resFed',fmtM(r.fed));setT('resSS',fmtM(r.ss));
  setT('resMed',fmtM(r.med));setT('resState',fmtM(r.state));
  setT('resBasis',fmtM(r.basis));
  document.getElementById('shareText').textContent='RSU vest '+fmtM(r.gross)+': after-tax '+fmtM(r.net);
}
['shares','price','whRate','stateRate'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'shares':200,'price':150,'whRate':22,'stateRate':5},
  'expect':{'gross':30000,'fed':6600,'ss':1860,'med':435,'state':1500,'net':19605}},
 {'inputs':{'shares':50,'price':400,'whRate':37,'stateRate':10},
  'expect':{'gross':20000,'fed':7400,'ss':1240,'med':290,'state':2000,'net':9070}},
],
})

# ---------------- 12. tax-refund-estimator (tax) ----------------
TOOLS.append({
'slug':'tax-refund-estimator','name':'Tax Refund Estimator','icon':'💸','cat':'tax','cat_label':'TAX',
'hub':'/tax-calculators','hub_title':'Tax Calculators',
'hub_blurb':'Browse all tax estimators: income, self-employment, and credits.',
'title':'Tax Refund Estimator — Will You Get a Refund in 2026?',
'desc':'Estimate your 2026 federal tax refund or balance due: enter income, withholding, and credits to see if a refund or a bill is coming.',
'keywords':'tax refund estimator 2026, how much refund will I get, tax refund calculator, will I owe taxes, federal refund estimate',
'h1':'Tax Refund Estimator',
'intro':'Refund or bill? Enter your income, total withholding, and credits to project your 2026 federal tax outcome.',
'inputs':[
 {'id':'salary','label':'Annual Gross Income','value':90000,'prefix':'$','min':0},
 {'id':'fstatus','label':'Filing Status','type':'select','options':[['0','Single'],['1','Married Filing Jointly']]},
 {'id':'pretax','label':'Pre-Tax Deductions (401k, HSA)','value':6000,'prefix':'$','min':0},
 {'id':'withheld','label':'Total Federal Withheld / Paid','value':14000,'prefix':'$','min':0},
 {'id':'credits','label':'Tax Credits (child, education, etc.)','value':2000,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Projected Outcome</div>
<div class="mort-result-big" id="resOut">$0</div>
<div id="resOutSub" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🧾 Total Tax Liability</span><span class="val" id="resTax">$0</span></div>
<div class="mort-row"><span class="lbl">💵 Already Paid (withholding)</span><span class="val" id="resPaid">$0</span></div>
<div class="mort-row"><span class="lbl">🎟️ Credits Applied</span><span class="val" id="resCred">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Taxable Income</span><span class="val" id="resTaxable">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Effective Tax Rate</span><span class="val" id="resEff">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Tax Refunds Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">A "refund" is not a bonus — it is the IRS returning <strong>your own overpayment</strong>. Your outcome is simple arithmetic: total tax liability minus everything you already paid.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Refund (or Owed) = Withholding + Estimates − (Income Tax − Credits)<br/>Positive = refund · Negative = amount owed</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Tax credits are the biggest swing factor: unlike deductions (which reduce taxable income), credits reduce your tax <strong>dollar-for-dollar</strong>. The Child Tax Credit (up to $2,000 per child) and education credits often flip a small bill into a refund.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Single filer, <strong>$90,000</strong> income, <strong>$6,000</strong> pre-tax deductions, <strong>$14,000</strong> withheld, <strong>$2,000</strong> in credits. Taxable = $90,000 − $6,000 − $15,000 = $69,000 → tax ≈ <strong>$10,094</strong> → minus $2,000 credits = <strong>$8,094</strong> liability. Refund = $14,000 − $8,094 = <strong>$5,906</strong>. Nice check — but it also means $5,906 sat with the IRS interest-free all year.</p>
'''+IRS_NOTE,
'faqs':[
 ('When will I get my tax refund?','E-filed returns with direct deposit typically arrive within 21 days. Paper returns take 6–8 weeks. Returns claiming EITC or the Additional Child Tax Credit are held until mid-February by law.'),
 ('Is it better to get a refund or owe?','Ideally neither — a refund near $0 means your withholding was perfectly tuned and you kept your money all year. Large refunds are interest-free loans to the IRS.'),
 ('What if I cannot pay what I owe?','File on time anyway to avoid the failure-to-file penalty (5%/month), then set up an IRS payment plan (Form 9465). The failure-to-pay penalty (0.5%/month) still accrues but is far smaller.'),
 ('Do tax credits increase my refund?','Refundable credits (like EITC and part of the Child Tax Credit) can generate a refund beyond what you paid in. Nonrefundable credits can only reduce your tax to zero.'),
 ('How do I track my refund?','Use the IRS "Where\'s My Refund?" tool at irs.gov — updated daily, usually showing status 24 hours after e-filing.'),
],
'related':[
 ('paycheck-calculator','Paycheck Net Take-Home (2026)','💵','Full paycheck after-tax breakdown.'),
 ('tax-withholding','Tax Withholding (2026)','🏛️','Federal withholding per paycheck.'),
 ('w-4-withholding-calculator','W-4 Withholding Calculator','📝','Tune withholding to kill the bill.'),
 ('child-tax-credit-calculator','Child Tax Credit & EITC','👶','Credits that boost refunds.'),
 ('freelance-tax-calculator','Freelance 1099 Tax Estimator','💼','For self-employment income.'),
],
'js_core':FED_BRACKETS_JS+'''function core(p){
  var married=p.fstatus==1;
  var taxable=Math.max(0,p.salary-p.pretax-(married?30000:15000));
  var tax=Math.max(0,fedTax(taxable,married)-p.credits);
  var diff=p.withheld-tax;
  return {tax:tax,diff:diff,taxable:taxable,refund:diff>=0,eff:p.salary>0?tax/p.salary*100:0};
}''',
'js_glue':'''function recalc(){
  var p={salary:num('salary'),fstatus:parseInt(document.getElementById('fstatus').value),pretax:num('pretax'),withheld:num('withheld'),credits:num('credits')};
  var r=core(p);
  setT('resOut',fmtM(Math.abs(r.diff)));
  var s=document.getElementById('resOutSub');
  s.textContent=r.refund?'🎉 Refund coming your way':'⚠️ Balance due at filing';
  s.style.color=r.refund?'#34d399':'#f87171';
  setT('resTax',fmtM(r.tax));setT('resPaid',fmtM(p.withheld));setT('resCred',fmtM(p.credits));
  setT('resTaxable',fmtM(r.taxable));setT('resEff',fmtP(r.eff,1));
  document.getElementById('shareText').textContent='Projected '+(r.refund?'refund ':'balance due ')+fmtM(Math.abs(r.diff));
}
['salary','pretax','withheld','credits'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('fstatus').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'salary':90000,'fstatus':0,'pretax':6000,'withheld':14000,'credits':2000},
  'expect':{'tax':8094,'diff':5906,'taxable':69000}},
 {'inputs':{'salary':60000,'fstatus':0,'pretax':0,'withheld':5000,'credits':0},
  'expect':{'tax':5161.5,'diff':-161.5,'taxable':45000}},
],
})

MORT_JS = '''function piFactor(ratePct,years){
  var r=ratePct/100/12,n=years*12;
  return r>0?r*Math.pow(1+r,n)/(Math.pow(1+r,n)-1):1/n;
}'''

# ---------------- 13. house-affordability-calculator (real-estate) ----------------
TOOLS.append({
'slug':'house-affordability-calculator','name':'House Affordability Calculator','icon':'🏡','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'House Affordability Calculator — How Much House Can I Afford?',
'desc':'How much house can you afford? Uses the 28/36 rule with your income, debts, down payment, rate, taxes, and insurance to find your max home price.',
'keywords':'how much house can I afford, home affordability calculator, 28/36 rule, max mortgage calculator, house price based on income',
'h1':'House Affordability Calculator',
'intro':'Lenders cap housing costs with the 28/36 rule. Enter your income, debts, and down payment to find your maximum home price.',
'inputs':[
 {'id':'income','label':'Annual Gross Income','value':120000,'prefix':'$','min':0},
 {'id':'debts','label':'Monthly Debt Payments (car, student, cards)','value':800,'prefix':'$','min':0},
 {'id':'down','label':'Down Payment Available','value':60000,'prefix':'$','min':0},
 {'id':'rate','label':'Mortgage Rate (%)','value':6.8,'suffix':'%','min':0,'max':15,'step':0.05},
 {'id':'term','label':'Loan Term (years)','value':30,'min':10,'max':30},
 {'id':'taxRate','label':'Property Tax Rate (%/year)','value':1.1,'suffix':'%','min':0,'max':5,'step':0.05},
 {'id':'ins','label':'Home Insurance ($/year)','value':1800,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Maximum Home Price</div>
<div class="mort-result-big" id="resPrice">$0</div>
<div id="resPriceSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🏦 Max Loan Amount</span><span class="val" id="resLoan">$0</span></div>
<div class="mort-row"><span class="lbl">💳 Principal & Interest /mo</span><span class="val" id="resPI">$0</span></div>
<div class="mort-row"><span class="lbl">🏛️ Property Tax /mo</span><span class="val" id="resTax">$0</span></div>
<div class="mort-row"><span class="lbl">🛡️ Insurance /mo</span><span class="val" id="resIns">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Total PITI /mo</span><span class="val" id="resPITI">$0</span></div>
<div class="mort-row"><span class="lbl">🎯 Housing Budget /mo (28%)</span><span class="val" id="resBudget">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Much House Can You Afford?',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Affordability is not about the sticker price — it is about the monthly payment. Lenders work backwards from your income using the <strong>28/36 rule</strong>, and this calculator does the same math in reverse.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The 28/36 Rule</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Your housing payment (PITI: principal, interest, taxes, insurance) should not exceed <strong>28% of gross monthly income</strong>, and all debts combined should stay under <strong>36%</strong>. Your housing budget is the smaller of (28% of income) and (36% of income minus other debts). The calculator then solves for the home price whose PITI exactly fills that budget, accounting for your down payment, rate, tax rate, and insurance.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$120,000</strong> income, <strong>$800/mo</strong> debts, <strong>$60,000</strong> down, 6.8% 30-year rate, 1.1% property tax, $1,800/yr insurance. Housing budget = min(28% × $10,000, 36% × $10,000 − $800) = <strong>$2,800/mo</strong>. Solving PITI = $2,800 gives a max price of about <strong>$409,000</strong> — a $349,000 loan with $2,275 P&I, $375 tax, and $150 insurance per month.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">How to Use This Calculator</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Use gross (pre-tax) income and list every recurring debt minimum. Remember the result is a <strong>ceiling, not a target</strong> — buying 10–20% below your max leaves room for maintenance (budget ~1% of home value per year), rate changes on ARMs, and life. A bigger down payment is the fastest way to raise your max price without raising risk.</p>''',
'faqs':[
 ('What is the 28/36 rule?','Spend no more than 28% of gross monthly income on housing (PITI) and no more than 36% on all debts combined. Conventional lenders use it as the benchmark, though programs like FHA allow higher ratios.'),
 ('How much house can I afford on $100k salary?','Roughly $350k–$400k with 20% down at 2026 rates and modest debts — but debts, taxes, and insurance swing it widely. Run your exact numbers above.'),
 ('Should I buy at my maximum approval amount?','Usually not. Lenders approve the max you can service, not the max that keeps you comfortable. Most advisors suggest housing at 25% or less of take-home pay.'),
 ('Does a bigger down payment increase affordability?','Yes, twice: it shrinks the loan (lower P&I) and avoids PMI below 20% down, which effectively raises the price you can carry on the same monthly budget.'),
 ('What costs do first-time buyers forget?','Closing costs (2–5% of price), moving, immediate repairs, and ongoing maintenance (~1% of value/year). Keep an emergency fund separate from your down payment.'),
],
'related':[
 ('mortgage-calculator','Mortgage Calculator','🏠','Monthly PITI payment and amortization.'),
 ('dti-calculator','Debt-to-Income (DTI)','⚖️','Quick DTI check for qualification.'),
 ('dti-calculator','Debt-to-Income (DTI) Calculator','⚖️','Front-end and back-end DTI detail.'),
 ('rent-vs-buy','Rent vs Buy Decision','⚖️','Compare renting vs buying.'),
 ('closing-costs-calculator','Home Closing Costs','🏡','Estimate purchase closing costs.'),
],
'js_core':MORT_JS+'''function core(p){
  var f=piFactor(p.rate,p.term);
  var budget=Math.min(p.income/12*0.28,p.income/12*0.36-p.debts);
  budget=Math.max(0,budget);
  var slope=f+p.taxRate/100/12;
  var price=Math.max(p.down,budget*120);
  for(var i=0;i<60;i++){
    var taxMo=price*p.taxRate/100/12,insMo=p.ins/12;
    var loan=Math.max(0,price-p.down);
    var piti=loan*f+taxMo+insMo;
    price+=(budget-piti)/slope;
    if(price<0){price=0;break;}
  }
  var loan=Math.max(0,price-p.down);
  var pi=loan*f,taxMo=price*p.taxRate/100/12,insMo=p.ins/12;
  return {price:price,loan:loan,pi:pi,tax:taxMo,ins:insMo,piti:pi+taxMo+insMo,budget:budget};
}''',
'js_glue':'''function recalc(){
  var p={income:num('income'),debts:num('debts'),down:num('down'),rate:num('rate'),term:num('term'),taxRate:num('taxRate'),ins:num('ins')};
  var r=core(p);
  setT('resPrice',fmtM(r.price));
  setT('resPriceSub','On a '+fmtM(r.budget)+'/mo housing budget');
  setT('resLoan',fmtM(r.loan));setT('resPI',fmtM(r.pi)+'/mo');setT('resTax',fmtM(r.tax)+'/mo');
  setT('resIns',fmtM(r.ins)+'/mo');setT('resPITI',fmtM(r.piti)+'/mo');setT('resBudget',fmtM(r.budget)+'/mo');
  document.getElementById('shareText').textContent='Max home price '+fmtM(r.price)+' on '+fmtM(p.income)+'/yr income';
}
['income','debts','down','rate','term','taxRate','ins'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'income':120000,'debts':800,'down':60000,'rate':6.8,'term':30,'taxRate':1.1,'ins':1800},
  'expect':{'price':409021,'loan':349021,'pi':2275,'piti':2800}},
 {'inputs':{'income':60000,'debts':500,'down':20000,'rate':7,'term':30,'taxRate':1.2,'ins':1200},
  'expect':{'price':174182,'loan':154182,'pi':1026,'piti':1300}},
],
})

# ---------------- 14. cash-flow-rental-calculator (real-estate) ----------------
TOOLS.append({
'slug':'cash-flow-rental-calculator','name':'Rental Cash Flow Calculator','icon':'💵','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'Rental Cash Flow Calculator — Monthly & Annual Rental Profit',
'desc':'Calculate rental property cash flow: rent minus mortgage, taxes, insurance, vacancy, maintenance, and management. See true monthly profit.',
'keywords':'rental cash flow calculator, rental property profit calculator, monthly cash flow real estate, is this rental profitable',
'h1':'Rental Cash Flow Calculator',
'intro':'Rent minus everything. Enter rent and all carrying costs to see whether a rental truly puts money in your pocket each month.',
'inputs':[
 {'id':'rent','label':'Monthly Rent','value':2200,'prefix':'$','min':0},
 {'id':'pi','label':'Mortgage P&I /mo','value':1350,'prefix':'$','min':0},
 {'id':'tax','label':'Property Tax /mo','value':250,'prefix':'$','min':0},
 {'id':'ins','label':'Insurance /mo','value':120,'prefix':'$','min':0},
 {'id':'vacPct','label':'Vacancy Rate (%)','value':5,'suffix':'%','min':0,'max':30},
 {'id':'maintPct','label':'Maintenance Reserve (%)','value':5,'suffix':'%','min':0,'max':30},
 {'id':'mgmtPct','label':'Property Management (%)','value':8,'suffix':'%','min':0,'max':20},
 {'id':'other','label':'Other Monthly Costs (HOA, utilities)','value':100,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Monthly Cash Flow</div>
<div class="mort-result-big" id="resCF">$0</div>
<div id="resCFSub" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🏠 Effective Rent (after vacancy)</span><span class="val" id="resEffRent">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Vacancy Reserve</span><span class="val" id="resVac">$0</span></div>
<div class="mort-row"><span class="lbl">🔧 Maintenance Reserve</span><span class="val" id="resMaint">$0</span></div>
<div class="mort-row"><span class="lbl">🤝 Management Fee</span><span class="val" id="resMgmt">$0</span></div>
<div class="mort-row"><span class="lbl">💸 Total Monthly Expenses</span><span class="val" id="resExp">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Annual Cash Flow</span><span class="val" id="resAnnual">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Rental Cash Flow Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Cash flow is the landlord\'s bottom line: rent collected minus <strong>every</strong> cost of owning and operating the property. Positive cash flow means the property pays you; negative means you feed it.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Cash Flow = Rent − P&I − Tax − Insurance − Vacancy − Maintenance − Management − Other</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The reserves matter most. Budget <strong>5% vacancy</strong> (about two weeks empty per year), <strong>5–10% maintenance</strong> (older homes need more), and <strong>8–10% management</strong> even if you self-manage today — your time has value, and someday you may hire out. Investors often target at least <strong>$200–$300/month</strong> positive cash flow per door after all reserves.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$2,200</strong> rent with $1,350 P&I, $250 tax, $120 insurance, 5% vacancy ($110), 5% maintenance ($110), 8% management ($176), and $100 other = <strong>$2,216</strong> in monthly costs. Cash flow = <strong>−$16/month</strong> — this property essentially breaks even and would bleed cash the first time the furnace dies. Raising rent just $200 flips it to a healthy +$184/month.</p>''',
'faqs':[
 ('What is good cash flow for a rental?','Many investors want $200–$300+ per month per unit after all reserves, or a cash-on-cash return above 8–12%. In expensive markets investors sometimes accept thinner cash flow for appreciation — know which game you are playing.'),
 ('Should I include principal paydown as profit?','For cash flow, no — only actual cash in minus cash out. But remember part of your P&I builds equity (amortization benefit), which is a real return on top of cash flow.'),
 ('What vacancy rate should I assume?','5% (about 18 days/year) is standard for stable markets; use 8–10% for rougher areas or single-family homes where one vacancy means 100% vacancy.'),
 ('Does cash flow include appreciation?','No. Cash flow is operational only. Total return = cash flow + principal paydown + appreciation + tax benefits. Appreciation is the least certain of the four.'),
 ('How do HOA fees affect the analysis?','They are a straight reduction of cash flow and they rise over time — $300/month HOA on a $2,000 rent wipes out most profit. Always include them in "other" costs.'),
],
'related':[
 ('mortgage-calculator','Mortgage Calculator','🏠','Dial in the P&I payment.'),
 ('cap-rate-calculator','Cap Rate Calculator','📊','Yield independent of financing.'),
 ('cash-on-cash-return-calculator','Cash-on-Cash Return Calculator','💰','Return on your cash invested.'),
 ('dscr-calculator','DSCR Calculator','🏦','What lenders require for rentals.'),
 ('nnn-lease-calculator','Triple Net (NNN) Lease','🏢','Commercial lease analysis.'),
],
'js_core':'''function core(p){
  var vac=p.rent*p.vacPct/100,maint=p.rent*p.maintPct/100,mgmt=p.rent*p.mgmtPct/100;
  var exp=p.pi+p.tax+p.ins+vac+maint+mgmt+p.other;
  var cf=p.rent-exp;
  return {cf:cf,annual:cf*12,exp:exp,vac:vac,maint:maint,mgmt:mgmt,effRent:p.rent-vac};
}''',
'js_glue':'''function recalc(){
  var p={rent:num('rent'),pi:num('pi'),tax:num('tax'),ins:num('ins'),vacPct:num('vacPct'),maintPct:num('maintPct'),mgmtPct:num('mgmtPct'),other:num('other')};
  var r=core(p);
  setT('resCF',(r.cf>=0?'':'−')+fmtM(Math.abs(r.cf)));
  var s=document.getElementById('resCFSub');
  s.textContent=r.cf>=0?'✅ Positive cash flow':'❌ Negative cash flow';
  s.style.color=r.cf>=0?'#34d399':'#f87171';
  setT('resEffRent',fmtM(r.effRent));setT('resVac',fmtM(r.vac));setT('resMaint',fmtM(r.maint));
  setT('resMgmt',fmtM(r.mgmt));setT('resExp',fmtM(r.exp));
  setT('resAnnual',(r.annual>=0?'':'−')+fmtM(Math.abs(r.annual))+'/yr');
  document.getElementById('shareText').textContent='Rental cash flow '+fmtM(r.cf)+'/mo ('+fmtM(r.annual)+'/yr)';
}
['rent','pi','tax','ins','vacPct','maintPct','mgmtPct','other'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'rent':2200,'pi':1350,'tax':250,'ins':120,'vacPct':5,'maintPct':5,'mgmtPct':8,'other':100},
  'expect':{'cf':-16,'annual':-192,'exp':2216}},
 {'inputs':{'rent':3000,'pi':1500,'tax':300,'ins':150,'vacPct':5,'maintPct':5,'mgmtPct':8,'other':50},
  'expect':{'cf':460,'annual':5520,'exp':2540}},
],
})

# ---------------- 15. airbnb-profit-calculator (real-estate) ----------------
TOOLS.append({
'slug':'airbnb-profit-calculator','name':'Airbnb Profit Calculator','icon':'🏖️','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'Airbnb Profit Calculator — Short-Term Rental Income',
'desc':'Estimate Airbnb monthly profit: nightly rate × occupancy minus mortgage, utilities, cleaning, and platform fees. Short-term rental calculator.',
'keywords':'Airbnb profit calculator, short term rental calculator, Airbnb income estimator, vacation rental profit, STR cash flow',
'h1':'Airbnb Profit Calculator',
'intro':'Short-term rentals can out-earn long-term rent — with more work and volatility. Model nightly rate, occupancy, and all STR costs.',
'inputs':[
 {'id':'rate','label':'Average Nightly Rate','value':185,'prefix':'$','min':0},
 {'id':'nights','label':'Nights Booked / Month','value':20,'min':0,'max':31},
 {'id':'turnovers','label':'Guest Turnovers / Month','value':8,'min':0,'max':31},
 {'id':'cleanCost','label':'Cleaning Cost Per Turnover','value':60,'prefix':'$','min':0},
 {'id':'mortgage','label':'Mortgage + Tax + Insurance /mo','value':1600,'prefix':'$','min':0},
 {'id':'utils','label':'Utilities + Internet /mo','value':250,'prefix':'$','min':0},
 {'id':'supplies','label':'Supplies & Restocking /mo','value':150,'prefix':'$','min':0},
 {'id':'feePct','label':'Platform Fee (%)','value':3,'suffix':'%','min':0,'max':20,'step':0.5},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly Profit</div>
<div class="mort-result-big" id="resProfit">$0</div>
<div id="resMargin" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💰 Gross Booking Revenue</span><span class="val" id="resRev">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Occupancy Rate</span><span class="val" id="resOcc">—</span></div>
<div class="mort-row"><span class="lbl">🧹 Turnover / Cleaning Costs</span><span class="val" id="resClean">$0</span></div>
<div class="mort-row"><span class="lbl">🏷️ Platform Fees</span><span class="val" id="resFee">$0</span></div>
<div class="mort-row"><span class="lbl">💸 Total Monthly Costs</span><span class="val" id="resCost">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Projected Annual Profit</span><span class="val" id="resAnnual">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Airbnb Profitability Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">A short-term rental earns hotel-like nightly rates but carries hotel-like costs: constant turnover, utilities you pay, restocking, and platform fees. Profit = bookings minus <em>all</em> of it.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Profit = (Nightly Rate × Nights Booked) − Platform Fees − Mortgage − Utilities − Supplies − (Turnovers × Cleaning)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Occupancy is the swing factor: 20 booked nights ≈ 65% occupancy. Most markets see strong seasonality — price 20–40% higher in peak season and expect 40–60% occupancy in shoulder months. Also budget for local STR permits, transient occupancy taxes (often 10–15%, sometimes collected by the platform), and higher insurance.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$185/night</strong> × <strong>20 nights</strong> = <strong>$3,700</strong> revenue. Costs: 3% platform fee ($111), mortgage/tax/insurance ($1,600), utilities ($250), supplies ($150), 8 turnovers × $60 cleaning ($480) = <strong>$2,591</strong>. Monthly profit ≈ <strong>$1,109</strong> (~30% margin) or about <strong>$13,308/year</strong> — roughly 2–3× what the same unit might net as a long-term rental, before valuing your time.</p>''',
'faqs':[
 ('Is Airbnb more profitable than long-term renting?','Often 2–3× the gross revenue, but with 3–5× the work: turnovers, guest messages, restocking, and volatile occupancy. After valuing your time, the gap narrows considerably.'),
 ('What occupancy rate should I expect?','60–75% is strong for most markets; 50% is average. New listings ramp over 3–6 months as reviews accumulate. Use conservative 55–60% for planning.'),
 ('What taxes apply to Airbnb income?','Federal/state income tax on net profit (Schedule C or E), plus local transient occupancy/hotel taxes (often 10–15%) — Airbnb collects these in many jurisdictions but not all. Track everything.'),
 ('Do I need special insurance for Airbnb?','Yes. Standard homeowners policies typically exclude commercial short-term rental activity. You need STR-specific coverage or a rider; Airbnb\'s Host Protection is not a substitute for your own policy.'),
 ('What are the biggest hidden costs?','Turnover labor, utilities (guests are not frugal), restocking, repairs from heavier wear, dynamic-pricing tools, and local permit fees. Budget 25–40% of revenue to operating costs.'),
],
'related':[
 ('cash-flow-rental-calculator','Rental Cash Flow Calculator','💵','Compare with long-term rental math.'),
 ('cap-rate-calculator','Cap Rate Calculator','📊','Yield independent of financing.'),
 ('mortgage-calculator','Mortgage Calculator','🏠','Dial in the P&I payment.'),
 ('extra-mortgage-payment-calculator','Extra Mortgage Payment','💸','Accelerate the underlying mortgage.'),
 ('cash-on-cash-return-calculator','Cash-on-Cash Return Calculator','💰','Return on your cash invested.'),
],
'js_core':'''function core(p){
  var rev=p.rate*p.nights;
  var fee=rev*p.feePct/100;
  var clean=p.turnovers*p.cleanCost;
  var cost=p.mortgage+p.utils+p.supplies+fee+clean;
  var profit=rev-cost;
  return {rev:rev,fee:fee,clean:clean,cost:cost,profit:profit,annual:profit*12,occ:p.nights/30*100,margin:rev>0?profit/rev*100:0};
}''',
'js_glue':'''function recalc(){
  var p={rate:num('rate'),nights:num('nights'),turnovers:num('turnovers'),cleanCost:num('cleanCost'),mortgage:num('mortgage'),utils:num('utils'),supplies:num('supplies'),feePct:num('feePct')};
  var r=core(p);
  setT('resProfit',(r.profit>=0?'':'−')+fmtM(Math.abs(r.profit)));
  setT('resMargin','Margin '+fmtP(r.margin,1)+' of revenue');
  setT('resRev',fmtM(r.rev));setT('resOcc',fmtP(r.occ,0));setT('resClean',fmtM(r.clean));
  setT('resFee',fmtM(r.fee));setT('resCost',fmtM(r.cost));
  setT('resAnnual',(r.annual>=0?'':'−')+fmtM(Math.abs(r.annual))+'/yr');
  document.getElementById('shareText').textContent='Airbnb profit '+fmtM(r.profit)+'/mo at '+r.occ.toFixed(0)+'% occupancy';
}
['rate','nights','turnovers','cleanCost','mortgage','utils','supplies','feePct'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'rate':185,'nights':20,'turnovers':8,'cleanCost':60,'mortgage':1600,'utils':250,'supplies':150,'feePct':3},
  'expect':{'rev':3700,'fee':111,'clean':480,'cost':2591,'profit':1109,'annual':13308}},
 {'inputs':{'rate':250,'nights':22,'turnovers':10,'cleanCost':70,'mortgage':2000,'utils':300,'supplies':200,'feePct':3},
  'expect':{'rev':5500,'fee':165,'clean':700,'cost':3365,'profit':2135,'annual':25620}},
],
})

# ---------------- 16. cap-rate-calculator (real-estate) ----------------
TOOLS.append({
'slug':'cap-rate-calculator','name':'Cap Rate Calculator','icon':'📊','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'Cap Rate Calculator — Capitalization Rate for Rental Property',
'desc':'Calculate cap rate: net operating income divided by property value. Compare rental property yields independent of financing. Free cap rate calculator.',
'keywords':'cap rate calculator, capitalization rate formula, NOI calculator, rental property yield, what is a good cap rate',
'h1':'Cap Rate Calculator',
'intro':'Cap rate strips out financing to show a property\'s raw yield. Enter income and expenses to get NOI and cap rate.',
'inputs':[
 {'id':'price','label':'Property Value / Price','value':350000,'prefix':'$','min':0},
 {'id':'rent','label':'Annual Gross Rent','value':36000,'prefix':'$','min':0},
 {'id':'tax','label':'Annual Property Tax','value':4200,'prefix':'$','min':0},
 {'id':'ins','label':'Annual Insurance','value':1800,'prefix':'$','min':0},
 {'id':'maint','label':'Annual Maintenance','value':2400,'prefix':'$','min':0},
 {'id':'mgmtPct','label':'Management (% of rent)','value':8,'suffix':'%','min':0,'max':20},
 {'id':'vacPct','label':'Vacancy Rate (%)','value':5,'suffix':'%','min':0,'max':30},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Capitalization Rate</div>
<div class="mort-result-big" id="resCap">0%</div>
<div id="resCapSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💰 Net Operating Income (NOI)</span><span class="val" id="resNOI">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Vacancy Allowance</span><span class="val" id="resVac">$0</span></div>
<div class="mort-row"><span class="lbl">🤝 Management Cost</span><span class="val" id="resMgmt">$0</span></div>
<div class="mort-row"><span class="lbl">💸 Total Operating Expenses</span><span class="val" id="resExp">$0</span></div>
<div class="mort-row"><span class="lbl">🏠 Monthly NOI</span><span class="val" id="resMo">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Cap Rate Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">The capitalization rate answers: <strong>if I paid all cash, what annual yield would this property produce?</strong> Because it ignores mortgages, cap rate lets you compare a $150k duplex in Ohio with a $900k condo in Austin on equal footing.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Cap Rate = Net Operating Income ÷ Property Value<br/>NOI = Gross Rent − Vacancy − Taxes − Insurance − Maintenance − Management</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Note what is <strong>excluded</strong>: mortgage payments, depreciation, and income taxes. Those are financing and tax choices, not property performance. Typical US residential cap rates run <strong>4–8%</strong>: lower in hot coastal markets (you pay for appreciation), higher in cash-flow markets.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$350,000</strong> property, <strong>$36,000</strong> gross annual rent. Expenses: vacancy 5% ($1,800), tax ($4,200), insurance ($1,800), maintenance ($2,400), management 8% ($2,880) = <strong>$13,080</strong>. NOI = $36,000 − $13,080 = <strong>$22,920</strong>. Cap rate = $22,920 ÷ $350,000 = <strong>6.55%</strong> — a solid cash-flow-market yield.</p>''',
'faqs':[
 ('What is a good cap rate?','4–5% is typical in expensive coastal markets, 6–8% in cash-flow markets, 8%+ in higher-risk or rural areas. Higher cap rate = higher yield but usually higher risk or lower appreciation.'),
 ('Is cap rate the same as ROI?','No. Cap rate ignores financing; cash-on-cash ROI includes your mortgage and down payment. A 6% cap rate property can produce a 10%+ cash-on-cash return with leverage — or go negative with too much leverage.'),
 ('Why is mortgage payment excluded from NOI?','Because financing is a buyer choice, not a property characteristic. Two buyers paying different down payments get the same NOI but different cash flow — cap rate isolates the asset itself.'),
 ('Can I use cap rate to value a property?','Yes, inversely: Value = NOI ÷ market cap rate. If similar properties trade at a 7% cap and yours produces $21,000 NOI, it is worth about $300,000. This is the income approach to valuation.'),
 ('Does cap rate include appreciation?','No — cap rate measures current income yield only. Total return adds appreciation, principal paydown, and tax benefits on top.'),
],
'related':[
 ('cash-flow-rental-calculator','Rental Cash Flow Calculator','💵','Cash flow with financing included.'),
 ('cash-on-cash-return-calculator','Cash-on-Cash Return Calculator','💰','Leveraged return on your cash.'),
 ('brrrr-calculator','BRRRR Calculator','🔁','The full BRRRR investment cycle.'),
 ('mortgage-calculator','Mortgage Calculator','🏠','Financing costs cap rate ignores.'),
 ('nnn-lease-calculator','Triple Net (NNN) Lease','🏢','Commercial cap rate context.'),
],
'js_core':'''function core(p){
  var vac=p.rent*p.vacPct/100,mgmt=p.rent*p.mgmtPct/100;
  var exp=vac+p.tax+p.ins+p.maint+mgmt;
  var noi=p.rent-exp;
  var cap=p.price>0?noi/p.price*100:0;
  return {noi:noi,cap:cap,exp:exp,vac:vac,mgmt:mgmt,mo:noi/12};
}''',
'js_glue':'''function recalc(){
  var p={price:num('price'),rent:num('rent'),tax:num('tax'),ins:num('ins'),maint:num('maint'),mgmtPct:num('mgmtPct'),vacPct:num('vacPct')};
  var r=core(p);
  setT('resCap',fmtP(r.cap,2));
  setT('resCapSub',r.cap>=8?'High yield — verify risk':(r.cap>=5?'Healthy cash-flow range':'Low yield — appreciation play?'));
  setT('resNOI',fmtM(r.noi)+'/yr');setT('resVac',fmtM(r.vac));setT('resMgmt',fmtM(r.mgmt));
  setT('resExp',fmtM(r.exp));setT('resMo',fmtM(r.mo)+'/mo');
  document.getElementById('shareText').textContent='Cap rate '+r.cap.toFixed(2)+'% (NOI '+fmtM(r.noi)+')';
}
['price','rent','tax','ins','maint','mgmtPct','vacPct'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'price':350000,'rent':36000,'tax':4200,'ins':1800,'maint':2400,'mgmtPct':8,'vacPct':5},
  'expect':{'noi':22920,'cap':6.55,'exp':13080}},
 {'inputs':{'price':500000,'rent':60000,'tax':6000,'ins':2400,'maint':3000,'mgmtPct':10,'vacPct':5},
  'expect':{'noi':39600,'cap':7.92,'exp':20400}},
],
})

# ---------------- 17. brrrr-calculator (real-estate) ----------------
TOOLS.append({
'slug':'brrrr-calculator','name':'BRRRR Calculator','icon':'🔁','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'BRRRR Calculator — Buy, Rehab, Rent, Refinance, Repeat',
'desc':'Model the BRRRR strategy: total cash invested, cash-out refinance, cash left in the deal, and infinite-return math. Free BRRRR calculator.',
'keywords':'BRRRR calculator, buy rehab rent refinance repeat, cash out refinance rental, infinite return real estate, BRRRR method',
'h1':'BRRRR Calculator',
'intro':'BRRRR recycles your capital: buy distressed, rehab, rent, refinance, repeat. See your cash left in and true return.',
'inputs':[
 {'id':'purchase','label':'Purchase Price','value':150000,'prefix':'$','min':0},
 {'id':'rehab','label':'Rehab Budget','value':40000,'prefix':'$','min':0},
 {'id':'arv','label':'After Repair Value (ARV)','value':250000,'prefix':'$','min':0},
 {'id':'ltv','label':'Refinance LTV (%)','value':75,'suffix':'%','min':50,'max':85},
 {'id':'rate','label':'Refi Mortgage Rate (%)','value':7,'suffix':'%','min':0,'max':15,'step':0.05},
 {'id':'rent','label':'Monthly Rent','value':2100,'prefix':'$','min':0},
 {'id':'costs','label':'Monthly Non-Debt Costs (tax, ins, vac, maint, mgmt)','value':600,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Cash Left in the Deal</div>
<div class="mort-result-big" id="resLeft">$0</div>
<div id="resLeftSub" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💵 Total Cash Invested</span><span class="val" id="resInv">$0</span></div>
<div class="mort-row"><span class="lbl">🏦 Cash-Out Refinance Loan</span><span class="val" id="resLoan">$0</span></div>
<div class="mort-row"><span class="lbl">💳 New Mortgage P&I /mo</span><span class="val" id="resPI">$0</span></div>
<div class="mort-row"><span class="lbl">💸 Monthly Cash Flow</span><span class="val" id="resCF">$0</span></div>
<div class="mort-row"><span class="lbl">📈 Cash-on-Cash Return</span><span class="val" id="resCoC">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How the BRRRR Strategy Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>Buy, Rehab, Rent, Refinance, Repeat.</strong> You buy below market, force appreciation with renovations, then refinance at the new appraised value — pulling most of your cash back out to repeat the cycle. Done well, you end up with a cash-flowing rental and almost none of your own money left in it.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Key Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Total Invested = Purchase + Rehab<br/>Refi Loan = ARV × LTV (typically 75%)<br/>Cash Left In = Total Invested − Refi Loan</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The magic metric is <strong>cash left in</strong>: the smaller it is, the higher your cash-on-cash return. If the refinance returns <em>all</em> your cash, your return is mathematically infinite — you collect cash flow on $0 invested. Lenders usually require 6–12 months of "seasoning" (ownership) before refinancing at appraised value.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Buy <strong>$150,000</strong> + rehab <strong>$40,000</strong> = <strong>$190,000</strong> invested. ARV <strong>$250,000</strong> → 75% refi loan = <strong>$187,500</strong>. Cash left in = just <strong>$2,500</strong>. At 7% the new P&I is ~$1,247/mo; with $2,100 rent and $600 other costs, cash flow ≈ <strong>$253/mo</strong> ($3,031/yr) — a <strong>121% cash-on-cash return</strong> on the $2,500 remaining. Repeat with the recycled $187,500.</p>''',
'faqs':[
 ('What does BRRRR stand for?','Buy, Rehab, Rent, Refinance, Repeat — a strategy popularized by BiggerPockets for building a rental portfolio by recycling the same capital through multiple properties.'),
 ('What is the 70% rule in BRRRR?','A buying guideline: pay no more than 70% of ARV minus rehab costs. It builds in margin so the refinance can return most of your cash. On a $250k ARV with $40k rehab, max price ≈ $135k.'),
 ('How long before I can refinance (seasoning)?','Most conventional lenders require 6 months of ownership before using the new appraised value; some allow 12 months. Delayed-financing exceptions exist for all-cash purchases.'),
 ('What are the risks of BRRRR?','Rehab overruns, ARV coming in low, rising rates shrinking refi proceeds, and extended vacancies during renovation. Always underwrite the deal as a mediocre flip first — the refinance is the bonus, not the plan.'),
 ('Can I BRRRR with little money?','You still need purchase + rehab capital upfront (cash, hard money, or partners). The strategy recycles capital — it does not eliminate the need for it on deal one.'),
],
'related':[
 ('cash-flow-rental-calculator','Rental Cash Flow Calculator','💵','Post-refi monthly cash flow.'),
 ('cap-rate-calculator','Cap Rate Calculator','📊','Yield independent of financing.'),
 ('dscr-calculator','DSCR Calculator','🏦','Refi lender requirements.'),
 ('mortgage-refinance-calculator','Mortgage Refinance Break-Even','🔄','Refinance cost analysis.'),
 ('heloc-calculator','HELOC & Credit Line','💳','Alternative equity access.'),
],
'js_core':MORT_JS+'''function core(p){
  var invested=p.purchase+p.rehab;
  var loan=p.arv*p.ltv/100;
  var left=invested-loan;
  var pi=loan*piFactor(p.rate,30);
  var cf=p.rent-pi-p.costs;
  var annual=cf*12;
  var coc=left>0?annual/left*100:(annual>0?Infinity:-Infinity);
  return {invested:invested,loan:loan,left:left,pi:pi,cf:cf,annual:annual,coc:coc};
}''',
'js_glue':'''function recalc(){
  var p={purchase:num('purchase'),rehab:num('rehab'),arv:num('arv'),ltv:num('ltv'),rate:num('rate'),rent:num('rent'),costs:num('costs')};
  var r=core(p);
  setT('resLeft',(r.left>=0?'':'−')+fmtM(Math.abs(r.left)));
  var s=document.getElementById('resLeftSub');
  if(r.left<=0){s.textContent='🚀 Infinite return — all cash recovered!';s.style.color='#34d399';}
  else{s.textContent=fmtP(r.left/p.arv*100,1)+' of ARV left invested';s.style.color='var(--text-muted)';}
  setT('resInv',fmtM(r.invested));setT('resLoan',fmtM(r.loan));
  setT('resPI',fmtM(r.pi)+'/mo');setT('resCF',(r.cf>=0?'':'−')+fmtM(Math.abs(r.cf))+'/mo');
  setT('resCoC',!isFinite(r.coc)?'∞ Infinite':fmtP(r.coc,1));
  document.getElementById('shareText').textContent='BRRRR: '+fmtM(r.left)+' left in, cash flow '+fmtM(r.cf)+'/mo';
}
['purchase','rehab','arv','ltv','rate','rent','costs'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'purchase':150000,'rehab':40000,'arv':250000,'ltv':75,'rate':7,'rent':2100,'costs':600},
  'expect':{'invested':190000,'loan':187500,'left':2500,'pi':1247,'cf':252.56,'annual':3031}},
 {'inputs':{'purchase':100000,'rehab':30000,'arv':180000,'ltv':75,'rate':7.5,'rent':1600,'costs':450},
  'expect':{'invested':130000,'loan':135000,'left':-5000,'pi':944,'cf':206,'annual':2473}},
],
})

# ---------------- 18. dscr-calculator (real-estate) ----------------
TOOLS.append({
'slug':'dscr-calculator','name':'DSCR Calculator','icon':'🏦','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'DSCR Calculator — Debt Service Coverage Ratio for Investors',
'desc':'Calculate DSCR (NOI ÷ debt service) to see if a rental qualifies for investor financing. Most DSCR lenders require 1.20–1.25× coverage.',
'keywords':'DSCR calculator, debt service coverage ratio, DSCR loan requirements, rental property DSCR, investor loan qualification',
'h1':'DSCR Calculator',
'intro':'DSCR lenders qualify you on the property\'s income — not yours. Enter NOI and debt service to check your coverage ratio.',
'inputs':[
 {'id':'rent','label':'Annual Gross Rent','value':48000,'prefix':'$','min':0},
 {'id':'exp','label':'Annual Operating Expenses','value':18000,'prefix':'$','min':0},
 {'id':'loan','label':'Loan Amount','value':300000,'prefix':'$','min':0},
 {'id':'rate','label':'Interest Rate (%)','value':7,'suffix':'%','min':0,'max':15,'step':0.05},
 {'id':'term','label':'Amortization (years)','value':30,'min':10,'max':30},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Debt Service Coverage Ratio</div>
<div class="mort-result-big" id="resDSCR">0.00×</div>
<div id="resQual" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💰 Net Operating Income</span><span class="val" id="resNOI">$0</span></div>
<div class="mort-row"><span class="lbl">💳 Annual Debt Service</span><span class="val" id="resDebt">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Monthly NOI</span><span class="val" id="resMo">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Coverage Cushion</span><span class="val" id="resCush">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How DSCR Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>DSCR = Net Operating Income ÷ Annual Debt Service.</strong> It measures how many times over a property\'s income covers its mortgage. A DSCR of 1.25 means the property earns 25% more than the loan costs — the cushion lenders want.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Why DSCR Loans Exist</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Traditional mortgages underwrite <em>you</em> (income, DTI, tax returns). <strong>DSCR loans underwrite the <em>property</em></strong> — no personal income verification, no DTI limit, and closings in an LLC. That is why they dominate among serious rental investors. The tradeoff: higher rates (typically 1–2% above conventional) and 20–25% down payments.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$48,000</strong> gross rent minus <strong>$18,000</strong> expenses = <strong>$30,000</strong> NOI. A <strong>$300,000</strong> loan at 7% amortized over 30 years costs about <strong>$23,951/year</strong>. DSCR = $30,000 ÷ $23,951 = <strong>1.25×</strong> — right at the typical lender minimum, so this deal qualifies (barely). Most lenders want <strong>1.20–1.25×</strong>; below 1.0 the property cannot service its own debt.</p>''',
'faqs':[
 ('What DSCR do lenders require?','Most DSCR lenders require 1.20–1.25×. Some offer reduced rates at 1.5×+ and will lend down to 1.0× at higher rates. Below 1.0× (negative leverage) is rarely financeable.'),
 ('Do DSCR loans check personal income?','No — that is the point. Qualification is based on the property\'s rent roll and a lease or appraisal rent schedule. You still need good credit (usually 660–680+) and reserves.'),
 ('Can I close a DSCR loan in an LLC?','Yes, and most investors do. DSCR loans are designed for entity borrowers, unlike conventional mortgages that generally require personal ownership.'),
 ('How can I improve a property\'s DSCR?','Raise rents, cut operating expenses, increase the down payment (smaller loan), buy down the rate, or choose a longer amortization. Every $100/month of NOI moves DSCR noticeably.'),
 ('DSCR vs. conventional investment loan?','Conventional: lower rates but personal income/DTI underwriting and a 10-loan cap. DSCR: higher rates, no income docs, no loan cap, LLC-friendly. Scale investors overwhelmingly use DSCR.'),
],
'related':[
 ('cash-flow-rental-calculator','Rental Cash Flow Calculator','💵','Monthly cash flow detail.'),
 ('mortgage-calculator','Mortgage Calculator','🏠','Dial in debt service.'),
 ('cap-rate-calculator','Cap Rate Calculator','📊','NOI-based yield metric.'),
 ('heloc-calculator','HELOC & Credit Line','💳','Alternative financing.'),
 ('brrrr-calculator','BRRRR Calculator','🔁','The BRRRR refinance cycle.'),
],
'js_core':MORT_JS+'''function core(p){
  var noi=p.rent-p.exp;
  var debt=p.loan*piFactor(p.rate,p.term)*12;
  var dscr=debt>0?noi/debt:0;
  return {noi:noi,debt:debt,dscr:dscr,mo:noi/12,cush:noi-debt,qual:dscr>=1.2};
}''',
'js_glue':'''function recalc(){
  var p={rent:num('rent'),exp:num('exp'),loan:num('loan'),rate:num('rate'),term:num('term')};
  var r=core(p);
  setT('resDSCR',r.dscr.toFixed(2)+'×');
  var q=document.getElementById('resQual');
  q.textContent=r.qual?'✅ Qualifies (≥ 1.20× lender bar)':'❌ Below 1.20× lender bar';
  q.style.color=r.qual?'#34d399':'#f87171';
  setT('resNOI',fmtM(r.noi)+'/yr');setT('resDebt',fmtM(r.debt)+'/yr');
  setT('resMo',fmtM(r.mo)+'/mo');setT('resCush',(r.cush>=0?'':'−')+fmtM(Math.abs(r.cush))+'/yr');
  document.getElementById('shareText').textContent='DSCR '+r.dscr.toFixed(2)+'× (NOI '+fmtM(r.noi)+', debt '+fmtM(r.debt)+')';
}
['rent','exp','loan','rate','term'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'rent':48000,'exp':18000,'loan':300000,'rate':7,'term':30},
  'expect':{'noi':30000,'debt':23951,'dscr':1.25}},
 {'inputs':{'rent':60000,'exp':22000,'loan':350000,'rate':6.5,'term':30},
  'expect':{'noi':38000,'debt':26547,'dscr':1.43}},
],
})

# ---------------- 19. cash-on-cash-return-calculator (real-estate) ----------------
TOOLS.append({
'slug':'cash-on-cash-return-calculator','name':'Cash-on-Cash Return Calculator','icon':'💰','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'Cash-on-Cash Return Calculator — Leveraged Rental ROI',
'desc':'Calculate cash-on-cash return: annual pre-tax cash flow divided by total cash invested. The real ROI on your down payment.',
'keywords':'cash on cash return calculator, CoC return real estate, rental ROI calculator, leveraged return rental property',
'h1':'Cash-on-Cash Return Calculator',
'intro':'Cap rate ignores your mortgage — cash-on-cash does not. See the true annual return on the cash you actually invested.',
'inputs':[
 {'id':'down','label':'Down Payment','value':70000,'prefix':'$','min':0},
 {'id':'closing','label':'Closing & Upfront Costs','value':8000,'prefix':'$','min':0},
 {'id':'rent','label':'Monthly Rent','value':2200,'prefix':'$','min':0},
 {'id':'pi','label':'Mortgage P&I /mo','value':1100,'prefix':'$','min':0},
 {'id':'tax','label':'Property Tax /mo','value':220,'prefix':'$','min':0},
 {'id':'ins','label':'Insurance /mo','value':110,'prefix':'$','min':0},
 {'id':'other','label':'Other Monthly (vacancy, maint, mgmt, HOA)','value':200,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Cash-on-Cash Return</div>
<div class="mort-result-big" id="resCoC">0%</div>
<div id="resCoCSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💵 Total Cash Invested</span><span class="val" id="resInv">$0</span></div>
<div class="mort-row"><span class="lbl">💸 Annual Pre-Tax Cash Flow</span><span class="val" id="resCF">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Monthly Cash Flow</span><span class="val" id="resMo">$0</span></div>
<div class="mort-row"><span class="lbl">📊 vs. Cap Rate Benchmark</span><span class="val" id="resNote">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Cash-on-Cash Return Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Cash-on-cash answers the question investors actually care about: <strong>for each dollar I put in, how many cents come back per year?</strong> Unlike cap rate, it includes your financing — so leverage shows up directly in the number.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">CoC = Annual Pre-Tax Cash Flow ÷ Total Cash Invested<br/>Cash Invested = Down Payment + Closing Costs + Initial Repairs</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Leverage is a double-edged sword: a smaller down payment boosts CoC when cash flow is positive — but also magnifies losses and risk if rents dip or rates rise. Most buy-and-hold investors target <strong>8–12%+</strong> cash-on-cash in the first year.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$70,000</strong> down + <strong>$8,000</strong> closing = <strong>$78,000</strong> invested. Rent <strong>$2,200</strong> minus $1,100 P&I, $220 tax, $110 insurance, $200 other = <strong>$570/mo</strong> cash flow, or <strong>$6,840/year</strong>. CoC = $6,840 ÷ $78,000 = <strong>8.77%</strong> — beating most bonds and savings accounts while the tenant also pays down your mortgage.</p>''',
'faqs':[
 ('What is a good cash-on-cash return?','8–12% is the common target for buy-and-hold rentals in the US. Below 6% you should ask whether the risk premium over bonds is worth it; above 15% usually signals high risk, heavy leverage, or an exceptional deal.'),
 ('Cash-on-cash vs. cap rate — which matters?','Both. Cap rate measures the property; cash-on-cash measures your investment including financing. Use cap rate to compare properties, cash-on-cash to compare against other uses of your cash.'),
 ('Does cash-on-cash include principal paydown?','No — only actual cash flow. But your total return is higher: add equity built through amortization (often 2–4% more per year) plus appreciation and tax benefits.'),
 ('Can cash-on-cash be infinite?','Yes — if a refinance returns all your invested cash (the BRRRR ideal), you earn cash flow on $0 invested. It is real, but remember the debt and risk remain.'),
 ('Is cash-on-cash before or after tax?','Conventionally before tax (pre-tax cash flow). After-tax CoC is more precise but requires your full tax picture including depreciation.'),
],
'related':[
 ('cash-flow-rental-calculator','Rental Cash Flow Calculator','💵','The cash flow numerator, detailed.'),
 ('cap-rate-calculator','Cap Rate Calculator','📊','Unleveraged yield comparison.'),
 ('brrrr-calculator','BRRRR Calculator','🔁','Maximize CoC via refinancing.'),
 ('mortgage-calculator','Mortgage Calculator','🏠','Leverage costs that drive CoC.'),
 ('dscr-calculator','DSCR Calculator','🏦','Lender coverage requirements.'),
],
'js_core':'''function core(p){
  var invested=p.down+p.closing;
  var cf=(p.rent-p.pi-p.tax-p.ins-p.other)*12;
  var coc=invested>0?cf/invested*100:0;
  return {invested:invested,cf:cf,mo:cf/12,coc:coc};
}''',
'js_glue':'''function recalc(){
  var p={down:num('down'),closing:num('closing'),rent:num('rent'),pi:num('pi'),tax:num('tax'),ins:num('ins'),other:num('other')};
  var r=core(p);
  setT('resCoC',fmtP(r.coc,2));
  setT('resCoCSub',r.coc>=8?'✅ Above the 8% investor target':(r.coc>=0?'⚠️ Below the 8% target':'❌ Negative return on cash'));
  setT('resInv',fmtM(r.invested));
  setT('resCF',(r.cf>=0?'':'−')+fmtM(Math.abs(r.cf))+'/yr');
  setT('resMo',(r.mo>=0?'':'−')+fmtM(Math.abs(r.mo))+'/mo');
  setT('resNote','Each $10k invested returns '+fmtM(r.coc/100*10000)+'/yr');
  document.getElementById('shareText').textContent='Cash-on-cash '+r.coc.toFixed(2)+'% on '+fmtM(r.invested)+' invested';
}
['down','closing','rent','pi','tax','ins','other'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'down':70000,'closing':8000,'rent':2200,'pi':1100,'tax':220,'ins':110,'other':200},
  'expect':{'invested':78000,'cf':6840,'coc':8.77}},
 {'inputs':{'down':40000,'closing':5000,'rent':1800,'pi':950,'tax':180,'ins':90,'other':150},
  'expect':{'invested':45000,'cf':5160,'coc':11.47}},
],
})

# ---------------- 20. real-estate-commission-calculator (real-estate) ----------------
TOOLS.append({
'slug':'real-estate-commission-calculator','name':'Real Estate Commission Calculator','icon':'🤝','cat':'real-estate','cat_label':'REAL ESTATE',
'hub':'/real-estate-calculators','hub_title':'Real Estate Calculators',
'hub_blurb':'Browse all real estate and mortgage calculators.',
'title':'Real Estate Commission Calculator — Agent Fees & Splits',
'desc':'Calculate real estate commissions: total fee, listing vs. buyer agent split, agent-broker split, and your net proceeds from the sale.',
'keywords':'real estate commission calculator, realtor fee calculator, how much is realtor commission, agent split calculator, home sale net proceeds',
'h1':'Real Estate Commission Calculator',
'intro':'Commissions are negotiable and splittable four ways. See exactly where every dollar of the fee goes — and what you net.',
'inputs':[
 {'id':'price','label':'Sale Price','value':450000,'prefix':'$','min':0},
 {'id':'commPct','label':'Total Commission (%)','value':5.5,'suffix':'%','min':0,'max':10,'step':0.1},
 {'id':'listSplit','label':'Listing Side Share (%)','value':50,'suffix':'%','min':0,'max':100},
 {'id':'agentSplit','label':'Your Agent Keeps (% of their side)','value':80,'suffix':'%','min':0,'max':100},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Seller Net Proceeds</div>
<div class="mort-result-big" id="resNet">$0</div>
<div id="resNetSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💰 Total Commission</span><span class="val" id="resTotal">$0</span></div>
<div class="mort-row"><span class="lbl">🏠 Listing Side</span><span class="val" id="resList">$0</span></div>
<div class="mort-row"><span class="lbl">🔑 Buyer Side</span><span class="val" id="resBuy">$0</span></div>
<div class="mort-row"><span class="lbl">👤 Listing Agent Nets</span><span class="val" id="resAgent">$0</span></div>
<div class="mort-row"><span class="lbl">🏢 Listing Broker Keeps</span><span class="val" id="resBroker">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Real Estate Commissions Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">The seller typically pays the entire commission from sale proceeds, and it is split four ways: listing brokerage vs. buyer brokerage, then each agent vs. their broker. Since 2024 rule changes, buyer-agent compensation is negotiated separately rather than set in the listing — making this math more important than ever.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Split Chain</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Total = Price × Commission %<br/>Each Side = Total × Side Split %<br/>Agent Nets = Side × Agent Split %</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The traditional total was 5–6%; post-2024, 4–5% totals are increasingly common and everything is negotiable. Agents then split their side with their broker (50/50 for new agents, up to 90/10+ for top producers).</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$450,000</strong> sale at <strong>5.5%</strong> = <strong>$24,750</strong> total commission. Split 50/50: <strong>$12,375</strong> per side. If the listing agent keeps 80% of their side, they net <strong>$9,900</strong> and their broker keeps <strong>$2,475</strong>. Seller nets <strong>$425,250</strong> before other closing costs.</p>''',
'faqs':[
 ('What is the average real estate commission in 2026?','Totals of 4.5–5.5% are now common, down from the old 6% standard. Luxury and competitive markets often see lower percentages; everything is negotiable by law.'),
 ('Who pays the buyer\'s agent now?','Since the 2024 NAR settlement, buyer-agent compensation is negotiated directly between buyers and their agents — it can be paid by the buyer, the seller (as a concession), or split. It is no longer preset in MLS listings.'),
 ('Are real estate commissions negotiable?','Yes — always. Federal law prohibits fixed commission rates. Interview 2–3 agents and negotiate both the rate and the services included.'),
 ('What is a typical agent-broker split?','New agents often start at 50/50, moving to 70/30 or 80/20+ with production. Top teams may keep 90–100% while paying desk fees. The split in this calculator defaults to 80/20.'),
 ('Can I avoid commission with FSBO?','For-sale-by-owner saves the listing side but you still usually offer buyer-agent compensation to attract showings, plus you handle pricing, marketing, contracts, and liability yourself.'),
],
'related':[
 ('closing-costs-calculator','Home Closing Costs','🏡','All seller closing costs.'),
 ('mortgage-calculator','Mortgage Calculator','🏠','Buyer financing costs.'),
 ('sales-commission-calculator','Sales Commission & Quota','📈','General commission math.'),
 ('house-affordability-calculator','House Affordability Calculator','🏡','What buyers can pay.'),
 ('capital-gains-tax-calculator','Capital Gains Tax (2026)','🏛️','Tax on your sale profit.'),
],
'js_core':'''function core(p){
  var total=p.price*p.commPct/100;
  var list=total*p.listSplit/100;
  var buy=total-list;
  var agent=list*p.agentSplit/100;
  var broker=list-agent;
  return {total:total,list:list,buy:buy,agent:agent,broker:broker,net:p.price-total};
}''',
'js_glue':'''function recalc(){
  var p={price:num('price'),commPct:num('commPct'),listSplit:num('listSplit'),agentSplit:num('agentSplit')};
  var r=core(p);
  setT('resNet',fmtM(r.net));
  setT('resNetSub','After '+fmtM(r.total)+' commission ('+fmtP(p.commPct,1)+')');
  setT('resTotal',fmtM(r.total));setT('resList',fmtM(r.list));setT('resBuy',fmtM(r.buy));
  setT('resAgent',fmtM(r.agent));setT('resBroker',fmtM(r.broker));
  document.getElementById('shareText').textContent='Commission '+fmtM(r.total)+' on '+fmtM(p.price)+', seller nets '+fmtM(r.net);
}
['price','commPct','listSplit','agentSplit'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'price':450000,'commPct':5.5,'listSplit':50,'agentSplit':80},
  'expect':{'total':24750,'list':12375,'buy':12375,'agent':9900,'broker':2475,'net':425250}},
 {'inputs':{'price':300000,'commPct':6,'listSplit':60,'agentSplit':70},
  'expect':{'total':18000,'list':10800,'buy':7200,'agent':7560,'broker':3240,'net':282000}},
],
})

# ---------------- 21. youtube-shorts-earnings-calculator (creator) ----------------
TOOLS.append({
'slug':'youtube-shorts-earnings-calculator','name':'YouTube Shorts Earnings Calculator','icon':'⚡','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'YouTube Shorts Earnings Calculator — Shorts Revenue Estimator',
'desc':'Estimate YouTube Shorts earnings: Shorts RPM is far lower than long-form. Enter views and RPM to project monthly and yearly Shorts revenue.',
'keywords':'YouTube Shorts earnings calculator, how much do Shorts pay, Shorts RPM, YouTube Shorts money calculator, Shorts revenue share',
'h1':'YouTube Shorts Earnings Calculator',
'intro':'Shorts pay a fraction of long-form rates. Enter your views and RPM to see realistic Shorts earnings.',
'inputs':[
 {'id':'views','label':'Monthly Shorts Views','value':2000000,'min':0},
 {'id':'rpm','label':'Shorts RPM ($ per 1,000 views)','value':0.08,'min':0,'max':2,'step':0.01},
 {'id':'months','label':'Projection (months)','value':12,'min':1,'max':60},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly Shorts Earnings</div>
<div class="mort-result-big" id="resMo">$0</div>
<div id="resMoSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📅 Projected Earnings (N months)</span><span class="val" id="resProj">$0</span></div>
<div class="mort-row"><span class="lbl">👁️ Earnings Per 1M Views</span><span class="val" id="resPerM">$0</span></div>
<div class="mort-row"><span class="lbl">📊 vs. Long-Form (typical $4 RPM)</span><span class="val" id="resVs">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How YouTube Shorts Pay Creators',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Shorts revenue works differently from long-form. Ad money from the Shorts feed goes into a <strong>creator pool</strong>; YouTube keeps 55% and distributes 45% to creators based on their share of views. Music licensing takes a further cut from the pool when licensed tracks are used.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Monthly Earnings = (Monthly Views ÷ 1,000) × Shorts RPM</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Realistic Shorts RPMs run <strong>$0.05–$0.15</strong> per 1,000 views — roughly 30–50× less than long-form ($2–$8+ RPM). That is why Shorts are a discovery engine first and a revenue engine second: creators monetize the audience Shorts build through long-form, sponsorships, and affiliates.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>2,000,000</strong> monthly Shorts views at a <strong>$0.08</strong> RPM = <strong>$160/month</strong>, or <strong>$1,920/year</strong>. Each million views earns about <strong>$80</strong>. The same 2M views on long-form at a $4 RPM would pay ~$8,000 — fifty times more. Treat Shorts as the top of your funnel.</p>''',
'faqs':[
 ('How much does YouTube pay per 1,000 Shorts views?','Typically $0.05–$0.15 (RPM) after YouTube\'s 45% creator-pool share. It varies by audience country, content category, and music usage. Viral Shorts with 10M views often earn just $500–$1,500.'),
 ('Do you need 1,000 subscribers to monetize Shorts?','The lower YPP tier requires 500 subscribers, 3M Shorts views in 90 days, and 3 uploads in 90 days — this unlocks fan funding and Shopping. Full ad-revenue sharing needs 1,000 subs plus 10M Shorts views in 90 days (or 4,000 watch hours).'),
 ('Why do Shorts pay so little?','Shorts ads (feed placements) command far lower CPMs than skippable long-form ads, and revenue is split across the entire creator pool by view share rather than attributed per video.'),
 ('Should I post Shorts or long-form for money?','Both: Shorts for subscriber growth and discovery, long-form for revenue. Many creators convert Shorts viewers into long-form watchers, where RPMs are 30–50× higher.'),
 ('Does using licensed music reduce Shorts revenue?','Yes. When your Short uses licensed music, a share of the creator pool is allocated to music rights holders first, reducing the distributable pool for creators.'),
],
'related':[
 ('youtube-money-calculator','YouTube Money & CPM','▶️','Long-form revenue estimates.'),
 ('tiktok-money-calculator','TikTok Money Calc','🎵','TikTok creator earnings.'),
 ('channel-growth-calculator','Channel Milestone Tracker','🚀','Track subscriber milestones.'),
 ('tiktok-rpm-calculator','TikTok RPM Calculator','📊','RPM math for TikTok.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','Monetize the audience instead.'),
],
'js_core':'''function core(p){
  var mo=p.views/1000*p.rpm;
  var perM=1000*p.rpm;
  var vs=p.rpm>0?4/p.rpm:0;
  return {mo:mo,proj:mo*p.months,perM:perM,vs:vs};
}''',
'js_glue':'''function recalc(){
  var p={views:num('views'),rpm:num('rpm'),months:num('months')};
  var r=core(p);
  setT('resMo',fmtM(r.mo));
  setT('resMoSub','At $'+p.rpm.toFixed(2)+' RPM');
  setT('resProj',fmtM(r.proj)+' / '+p.months+' mo');
  setT('resPerM',fmtM(r.perM));
  setT('resVs','Long-form pays ~'+Math.round(r.vs)+'× more');
  document.getElementById('shareText').textContent='Shorts earnings '+fmtM(r.mo)+'/mo at '+fmtM(p.views)+' views';
}
['views','rpm','months'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'views':2000000,'rpm':0.08,'months':12},'expect':{'mo':160,'proj':1920,'perM':80}},
 {'inputs':{'views':5000000,'rpm':0.12,'months':6},'expect':{'mo':600,'proj':3600,'perM':120}},
],
})

# ---------------- 22. tiktok-rpm-calculator (creator) ----------------
TOOLS.append({
'slug':'tiktok-rpm-calculator','name':'TikTok RPM Calculator','icon':'📊','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'TikTok RPM Calculator — Revenue Per 1,000 Views',
'desc':'Calculate your TikTok RPM from actual earnings and views, then project what future videos could earn. Free TikTok RPM calculator.',
'keywords':'TikTok RPM calculator, TikTok revenue per 1000 views, how much does TikTok pay per view, TikTok creativity program payout',
'h1':'TikTok RPM Calculator',
'intro':'Enter your real TikTok earnings and views to find your RPM — then project earnings for any view count.',
'inputs':[
 {'id':'views','label':'Views in Period','value':500000,'min':0},
 {'id':'revenue','label':'Revenue Earned ($)','value':350,'prefix':'$','min':0},
 {'id':'days','label':'Days in Period','value':30,'min':1,'max':365},
 {'id':'target','label':'Target Views to Project','value':1000000,'min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Your TikTok RPM</div>
<div class="mort-result-big" id="resRPM">$0.00</div>
<div id="resRPMSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;">per 1,000 qualified views</div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🎯 Projected Earnings (target views)</span><span class="val" id="resTarget">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Daily Views (avg)</span><span class="val" id="resDaily">0</span></div>
<div class="mort-row"><span class="lbl">📆 Projected Monthly Earnings</span><span class="val" id="resMonthly">$0</span></div>
<div class="mort-row"><span class="lbl">💵 Earnings Per Million Views</span><span class="val" id="resPerM">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How TikTok RPM Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>RPM = revenue per mille</strong> — what you earn per 1,000 views. On TikTok it is the cleanest way to compare monetization across accounts and content types, because raw view counts say nothing about payout.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">RPM = (Revenue ÷ Views) × 1,000<br/>Projected Earnings = (Target Views ÷ 1,000) × RPM</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">TikTok\'s Creativity Program (1-minute+ videos) typically pays <strong>$0.40–$1.00 RPM</strong> on qualified views — far above the old Creator Fund\'s $0.02–$0.04. Only <strong>qualified views</strong> count (real users, minimum watch time, not from ads or your own loops), which is why your RPM here uses your actual numbers.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>500,000</strong> views earning <strong>$350</strong> over 30 days → RPM = ($350 ÷ 500,000) × 1,000 = <strong>$0.70</strong>. At that RPM, <strong>1,000,000</strong> target views project to <strong>$700</strong>, and the current pace annualizes to roughly <strong>$350/month</strong> (~16,667 views/day).</p>''',
'faqs':[
 ('What is a good TikTok RPM?','$0.40–$1.00 is typical for the Creativity Program on 1-minute+ videos. Finance and business content often pays at the high end; entertainment trends pay less. The old Creator Fund paid a dismal $0.02–$0.04.'),
 ('Why is my TikTok RPM dropping?','RPM fluctuates with advertiser demand (Q4 is highest, January lowest), audience geography (US/UK/DE pay most), and the share of qualified vs. unqualified views. Content mix shifts move it too.'),
 ('Do I need 10k followers to earn on TikTok?','For the Creativity Program Beta: 10,000 followers, 100,000 video views in 30 days, 18+, and videos over 1 minute. Requirements vary by region.'),
 ('What counts as a qualified view?','TikTok counts views from real users meeting minimum watch-time and engagement thresholds. Self-views, loops under the threshold, and paid promotion views generally do not qualify.'),
 ('Is TikTok Shop better than the Creativity Program?','For many creators, yes — affiliate commissions on viral product videos routinely beat ad RPMs. A single viral Shop video can out-earn months of program payouts.'),
],
'related':[
 ('tiktok-money-calculator','TikTok Money Calc','🎵','Estimate TikTok creator earnings.'),
 ('youtube-shorts-earnings-calculator','YouTube Shorts Earnings','⚡','Shorts RPM comparison.'),
 ('youtube-money-calculator','YouTube Money & CPM','▶️','YouTube RPM benchmarks.'),
 ('tiktok-coins-calculator','TikTok Coins & Gifts to USD','🪙','Live gift revenue.'),
 ('tiktok-shop-profit-calculator','TikTok Shop Profit Calculator','🛍️','Shop affiliate profits.'),
],
'js_core':'''function core(p){
  var rpm=p.views>0?p.revenue/p.views*1000:0;
  var daily=p.days>0?p.views/p.days:0;
  var monthly=daily*30/1000*rpm;
  return {rpm:rpm,target:p.target/1000*rpm,daily:daily,monthly:monthly,perM:rpm*1000};
}''',
'js_glue':'''function recalc(){
  var p={views:num('views'),revenue:num('revenue'),days:num('days'),target:num('target')};
  var r=core(p);
  setT('resRPM','$'+r.rpm.toFixed(2));
  setT('resTarget',fmtM(r.target));
  setT('resDaily',fmt0(r.daily));
  setT('resMonthly',fmtM(r.monthly)+'/mo');
  setT('resPerM',fmtM(r.perM));
  document.getElementById('shareText').textContent='TikTok RPM $'+r.rpm.toFixed(2)+', target views project '+fmtM(r.target);
}
['views','revenue','days','target'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'views':500000,'revenue':350,'days':30,'target':1000000},
  'expect':{'rpm':0.70,'target':700,'daily':16666.67,'monthly':350}},
 {'inputs':{'views':2000000,'revenue':900,'days':60,'target':5000000},
  'expect':{'rpm':0.45,'target':2250,'daily':33333.33,'monthly':450}},
],
})

# ---------------- 23. tiktok-shop-profit-calculator (creator) ----------------
TOOLS.append({
'slug':'tiktok-shop-profit-calculator','name':'TikTok Shop Profit Calculator','icon':'🛍️','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'TikTok Shop Profit Calculator — Affiliate & Seller Margins',
'desc':'Calculate TikTok Shop profit: commissions, product costs, platform fees, shipping, and ad spend. See true margin per sale.',
'keywords':'TikTok Shop profit calculator, TikTok Shop affiliate commission, TikTok Shop seller fees, TikTok Shop margin calculator',
'h1':'TikTok Shop Profit Calculator',
'intro':'Viral videos are great — margins are better. Enter units, price, commission, and costs to see true TikTok Shop profit.',
'inputs':[
 {'id':'units','label':'Units Sold / Month','value':300,'min':0},
 {'id':'price','label':'Price Per Unit','value':24.99,'prefix':'$','min':0},
 {'id':'commPct','label':'Affiliate Commission (%)','value':15,'suffix':'%','min':0,'max':100},
 {'id':'cost','label':'Product Cost Per Unit','value':8,'prefix':'$','min':0},
 {'id':'ship','label':'Shipping Per Unit','value':2,'prefix':'$','min':0},
 {'id':'feePct','label':'TikTok Platform Fee (%)','value':5,'suffix':'%','min':0,'max':20,'step':0.5},
 {'id':'ads','label':'Monthly Ad Spend','value':400,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly Profit</div>
<div class="mort-result-big" id="resProfit">$0</div>
<div id="resMargin" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💰 Gross Revenue</span><span class="val" id="resRev">$0</span></div>
<div class="mort-row"><span class="lbl">🤝 Affiliate Commissions Paid</span><span class="val" id="resComm">$0</span></div>
<div class="mort-row"><span class="lbl">📦 Product + Shipping Costs</span><span class="val" id="resCogs">$0</span></div>
<div class="mort-row"><span class="lbl">🏷️ Platform Fees</span><span class="val" id="resFee">$0</span></div>
<div class="mort-row"><span class="lbl">📣 Ad Spend</span><span class="val" id="resAds">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Profit Per Unit</span><span class="val" id="resPerUnit">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How TikTok Shop Profit Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">TikTok Shop blends content and commerce: creators earn <strong>affiliate commissions</strong> (typically 10–20%) promoting products, while sellers keep the sale minus fees. Both sides need the same margin math.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Profit = Revenue − Commissions − COGS − Shipping − Platform Fees − Ad Spend<br/>Revenue = Units × Price</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Watch the stacked fees: affiliate commission + ~5% platform/transaction fees + payment processing can total 20–25% before product cost. Sellers should target <strong>30%+ net margins</strong> after everything; affiliates should compare commission per video against their usual sponsorship rates.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>300 units</strong> at <strong>$24.99</strong> = <strong>$7,497</strong> revenue. Costs: 15% affiliate commission ($1,124.55), product $8/unit ($2,400), shipping $2/unit ($600), 5% platform fee ($374.85), ads ($400) = $4,899.40. Profit ≈ <strong>$2,597.60/month</strong> — a <strong>34.6%</strong> margin, or $8.66 per unit.</p>''',
'faqs':[
 ('What commission do TikTok Shop affiliates earn?','Typically 10–20% of the sale price, set by the seller. Top products offer 20%+ during promotions. Commissions are tracked through TikTok\'s affiliate center.'),
 ('What fees does TikTok Shop charge sellers?','Around 5–6% in platform/transaction fees plus payment processing, on top of any affiliate commission you offer. Exact fees vary by region and category.'),
 ('Do I need inventory to earn on TikTok Shop?','No — as an affiliate creator you promote other sellers\' products and earn commission per sale with zero inventory, shipping, or customer service.'),
 ('How are TikTok Shop earnings taxed?','As ordinary business income (Schedule C for creators/affiliates). TikTok issues 1099s above thresholds. Track payouts monthly — they arrive with a delay after the return window.'),
 ('What is a good profit margin on TikTok Shop?','Sellers: 30%+ net after all fees is healthy. Affiliates: compare effective earnings per hour of content against sponsorships — viral Shop videos often win by a wide margin.'),
],
'related':[
 ('tiktok-shop-affiliate-calculator','TikTok Shop Affiliate','🛍️','Affiliate-side earnings detail.'),
 ('amazon-fba-calculator','Amazon FBA Fee Calculator','📦','Compare Amazon fee stacks.'),
 ('ecommerce-profit-comparator','Multi-Platform Profit Comparator','⚖️','Compare marketplace margins.'),
 ('affiliate-commission-calculator','Affiliate Commission Calculator','💸','General affiliate math.'),
 ('tiktok-money-calculator','TikTok Money Calc','🎵','Ad-program earnings.'),
],
'js_core':'''function core(p){
  var rev=p.units*p.price;
  var comm=rev*p.commPct/100;
  var cogs=p.units*(p.cost+p.ship);
  var fee=rev*p.feePct/100;
  var profit=rev-comm-cogs-fee-p.ads;
  return {rev:rev,comm:comm,cogs:cogs,fee:fee,profit:profit,perUnit:p.units>0?profit/p.units:0,margin:rev>0?profit/rev*100:0};
}''',
'js_glue':'''function recalc(){
  var p={units:num('units'),price:num('price'),commPct:num('commPct'),cost:num('cost'),ship:num('ship'),feePct:num('feePct'),ads:num('ads')};
  var r=core(p);
  setT('resProfit',(r.profit>=0?'':'−')+fmtM(Math.abs(r.profit)));
  setT('resMargin','Net margin '+fmtP(r.margin,1));
  setT('resRev',fmtM(r.rev));setT('resComm',fmtM(r.comm));setT('resCogs',fmtM(r.cogs));
  setT('resFee',fmtM(r.fee));setT('resAds',fmtM(r.ads));setT('resPerUnit',fmtM(r.perUnit)+'/unit');
  document.getElementById('shareText').textContent='TikTok Shop profit '+fmtM(r.profit)+'/mo ('+r.margin.toFixed(1)+'% margin)';
}
['units','price','commPct','cost','ship','feePct','ads'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'units':300,'price':24.99,'commPct':15,'cost':8,'ship':2,'feePct':5,'ads':400},
  'expect':{'rev':7497,'comm':1124.55,'cogs':3000,'fee':374.85,'profit':2597.6}},
 {'inputs':{'units':100,'price':49.99,'commPct':20,'cost':15,'ship':3,'feePct':5,'ads':200},
  'expect':{'rev':4999,'comm':999.8,'cogs':1800,'fee':249.95,'profit':1749.25}},
],
})

# ---------------- 24. instagram-engagement-rate-calculator (creator) ----------------
TOOLS.append({
'slug':'instagram-engagement-rate-calculator','name':'Instagram Engagement Rate Calculator','icon':'📸','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'Instagram Engagement Rate Calculator — ER by Followers',
'desc':'Calculate Instagram engagement rate: likes + comments ÷ followers. See how your ER benchmarks against average rates by account size.',
'keywords':'Instagram engagement rate calculator, what is good engagement rate Instagram, ER formula Instagram, average engagement rate by followers',
'h1':'Instagram Engagement Rate Calculator',
'intro':'Brands buy engagement, not followers. Enter your averages to see your true engagement rate and benchmark.',
'inputs':[
 {'id':'followers','label':'Followers','value':50000,'min':0},
 {'id':'likes','label':'Average Likes Per Post','value':2500,'min':0},
 {'id':'comments','label':'Average Comments Per Post','value':120,'min':0},
 {'id':'shares','label':'Average Shares Per Post','value':60,'min':0},
 {'id':'saves','label':'Average Saves Per Post','value':150,'min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Engagement Rate</div>
<div class="mort-result-big" id="resER">0%</div>
<div id="resERSub" style="font-size:0.85rem;font-weight:700;margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💯 True ER (all interactions)</span><span class="val" id="resTrue">—</span></div>
<div class="mort-row"><span class="lbl">❤️ Interactions Per Post</span><span class="val" id="resInter">0</span></div>
<div class="mort-row"><span class="lbl">📊 Benchmark for Your Size</span><span class="val" id="resBench">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Instagram Engagement Rate Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Engagement rate is the <strong>currency of influencer marketing</strong>. A 50k account with 5% engagement routinely out-earns a 500k account with 0.5% — brands know an engaged audience buys.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">ER = (Likes + Comments) ÷ Followers × 100<br/>True ER = (Likes + Comments + Shares + Saves) ÷ Followers × 100</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Benchmarks fall as accounts grow: nano accounts (1–10k) average ~3–5%, mid-tier (50–500k) ~1.5–3%, and mega accounts (1M+) often under 1.5%. Saves and shares weigh heaviest with the algorithm — the "true ER" including them is what savvy brands now request.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>50,000</strong> followers, <strong>2,500</strong> likes + <strong>120</strong> comments per post → ER = 2,620 ÷ 50,000 = <strong>5.24%</strong> — excellent for this size. Including 60 shares and 150 saves, true ER = <strong>5.66%</strong>. This account can credibly charge premium sponsorship rates.</p>''',
'faqs':[
 ('What is a good Instagram engagement rate?','Above 3% is strong for most accounts; 1–3% is average; under 1% suggests ghost followers or content mismatch. Smaller accounts should benchmark higher than large ones.'),
 ('Do saves and shares count as engagement?','Yes — and Instagram\'s algorithm weights them heavily as "meaningful" interactions. Many brands now ask for saves/shares data alongside likes and comments.'),
 ('How can I increase my engagement rate?','Post carousels and reels (highest ER formats), use strong hooks in the first line, reply to every comment in the first hour, and prune ghost followers — fewer, real followers raises ER.'),
 ('Should I calculate ER by followers or reach?','By followers is the industry standard for benchmarking and sponsorships. ER by reach is useful internally for content analysis but is not comparable across accounts.'),
 ('Does buying followers hurt engagement rate?','Devastatingly. Fake followers never interact, so your denominator grows while interactions flatline — cratering ER and signaling low quality to both brands and the algorithm.'),
],
'related':[
 ('instagram-money-calculator','Instagram Sponsored Rate','📸','Price sponsored posts.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','Rate cards from your metrics.'),
 ('ugc-creator-rate-calculator','UGC Creator Rate Calculator','🎬','UGC pricing without followers.'),
 ('channel-growth-calculator','Channel Milestone Tracker','🚀','Growth milestones.'),
 ('tiktok-rpm-calculator','TikTok RPM Calculator','📊','TikTok monetization math.'),
],
'js_core':'''function core(p){
  var er=p.followers>0?(p.likes+p.comments)/p.followers*100:0;
  var tru=p.followers>0?(p.likes+p.comments+p.shares+p.saves)/p.followers*100:0;
  var bench=p.followers<10000?'3–5% (nano)':(p.followers<100000?'2–4% (micro)':(p.followers<1000000?'1.5–3% (mid-tier)':'1–2% (macro)'));
  return {er:er,tru:tru,inter:p.likes+p.comments+p.shares+p.saves,bench:bench,
    rating:er>=4?'🔥 Excellent':(er>=2?'✅ Good':(er>=1?'⚠️ Average':'❌ Low'))};
}''',
'js_glue':'''function recalc(){
  var p={followers:num('followers'),likes:num('likes'),comments:num('comments'),shares:num('shares'),saves:num('saves')};
  var r=core(p);
  setT('resER',fmtP(r.er,2));
  var s=document.getElementById('resERSub');s.textContent=r.rating;
  setT('resTrue',fmtP(r.tru,2));setT('resInter',fmt0(r.inter));setT('resBench',r.bench);
  document.getElementById('shareText').textContent='Instagram ER '+r.er.toFixed(2)+'% ('+fmt0(p.followers)+' followers)';
}
['followers','likes','comments','shares','saves'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'followers':50000,'likes':2500,'comments':120,'shares':60,'saves':150},
  'expect':{'er':5.24,'tru':5.66,'inter':2830}},
 {'inputs':{'followers':100000,'likes':3000,'comments':200,'shares':100,'saves':300},
  'expect':{'er':3.2,'tru':3.6,'inter':3600}},
],
})

# ---------------- 25. ugc-creator-rate-calculator (creator) ----------------
TOOLS.append({
'slug':'ugc-creator-rate-calculator','name':'UGC Creator Rate Calculator','icon':'🎬','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'UGC Creator Rate Calculator — Price Brand Content Right',
'desc':'Price UGC packages: base rate per video × usage rights multipliers (organic, paid ads, whitelisting, buyout) plus revisions and rush fees.',
'keywords':'UGC rate calculator, how much to charge for UGC, UGC pricing 2026, UGC usage rights rates, content creator rates',
'h1':'UGC Creator Rate Calculator',
'intro':'UGC pricing is about usage, not followers. Build a quote from deliverables, usage rights, and add-ons.',
'inputs':[
 {'id':'videos','label':'Number of Videos','value':3,'min':1,'max':50},
 {'id':'base','label':'Base Rate Per Video ($)','value':250,'prefix':'$','min':0},
 {'id':'usage','label':'Usage Rights','type':'select','options':[['1','Organic Only (1×)'],['2.5','Paid Ads — 3 mo (2.5×)'],['1.5','Whitelisting / Spark Ads (1.5×)'],['3','Full Buyout / Perpetuity (3×)']]},
 {'id':'revisions','label':'Extra Revision Rounds','value':0,'min':0,'max':10},
 {'id':'revFee','label':'Fee Per Extra Revision ($)','value':50,'prefix':'$','min':0},
 {'id':'rushPct','label':'Rush Fee (%)','value':0,'suffix':'%','min':0,'max':100},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Suggested Package Price</div>
<div class="mort-result-big" id="resTotal">$0</div>
<div id="resPerVideo" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🎥 Content Base (videos × rate)</span><span class="val" id="resBase">$0</span></div>
<div class="mort-row"><span class="lbl">📜 Usage Rights Multiplier</span><span class="val" id="resMult">—</span></div>
<div class="mort-row"><span class="lbl">✏️ Revision Add-Ons</span><span class="val" id="resRev">$0</span></div>
<div class="mort-row"><span class="lbl">⚡ Rush Fee</span><span class="val" id="resRush">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How UGC Pricing Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">UGC (user-generated content) is brand content that looks organic — and unlike influencer posts, it is priced on <strong>deliverables + usage</strong>, not follower count. A creator with 500 followers can charge the same as one with 50k for the same package.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Pricing Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Price = (Videos × Base Rate × Usage Multiplier) + Revisions + Rush Fee</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Industry ranges: <strong>$150–$350/video</strong> for organic use; paid-ad usage typically <strong>2–3×</strong> base; whitelisting (running ads from your handle) ~1.5×; full buyout 3×+. Always define usage <strong>term limits</strong> (e.g., 3 months paid) — renewals are recurring revenue most creators leave on the table.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>3 videos</strong> at <strong>$250</strong> base = $750. For <strong>paid ads (2.5×)</strong> → <strong>$1,875</strong>. Add one extra revision round ($50) and a 25% rush fee ($481.25) → total <strong>$2,406.25</strong>. The same 3 videos for organic-only use would be just $750 — usage rights are where the money is.</p>''',
'faqs':[
 ('How much should beginners charge for UGC?','$100–$200 per video for organic use is a common starting point. Raise rates every 5–10 brand deals as your portfolio and turnaround speed improve — not your follower count.'),
 ('What are UGC usage rights?','The license a brand buys to use your content: where (organic, paid ads, whitelisting), how long (30 days, 3 months, perpetuity), and in what media. Broader/longer usage = higher multipliers.'),
 ('Should I charge for whitelisting?','Absolutely — whitelisting lets brands run ads from your handle, spending your social capital. 1.5× base per 30–90 days is standard, and many creators charge monthly renewals.'),
 ('How many revisions should I include?','One to two rounds included is standard; charge $50–$100+ per extra round. Unlimited revisions is the fastest way to burn out on a $200 video.'),
 ('Do I need a contract for UGC deals?','Yes — even a one-page agreement covering deliverables, usage term, payment timeline (50% upfront is common), and revision limits. It prevents 90% of creator-brand disputes.'),
],
'related':[
 ('instagram-money-calculator','Instagram Sponsored Rate','📸','Influencer-side pricing.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','Sponsorship rate cards.'),
 ('tiktok-money-calculator','TikTok Money Calc','🎵','Platform earnings baseline.'),
 ('hourly-rate','Freelancer Hourly Rate','💼','Hourly floor for your time.'),
 ('instagram-engagement-rate-calculator','Instagram Engagement Rate','📸','Prove audience quality.'),
],
'js_core':'''function core(p){
  var base=p.videos*p.base;
  var withUsage=base*p.usage;
  var rev=p.revisions*p.revFee;
  var rush=(withUsage+rev)*p.rushPct/100;
  return {total:withUsage+rev+rush,perVideo:p.videos>0?(withUsage+rev+rush)/p.videos:0,base:base,mult:p.usage,rev:rev,rush:rush};
}''',
'js_glue':'''function recalc(){
  var p={videos:num('videos'),base:num('base'),usage:parseFloat(document.getElementById('usage').value),revisions:num('revisions'),revFee:num('revFee'),rushPct:num('rushPct')};
  var r=core(p);
  setT('resTotal',fmtM(r.total));
  setT('resPerVideo',fmtM(r.perVideo)+' per video');
  setT('resBase',fmtM(r.base));setT('resMult',r.mult+'×');
  setT('resRev',fmtM(r.rev));setT('resRush',fmtM(r.rush));
  document.getElementById('shareText').textContent='UGC package: '+fmtM(r.total)+' for '+p.videos+' videos';
}
['videos','base','revisions','revFee','rushPct'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('usage').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'videos':3,'base':250,'usage':1,'revisions':0,'revFee':50,'rushPct':0},
  'expect':{'total':750,'perVideo':250}},
 {'inputs':{'videos':3,'base':250,'usage':2.5,'revisions':1,'revFee':50,'rushPct':25},
  'expect':{'total':2406.25,'perVideo':802.08}},
],
})

# ---------------- 26. podcast-revenue-calculator (creator) ----------------
TOOLS.append({
'slug':'podcast-revenue-calculator','name':'Podcast Revenue Calculator','icon':'🎙️','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'Podcast Revenue Calculator — Ad Income from Downloads',
'desc':'Estimate podcast ad revenue: downloads × CPM × ad slots. Uses industry-standard $18–$30 CPMs for host-read podcast ads.',
'keywords':'podcast revenue calculator, how much do podcasts make, podcast CPM rates, podcast ad revenue calculator, podcast sponsorship rates',
'h1':'Podcast Revenue Calculator',
'intro':'Podcast ads pay per thousand downloads. Enter your downloads, episode cadence, and ad slots to project revenue.',
'inputs':[
 {'id':'dl','label':'Downloads Per Episode','value':8000,'min':0},
 {'id':'eps','label':'Episodes Per Month','value':4,'min':1,'max':31},
 {'id':'slots','label':'Ad Slots Per Episode','value':2,'min':1,'max':6},
 {'id':'cpm','label':'CPM ($ per 1,000 downloads)','value':22,'prefix':'$','min':0,'max':100},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly Ad Revenue</div>
<div class="mort-result-big" id="resMo">$0</div>
<div id="resMoSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🎧 Monthly Downloads</span><span class="val" id="resDl">0</span></div>
<div class="mort-row"><span class="lbl">💵 Revenue Per Episode</span><span class="val" id="resEp">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Projected Annual Revenue</span><span class="val" id="resAnnual">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Revenue Per 1,000 Downloads</span><span class="val" id="resPerK">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Podcast Advertising Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Podcast ads are sold on <strong>CPM</strong> — cost per mille (thousand downloads). Host-read mid-rolls are podcasting\'s premium inventory because listeners trust hosts and cannot easily skip baked-in reads.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Monthly Revenue = (Downloads/Ep × Episodes × Slots ÷ 1,000) × CPM</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Industry CPMs: <strong>$18–$25</strong> for host-read mid-rolls, $15–$20 for pre-rolls, $25–$30+ for niche B2B audiences. Most networks require ~5,000+ downloads/episode for representation; below that, affiliate deals and direct sponsorships pay better than programmatic ads.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>8,000</strong> downloads/episode × <strong>4</strong> episodes × <strong>2</strong> ad slots = 64,000 monthly ad impressions. At a <strong>$22 CPM</strong> → <strong>$1,408/month</strong>, or <strong>$16,896/year</strong>. Each episode earns about $352. Doubling to 8 episodes (or adding a third slot) doubles revenue linearly.</p>''',
'faqs':[
 ('How much do podcasts make per 1,000 downloads?','$18–$30 for host-read ads is the industry standard range. A 10,000-download episode with two mid-rolls at $25 CPM earns about $500.'),
 ('How many downloads do I need to monetize a podcast?','Ad networks typically want 5,000+ downloads per episode. Under that, try affiliate marketing, premium subscriptions, or direct local sponsors — often more lucrative per listener.'),
 ('What is dynamic ad insertion?','Technology that swaps ads into episodes at download time, letting you sell your back catalog\'s downloads months later. Most hosts (Megaphone, ART19, Spotify) offer it.'),
 ('Pre-roll vs mid-roll — which pays more?','Mid-rolls pay the most ($20–$30 CPM) since completion is highest; pre-rolls pay slightly less; post-rolls pay least. Two mid-rolls is the standard episode load.'),
 ('Do video podcasts earn more?','Video unlocks YouTube AdSense plus higher sponsor rates, but production costs rise too. Many top earners run audio + YouTube simultaneously.'),
],
'related':[
 ('podcast-sponsorship-calculator','Podcast Ad Sponsorship','🎙️','Sponsorship pricing detail.'),
 ('substack-calculator','Substack Newsletter Revenue','📰','Newsletter revenue model.'),
 ('newsletter-valuation-calculator','Newsletter Valuation Calculator','📰','Value your audience asset.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','General sponsorship rates.'),
 ('youtube-money-calculator','YouTube Money & CPM','▶️','Video CPM comparison.'),
],
'js_core':'''function core(p){
  var mdl=p.dl*p.eps;
  var mo=mdl/1000*p.slots*p.cpm;
  return {mo:mo,mdl:mdl,ep:p.dl/1000*p.slots*p.cpm,annual:mo*12,perK:p.slots*p.cpm};
}''',
'js_glue':'''function recalc(){
  var p={dl:num('dl'),eps:num('eps'),slots:num('slots'),cpm:num('cpm')};
  var r=core(p);
  setT('resMo',fmtM(r.mo));
  setT('resMoSub','At $'+p.cpm+' CPM × '+p.slots+' slots');
  setT('resDl',fmt0(r.mdl));setT('resEp',fmtM(r.ep));
  setT('resAnnual',fmtM(r.annual)+'/yr');setT('resPerK',fmtM(r.perK));
  document.getElementById('shareText').textContent='Podcast revenue '+fmtM(r.mo)+'/mo ('+fmt0(r.mdl)+' downloads)';
}
['dl','eps','slots','cpm'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'dl':8000,'eps':4,'slots':2,'cpm':22},'expect':{'mo':1408,'mdl':32000,'ep':352,'annual':16896}},
 {'inputs':{'dl':20000,'eps':4,'slots':3,'cpm':25},'expect':{'mo':6000,'mdl':80000,'ep':1500,'annual':72000}},
],
})

# ---------------- 27. newsletter-valuation-calculator (creator) ----------------
TOOLS.append({
'slug':'newsletter-valuation-calculator','name':'Newsletter Valuation Calculator','icon':'📰','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'Newsletter Valuation Calculator — What Is Your Newsletter Worth?',
'desc':'Value a newsletter using ARR multiples (2–4×) and per-subscriber benchmarks. Used by buyers, sellers, and acquirers.',
'keywords':'newsletter valuation calculator, how much is my newsletter worth, Substack valuation, newsletter acquisition multiple, sell newsletter',
'h1':'Newsletter Valuation Calculator',
'intro':'Newsletters trade on revenue multiples and per-subscriber prices. Enter your list stats to get a valuation range.',
'inputs':[
 {'id':'subs','label':'Total Subscribers','value':25000,'min':0},
 {'id':'paidPct','label':'Paid Subscribers (%)','value':8,'suffix':'%','min':0,'max':100,'step':0.5},
 {'id':'arpu','label':'ARPU — Annual Revenue Per Paid Sub ($)','value':60,'prefix':'$','min':0},
 {'id':'multLo','label':'Low Multiple (× ARR)','value':2,'min':0.5,'max':10,'step':0.5},
 {'id':'multHi','label':'High Multiple (× ARR)','value':4,'min':0.5,'max':10,'step':0.5},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Valuation Range</div>
<div class="mort-result-big" id="resVal">$0</div>
<div id="resValSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💳 Paid Subscribers</span><span class="val" id="resPaid">0</span></div>
<div class="mort-row"><span class="lbl">💰 Annual Recurring Revenue</span><span class="val" id="resARR">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Low Valuation</span><span class="val" id="resLo">$0</span></div>
<div class="mort-row"><span class="lbl">📈 High Valuation</span><span class="val" id="resHi">$0</span></div>
<div class="mort-row"><span class="lbl">👤 Value Per Subscriber</span><span class="val" id="resPerSub">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Newsletter Valuations Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Newsletters are valued like small SaaS businesses: on <strong>recurring revenue multiples</strong>, cross-checked against <strong>per-subscriber prices</strong>. Engaged, niche B2B lists command the highest multiples.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">ARR = Subscribers × Paid % × ARPU<br/>Valuation = ARR × Multiple (typically 2–4×)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Market reality: bootstrapped newsletters often sell at <strong>2–4× annual revenue</strong>; premium B2B or high-growth lists can reach 5×+. Per-subscriber benchmarks run <strong>$10–$40</strong> for quality lists. Growth rate, churn, open rates (40%+ is strong), and niche monetization all push you up or down the range.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>25,000</strong> subscribers at <strong>8%</strong> paid = <strong>2,000</strong> paying readers × <strong>$60</strong> ARPU = <strong>$120,000</strong> ARR. At 2–4× → valuation range <strong>$240,000–$480,000</strong>, or $9.60–$19.20 per subscriber. A buyer paying 3× is effectively betting the list sustains revenue for three years.</p>''',
'faqs':[
 ('How much is a newsletter subscriber worth?','$10–$40 per subscriber is the common acquisition range for engaged lists; premium B2B niches go higher. Free subscribers are worth far less than paid ones — value follows revenue.'),
 ('What multiple do newsletters sell for?','2–4× annual recurring revenue is typical for independent newsletters; strategic buyers (media companies, competitors) sometimes pay 5×+ for high-growth or perfectly-fitting lists.'),
 ('Does open rate affect valuation?','Yes. Buyers discount lists with sub-30% open rates as unengaged or stale. 40%+ open rates support top-of-range multiples; verify with 90 days of ESP analytics.'),
 ('Should I sell my newsletter or keep it?','Compare the offer against 2–3 years of projected profit plus the value of your time. Earnouts (getting paid as revenue continues) bridge valuation gaps but add risk.'),
 ('What increases a newsletter\'s value most?','Paid conversion rate, low churn, list growth trend, a defensible niche, diversified revenue (ads + paid + affiliates), and clean email infrastructure (own your list export).'),
],
'related':[
 ('substack-calculator','Substack Newsletter Revenue','📰','Project paid newsletter income.'),
 ('podcast-sponsorship-calculator','Podcast Sponsorship Calculator','🎙️','Audio audience revenue.'),
 ('youtube-channel-valuation-calculator','YouTube Channel Valuation','▶️','Video audience valuation.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','Sponsorship revenue input.'),
 ('customer-ltv-calculator','Customer LTV Calculator','👥','Subscriber lifetime value.'),
],
'js_core':'''function core(p){
  var paid=p.subs*p.paidPct/100;
  var arr=paid*p.arpu;
  return {paid:paid,arr:arr,lo:arr*p.multLo,hi:arr*p.multHi,
    perLo:p.subs>0?arr*p.multLo/p.subs:0,perHi:p.subs>0?arr*p.multHi/p.subs:0};
}''',
'js_glue':'''function recalc(){
  var p={subs:num('subs'),paidPct:num('paidPct'),arpu:num('arpu'),multLo:num('multLo'),multHi:num('multHi')};
  var r=core(p);
  setT('resVal',fmtM(r.lo)+' – '+fmtM(r.hi));
  setT('resValSub',p.multLo+'× – '+p.multHi+'× ARR');
  setT('resPaid',fmt0(r.paid));setT('resARR',fmtM(r.arr)+'/yr');
  setT('resLo',fmtM(r.lo));setT('resHi',fmtM(r.hi));
  setT('resPerSub','$'+r.perLo.toFixed(2)+' – $'+r.perHi.toFixed(2));
  document.getElementById('shareText').textContent='Newsletter valuation '+fmtM(r.lo)+'–'+fmtM(r.hi)+' ('+fmtM(r.arr)+' ARR)';
}
['subs','paidPct','arpu','multLo','multHi'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'subs':25000,'paidPct':8,'arpu':60,'multLo':2,'multHi':4},
  'expect':{'paid':2000,'arr':120000,'lo':240000,'hi':480000}},
 {'inputs':{'subs':100000,'paidPct':5,'arpu':80,'multLo':3,'multHi':5},
  'expect':{'paid':5000,'arr':400000,'lo':1200000,'hi':2000000}},
],
})

# ---------------- 28. youtube-channel-valuation-calculator (creator) ----------------
TOOLS.append({
'slug':'youtube-channel-valuation-calculator','name':'YouTube Channel Valuation Calculator','icon':'▶️','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'YouTube Channel Valuation Calculator — What Is Your Channel Worth?',
'desc':'Value a YouTube channel using monthly revenue multiples (24–36×). For buyers, sellers, and curious creators.',
'keywords':'YouTube channel valuation, how much is my YouTube channel worth, sell YouTube channel, channel acquisition multiple',
'h1':'YouTube Channel Valuation Calculator',
'intro':'Channels trade on revenue multiples like digital businesses. Enter monthly revenue to get a valuation range.',
'inputs':[
 {'id':'rev','label':'Monthly Revenue (ads + sponsors + affiliates)','value':3500,'prefix':'$','min':0},
 {'id':'views','label':'Monthly Views','value':800000,'min':0},
 {'id':'multLo','label':'Low Multiple (× monthly)','value':24,'min':6,'max':60},
 {'id':'multHi','label':'High Multiple (× monthly)','value':36,'min':6,'max':60},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Channel Valuation</div>
<div class="mort-result-big" id="resVal">$0</div>
<div id="resValSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📉 Low Valuation</span><span class="val" id="resLo">$0</span></div>
<div class="mort-row"><span class="lbl">📈 High Valuation</span><span class="val" id="resHi">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Annual Revenue</span><span class="val" id="resAnnual">$0</span></div>
<div class="mort-row"><span class="lbl">👁️ Blended RPM</span><span class="val" id="resRPM">$0</span></div>
<div class="mort-row"><span class="lbl">💵 Value Per 1k Monthly Views</span><span class="val" id="resPerV">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How YouTube Channel Valuations Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Established YouTube channels sell like cash-flowing businesses on marketplaces such as Flippa and Empire Flippers. The standard yardstick: <strong>24–36× average monthly profit</strong> (2–3 years of earnings).</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Valuation = Avg Monthly Revenue × Multiple (24–36×)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">What moves the multiple: revenue <strong>diversification</strong> (sponsors + affiliates + digital products beat AdSense-only), niche CPM (finance/tech pay more), growth trend, evergreen vs. trendy content, and whether the channel depends on the creator\'s face. Faceless, systems-driven channels fetch premiums.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$3,500/month</strong> revenue, <strong>800,000</strong> monthly views. Valuation at 24–36× = <strong>$84,000–$126,000</strong>. Annual revenue = $42,000; blended RPM = $4.38. A buyer at 30× ($105,000) earns their money back in 2.5 years if revenue holds — the standard bet.</p>''',
'faqs':[
 ('Can you legally sell a YouTube channel?','Yes — channel sales are common, though YouTube\'s ToS technically restricts account transfers; in practice, established brokers handle thousands of sales via secure asset-transfer processes. Use escrow.'),
 ('What multiple do YouTube channels sell for?','24–36× monthly revenue is the standard range (2–3× annual). Premium niches with diversified income reach 40×+; declining or AdSense-only channels go for less.'),
 ('Does subscriber count affect the price?','Less than you think — buyers pay for revenue and its durability, not subs. 100k engaged subs in finance beats 1M inactive subs in pranks.'),
 ('What due diligence do buyers do?','12+ months of YouTube Analytics exports, revenue screenshots, traffic source breakdown, copyright strike history, and sponsor contract terms.'),
 ('How do I increase my channel\'s value?','Diversify revenue beyond AdSense, publish evergreen content, document SOPs so it runs without you, and show 6–12 months of stable or growing revenue.'),
],
'related':[
 ('youtube-money-calculator','YouTube Money & CPM','▶️','Revenue inputs for valuation.'),
 ('channel-growth-calculator','Channel Milestone Tracker','🚀','Growth trend buyers want.'),
 ('newsletter-valuation-calculator','Newsletter Valuation Calculator','📰','Value a newsletter asset.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','Sponsor revenue component.'),
 ('youtube-shorts-earnings-calculator','YouTube Shorts Earnings','⚡','Shorts revenue slice.'),
],
'js_core':'''function core(p){
  return {lo:p.rev*p.multLo,hi:p.rev*p.multHi,annual:p.rev*12,
    rpm:p.views>0?p.rev/p.views*1000:0,perV:p.views>0?p.rev*p.multHi/(p.views/1000):0};
}''',
'js_glue':'''function recalc(){
  var p={rev:num('rev'),views:num('views'),multLo:num('multLo'),multHi:num('multHi')};
  var r=core(p);
  setT('resVal',fmtM(r.lo)+' – '+fmtM(r.hi));
  setT('resValSub',p.multLo+'× – '+p.multHi+'× monthly revenue');
  setT('resLo',fmtM(r.lo));setT('resHi',fmtM(r.hi));
  setT('resAnnual',fmtM(r.annual)+'/yr');setT('resRPM','$'+r.rpm.toFixed(2));
  setT('resPerV',fmtM(r.perV));
  document.getElementById('shareText').textContent='Channel valuation '+fmtM(r.lo)+'–'+fmtM(r.hi);
}
['rev','views','multLo','multHi'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'rev':3500,'views':800000,'multLo':24,'multHi':36},
  'expect':{'lo':84000,'hi':126000,'annual':42000,'rpm':4.375}},
 {'inputs':{'rev':10000,'views':3000000,'multLo':30,'multHi':48},
  'expect':{'lo':300000,'hi':480000,'annual':120000,'rpm':3.33}},
],
})

# ---------------- 29. affiliate-commission-calculator (creator) ----------------
TOOLS.append({
'slug':'affiliate-commission-calculator','name':'Affiliate Commission Calculator','icon':'💸','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'Affiliate Commission Calculator — Earnings Per Click',
'desc':'Calculate affiliate earnings: clicks × conversion rate × order value × commission %. See EPC and which levers grow income fastest.',
'keywords':'affiliate commission calculator, affiliate earnings calculator, EPC calculator, affiliate conversion rate, how much do affiliates make',
'h1':'Affiliate Commission Calculator',
'intro':'Affiliate income is a funnel: traffic → conversion → order value → commission. Model every stage.',
'inputs':[
 {'id':'clicks','label':'Monthly Clicks','value':10000,'min':0},
 {'id':'conv','label':'Conversion Rate (%)','value':3,'suffix':'%','min':0,'max':100,'step':0.1},
 {'id':'aov','label':'Average Order Value','value':85,'prefix':'$','min':0},
 {'id':'comm','label':'Commission Rate (%)','value':10,'suffix':'%','min':0,'max':100,'step':0.5},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly Affiliate Earnings</div>
<div class="mort-result-big" id="resEarn">$0</div>
<div id="resEarnSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🛒 Conversions (sales)</span><span class="val" id="resSales">0</span></div>
<div class="mort-row"><span class="lbl">💰 Gross Merchandise Value</span><span class="val" id="resGMV">$0</span></div>
<div class="mort-row"><span class="lbl">📊 EPC (Earnings Per Click)</span><span class="val" id="resEPC">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Projected Annual Earnings</span><span class="val" id="resAnnual">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Affiliate Commissions Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Affiliate marketing pays you for <strong>referred sales</strong>, not clicks or views. Your link tracks buyers (usually for 24 hours to 30 days via cookie), and you earn a percentage of each resulting order.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Earnings = Clicks × Conversion % × AOV × Commission %<br/>EPC = Earnings ÷ Clicks</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>EPC (earnings per click)</strong> is the pro metric — it collapses the whole funnel into one number for comparing programs. Typical conversion rates: 1–5% for content sites, higher for warm email lists. Commission rates range from ~3% (Amazon) to 30–50% (software/SaaS).</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>10,000</strong> clicks at <strong>3%</strong> conversion = <strong>300 sales</strong> × <strong>$85</strong> AOV = $25,500 GMV × <strong>10%</strong> commission = <strong>$2,550/month</strong> ($30,600/year). EPC = <strong>$0.26</strong>. Doubling conversion to 6% doubles earnings without a single extra click — conversion work beats traffic work.</p>''',
'faqs':[
 ('What is a good affiliate conversion rate?','1–3% is typical for blog/content traffic; 5–10%+ for warm email lists or review content with buying intent. "Best X" review posts convert far better than informational content.'),
 ('What is EPC in affiliate marketing?','Earnings Per Click = total commissions ÷ total clicks. It is the best single metric for comparing affiliate programs — a 50% commission program with terrible conversion can have lower EPC than a 5% one.'),
 ('How much do Amazon affiliates make?','Amazon pays ~3–4.5% in most categories with a 24-hour cookie — low rate, but massive conversion. High-ticket software affiliates (30–50%, 30–90 day cookies) often earn more per click.'),
 ('Do I have to disclose affiliate links?','Yes — the FTC requires clear disclosure of material connections, and Amazon specifically requires it. "I earn from qualifying purchases" near the link satisfies it.'),
 ('When do affiliates get paid?','Most programs pay 30–60 days after month-end (after the return window closes), with $10–$100 minimum thresholds. Track payouts — networks occasionally misattribute sales.'),
],
'related':[
 ('amazon-fba-calculator','Amazon FBA Fee Calculator','📦','Amazon-side fee math.'),
 ('tiktok-shop-affiliate-calculator','TikTok Shop Affiliate','🛍️','TikTok affiliate earnings.'),
 ('tiktok-shop-profit-calculator','TikTok Shop Profit Calculator','🛍️','Shop margin detail.'),
 ('ecommerce-profit-comparator','Multi-Platform Profit Comparator','⚖️','Compare platform margins.'),
 ('sponsorship-pricing-calculator','Sponsorship Pricing Calculator','💼','Flat-fee alternative income.'),
],
'js_core':'''function core(p){
  var sales=p.clicks*p.conv/100;
  var gmv=sales*p.aov;
  var earn=gmv*p.comm/100;
  return {sales:sales,gmv:gmv,earn:earn,epc:p.clicks>0?earn/p.clicks:0,annual:earn*12};
}''',
'js_glue':'''function recalc(){
  var p={clicks:num('clicks'),conv:num('conv'),aov:num('aov'),comm:num('comm')};
  var r=core(p);
  setT('resEarn',fmtM(r.earn));
  setT('resEarnSub','EPC $'+r.epc.toFixed(3)+' per click');
  setT('resSales',fmt0(r.sales));setT('resGMV',fmtM(r.gmv));
  setT('resEPC','$'+r.epc.toFixed(3));setT('resAnnual',fmtM(r.annual)+'/yr');
  document.getElementById('shareText').textContent='Affiliate earnings '+fmtM(r.earn)+'/mo (EPC $'+r.epc.toFixed(3)+')';
}
['clicks','conv','aov','comm'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'clicks':10000,'conv':3,'aov':85,'comm':10},
  'expect':{'sales':300,'gmv':25500,'earn':2550,'epc':0.255}},
 {'inputs':{'clicks':50000,'conv':2,'aov':120,'comm':8},
  'expect':{'sales':1000,'gmv':120000,'earn':9600,'epc':0.192}},
],
})

# ---------------- 30. sponsorship-pricing-calculator (creator) ----------------
TOOLS.append({
'slug':'sponsorship-pricing-calculator','name':'Sponsorship Pricing Calculator','icon':'💼','cat':'creator','cat_label':'CREATOR',
'hub':'/creator-calculators','hub_title':'Creator Calculators',
'hub_blurb':'Browse all creator and social media calculators.',
'title':'Sponsorship Pricing Calculator — What to Charge Brands',
'desc':'Price brand sponsorships two ways: CPM on average views and the follower rule-of-thumb. Get a defensible rate range for any platform.',
'keywords':'sponsorship pricing calculator, how much to charge for sponsorship, influencer rate calculator, brand deal pricing, CPM sponsorship rates',
'h1':'Sponsorship Pricing Calculator',
'intro':'Stop guessing your rates. Price sponsorships from views (CPM) and followers — then quote the range with confidence.',
'inputs':[
 {'id':'views','label':'Average Views Per Post/Video','value':150000,'min':0},
 {'id':'cpm','label':'Your CPM ($ per 1,000 views)','value':25,'prefix':'$','min':0,'max':200},
 {'id':'followers','label':'Follower / Subscriber Count','value':100000,'min':0},
 {'id':'cents','label':'Cents Per Follower (rule of thumb)','value':2,'min':0,'max':20,'step':0.5},
 {'id':'deliv','label':'Deliverables in Package','value':1,'min':1,'max':20},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Suggested Rate Range</div>
<div class="mort-result-big" id="resRange" style="font-size:1.5rem;">$0</div>
<div id="resRangeSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📊 CPM-Based Rate (per post)</span><span class="val" id="resCPM">$0</span></div>
<div class="mort-row"><span class="lbl">👥 Follower-Based Rate (per post)</span><span class="val" id="resFol">$0</span></div>
<div class="mort-row"><span class="lbl">📦 Full Package Price</span><span class="val" id="resPack">$0</span></div>
<div class="mort-row"><span class="lbl">💡 Recommended Ask</span><span class="val" id="resAsk">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Sponsorship Pricing Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Brands pay for <strong>attention with intent</strong>. Two industry-standard methods price it: <strong>CPM pricing</strong> (views × rate per thousand) and the <strong>follower rule</strong> (a few cents per follower). Professionals quote from both and negotiate in the overlap.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">CPM Rate = (Avg Views ÷ 1,000) × CPM<br/>Follower Rate = Followers × $0.01–$0.05</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">CPMs vary wildly: <strong>$15–$30</strong> is typical for YouTube integrations, $20–$50+ for niche B2B, $10–$20 for TikTok/Instagram. Add 25–50% for exclusivity, rush timelines, or whitelisting rights. Never publish a fixed rate card publicly — it caps your upside with big brands.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>150,000</strong> avg views at a <strong>$25 CPM</strong> = <strong>$3,750/post</strong>. Follower rule: 100,000 × $0.02 = <strong>$2,000/post</strong>. Suggested range: <strong>$2,000–$3,750</strong> per deliverable — quote $3,750 as the ask with room to meet near the middle. A 3-post package at the midpoint (~$2,875) prices at <strong>$8,625</strong>.</p>''',
'faqs':[
 ('How much should I charge for a sponsored post?','Between the CPM-based rate (views/1000 × $15–$30) and the follower rule ($0.01–$0.05 per follower). Quote the top of the range — brands expect negotiation.'),
 ('What is a good influencer CPM?','$15–$30 for YouTube, $10–$20 for TikTok/Instagram is typical; niche B2B or finance audiences command $30–$50+. Micro-influencers often earn higher effective CPMs due to trust.'),
 ('Should I charge more for exclusivity?','Yes — 25–50% premium for category exclusivity (e.g., no competing brands for 60–90 days). Exclusivity without a premium is leaving money on the table.'),
 ('Flat fee vs. performance-based deals?','Prefer flat fees for predictable income; accept performance bonuses as upside, not the base. Pure affiliate/rev-share deals transfer all risk to you — price them accordingly.'),
 ('How do I raise my rates over time?','Raise 10–20% every 2–3 brand deals or quarterly as metrics grow. Track past deal performance (views, conversions) — proof of ROI justifies every increase.'),
],
'related':[
 ('instagram-money-calculator','Instagram Sponsored Rate','📸','Instagram-specific pricing.'),
 ('youtube-money-calculator','YouTube Money & CPM','▶️','YouTube CPM benchmarks.'),
 ('podcast-sponsorship-calculator','Podcast Ad Sponsorship','🎙️','Podcast sponsor rates.'),
 ('ugc-creator-rate-calculator','UGC Creator Rate Calculator','🎬','UGC package pricing.'),
 ('instagram-engagement-rate-calculator','Instagram Engagement Rate','📸','Engagement proof for brands.'),
],
'js_core':'''function core(p){
  var cpmRate=p.views/1000*p.cpm;
  var folRate=p.followers*p.cents/100;
  var lo=Math.min(cpmRate,folRate),hi=Math.max(cpmRate,folRate);
  var ask=hi;
  return {cpmRate:cpmRate,folRate:folRate,lo:lo,hi:hi,ask:ask,packLo:lo*p.deliv,packHi:hi*p.deliv};
}''',
'js_glue':'''function recalc(){
  var p={views:num('views'),cpm:num('cpm'),followers:num('followers'),cents:num('cents'),deliv:num('deliv')};
  var r=core(p);
  setT('resRange',fmtM(r.lo)+' – '+fmtM(r.hi));
  setT('resRangeSub','per deliverable');
  setT('resCPM',fmtM(r.cpmRate));setT('resFol',fmtM(r.folRate));
  setT('resPack',fmtM(r.packLo)+' – '+fmtM(r.packHi));
  setT('resAsk',fmtM(r.ask)+' (quote high)');
  document.getElementById('shareText').textContent='Sponsorship range '+fmtM(r.lo)+'–'+fmtM(r.hi)+' per post';
}
['views','cpm','followers','cents','deliv'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'views':150000,'cpm':25,'followers':100000,'cents':2,'deliv':1},
  'expect':{'cpmRate':3750,'folRate':2000,'lo':2000,'hi':3750}},
 {'inputs':{'views':500000,'cpm':20,'followers':500000,'cents':2,'deliv':3},
  'expect':{'cpmRate':10000,'folRate':10000,'packLo':30000,'packHi':30000}},
],
})

# ---------------- 31. openai-api-cost-calculator (AI) ----------------
TOOLS.append({
'slug':'openai-api-cost-calculator','name':'OpenAI API Cost Calculator','icon':'🤖','cat':'ai','cat_label':'AI',
'hub':'/ai-calculators','hub_title':'AI Calculators',
'hub_blurb':'Browse all AI and LLM calculators.',
'title':'OpenAI API Cost Calculator — GPT Token Pricing Estimator',
'desc':'Estimate OpenAI API costs: pick a model (GPT-5, GPT-4o, o1, minis), enter input/output tokens, and see per-request and monthly costs.',
'keywords':'OpenAI API cost calculator, GPT-4o pricing calculator, GPT-5 API cost, OpenAI token cost estimator, how much does GPT API cost',
'h1':'OpenAI API Cost Calculator',
'intro':'API bills scale with tokens. Pick your model, enter token volumes, and see exactly what OpenAI will charge.',
'inputs':[
 {'id':'model','label':'Model','type':'select','options':[['1.25|10','GPT-5 — $1.25 / $10 per 1M'],['2.50|10','GPT-4o — $2.50 / $10 per 1M'],['2.00|8','GPT-4.1 — $2.00 / $8 per 1M'],['0.40|1.60','GPT-4.1 mini — $0.40 / $1.60 per 1M'],['0.15|0.60','GPT-4o mini — $0.15 / $0.60 per 1M'],['15|60','o1 — $15 / $60 per 1M']]},
 {'id':'inTok','label':'Monthly Input Tokens','value':2000000,'min':0},
 {'id':'outTok','label':'Monthly Output Tokens','value':1000000,'min':0},
 {'id':'reqs','label':'Monthly API Requests','value':100000,'min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly API Cost</div>
<div class="mort-result-big" id="resTotal">$0</div>
<div id="resSplit" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📥 Input Token Cost</span><span class="val" id="resIn">$0</span></div>
<div class="mort-row"><span class="lbl">📤 Output Token Cost</span><span class="val" id="resOut">$0</span></div>
<div class="mort-row"><span class="lbl">🔁 Cost Per Request</span><span class="val" id="resPerReq">$0</span></div>
<div class="mort-row"><span class="lbl">💵 Cost Per 1,000 Requests</span><span class="val" id="resPerK">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Projected Annual Cost</span><span class="val" id="resAnnual">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How OpenAI API Pricing Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">OpenAI charges per <strong>million tokens</strong>, split into cheaper <strong>input</strong> tokens (your prompt) and pricier <strong>output</strong> tokens (the completion). Roughly: 1 token ≈ ¾ of an English word, so 1,000 words ≈ 1,333 tokens.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Cost = (Input Tokens ÷ 1M × Input Price) + (Output Tokens ÷ 1M × Output Price)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Output tokens cost 2–4× input tokens because generation is compute-heavy. The mini models are 10–30× cheaper than flagships — most apps should <strong>prototype on the flagship, then downgrade</strong> per endpoint after quality testing. Prompt caching (50%+ off repeated prefixes) and batch API (50% off, slower) cut bills further. Prices change; verify on OpenAI\'s pricing page.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>GPT-4o</strong> ($2.50 in / $10 out per 1M) with <strong>2M</strong> input and <strong>1M</strong> output tokens/month: input = 2 × $2.50 = <strong>$5.00</strong>, output = 1 × $10 = <strong>$10.00</strong>, total <strong>$15.00/month</strong>. Across 100,000 requests that is <strong>$0.00015/request</strong> — fifteen-hundredths of a cent. Switching to GPT-4o mini would cut it to about $0.90.</p>''',
'faqs':[
 ('How much does the GPT-4o API cost?','About $2.50 per million input tokens and $10 per million output tokens. A typical short chat request (500 in / 200 out) costs roughly $0.003.'),
 ('What is the cheapest OpenAI model?','The mini models (GPT-4o mini, GPT-4.1 mini) at ~$0.15–$0.40 input per 1M tokens — roughly 15× cheaper than flagships, and sufficient for classification, extraction, and simple chat.'),
 ('Do cached tokens cost less?','Yes — OpenAI\'s prompt caching discounts repeated prompt prefixes by 50%+ automatically once cached. Design prompts with stable prefixes to maximize cache hits.'),
 ('Input vs output tokens — which costs more?','Output tokens, typically 2–4× the input price. Long generations (reports, code) dominate bills — constrain max_tokens where quality allows.'),
 ('How do I reduce my OpenAI API bill?','Use mini models where quality suffices, enable prompt caching, use the Batch API for offline work (50% off), trim system prompts, and set max_tokens caps.'),
],
'related':[
 ('claude-api-cost-calculator','Claude API Cost Calculator','🧠','Compare Anthropic pricing.'),
 ('ai-token-calculator','AI Token Calculator','🔢','Count tokens before pricing.'),
 ('ai-prompt-cost-calculator','AI Prompt Cost Calculator','🤖','LLM prompt cost planning.'),
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','Model API costs into SaaS margins.'),
],
'js_core':'''function core(p){
  var inC=p.inTok/1e6*p.pin, outC=p.outTok/1e6*p.pout;
  var tot=inC+outC;
  return {inC:inC,outC:outC,tot:tot,perReq:p.reqs>0?tot/p.reqs:0,perK:p.reqs>0?tot/p.reqs*1000:0,annual:tot*12};
}''',
'js_glue':'''function parseModel(){var v=document.getElementById('model').value.split('|');return {pin:parseFloat(v[0]),pout:parseFloat(v[1])};}
function recalc(){
  var m=parseModel();
  var p={pin:m.pin,pout:m.pout,inTok:num('inTok'),outTok:num('outTok'),reqs:num('reqs')};
  var r=core(p);
  setT('resTotal',fmtM(r.tot)+'/mo');
  setT('resSplit','Input '+fmtM(r.inC)+' · Output '+fmtM(r.outC));
  setT('resIn',fmtM(r.inC));setT('resOut',fmtM(r.outC));
  setT('resPerReq','$'+r.perReq.toFixed(5));setT('resPerK','$'+r.perK.toFixed(4));
  setT('resAnnual',fmtM(r.annual)+'/yr');
  document.getElementById('shareText').textContent='OpenAI API cost '+fmtM(r.tot)+'/mo';
}
['inTok','outTok','reqs'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('model').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'pin':2.50,'pout':10,'inTok':2000000,'outTok':1000000,'reqs':100000},
  'expect':{'inC':5,'outC':10,'tot':15,'perReq':0.00015}},
 {'inputs':{'pin':0.15,'pout':0.60,'inTok':10000000,'outTok':2000000,'reqs':500000},
  'expect':{'inC':1.5,'outC':1.2,'tot':2.7}},
],
})

# ---------------- 32. claude-api-cost-calculator (AI) ----------------
TOOLS.append({
'slug':'claude-api-cost-calculator','name':'Claude API Cost Calculator','icon':'🧠','cat':'ai','cat_label':'AI',
'hub':'/ai-calculators','hub_title':'AI Calculators',
'hub_blurb':'Browse all AI and LLM calculators.',
'title':'Claude API Cost Calculator — Anthropic Token Pricing Estimator',
'desc':'Estimate Claude API costs: pick a model (Opus, Sonnet, Haiku), enter tokens, and factor in 90%-off prompt cache hits.',
'keywords':'Claude API cost calculator, Anthropic API pricing, Sonnet vs Haiku cost, Claude prompt caching discount, Claude token price',
'h1':'Claude API Cost Calculator',
'intro':'Claude pricing rewards prompt caching — cached input tokens cost ~90% less. Model your real workload here.',
'inputs':[
 {'id':'model','label':'Model','type':'select','options':[['15|75','Claude Opus 4.1 — $15 / $75 per 1M'],['3|15','Claude Sonnet 4.5 — $3 / $15 per 1M'],['1|5','Claude Haiku 4.5 — $1 / $5 per 1M'],['0.80|4','Claude Haiku 3.5 — $0.80 / $4 per 1M']]},
 {'id':'inTok','label':'Monthly Input Tokens','value':5000000,'min':0},
 {'id':'outTok','label':'Monthly Output Tokens','value':2000000,'min':0},
 {'id':'cachePct','label':'Cached Input Tokens (%)','value':50,'suffix':'%','min':0,'max':100},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Est. Monthly API Cost</div>
<div class="mort-result-big" id="resTotal">$0</div>
<div id="resSplit" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📥 Input Token Cost (after cache)</span><span class="val" id="resIn">$0</span></div>
<div class="mort-row"><span class="lbl">📤 Output Token Cost</span><span class="val" id="resOut">$0</span></div>
<div class="mort-row"><span class="lbl">💾 Cache Savings</span><span class="val" id="resSave">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Projected Annual Cost</span><span class="val" id="resAnnual">$0</span></div>
<div class="mort-row"><span class="lbl">⚖️ vs. No Cache</span><span class="val" id="resNoCache">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Claude API Pricing Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Anthropic charges per million tokens with three tiers: <strong>Opus</strong> (flagship intelligence), <strong>Sonnet</strong> (balanced), <strong>Haiku</strong> (fast and cheap). Its killer feature is <strong>prompt caching</strong>: repeated prompt prefixes are billed at roughly <strong>10% of the input price</strong>.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formula</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Effective Input = Fresh + Cached × 0.10<br/>Cost = (Effective Input ÷ 1M × Input Price) + (Output ÷ 1M × Output Price)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Agentic workloads with long system prompts and tool definitions routinely hit 70–90% cache rates, cutting input bills by more than half. Sonnet handles most production workloads; reserve Opus for the hardest reasoning; Haiku for classification and high-volume simple tasks. Prices change; verify on Anthropic\'s pricing page.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Sonnet 4.5</strong> ($3 in / $15 out) with <strong>5M</strong> input tokens at <strong>50%</strong> cache hit rate and <strong>2M</strong> output: effective input = 2.5M + 2.5M × 0.1 = <strong>2.75M</strong> → $8.25 input + $30.00 output = <strong>$38.25/month</strong>. Without caching it would be $45.00 — caching saves <strong>$6.75</strong>. Annual cost ≈ <strong>$459</strong>.</p>''',
'faqs':[
 ('How does Claude prompt caching work?','Mark stable prompt prefixes (system prompt, few-shot examples, tool schemas) as cacheable; repeat requests hit the cache and bill at ~10% of input price. Cache writes cost extra but pay off within a few hits.'),
 ('Sonnet vs Haiku — which should I use?','Sonnet for general production quality; Haiku for high-volume simple tasks (classification, extraction, moderation) at ~⅓ the price. Benchmark both on your evals before deciding.'),
 ('When is Opus worth it?','For the hardest reasoning — complex agentic coding, deep research, difficult math. Most apps use Opus selectively (fallback tier) with Sonnet as the default.'),
 ('How much can caching save?','With 80%+ cache hit rates on long prompts, input costs drop 70%+. Agentic loops re-sending tool definitions are the biggest winners.'),
 ('Claude vs GPT-4o on cost?','Comparable flagships: Sonnet 4.5 ($3/$15) vs GPT-4o ($2.50/$10) — GPT-4o is slightly cheaper sticker-price, but Claude\'s deeper cache discount can flip the comparison on cacheable workloads.'),
],
'related':[
 ('openai-api-cost-calculator','OpenAI API Cost Calculator','🤖','Compare OpenAI pricing.'),
 ('ai-token-calculator','AI Token Calculator','🔢','Count tokens before pricing.'),
 ('ai-prompt-cost-calculator','AI Prompt Cost Calculator','🤖','LLM prompt cost planning.'),
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','Model API costs into SaaS margins.'),
],
'js_core':'''function core(p){
  var effIn=p.inTok*(1-p.cachePct/100)+p.inTok*(p.cachePct/100)*0.1;
  var inC=effIn/1e6*p.pin, outC=p.outTok/1e6*p.pout;
  var noCache=p.inTok/1e6*p.pin+outC;
  return {inC:inC,outC:outC,tot:inC+outC,save:noCache-(inC+outC),noCache:noCache,annual:(inC+outC)*12};
}''',
'js_glue':'''function parseModel(){var v=document.getElementById('model').value.split('|');return {pin:parseFloat(v[0]),pout:parseFloat(v[1])};}
function recalc(){
  var m=parseModel();
  var p={pin:m.pin,pout:m.pout,inTok:num('inTok'),outTok:num('outTok'),cachePct:num('cachePct')};
  var r=core(p);
  setT('resTotal',fmtM(r.tot)+'/mo');
  setT('resSplit','Input '+fmtM(r.inC)+' · Output '+fmtM(r.outC));
  setT('resIn',fmtM(r.inC));setT('resOut',fmtM(r.outC));
  setT('resSave','−'+fmtM(r.save));setT('resAnnual',fmtM(r.annual)+'/yr');
  setT('resNoCache',fmtM(r.noCache)+'/mo');
  document.getElementById('shareText').textContent='Claude API cost '+fmtM(r.tot)+'/mo';
}
['inTok','outTok','cachePct'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('model').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'pin':3,'pout':15,'inTok':5000000,'outTok':2000000,'cachePct':50},
  'expect':{'inC':8.25,'outC':30,'tot':38.25,'save':6.75}},
 {'inputs':{'pin':1,'pout':5,'inTok':20000000,'outTok':5000000,'cachePct':80},
  'expect':{'inC':5.6,'outC':25,'tot':30.6}},
],
})

# ---------------- 33. ai-token-calculator (AI) ----------------
TOOLS.append({
'slug':'ai-token-calculator','name':'AI Token Calculator','icon':'🔢','cat':'ai','cat_label':'AI',
'hub':'/ai-calculators','hub_title':'AI Calculators',
'hub_blurb':'Browse all AI and LLM calculators.',
'title':'AI Token Calculator — Words to Tokens & Context Window',
'desc':'Convert text length to LLM tokens, check context-window usage, and estimate the cost of one request at current model prices.',
'keywords':'AI token calculator, words to tokens, how many tokens in 1000 words, context window calculator, token counter estimator',
'h1':'AI Token Calculator',
'intro':'Estimate tokens from any text length, see how much context window it fills, and what a single request costs.',
'inputs':[
 {'id':'chars','label':'Text Length (characters)','value':100000,'min':0},
 {'id':'window','label':'Context Window','type':'select','options':[['128000','128K tokens (GPT-4o, Sonnet)'],['200000','200K tokens (Claude)'],['1000000','1M tokens (Gemini, GPT-4.1)'],['32000','32K tokens (smaller models)']]},
 {'id':'price','label':'Input Price ($ per 1M tokens)','value':1.25,'prefix':'$','min':0,'max':100,'step':0.05},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Estimated Tokens</div>
<div class="mort-result-big" id="resTok">0</div>
<div id="resWords" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🪟 Context Window Used</span><span class="val" id="resWin">—</span></div>
<div class="mort-row"><span class="lbl">💵 Cost Per Request (input)</span><span class="val" id="resCost">$0</span></div>
<div class="mort-row"><span class="lbl">📄 Equivalent Pages</span><span class="val" id="resPages">0</span></div>
<div class="mort-row"><span class="lbl">📚 1M-Token Scale</span><span class="val" id="resScale">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Token Estimation Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">LLMs don\'t read characters or words — they read <strong>tokens</strong>, sub-word chunks averaging ~4 characters in English. Every API bill, context limit, and rate limit is denominated in tokens, so estimating them is step zero of AI cost control.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Rules of Thumb</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Tokens ≈ Characters ÷ 4 ≈ Words × 1.33<br/>Window % = Tokens ÷ Context Window × 100</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Estimates vary by content: code and non-English text tokenize less efficiently (more tokens per character), while plain English is close to 4 chars/token. For exact counts use a tokenizer (tiktoken); for budgeting, this approximation is within ~10%. Remember outputs count against the window too.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>100,000</strong> characters ≈ <strong>25,000 tokens</strong> (~18,750 words, ~50 pages). In a <strong>128K</strong> window that fills <strong>19.5%</strong>. At <strong>$1.25/M</strong> input, one such request costs <strong>$0.031</strong> in input tokens — about 3 cents. A million tokens is roughly 40 novels\' worth of text.</p>''',
'faqs':[
 ('How many tokens are in 1,000 words?','About 1,333 tokens for typical English prose (words × 1.33). Code can run 1,500–2,000 tokens per 1,000 words.'),
 ('What is a context window?','The maximum tokens a model can consider in one request — input plus output combined. 128K ≈ 300 pages; 1M ≈ 1,500 pages of text.'),
 ('Why do tokens matter for cost?','APIs bill per token, so token count × price = your bill. Long system prompts and chat histories silently inflate every request\'s input tokens.'),
 ('Is this exact?','No — it\'s an estimate within ~10% for English prose. Exact tokenization depends on the model\'s tokenizer (tiktoken for OpenAI, different ones for Claude/Gemini).'),
 ('How do I reduce token usage?','Trim system prompts, summarize chat history instead of resending it, use prompt caching for repeated prefixes, and pick smaller models for simple subtasks.'),
],
'related':[
 ('openai-api-cost-calculator','OpenAI API Cost Calculator','🤖','Price OpenAI workloads.'),
 ('claude-api-cost-calculator','Claude API Cost Calculator','🧠','Price Claude workloads.'),
 ('ai-prompt-cost-calculator','AI Prompt Cost Calculator','🤖','LLM prompt cost planning.'),
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','Model API costs into SaaS margins.'),
],
'js_core':'''function core(p){
  var tok=p.chars/4;
  var words=p.chars/5;
  return {tok:tok,words:words,winPct:p.window>0?tok/p.window*100:0,
    cost:tok/1e6*p.price,pages:words/500,scale:tok>0?(1e6/tok):0};
}''',
'js_glue':'''function recalc(){
  var p={chars:num('chars'),window:parseFloat(document.getElementById('window').value),price:num('price')};
  var r=core(p);
  setT('resTok',fmt0(r.tok)+' tokens');
  setT('resWords','≈ '+fmt0(r.words)+' words');
  setT('resWin',fmtP(r.winPct,1)+' of window');
  setT('resCost','$'+r.cost.toFixed(4)+' / request');
  setT('resPages','≈ '+fmt0(r.pages)+' pages');
  setT('resScale','1M tokens ≈ '+r.scale.toFixed(1)+'× this text');
  document.getElementById('shareText').textContent=fmt0(r.tok)+' tokens ≈ $'+r.cost.toFixed(4)+'/request';
}
['chars','price'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('window').addEventListener('change',recalc);
recalc();''',
'tests':[
 {'inputs':{'chars':100000,'window':128000,'price':1.25},
  'expect':{'tok':25000,'winPct':19.53,'cost':0.03125}},
 {'inputs':{'chars':500000,'window':200000,'price':3},
  'expect':{'tok':125000,'winPct':62.5,'cost':0.375}},
],
})

# ---------------- 34. saas-mrr-calculator (business) ----------------
TOOLS.append({
'slug':'saas-mrr-calculator','name':'SaaS MRR Calculator','icon':'💰','cat':'business','cat_label':'BUSINESS',
'hub':'/business-calculators','hub_title':'Business Calculators',
'hub_blurb':'Browse all business and finance calculators.',
'title':'SaaS MRR Calculator — Monthly Recurring Revenue Growth',
'desc':'Calculate SaaS MRR and ARR, model expansion vs. churn, and project next month\'s recurring revenue.',
'keywords':'SaaS MRR calculator, monthly recurring revenue formula, ARR calculator, expansion revenue, net revenue retention',
'h1':'SaaS MRR Calculator',
'intro':'MRR is the pulse of a SaaS business. Enter customers, ARPU, expansion, and churn to see where revenue is heading.',
'inputs':[
 {'id':'cust','label':'Paying Customers','value':500,'min':0},
 {'id':'arpu','label':'ARPU (Monthly $ Per Customer)','value':49,'prefix':'$','min':0},
 {'id':'expPct','label':'Expansion Revenue (% of MRR)','value':5,'suffix':'%','min':0,'max':50,'step':0.5},
 {'id':'churnPct','label':'Revenue Churn (% of MRR)','value':3,'suffix':'%','min':0,'max':50,'step':0.5},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Current MRR</div>
<div class="mort-result-big" id="resMRR">$0</div>
<div id="resMRRSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">📅 ARR (Annualized)</span><span class="val" id="resARR">$0</span></div>
<div class="mort-row"><span class="lbl">📈 Expansion Revenue / Mo</span><span class="val" id="resExp">$0</span></div>
<div class="mort-row"><span class="lbl">📉 Churned Revenue / Mo</span><span class="val" id="resChurn">$0</span></div>
<div class="mort-row"><span class="lbl">🔮 Projected MRR (next month)</span><span class="val" id="resNext">$0</span></div>
<div class="mort-row"><span class="lbl">🧭 Net Revenue Retention</span><span class="val" id="resNRR">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How MRR Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>MRR (monthly recurring revenue)</strong> normalizes all subscription revenue into a monthly figure. It is the single number investors, acquirers, and founders track — ARR is just MRR × 12.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">MRR = Customers × ARPU<br/>Net Change = Expansion − Churn<br/>NRR = (Starting MRR + Expansion − Churn) ÷ Starting MRR</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>Net Revenue Retention (NRR)</strong> is the quality metric: above 100% means existing customers grow revenue faster than churn eats it (best-in-class SaaS: 110–130%). Below 100% means you are on a treadmill — growth depends entirely on new sales.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>500</strong> customers × <strong>$49</strong> ARPU = <strong>$24,500 MRR</strong> ($294,000 ARR). With 5% expansion ($1,225) and 3% churn ($735), net change = <strong>+$490/month</strong> → next month ≈ <strong>$24,990 MRR</strong>. NRR = 102% — healthy, expansion-led growth.</p>''',
'faqs':[
 ('What is the difference between MRR and ARR?','MRR is monthly recurring revenue; ARR = MRR × 12. Use MRR for operations, ARR for fundraising and valuation conversations.'),
 ('What is good net revenue retention?','100%+ is good; 110–130% is best-in-class (expansion outpaces churn). Below 90% signals serious churn or downsell problems.'),
 ('Should one-time fees count in MRR?','No — MRR is recurring revenue only. Track one-time setup/professional-services fees separately to avoid inflating the core metric.'),
 ('How do annual plans affect MRR?','Divide the annual contract by 12 and recognize it monthly. A $1,188 annual plan = $99 MRR — never book the full amount in one month.'),
 ('What MRR multiple do SaaS companies sell for?','Growth-stage SaaS: roughly 5–10× ARR depending on growth rate and NRR; slower or churning businesses trade much lower.'),
],
'related':[
 ('saas-churn-calculator','SaaS Churn Calculator','📉','Churn deep-dive.'),
 ('customer-ltv-calculator','Customer LTV Calculator','👥','Lifetime value from ARPU.'),
 ('startup-runway-calculator','Startup Runway Calculator','✈️','Burn vs. MRR coverage.'),
 ('markup-vs-margin-calculator','Markup vs Margin Calculator','🏷️','Set ARPU profitably.'),
 ('break-even','Break-Even Calculator','⚖️','When revenue covers costs.'),
],
'js_core':'''function core(p){
  var mrr=p.cust*p.arpu;
  var exp=mrr*p.expPct/100, churn=mrr*p.churnPct/100;
  var next=mrr+exp-churn;
  return {mrr:mrr,arr:mrr*12,exp:exp,churn:churn,next:next,nrr:mrr>0?next/mrr*100:0,net:exp-churn};
}''',
'js_glue':'''function recalc(){
  var p={cust:num('cust'),arpu:num('arpu'),expPct:num('expPct'),churnPct:num('churnPct')};
  var r=core(p);
  setT('resMRR',fmtM(r.mrr)+'/mo');
  setT('resMRRSub','Net '+(r.net>=0?'+':'−')+fmtM(Math.abs(r.net))+'/mo');
  setT('resARR',fmtM(r.arr)+'/yr');setT('resExp','+'+fmtM(r.exp));
  setT('resChurn','−'+fmtM(r.churn));setT('resNext',fmtM(r.next)+'/mo');
  setT('resNRR',fmtP(r.nrr,1));
  document.getElementById('shareText').textContent='MRR '+fmtM(r.mrr)+'/mo, NRR '+r.nrr.toFixed(1)+'%';
}
['cust','arpu','expPct','churnPct'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'cust':500,'arpu':49,'expPct':5,'churnPct':3},
  'expect':{'mrr':24500,'arr':294000,'exp':1225,'churn':735,'next':24990,'nrr':102}},
 {'inputs':{'cust':2000,'arpu':29,'expPct':4,'churnPct':6},
  'expect':{'mrr':58000,'arr':696000,'next':56840,'nrr':98}},
],
})

# ---------------- 35. saas-churn-calculator (business) ----------------
TOOLS.append({
'slug':'saas-churn-calculator','name':'SaaS Churn Calculator','icon':'📉','cat':'business','cat_label':'BUSINESS',
'hub':'/business-calculators','hub_title':'Business Calculators',
'hub_blurb':'Browse all business and finance calculators.',
'title':'SaaS Churn Calculator — Logo & Revenue Churn Rates',
'desc':'Calculate customer churn rate and revenue churn rate, retention, and the growth you need just to stand still.',
'keywords':'SaaS churn calculator, churn rate formula, logo churn vs revenue churn, customer retention rate, net churn calculator',
'h1':'SaaS Churn Calculator',
'intro':'Churn is the silent killer of SaaS. Measure logo churn and revenue churn to see how fast the bucket leaks.',
'inputs':[
 {'id':'start','label':'Customers at Start of Period','value':1000,'min':0},
 {'id':'lost','label':'Customers Lost in Period','value':40,'min':0},
 {'id':'new','label':'New Customers Added','value':80,'min':0},
 {'id':'mrrStart','label':'MRR at Start of Period ($)','value':50000,'prefix':'$','min':0},
 {'id':'mrrLost','label':'MRR Lost to Churn ($)','value':1500,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Customer (Logo) Churn Rate</div>
<div class="mort-result-big" id="resChurn">0%</div>
<div id="resChurnSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💵 Revenue Churn Rate</span><span class="val" id="resRev">—</span></div>
<div class="mort-row"><span class="lbl">🔁 Customer Retention Rate</span><span class="val" id="resRet">—</span></div>
<div class="mort-row"><span class="lbl">👥 Customers at End</span><span class="val" id="resEnd">0</span></div>
<div class="mort-row"><span class="lbl">📈 Net Customer Growth</span><span class="val" id="resNet">0</span></div>
<div class="mort-row"><span class="lbl">🎯 New Customers Needed to Break Even</span><span class="val" id="resBE">0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Churn Measurement Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>Churn rate</strong> is the share of customers (or revenue) lost in a period. Two flavors matter: <strong>logo churn</strong> (customers lost) and <strong>revenue churn</strong> (MRR lost). Revenue churn is the money metric — losing small accounts while keeping big ones shows up here.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Logo Churn = Lost Customers ÷ Starting Customers × 100<br/>Revenue Churn = Lost MRR ÷ Starting MRR × 100<br/>Retention = 100% − Churn</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Benchmarks (monthly): SMB SaaS 3–7% logo churn is common; enterprise <1–2%. The magic threshold is <strong>net revenue retention ≥100%</strong> — expansion from remaining customers fully offsets churn. Annualize monthly churn × 12 for yearly, but compounding makes the true annual figure higher.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>1,000</strong> customers, <strong>40</strong> lost → logo churn = <strong>4%</strong>, retention 96%. MRR churn: $1,500 ÷ $50,000 = <strong>3%</strong>. With 80 new customers added, net growth = <strong>+40</strong> (1,040 end). Break-even needs just 40 new customers — this business grows comfortably.</p>''',
'faqs':[
 ('What is a good churn rate for SaaS?','Monthly: under 2% is excellent, 3–5% typical for SMB, 5–7%+ is a red flag. Annual enterprise churn under 10% is strong. Context matters — price point and contract length drive huge differences.'),
 ('Logo churn vs revenue churn?','Logo churn counts customers; revenue churn counts dollars. If big accounts stay and small ones leave, revenue churn looks better — track both, optimize revenue churn.'),
 ('What is net revenue churn?','Gross churn minus expansion (upsells) from remaining customers. Negative net churn (expansion > churn) is the hallmark of best-in-class SaaS.'),
 ('How do I reduce churn?','Onboarding that drives time-to-value, usage monitoring with save plays, annual plans (structural retention), and exit interviews that feed the roadmap.'),
 ('Should churn be monthly or annual?','Measure monthly for operations, report annual for strategy. Never just multiply monthly × 12 — compounding means 5% monthly ≈ 46% annual, not 60%.'),
],
'related':[
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','MRR the churn eats.'),
 ('customer-ltv-calculator','Customer LTV Calculator','👥','Churn drives lifetime value.'),
 ('cac-ltv-calculator','CAC to LTV Ratio Calculator','⚖️','How churn hits unit economics.'),
 ('startup-runway-calculator','Startup Runway Calculator','✈️','Burn vs. growth math.'),
 ('break-even','Break-Even Calculator','⚖️','Growth break-even point.'),
],
'js_core':'''function core(p){
  var logo=p.start>0?p.lost/p.start*100:0;
  var rev=p.mrrStart>0?p.mrrLost/p.mrrStart*100:0;
  var end=p.start-p.lost+p.new;
  return {logo:logo,rev:rev,ret:100-logo,end:end,net:p.new-p.lost,be:p.lost,
    rating:logo<2?'✅ Excellent':(logo<=5?'⚠️ Watch it':'❌ Critical')};
}''',
'js_glue':'''function recalc(){
  var p={start:num('start'),lost:num('lost'),new:num('new'),mrrStart:num('mrrStart'),mrrLost:num('mrrLost')};
  var r=core(p);
  setT('resChurn',fmtP(r.logo,2));
  setT('resChurnSub',r.rating);
  setT('resRev',fmtP(r.rev,2));setT('resRet',fmtP(r.ret,2));
  setT('resEnd',fmt0(r.end));
  setT('resNet',(r.net>=0?'+':'−')+fmt0(Math.abs(r.net)));
  setT('resBE',fmt0(r.be)+' customers');
  document.getElementById('shareText').textContent='Churn '+r.logo.toFixed(2)+'% logo, '+r.rev.toFixed(2)+'% revenue';
}
['start','lost','new','mrrStart','mrrLost'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'start':1000,'lost':40,'new':80,'mrrStart':50000,'mrrLost':1500},
  'expect':{'logo':4,'rev':3,'ret':96,'end':1040,'net':40}},
 {'inputs':{'start':5000,'lost':300,'new':500,'mrrStart':250000,'mrrLost':20000},
  'expect':{'logo':6,'rev':8,'end':5200,'net':200}},
],
})

# ---------------- 36. customer-ltv-calculator (business) ----------------
TOOLS.append({
'slug':'customer-ltv-calculator','name':'Customer LTV Calculator','icon':'👥','cat':'business','cat_label':'BUSINESS',
'hub':'/business-calculators','hub_title':'Business Calculators',
'hub_blurb':'Browse all business and finance calculators.',
'title':'Customer Lifetime Value (LTV) Calculator — LTV:CAC Ratio',
'desc':'Calculate customer lifetime value from ARPU, margin, and churn. Compare LTV to CAC — the ratio that decides if growth is profitable.',
'keywords':'customer lifetime value calculator, LTV formula, LTV to CAC ratio, CLV calculator SaaS, average customer lifespan',
'h1':'Customer Lifetime Value Calculator',
'intro':'LTV tells you what a customer is worth over their lifetime — and how much you can afford to spend acquiring one.',
'inputs':[
 {'id':'arpu','label':'ARPU (Monthly $ Per Customer)','value':120,'prefix':'$','min':0},
 {'id':'margin','label':'Gross Margin (%)','value':80,'suffix':'%','min':0,'max':100},
 {'id':'churn','label':'Monthly Churn Rate (%)','value':5,'suffix':'%','min':0.1,'max':100,'step':0.1},
 {'id':'cac','label':'Customer Acquisition Cost (CAC) ($)','value':300,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Customer Lifetime Value</div>
<div class="mort-result-big" id="resLTV">$0</div>
<div id="resLTVSub" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">⏳ Average Customer Lifespan</span><span class="val" id="resLife">—</span></div>
<div class="mort-row"><span class="lbl">💵 Gross Profit Per Month</span><span class="val" id="resGP">$0</span></div>
<div class="mort-row"><span class="lbl">⚖️ LTV : CAC Ratio</span><span class="val" id="resRatio">—</span></div>
<div class="mort-row"><span class="lbl">📊 Max Affordable CAC (at 3:1)</span><span class="val" id="resMaxCAC">$0</span></div>
<div class="mort-row"><span class="lbl">💰 Lifetime Profit Per Customer</span><span class="val" id="resProfit">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Customer Lifetime Value Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>LTV (lifetime value)</strong> is the total gross profit a customer generates before churning. Paired with CAC, it answers the existential question: <em>does our growth engine make money?</em></p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Lifespan (months) = 1 ÷ Churn Rate<br/>LTV = ARPU × Gross Margin × Lifespan</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">The golden rule: <strong>LTV:CAC ≥ 3:1</strong>. Below 3:1, growth destroys value; above 5:1, you are likely under-investing in growth. Because churn sits in the denominator, <strong>cutting churn is the highest-leverage way to raise LTV</strong> — halving churn doubles lifetime value.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$120</strong> ARPU × <strong>80%</strong> margin = $96/month gross profit. At <strong>5%</strong> monthly churn, lifespan = 1 ÷ 0.05 = <strong>20 months</strong> → LTV = <strong>$1,920</strong>. With $300 CAC, LTV:CAC = <strong>6.4:1</strong> — excellent. Max affordable CAC at 3:1 = <strong>$640</strong>; lifetime profit per customer = <strong>$1,620</strong>.</p>''',
'faqs':[
 ('What is a good LTV to CAC ratio?','3:1 or higher is the standard benchmark. Below 3:1 suggests unprofitable growth; above 5:1 suggests you could profitably spend more on acquisition.'),
 ('How do I calculate customer lifespan?','1 ÷ churn rate (as a decimal). 5% monthly churn → 20-month lifespan. Use cohort-measured churn, not aspirational targets.'),
 ('Should LTV use revenue or gross profit?','Gross profit — always subtract cost of goods/servicing. Revenue-based LTV overstates value, especially for low-margin businesses.'),
 ('How can I increase LTV?','Reduce churn (biggest lever), raise prices or upsell (expansion revenue), and improve gross margin. Retention work compounds across every future cohort.'),
 ('LTV for e-commerce vs SaaS?','E-commerce: average order value × purchase frequency × lifespan. SaaS: ARPU × margin ÷ churn. Same concept, different inputs.'),
],
'related':[
 ('saas-churn-calculator','SaaS Churn Calculator','📉','Churn input for LTV.'),
 ('cac-ltv-calculator','CAC to LTV Ratio Calculator','💸','The full CAC:LTV picture.'),
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','ARPU and MRR context.'),
 ('newsletter-valuation-calculator','Newsletter Valuation Calculator','📰','Subscriber value parallel.'),
 ('break-even','Break-Even Calculator','⚖️','Payback math.'),
],
'js_core':'''function core(p){
  var gp=p.arpu*p.margin/100;
  var life=p.churn>0?1/(p.churn/100):0;
  var ltv=gp*life;
  var ratio=p.cac>0?ltv/p.cac:0;
  return {ltv:ltv,life:life,gp:gp,ratio:ratio,maxCac:ltv/3,profit:ltv-p.cac,
    rating:ratio>=3?'✅ Healthy (≥3:1)':(ratio>=1?'⚠️ Tight (<3:1)':'❌ Unprofitable')};
}''',
'js_glue':'''function recalc(){
  var p={arpu:num('arpu'),margin:num('margin'),churn:num('churn'),cac:num('cac')};
  var r=core(p);
  setT('resLTV',fmtM(r.ltv));
  setT('resLTVSub',r.rating);
  setT('resLife',r.life.toFixed(1)+' months');setT('resGP',fmtM(r.gp)+'/mo');
  setT('resRatio',r.ratio.toFixed(2)+' : 1');setT('resMaxCAC',fmtM(r.maxCac));
  setT('resProfit',(r.profit>=0?'':'−')+fmtM(Math.abs(r.profit)));
  document.getElementById('shareText').textContent='LTV '+fmtM(r.ltv)+', LTV:CAC '+r.ratio.toFixed(1)+':1';
}
['arpu','margin','churn','cac'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'arpu':120,'margin':80,'churn':5,'cac':300},
  'expect':{'ltv':1920,'life':20,'gp':96,'ratio':6.4,'profit':1620}},
 {'inputs':{'arpu':500,'margin':90,'churn':2,'cac':2000},
  'expect':{'ltv':22500,'life':50,'gp':450,'ratio':11.25}},
],
})

# ---------------- 37. startup-runway-calculator (business) ----------------
TOOLS.append({
'slug':'startup-runway-calculator','name':'Startup Runway Calculator','icon':'✈️','cat':'business','cat_label':'BUSINESS',
'hub':'/business-calculators','hub_title':'Business Calculators',
'hub_blurb':'Browse all business and finance calculators.',
'title':'Startup Runway Calculator — Burn Rate & Months of Cash',
'desc':'Calculate startup runway: cash on hand ÷ net burn rate. See months until cash-out and the date you hit the wall.',
'keywords':'startup runway calculator, burn rate calculator, how long will my cash last, cash runway formula, zero cash date',
'h1':'Startup Runway Calculator',
'intro':'Runway is survival measured in months. Enter cash, revenue, and expenses to see exactly how long you have.',
'inputs':[
 {'id':'cash','label':'Cash on Hand ($)','value':500000,'prefix':'$','min':0},
 {'id':'rev','label':'Monthly Revenue ($)','value':40000,'prefix':'$','min':0},
 {'id':'exp','label':'Monthly Expenses ($)','value':90000,'prefix':'$','min':0},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Runway Remaining</div>
<div class="mort-result-big" id="resRun">0 mo</div>
<div id="resZero" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">🔥 Net Burn Rate / Mo</span><span class="val" id="resBurn">$0</span></div>
<div class="mort-row"><span class="lbl">💰 Gross Burn / Mo</span><span class="val" id="resGross">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Burn Multiple (burn ÷ net new ARR/mo)</span><span class="val" id="resMult">—</span></div>
<div class="mort-row"><span class="lbl">🎯 Cash Needed for 18 Months</span><span class="val" id="resNeed">$0</span></div>
<div class="mort-row"><span class="lbl">✅ Status</span><span class="val" id="resStatus">—</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Runway Math Works',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;"><strong>Runway</strong> is how many months your cash lasts at the current burn rate. It is the most-watched number in early-stage startups — every fundraise, hiring plan, and pivot decision runs through it.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Net Burn = Monthly Expenses − Monthly Revenue<br/>Runway = Cash on Hand ÷ Net Burn</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Rules of thumb: raise when you have <strong>6+ months</strong> left (fundraising takes 3–6 months); <strong>18–24 months</strong> is the standard post-raise target; under 6 months is the danger zone. If revenue exceeds expenses you are <strong>profitable</strong> — runway is infinite, and the question flips to growth rate.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;"><strong>$500,000</strong> cash, <strong>$40,000</strong> monthly revenue, <strong>$90,000</strong> expenses → net burn = <strong>$50,000/month</strong> → runway = <strong>10 months</strong>. To reach a comfortable 18 months at this burn, the company needs <strong>$900,000</strong> total — i.e., raise at least $400,000, and start now.</p>''',
'faqs':[
 ('What is a good startup runway?','18–24 months after a fundraise is standard. Start raising with 6+ months remaining — fundraising typically takes 3–6 months and desperation kills valuations.'),
 ('Gross burn vs net burn?','Gross burn = total monthly expenses. Net burn = expenses minus revenue — the actual cash drain. Runway always uses net burn.'),
 ('What is the burn multiple?','Net burn ÷ net new ARR. Under 1× is efficient; 2–3× is typical for venture-backed growth; above 3× suggests unsustainable spending.'),
 ('When should a startup cut costs?','When runway drops under 12 months with no fundraise in sight, or when the burn multiple stays above 3×. Cut once, cut deep — death by a thousand cuts destroys morale.'),
 ('Does profitability mean infinite runway?','Yes — if revenue covers expenses, cash grows instead of shrinking. Then optimize for growth rate and margins rather than survival.'),
],
'related':[
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','Revenue covering burn.'),
 ('break-even','Break-Even Calculator','⚖️','Path to profitability.'),
 ('emergency-fund-calculator','Emergency Fund Calculator','🛟','How many months cash covers.'),
 ('llc-vs-scorp-calculator','LLC vs S-Corp Calculator','🏢','Structure to cut burn via taxes.'),
],
'js_core':'''function core(p){
  var burn=p.exp-p.rev;
  var run=burn>0?p.cash/burn:Infinity;
  var d=new Date();d.setMonth(d.getMonth()+Math.floor(run));
  var months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return {burn:burn,run:run,gross:p.exp,need:burn>0?burn*18:0,
    zero:burn>0?months[d.getMonth()]+' '+d.getFullYear():'—',
    status:burn<=0?'✅ Profitable — infinite runway':(run<6?'🔴 Danger (<6 mo)':(run<12?'🟡 Raise soon (<12 mo)':'🟢 Healthy (12+ mo)'))};
}''',
'js_glue':'''function recalc(){
  var p={cash:num('cash'),rev:num('rev'),exp:num('exp')};
  var r=core(p);
  setT('resRun',isFinite(r.run)?r.run.toFixed(1)+' months':'∞');
  setT('resZero',r.burn>0?'Out of cash ≈ '+r.zero:'Cash growing monthly');
  setT('resBurn',(r.burn>=0?'':'−')+fmtM(Math.abs(r.burn))+'/mo');
  setT('resGross',fmtM(r.gross)+'/mo');
  setT('resMult','—');
  setT('resNeed',fmtM(r.need));
  setT('resStatus',r.status);
  document.getElementById('shareText').textContent='Runway '+(isFinite(r.run)?r.run.toFixed(1)+' months':'infinite')+', burn '+fmtM(r.burn)+'/mo';
}
['cash','rev','exp'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
recalc();''',
'tests':[
 {'inputs':{'cash':500000,'rev':40000,'exp':90000},
  'expect':{'burn':50000,'run':10,'gross':90000,'need':900000}},
 {'inputs':{'cash':1200000,'rev':100000,'exp':180000},
  'expect':{'burn':80000,'run':15,'need':1440000}},
],
})

# ---------------- 38. stripe-fee-calculator (business) ----------------
TOOLS.append({
'slug':'stripe-fee-calculator','name':'Stripe Fee Calculator','icon':'💳','cat':'business','cat_label':'BUSINESS',
'hub':'/business-calculators','hub_title':'Business Calculators',
'hub_blurb':'Browse all business and finance calculators.',
'title':'Stripe Fee Calculator — Processing Fees & Net Payout',
'desc':'Calculate Stripe processing fees: 2.9% + 30¢ per transaction. See net payout, effective rate, and international/micropayment options.',
'keywords':'Stripe fee calculator, Stripe processing fees, how much does Stripe take, Stripe international fee, Stripe net payout calculator',
'h1':'Stripe Fee Calculator',
'intro':'Stripe takes its cut before you see a dime. Enter any transaction amount to see the fee, your net, and the effective rate.',
'inputs':[
 {'id':'amount','label':'Transaction Amount ($)','value':100,'prefix':'$','min':0},
 {'id':'rate','label':'Rate (%)','value':2.9,'suffix':'%','min':0,'max':10,'step':0.1},
 {'id':'fixed','label':'Fixed Fee Per Transaction ($)','value':0.30,'prefix':'$','min':0,'max':5,'step':0.05},
 {'id':'preset','label':'Card Type Preset','type':'select','options':[['2.9|0.30','US Domestic Card — 2.9% + 30¢'],['4.4|0.30','International Card — 2.9% + 1.5% + 30¢'],['5|0.05','Micropayments — 5% + 5¢']]},
],
'results_html':'''
<div class="result-card" style="text-align:center;padding:24px;">
<div style="font-size:0.82rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Stripe Fee</div>
<div class="mort-result-big" id="resFee">$0</div>
<div id="resNet" style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;"></div>
</div>
<div style="margin: 12px 0;">
<button class="btn btn-secondary" id="shareBtn" style="width: 100%; padding: 11px 16px; margin-top: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md);" type="button"><span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span></button>
</div>
<div class="result-card" style="margin-top:14px;">
<div class="mort-row"><span class="lbl">💵 You Receive (net)</span><span class="val" id="resReceive">$0</span></div>
<div class="mort-row"><span class="lbl">📊 Effective Rate</span><span class="val" id="resEff">—</span></div>
<div class="mort-row"><span class="lbl">💸 Fee on $1,000 Volume</span><span class="val" id="resK">$0</span></div>
<div class="mort-row"><span class="lbl">📅 Fee on $10k / Month</span><span class="val" id="resMo">$0</span></div>
<div class="mort-row"><span class="lbl">🔁 To Receive $100 Exactly, Charge</span><span class="val" id="resGrossUp">$0</span></div>
</div>
<div id="shareText" style="display:none;"></div>''',
'guide_h2':'How Stripe Fees Work',
'guide':'''
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;margin-bottom:18px;">Stripe\'s standard US pricing is <strong>2.9% + 30¢</strong> per successful card charge — no monthly fees, no setup. The percentage scales with amount; the fixed 30¢ hits small transactions hardest.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">The Formulas</h3>
<div style="background:var(--bg-subtle,#f3f4f6);padding:14px 18px;border-left:4px solid var(--brand-primary,#2563eb);border-radius:6px;font-family:monospace;font-size:0.95rem;margin:15px 0;">Fee = Amount × Rate % + Fixed Fee<br/>Net = Amount − Fee<br/>Gross-up: Charge = (Target + Fixed) ÷ (1 − Rate)</div>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">Watch the add-ons: <strong>international cards +1.5%</strong>, currency conversion +1%, dispute fee $15. The <strong>effective rate</strong> (fee ÷ amount) is what matters — on a $5 sale at 2.9% + 30¢ it is 8.9%, but on $500 it is 2.96%. High-volume businesses ($80k+/mo) can negotiate custom rates.</p>
<h3 style="margin-top:20px;font-size:1.2rem;">Worked Example</h3>
<p style="color:var(--text-muted);font-size:0.9rem;line-height:1.75;">On a <strong>$100</strong> domestic charge: fee = $100 × 2.9% + $0.30 = <strong>$3.20</strong>; you receive <strong>$96.80</strong> (3.20% effective). On <strong>$2,500</strong>: fee = <strong>$72.80</strong>, net <strong>$2,427.20</strong>. To net exactly $100, charge ($100 + $0.30) ÷ 0.971 = <strong>$103.30</strong>.</p>''',
'faqs':[
 ('How much does Stripe charge per transaction?','2.9% + 30¢ for US domestic cards. International cards add 1.5%; ACH bank debits are 0.8% (capped at $5).'),
 ('What is Stripe\'s fee for international payments?','An extra 1.5% on top of the domestic rate (so 4.4% + 30¢ for US businesses), plus 1% if currency conversion is needed.'),
 ('Does Stripe charge on refunds?','The original processing fee is not returned on refunds (since 2020) — you eat the fee. Disputed payments add a $15 dispute fee.'),
 ('How can I reduce Stripe fees?','Negotiate volume pricing above ~$80k/month, route small transactions to micropayment pricing or ACH, and use local payment methods where cheaper.'),
 ('Stripe vs PayPal fees?','Nearly identical headline rates (2.9% + 30¢). Differences show up in international fees, dispute handling, and payout speed — compare on your actual transaction mix.'),
],
'related':[
 ('ebay-fee-calculator','eBay Fee Calculator','🏷️','Compare marketplace fees.'),
 ('shopify-fee-calculator','Shopify Fee Calculator','🛒',"Shopify's cut vs Stripe."),
 ('amazon-fba-calculator','Amazon FBA Fee Calculator','📦','Amazon fee stacks.'),
 ('markup-vs-margin-calculator','Markup vs Margin Calculator','📊','Margin after fees.'),
 ('saas-mrr-calculator','SaaS MRR Calculator','💰','MRR net of processing.'),
],
'js_core':'''function core(p){
  var fee=p.amount*p.rate/100+p.fixed;
  var net=p.amount-fee;
  var grossUp=p.rate<100?(100+p.fixed)/(1-p.rate/100):0;
  return {fee:fee,net:net,eff:p.amount>0?fee/p.amount*100:0,
    k:p.amount>0?(1000/p.amount)*fee:0,
    mo:p.amount>0?(10000/p.amount)*fee:0,grossUp:grossUp};
}''',
'js_glue':'''function applyPreset(){var v=document.getElementById('preset').value.split('|');document.getElementById('rate').value=v[0];document.getElementById('fixed').value=v[1];recalc();}
function recalc(){
  var p={amount:num('amount'),rate:num('rate'),fixed:num('fixed')};
  var r=core(p);
  setT('resFee',fmtM(r.fee));
  setT('resNet','You keep '+fmtM(r.net));
  setT('resReceive',fmtM(r.net));setT('resEff',fmtP(r.eff,2));
  setT('resK',fmtM(r.k));setT('resMo',fmtM(r.mo)+'/mo');setT('resGrossUp',fmtM(r.grossUp));
  document.getElementById('shareText').textContent='Stripe fee '+fmtM(r.fee)+' on '+fmtM(p.amount)+' (net '+fmtM(r.net)+')';
}
['amount','rate','fixed'].forEach(function(id){document.getElementById(id).addEventListener('input',recalc);});
document.getElementById('preset').addEventListener('change',applyPreset);
recalc();''',
'tests':[
 {'inputs':{'amount':100,'rate':2.9,'fixed':0.30},'expect':{'fee':3.2,'net':96.8,'eff':3.2}},
 {'inputs':{'amount':2500,'rate':2.9,'fixed':0.30},'expect':{'fee':72.8,'net':2427.2}},
],
})

# ================= MAIN EXECUTION =================
import json as _json
import subprocess as _sp
import tempfile as _tf

SKIP = {
    'debt-to-income-calculator': 'close variant of existing tools/dti-calculator.html ("Debt-to-Income (DTI) Calculator — Mortgage Underwriting Ratios")',
    'roth-ira-conversion-calculator': 'close variant of existing tools/roth-conversion-calculator.html ("Roth Conversion Tax & Break-Even Calculator 2026")',
    'podcast-revenue-calculator': 'close variant of existing tools/podcast-sponsorship-calculator.html ("Podcast Ad Revenue Calculator — CPM Rates & Sponsorship"; same downloads×CPM×slots math)',
}
TAX_SLUGS = {'w-4-withholding-calculator','llc-tax-calculator','s-corp-tax-savings-calculator',
             'self-employment-tax-calculator','quarterly-tax-calculator','bonus-tax-calculator',
             'rsu-tax-calculator','tax-refund-estimator'}
REQUIRED_KEYS = ['slug','name','icon','cat','cat_label','hub','hub_title','hub_blurb','title','desc',
                 'keywords','h1','intro','inputs','results_html','guide_h2','guide','faqs','related',
                 'js_core','js_glue','tests']
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools')

def full_inline_js(t):
    return (JS_PRELUDE + "\n" + t['js_core'] + "\n" + t['js_glue'] + "\n"
            + SHARE_SNIPPET.replace('{NAME}', t['name']))

def node_check_syntax(src):
    with _tf.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(src); path = f.name
    try:
        r = _sp.run(['node','--check',path], capture_output=True, text=True, timeout=30)
        return r.returncode == 0, (r.stderr.strip() or r.stdout.strip())
    finally:
        os.unlink(path)

def node_run_tests(t):
    driver = "\n;(function(){\nvar cases = %s;\nvar out = [];\nfor (var i=0;i<cases.length;i++){\n  var c = cases[i]; var r = core(c.inputs); var errs = [];\n  for (var k in c.expect){\n    var a = r[k], b = c.expect[k];\n    if (typeof a !== 'number' || !isFinite(a)) { errs.push(k+': non-numeric '+a); continue; }\n    var tol = Math.max(0.02, Math.abs(b)*0.001);\n    if (Math.abs(a-b) > tol) errs.push(k+': got '+a+' want '+b);\n  }\n  out.push({idx:i, pass: errs.length===0, errors: errs, got: r});\n}\nconsole.log(JSON.stringify(out));\n})();\n" % _json.dumps(t['tests'])
    src = JS_PRELUDE + "\n" + t['js_core'] + driver
    with _tf.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(src); path = f.name
    try:
        r = _sp.run(['node', path], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False, 'node runtime error: ' + (r.stderr.strip() or r.stdout.strip())[:300]
        return True, _json.loads(r.stdout.strip())
    finally:
        os.unlink(path)

def validate_tool(t, valid_files):
    errs = []
    for k in REQUIRED_KEYS:
        if k not in t: errs.append('missing key: '+k)
    if not (4 <= len(t.get('faqs',[])) <= 6): errs.append('FAQs must be 4-6, got %d' % len(t.get('faqs',[])))
    n = guide_wordcount(t)
    if not (300 <= n <= 500): errs.append('guide words %d not in 300-500' % n)
    rel = t.get('related', [])
    if not (4 <= len(rel) <= 6): errs.append('related tools must be 4-6, got %d' % len(rel))
    for slug, _ti, _ic, _bl in rel:
        if slug in SKIP: errs.append('related links to skipped slug: '+slug)
        elif slug+'.html' not in valid_files: errs.append('related target missing: '+slug+'.html')
    if t['slug'] in TAX_SLUGS:
        if 'https://www.irs.gov/' not in t['guide']: errs.append('tax page missing https://www.irs.gov/ link')
        gl = t['guide'].lower()
        if 'not tax advice' not in gl and 'estimate' not in gl: errs.append('tax page missing estimate/not-tax-advice statement')
    ids = [i['id'] for i in t.get('inputs',[])]
    if len(ids) != len(set(ids)): errs.append('duplicate input ids')
    if 'Last updated' in t['guide']: errs.append('guide must not contain Last updated (template adds it)')
    return errs

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    existing_files = set(os.listdir(OUT_DIR))
    # related targets may point at pages generated in this same run
    valid_files = set(existing_files) | {t['slug']+'.html' for t in TOOLS if t['slug'] not in SKIP}
    # AdSense reference: extract canonical ad block from the mortgage template page
    mpath = os.path.join(OUT_DIR, 'mortgage-calculator.html')
    ads_ref = ADSENSE  # chrome was extracted from this page; verify it's intact there
    if os.path.exists(mpath):
        mhtml = open(mpath, encoding='utf-8').read()
        if ADSENSE.strip() not in mhtml:
            print('FATAL: AdSense block in chrome does not match mortgage-calculator.html; aborting.')
            return
    print('AdSense chrome check: OK (block matches mortgage-calculator.html)')
    print('Skipped (close variants):')
    for s, reason in SKIP.items():
        print('  - %s: %s' % (s, reason))
    results = []
    for t in TOOLS:
        slug = t['slug']
        if slug in SKIP:
            results.append((slug, 'SKIPPED', SKIP[slug])); continue
        errs = validate_tool(t, valid_files)
        if errs:
            results.append((slug, 'FAIL', 'validation: ' + '; '.join(errs))); continue
        html = page(t)
        ok, msg = node_check_syntax(full_inline_js(t))
        if not ok:
            results.append((slug, 'FAIL', 'JS syntax: ' + msg[:200])); continue
        ok, res = node_run_tests(t)
        if not ok:
            results.append((slug, 'FAIL', res)); continue
        failed = [c for c in res if not c['pass']]
        if failed:
            results.append((slug, 'FAIL', 'calc tests: ' + _json.dumps(failed)[:300])); continue
        # related hub must be first related card
        relsec = html.split('Related Precision Calculators',1)[1] if 'Related Precision Calculators' in html else ''
        hubpos = relsec.find(t['hub_title'])
        first_tool = relsec.find('/tools/')
        if hubpos == -1 or (first_tool != -1 and first_tool < hubpos):
            results.append((slug, 'FAIL', 'hub is not the first related card')); continue
        if 'Last updated: September 2026' not in html:
            results.append((slug, 'FAIL', 'missing Last updated stamp')); continue
        out = os.path.join(OUT_DIR, slug + '.html')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html)
        existing_files.add(slug + '.html')
        results.append((slug, 'PASS', out))
    print('\n==== GENERATION RESULTS ====')
    npass = sum(1 for _, s, _ in results if s == 'PASS')
    for slug, status, info in results:
        print('%-38s %-7s %s' % (slug, status, info if status != 'PASS' else 'written'))
    print('PASS: %d  FAIL: %d  SKIPPED: %d' % (npass,
          sum(1 for _, s, _ in results if s == 'FAIL'),
          sum(1 for _, s, _ in results if s == 'SKIPPED')))
    # ---- post-generation validation on new files ----
    new_files = [os.path.join(OUT_DIR, s + '.html') for s, st, _ in results if st == 'PASS']
    print('\n==== POST-CHECKS ====')
    # 1. link resolution
    bad_links = []
    for fp in new_files:
        h = open(fp, encoding='utf-8').read()
        for m in re.finditer(r'href="(/tools/[a-z0-9-]+\.html)"', h):
            target = os.path.join(OUT_DIR, os.path.basename(m.group(1)))
            if not os.path.exists(target):
                bad_links.append((os.path.basename(fp), m.group(1)))
    print('link check: %s' % ('ALL RESOLVE' if not bad_links else 'BROKEN: %s' % bad_links[:10]))
    # 2. JSON-LD parse + FAQ mirror (single block: [SoftwareApplication, FAQPage])
    ld_ok, ld_bad = 0, []
    for fp in new_files:
        h = open(fp, encoding='utf-8').read()
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
        try:
            assert len(blocks) == 1, 'expected 1 ld+json block, got %d' % len(blocks)
            data = _json.loads(blocks[0])
            assert isinstance(data, list) and len(data) == 2, 'expected [SoftwareApplication, FAQPage]'
            faq = next(x for x in data if x.get('@type') == 'FAQPage')
            slug = os.path.basename(fp)[:-5]
            t = next(x for x in TOOLS if x['slug'] == slug)
            assert len(faq['mainEntity']) == len(t['faqs']), 'FAQ count mismatch'
            # every FAQ question text mirrored
            qnames = [q for q, _a in t['faqs']]
            assert all(any(q == e['name'] for e in faq['mainEntity']) for q in qnames), 'FAQ text not mirrored'
            ld_ok += 1
        except Exception as e:
            ld_bad.append((os.path.basename(fp), str(e)[:120]))
    print('JSON-LD: %d/%d parse, FAQ mirror %s' % (ld_ok, len(new_files), 'OK' if not ld_bad else ld_bad[:5]))
    # 3. HTML parse
    try:
        import html5lib
        h_ok, h_bad = 0, []
        for fp in new_files:
            try:
                html5lib.parse(open(fp, encoding='utf-8').read())
                h_ok += 1
            except Exception as e:
                h_bad.append((os.path.basename(fp), str(e)[:120]))
        print('HTML5 parse: %d/%d OK %s' % (h_ok, len(new_files), '' if not h_bad else h_bad[:5]))
    except ImportError:
        from html.parser import HTMLParser
        h_ok, h_bad = 0, []
        for fp in new_files:
            try:
                HTMLParser().feed(open(fp, encoding='utf-8').read()); h_ok += 1
            except Exception as e:
                h_bad.append((os.path.basename(fp), str(e)[:120]))
        print('HTML parse (html.parser fallback): %d/%d OK %s' % (h_ok, len(new_files), '' if not h_bad else h_bad[:5]))
    # 4. AdSense byte-for-byte
    abad = [os.path.basename(fp) for fp in new_files
            if ADSENSE.strip() not in open(fp, encoding='utf-8').read()]
    print('AdSense block byte-for-byte: %s' % ('ALL OK' if not abad else 'MISMATCH: %s' % abad))
    # 5. canonical/title/meta uniqueness
    seen_c, seen_t, dup = set(), set(), []
    for fp in new_files:
        h = open(fp, encoding='utf-8').read()
        c = re.search(r'<link href="([^"]+)" rel="canonical"', h).group(1)
        ti = re.search(r'<title>([^<]+)</title>', h).group(1)
        if c in seen_c or ti in seen_t: dup.append(os.path.basename(fp))
        seen_c.add(c); seen_t.add(ti)
    print('canonical/title uniqueness: %s' % ('ALL UNIQUE' if not dup else 'DUP: %s' % dup))
    # 6. IRS on tax pages
    ibad = []
    for fp in new_files:
        slug = os.path.basename(fp)[:-5]
        if slug in TAX_SLUGS:
            h = open(fp, encoding='utf-8').read()
            if 'https://www.irs.gov/' not in h or 'not tax advice' not in h.lower():
                ibad.append(slug)
    print('tax pages IRS+disclaimer: %s' % ('ALL OK' if not ibad else 'MISSING: %s' % ibad))
    # 7. file sizes
    sizes = [(os.path.basename(fp), os.path.getsize(fp)) for fp in new_files]
    out_range = [(b, s) for b, s in sizes if not (40*1024 <= s <= 90*1024)]
    print('size 40-90KB: %d/%d in range %s' % (len(sizes)-len(out_range), len(sizes),
          '' if not out_range else 'OUT: %s' % [(b, round(s/1024,1)) for b, s in out_range][:8]))

if __name__ == '__main__':
    main()
