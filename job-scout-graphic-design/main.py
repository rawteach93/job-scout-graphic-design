import os
import re
import smtplib
import ssl
import csv
import datetime as dt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from scrapers.sites import scrape_all_sources

OUT_DIR = Path("out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_config():
    load_dotenv()
    cfg = {
        "smtp_host": os.getenv("SMTP_HOST", ""),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_pass": os.getenv("SMTP_PASS", ""),
        "mail_from": os.getenv("MAIL_FROM", ""),
        "mail_to": os.getenv("MAIL_TO", ""),
        "keywords": [s.strip() for s in os.getenv("KEYWORDS", "graphic designer,logo design,branding").split(",") if s.strip()],
        "lead_email_domains_blocklist": [s.strip().lower() for s in os.getenv("LEAD_EMAIL_DOMAINS_BLOCKLIST", "no-reply,noreply,donotreply").split(",") if s.strip()],
        "max_pages_per_site": int(os.getenv("MAX_PAGES_PER_SITE", "1")),
        "timeout_seconds": int(os.getenv("TIMEOUT_SECONDS", "20")),
    }
    return cfg

def normalize_row(row):
    return {
        "title": (row.get("title") or "").strip(),
        "company": (row.get("company") or "").strip(),
        "location": (row.get("location") or "").strip(),
        "link": (row.get("link") or "").strip(),
        "source": (row.get("source") or "").strip(),
        "posted": (row.get("posted") or "").strip(),
    }

def write_csv(rows, path):
    if not rows:
        return
    cols = ["title","company","location","link","source","posted"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(normalize_row(r))

def write_leads_csv(leads, path):
    if not leads:
        return
    cols = ["company","email","source","link"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in leads:
            w.writerow({
                "company": (r.get("company") or "").strip(),
                "email": (r.get("email") or "").strip(),
                "source": (r.get("source") or "").strip(),
                "link": (r.get("link") or "").strip(),
            })

def render_email_html(top_rows, leads_rows, keywords):
    def row_html(r):
        title = r.get("title","")
        company = r.get("company","")
        location = r.get("location","")
        posted = r.get("posted","")
        link = r.get("link","")
        source = r.get("source","")
        return f"<li><a href='{link}'>{title}</a> — <b>{company}</b> ({location}) · <i>{source}</i> · <small>{posted}</small></li>"

    top_block = "<ul>" + "".join(row_html(r) for r in top_rows[:30]) + "</ul>" if top_rows else "<p>No matches today.</p>"
    leads_block = ""
    if leads_rows:
        items = "".join(f"<li>{l.get('company','')} — <a href='mailto:{l.get('email','')}'>{l.get('email','')}</a> · <small>{l.get('source','')}</small></li>" for l in leads_rows[:40])
        leads_block = f"<h3>Lead Emails</h3><ul>{items}</ul>"

    return f"""
    <html>
    <body>
      <h2>Daily Job Scout — Graphic/Logo/Branding</h2>
      <p>Keywords: {', '.join(keywords)}</p>
      <h3>New Roles</h3>
      {top_block}
      {leads_block}
      <hr/>
      <small>Generated {dt.datetime.utcnow().isoformat()}Z</small>
    </body>
    </html>
    """

def send_mail(cfg, subject, html_body):
    if not cfg["smtp_host"] or not cfg["smtp_user"] or not cfg["smtp_pass"] or not cfg["mail_from"] or not cfg["mail_to"]:
        print("⚠️ SMTP not fully configured. Skipping email.")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["mail_from"]
    msg["To"] = cfg["mail_to"]
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.starttls(context=context)
        server.login(cfg["smtp_user"], cfg["smtp_pass"])
        server.sendmail(cfg["mail_from"], [cfg["mail_to"]], msg.as_string())
        print("✅ Email sent.")

def main():
    cfg = load_config()
    print("Loaded config:", cfg)

    jobs, leads = scrape_all_sources(cfg)
    today = dt.date.today().isoformat()

    OUT_DIR = Path("out")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    jobs_path = OUT_DIR / f"jobs_{today}.csv"
    leads_path = OUT_DIR / f"leads_{today}.csv"
    write_csv(jobs, jobs_path)
    write_leads_csv(leads, leads_path)

    subject = f"[Job Scout] {len(jobs)} roles · {len(leads)} leads — {today}"
    html = render_email_html(jobs, leads, cfg["keywords"])
    send_mail(cfg, subject, html)

    print(f"Saved: {jobs_path}")
    print(f"Saved: {leads_path}")
    print("Done.")

if __name__ == "__main__":
    main()
