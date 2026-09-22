#!/usr/bin/env python3
"""
Autonomous 24/7 AI SEO Agent for CalcWorker.com
Connects to Groq API, selects unwritten calculator topics,
generates in-depth 2000+ words SEO guides with embedded tools,
updates sitemap.xml, and pings IndexNow.
"""

import os
import re
import sys
import json
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")

# Read securely from Environment Variable (GitHub Secrets / Vercel Env)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"  # 120B state-of-the-art model



sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from seo_agent import render_article_html, update_sitemap_with_article, notify_indexnow

# High-priority topic queue mapped to tools
TOPIC_QUEUE = [
    {
        "slug": "1099-freelance-quarterly-tax-guide-2026",
        "tool_file": "freelance-tax-calculator.html",
        "tool_name": "1099 Freelance Tax Calculator",
        "topic": "1099 Freelance and Self-Employment Quarterly Taxes",
        "focus": "How to calculate Schedule C net profit, 15.3% SE tax, federal tax brackets, safe harbor rules, and IRS quarterly payment deadlines (Form 1040-ES) in 2026."
    },
    {
        "slug": "auto-loan-payment-and-interest-calculation-guide",
        "tool_file": "auto-loan.html",
        "tool_name": "Auto Loan Calculator",
        "topic": "Auto Loan Payments, Dealer Fees, and Total Interest",
        "focus": "How car loan amortization works, impact of loan terms (36 vs 48 vs 72 months), the 20/4/10 financial rule, and how down payments lower interest charges."
    },
    {
        "slug": "401k-rmd-rules-and-deadlines-2026",
        "tool_file": "401k-rmd-calculator.html",
        "tool_name": "401(k) & IRA RMD Calculator",
        "topic": "401(k) and IRA Required Minimum Distributions (RMDs)",
        "focus": "IRS Uniform Lifetime Table, SECURE 2.0 Act age requirements (age 73 and 75), calculation formulas, and how to avoid the 25% penalty."
    },
    {
        "slug": "crypto-profit-and-capital-gains-tax-guide-2026",
        "tool_file": "crypto-profit-calculator.html",
        "tool_name": "Crypto Profit & ROI Calculator",
        "topic": "Cryptocurrency Profits and Capital Gains Taxes",
        "focus": "Short-term vs long-term capital gains tax rates, cost basis accounting (FIFO, HIFO, LIFO), wash sale tax rules, and calculating net ROI."
    },
    {
        "slug": "residential-solar-panel-payback-and-roi-guide",
        "tool_file": "solar-roi.html",
        "tool_name": "Solar Panel ROI Calculator",
        "topic": "Residential Solar Panel Payback Period and ROI",
        "focus": "Section 25D 30% Federal Clean Energy Credit, net metering math, utility inflation offsets, and calculating exact break-even years."
    },
    {
        "slug": "ai-prompt-engineering-token-cost-guide-2026",
        "tool_file": "ai-prompt-cost-calculator.html",
        "tool_name": "AI Prompt & Cost Calculator",
        "topic": "AI Token Pricing and LLM Prompt Optimization",
        "focus": "Input vs output token pricing, context caching economics, latency trade-offs, and calculating monthly API bills for production AI systems."
    },
    {
        "slug": "fha-vs-conventional-mortgage-comparison-2026",
        "tool_file": "fha-vs-conventional-calculator.html",
        "tool_name": "FHA vs Conventional Loan Calculator",
        "topic": "FHA vs Conventional Home Loans",
        "focus": "Credit score minimums, down payment comparisons (3.5% vs 3%), mortgage insurance differences (life-of-loan MIP vs cancellable PMI), and loan limits."
    }
]

def call_groq(prompt):
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a Senior Certified Financial Analyst and Expert SEO Technical Writer for CalcWorker.com. Write thorough, highly authoritative, humanized financial articles with deep mathematical explanations, realistic 2026 numbers, and clean HTML structure."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.4,
        "max_tokens": 4000
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

def generate_and_publish_next_article():
    # Find first unwritten topic
    selected = None
    for t in TOPIC_QUEUE:
        article_file = os.path.join(ARTICLES_DIR, f"{t['slug']}.html")
        if not os.path.exists(article_file):
            selected = t
            break

    if not selected:
        print("[AGENT] All queued articles are already published!")
        return None

    print(f"\n[AGENT] Selected Topic: {selected['topic']}")
    print(f"[AGENT] Related Tool: {selected['tool_name']}")

    prompt = f"""
Write a comprehensive, publication-ready SEO guide for CalcWorker.com on the topic: '{selected['topic']}'.
Focus: {selected['focus']}
Associated Tool: {selected['tool_name']} ({selected['tool_file']})

You must return valid JSON ONLY with the exact following schema:
{{
  "title": "Clear, compelling title (under 70 chars)",
  "meta_desc": "SEO meta description under 155 chars with high CTR appeal",
  "read_time": "8 min read",
  "sections": [
    {{
      "title": "Section 1 Title (Overview & Foundational Math)",
      "body": "HTML formatted paragraphs, <div class='formula-box'>the exact mathematical formula</div>, and explanations."
    }},
    {{
      "title": "Section 2 Title (Pillars / Breakdown Table)",
      "body": "HTML formatted explanation with a <table class='data-table'>...</table> showing itemized components."
    }},
    {{
      "title": "Section 3 Title (Worked Calculation Example for 2026)",
      "body": "HTML formatted step-by-step math with realistic 2026 dollar numbers, interest rates, and final take-home or payment totals."
    }},
    {{
      "title": "Section 4 Title (Actionable Optimization Strategies)",
      "body": "HTML formatted actionable tips with an <ol> list of practical strategies."
    }}
  ],
  "faqs": [
    ["Question 1?", "Direct, authoritative 2-3 sentence answer."],
    ["Question 2?", "Direct, authoritative 2-3 sentence answer."],
    ["Question 3?", "Direct, authoritative 2-3 sentence answer."],
    ["Question 4?", "Direct, authoritative 2-3 sentence answer."],
    ["Question 5?", "Direct, authoritative 2-3 sentence answer."]
  ]
}}
Do not include any text outside the JSON block. Do not wrap in markdown code blocks if possible, or wrap cleanly in ```json.
"""

    print("[AGENT] Querying Groq 120B AI model...")
    raw_response = call_groq(prompt)

    # Clean markdown code block if present
    clean_json = raw_response.strip()
    if clean_json.startswith("```"):
        clean_json = re.sub(r"^```(?:json)?", "", clean_json)
        clean_json = re.sub(r"```$", "", clean_json).strip()

    data = json.loads(clean_json)

    print(f"[AGENT] Article Title Generated: {data['title']}")

    html = render_article_html(
        slug=selected["slug"],
        title=data["title"],
        meta_desc=data["meta_desc"],
        read_time=data.get("read_time", "8 min read"),
        related_tool_file=selected["tool_file"],
        related_tool_name=selected["tool_name"],
        sections=data["sections"],
        faqs=data["faqs"]
    )

    out_file = os.path.join(ARTICLES_DIR, f"{selected['slug']}.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    article_url = f"https://calcworker.com/articles/{selected['slug']}.html"
    update_sitemap_with_article(article_url)
    notify_indexnow(article_url)

    print(f"[SUCCESS] Article published: {article_url} ({len(html)} bytes)")
    return article_url

if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY environment variable is not set. "
              "Set it as a GitHub Actions secret named GROQ_API_KEY for the "
              "scheduled workflow, or export GROQ_API_KEY locally before running.",
              file=sys.stderr)
        sys.exit(1)
    generate_and_publish_next_article()
