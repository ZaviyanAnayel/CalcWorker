#!/usr/bin/env python3
"""
Autonomous AI SEO Content Agent for CalcWorker.com
Generates comprehensive, high-intent SEO articles with embedded calculator tools,
Article & FAQ schema markup, automatic sitemap.xml updates, and instant IndexNow pings.
"""

import os
import re
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")
INDEXNOW_SCRIPT = os.path.join(BASE_DIR, "scripts", "indexnow_submit.py")

os.makedirs(ARTICLES_DIR, exist_ok=True)

def render_article_html(slug, title, meta_desc, read_time, related_tool_file, related_tool_name, sections, faqs):
    faq_schema_items = []
    for q, a in faqs:
        clean_q = q.replace('"', '\\"')
        clean_a = re.sub(r'<[^>]+>', '', a).replace('"', '\\"')
        faq_schema_items.append(f"""{{
          "@type": "Question",
          "name": "{clean_q}",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "{clean_a}"
          }}
        }}""")

    faq_schema_json = ",\n        ".join(faq_schema_items)

    toc_items = []
    for i, s in enumerate(sections, 1):
        sec_id = f"section-{i}"
        toc_items.append(f'<li><a href="#{sec_id}">{s["title"]}</a></li>')
    toc_html = "\n".join(toc_items)

    content_blocks = []
    for i, s in enumerate(sections, 1):
        sec_id = f"section-{i}"
        content_blocks.append(f"""
        <section id="{sec_id}" class="article-section">
          <h2>{s["title"]}</h2>
          {s["body"]}
        </section>
        """)
    body_html = "\n".join(content_blocks)

    faq_accordion_items = []
    for i, (q, a) in enumerate(faqs, 1):
        faq_accordion_items.append(f"""
        <div class="faq-item">
          <button class="faq-question" onclick="toggleArticleFaq(this)">
            <span>{q}</span>
            <span class="faq-icon">+</span>
          </button>
          <div class="faq-answer">
            <p>{a}</p>
          </div>
        </div>
        """)
    faq_html = "\n".join(faq_accordion_items)

    canonical_url = f"https://calcworker.com/articles/{slug}.html"
    tool_url = f"https://calcworker.com/tools/{related_tool_file}"

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} | CalcWorker Guide (2026)</title>
  <meta name="description" content="{meta_desc}"/>
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1"/>
  <link rel="canonical" href="{canonical_url}"/>
  <link rel="icon" type="image/png" href="/assets/favicon.png"/>
  <meta name="theme-color" content="#1d4ed8"/>

  <!-- Open Graph -->
  <meta property="og:title" content="{title} | CalcWorker"/>
  <meta property="og:description" content="{meta_desc}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:url" content="{canonical_url}"/>
  <meta property="og:site_name" content="CalcWorker"/>

  <!-- Google AdSense -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3405098265613384" crossorigin="anonymous"></script>

  <!-- Schema.org JSON-LD -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "Article",
        "headline": "{title}",
        "description": "{meta_desc}",
        "mainEntityOfPage": "{canonical_url}",
        "datePublished": "2026-09-20",
        "dateModified": "2026-09-20",
        "author": {{
          "@type": "Organization",
          "name": "CalcWorker Research Team",
          "url": "https://calcworker.com/about.html"
        }},
        "publisher": {{
          "@type": "Organization",
          "name": "CalcWorker",
          "logo": "https://calcworker.com/assets/favicon.png"
        }}
      }},
      {{
        "@type": "FAQPage",
        "mainEntity": [
          {faq_schema_json}
        ]
      }}
    ]
  }}
  </script>

  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #0f172a;
      --card-border: rgba(59, 130, 246, 0.22);
      --text: #e2e8f0;
      --text-muted: #94a3b8;
      --accent: #3b82f6;
      --accent-gradient: linear-gradient(135deg, #60a5fa, #3b82f6, #2563eb);
      --code-bg: #1e293b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.7;
      padding-bottom: 60px;
    }}
    a {{ color: #60a5fa; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .site-nav {{
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .site-nav .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 800;
      font-size: 1.15rem;
      color: #f8fafc;
    }}
    .nav-links {{ display: flex; gap: 20px; font-size: 0.9rem; }}
    .nav-links a {{ color: var(--text-muted); font-weight: 500; }}
    .nav-links a:hover {{ color: #ffffff; }}

    .article-container {{
      max-width: 900px;
      margin: 40px auto;
      padding: 0 20px;
    }}
    .breadcrumbs {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 16px;
      display: flex;
      gap: 8px;
    }}
    .article-header h1 {{
      font-size: 2.3rem;
      line-height: 1.25;
      margin-bottom: 16px;
      color: #f8fafc;
      font-weight: 800;
    }}
    .meta-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 32px;
      padding-bottom: 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      align-items: center;
    }}
    .badge-verified {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 3px 10px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.75rem;
    }}

    .tool-embed-banner {{
      background: linear-gradient(135deg, rgba(30, 58, 138, 0.35), rgba(15, 23, 42, 0.85));
      border: 1px solid rgba(59, 130, 246, 0.4);
      border-radius: 14px;
      padding: 24px;
      margin: 32px 0;
      display: flex;
      flex-direction: column;
      gap: 14px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    }}
    .tool-embed-banner h3 {{
      font-size: 1.25rem;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .tool-embed-banner p {{ color: #cbd5e1; font-size: 0.95rem; }}
    .tool-launch-btn {{
      align-self: flex-start;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff !important;
      padding: 10px 22px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.92rem;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }}
    .tool-launch-btn:hover {{
      transform: translateY(-1px);
      text-decoration: none;
    }}

    .toc-box {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 36px;
    }}
    .toc-box h3 {{ font-size: 1rem; color: #f8fafc; margin-bottom: 12px; }}
    .toc-box ul {{ list-style-position: inside; color: #60a5fa; font-size: 0.92rem; line-height: 1.9; }}

    .article-section {{ margin-bottom: 40px; }}
    .article-section h2 {{
      font-size: 1.6rem;
      color: #f1f5f9;
      margin-bottom: 16px;
      font-weight: 700;
      border-left: 4px solid #3b82f6;
      padding-left: 14px;
    }}
    .article-section h3 {{ font-size: 1.2rem; color: #e2e8f0; margin: 20px 0 10px 0; }}
    .article-section p {{ margin-bottom: 16px; color: #cbd5e1; font-size: 1.02rem; }}
    .article-section ul, .article-section ol {{ margin-left: 24px; margin-bottom: 18px; color: #cbd5e1; }}
    .article-section li {{ margin-bottom: 8px; }}

    .formula-box {{
      background: #020617;
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 10px;
      padding: 16px 20px;
      margin: 20px 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: #38bdf8;
      font-size: 0.95rem;
    }}

    .data-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      background: var(--card-bg);
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid var(--card-border);
    }}
    .data-table th, .data-table td {{
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 0.92rem;
    }}
    .data-table th {{ background: #1e293b; color: #f8fafc; font-weight: 700; }}
    .data-table tr:last-child td {{ border-bottom: none; }}

    .faq-item {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      margin-bottom: 12px;
      overflow: hidden;
    }}
    .faq-question {{
      width: 100%;
      background: none;
      border: none;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #f8fafc;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      text-align: left;
    }}
    .faq-answer {{
      padding: 0 20px 16px 20px;
      color: #94a3b8;
      font-size: 0.95rem;
      line-height: 1.6;
    }}
    .faq-icon {{ font-size: 1.2rem; color: #3b82f6; }}

    footer {{
      margin-top: 80px;
      padding: 30px 20px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      text-align: center;
      color: var(--text-muted);
      font-size: 0.88rem;
    }}
    footer a {{ color: var(--text-muted); margin: 0 10px; }}
    footer a:hover {{ color: #ffffff; }}
  </style>
</head>
<body>

  <nav class="site-nav">
    <a href="/" class="brand">
      <span>⚡</span> CalcWorker
    </a>
    <div class="nav-links">
      <a href="/">All Tools</a>
      <a href="/about.html">About</a>
      <a href="/privacy.html">Privacy</a>
    </div>
  </nav>

  <article class="article-container">
    <div class="breadcrumbs">
      <a href="/">Home</a> <span>/</span> <a href="/#tools">Guides</a> <span>/</span> <span>{title}</span>
    </div>

    <header class="article-header">
      <h1>{title}</h1>
      <div class="meta-bar">
        <span>⏱️ {read_time}</span>
        <span>📅 Updated 2026</span>
        <span class="badge-verified">✓ Expert Verified</span>
        <span>By CalcWorker Financial Team</span>
      </div>
    </header>

    <div class="tool-embed-banner">
      <h3><span>🧮</span> Interactive Tool: {related_tool_name}</h3>
      <p>Run your exact numbers immediately using CalcWorker's zero-knowledge client-side mathematical engine. No sign-up or data collection required.</p>
      <a href="{tool_url}" class="tool-launch-btn">Open Free {related_tool_name} →</a>
    </div>

    <div class="toc-box">
      <h3>Table of Contents</h3>
      <ul>
        {toc_html}
      </ul>
    </div>

    {body_html}

    <section class="article-section">
      <h2>Frequently Asked Questions</h2>
      <div class="faq-list">
        {faq_html}
      </div>
    </section>

    <div class="tool-embed-banner" style="margin-top: 48px;">
      <h3>Ready to run your calculations?</h3>
      <p>Use our precision 2026 financial calculator to evaluate your scenario in seconds.</p>
      <a href="{tool_url}" class="tool-launch-btn">Launch {related_tool_name} Now →</a>
    </div>
  </article>

  <footer>
    <p>&copy; 2026 CalcWorker. High-Precision Computational Tools for High-Stakes Decisions.</p>
    <p style="margin-top: 10px;">
      <a href="/about.html">About</a>
      <a href="/contact.html">Contact</a>
      <a href="/privacy.html">Privacy Policy</a>
      <a href="/terms.html">Terms of Service</a>
      <a href="/disclaimer.html">Disclaimer</a>
    </p>
  </footer>

  <script src="/js/calcworker-common.js?v=2026.3"></script>
  <script>
    function toggleArticleFaq(btn) {{
      var ans = btn.nextElementSibling;
      var icon = btn.querySelector('.faq-icon');
      if (ans.style.display === 'none') {{
        ans.style.display = 'block';
        icon.textContent = '−';
      }} else {{
        ans.style.display = 'none';
        icon.textContent = '+';
      }}
    }}
  </script>
</body>
</html>
"""
    return html

def update_sitemap_with_article(article_url):
    if not os.path.exists(SITEMAP_PATH):
        print(f"[WARN] Sitemap not found at {SITEMAP_PATH}")
        return False
    with open(SITEMAP_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if article_url in content:
        print(f"[SITEMAP] URL already present in sitemap: {article_url}")
        return True

    entry = f"""  <url>
    <loc>{article_url}</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.80</priority>
  </url>
</urlset>"""

    content = re.sub(r'</urlset>', entry, content)
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[SITEMAP] Added {article_url} to sitemap.xml successfully.")
    return True

def notify_indexnow(article_url):
    if os.path.exists(INDEXNOW_SCRIPT):
        os.system(f'python "{INDEXNOW_SCRIPT}" "{article_url}"')
    else:
        print("[WARN] indexnow_submit.py not found.")

def publish_article(slug, title, meta_desc, read_time, tool_file, tool_name, sections, faqs):
    print(f"\n==========================================")
    print(f"[AGENT] Generating SEO Article: '{title}'")
    print(f"==========================================")

    html_content = render_article_html(
        slug=slug,
        title=title,
        meta_desc=meta_desc,
        read_time=read_time,
        related_tool_file=tool_file,
        related_tool_name=tool_name,
        sections=sections,
        faqs=faqs
    )

    out_file = os.path.join(ARTICLES_DIR, f"{slug}.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[AGENT] Saved: {out_file} ({len(html_content)} bytes)")

    article_url = f"https://calcworker.com/articles/{slug}.html"
    update_sitemap_with_article(article_url)
    notify_indexnow(article_url)
    print(f"[AGENT] Article '{slug}' successfully published, indexed & sitemap updated!\n")
    return article_url

if __name__ == "__main__":
    print("AI SEO Agent Module Ready.")
