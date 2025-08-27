# job-scout-graphic-design

Automated daily job scout for **Graphic Design / Logo Design / Branding** roles + **lead prospecting**.
- Scrapes a curated list of job boards (URLs provided) using best‑effort HTML parsing.
- Filters by your keywords.
- Also scrapes **company names & emails** from other listings to build a leads file.
- Sends you an email digest (and saves CSVs).

> ⚠️ Note: Some sites (LinkedIn, Glassdoor, Indeed, FlexJobs, Behance) rate‑limit or require JS/login.
> This tool handles failures gracefully and focuses on sources that are publicly parsable.
> Add your own adapters anytime in `scrapers/sites.py`.

## Quick Start

### 1) Python setup
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure
Copy `.env.example` to `.env` and fill in values:
```bash
cp .env.example .env
```

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`: your email SMTP (e.g., Gmail app password)
- `MAIL_TO`: where to send the digest
- `MAIL_FROM`: sender address
- `KEYWORDS`: comma‑separated search terms
- `LEAD_EMAIL_DOMAINS_BLOCKLIST`: comma‑separated domains to ignore (e.g., no‑reply)
- `MAX_PAGES_PER_SITE`: safety limit for pagination

### 3) Run
```bash
python main.py
```

Artifacts:
- `out/jobs_{today}.csv`
- `out/leads_{today}.csv`
- Email summary with top matches.

### 4) Schedule (GitHub Actions)
- Push this repo to GitHub.
- In **Repo → Settings → Secrets and variables → Actions**, add the secrets from `.env` as Actions secrets:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_TO`, `MAIL_FROM`, `KEYWORDS` (optional), etc.
- The workflow `.github/workflows/daily.yml` runs **every day at 06:00 UTC** by default.

---

## Supported Sites (initial adapters)
- Trabajo (US/GB/KE) — public search pages
- RemoteOK — public HTML
- We Work Remotely — public HTML
- UNjobnet — public HTML
- Remote.co — public HTML
- MyJobMag Kenya — public HTML
- BrighterMonday Kenya — public HTML (limited)
- Fuzu — public HTML (limited)
- Summit Recruitment — public HTML (limited)
- Shortlist — public HTML (limited)
- JobsInKenya.co.ke — public HTML
- MyJobsInKenya — public HTML (limited)
- Opportunities For Young Kenyans — landing page (leads only)
- JobWeb Kenya — public HTML
- KenyaJob — public HTML
- CDL Kenya — public HTML (leads only)
- NGO Jobs in Africa — public HTML
- beBee Kenya — public HTML (limited)

Other sites are included but may be skipped automatically if blocked by anti‑bot or require login.

---

## Extend
Add new scrapers in `scrapers/sites.py`. Implement a function that yields dicts with:
```python
{
  "title": str,
  "company": str or None,
  "location": str or None,
  "link": str,
  "source": str,      # short name
  "posted": str or None,  # date string if available
}
```

## Legal
Respect each website's Terms of Service and robots.txt.
Use reasonable frequency (the workflow runs once daily).
