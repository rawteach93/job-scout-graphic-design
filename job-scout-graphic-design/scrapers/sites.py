import re
import time
from dataclasses import dataclass
from typing import Iterable, Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_REGEX = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

@dataclass
class Ctx:
    keywords: List[str]
    timeout: int
    max_pages: int

def get(url: str, ctx: Ctx):
    try:
        r = requests.get(url, headers=HEADERS, timeout=ctx.timeout)
        if r.status_code == 200:
            return r.text
        print(f"{url} -> HTTP {r.status_code}")
    except Exception as e:
        print(f"GET error {url}: {e}")
    return ""

def soupify(html: str):
    if not html:
        return None
    return BeautifulSoup(html, "lxml")

def match_keywords(text: str, keywords: List[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords)

def extract_emails(text: str) -> List[str]:
    return list(set(EMAIL_REGEX.findall(text or "")))

def mk_job(title, company, link, source, location=None, posted=None):
    return {
        "title": title or "",
        "company": company or "",
        "location": location or "",
        "link": link or "",
        "source": source,
        "posted": posted or "",
    }

def mk_lead(company, email, source, link):
    return {
        "company": company or "",
        "email": email or "",
        "source": source,
        "link": link or "",
    }

# --- Site-specific scrapers (best-effort) ---

def trabajo(search_url: str, ctx: Ctx) -> Tuple[List[Dict], List[Dict]]:
    jobs, leads = [], []
    html = get(search_url, ctx)
    s = soupify(html)
    if not s:
        return jobs, leads
    for li in s.select("ul li a[href], .job-result a[href], a[href*='/job/']"):
        title = li.get_text(strip=True)
        href = urljoin(search_url, li.get("href"))
        if match_keywords(title, ctx.keywords):
            jobs.append(mk_job(title=title, company="", link=href, source="Trabajo"))
    text = s.get_text(" ", strip=True)
    for email in extract_emails(text):
        leads.append(mk_lead(company="", email=email, source="Trabajo", link=search_url))
    return dedupe_jobs(jobs), dedupe_leads(leads)

def remoteok(url: str, ctx: Ctx):
    jobs, leads = [], []
    html = get(url, ctx)
    s = soupify(html)
    if not s: return jobs, leads
    for row in s.select("tr.job a[href]"):
        title = row.get_text(" ", strip=True)
        href = urljoin(url, row.get("href"))
        if match_keywords(title, ctx.keywords):
            company = ""
            comp = row.find_previous("td", class_="company")
            if comp:
                company = comp.get_text(" ", strip=True)
            jobs.append(mk_job(title, company, href, "RemoteOK"))
    text = s.get_text(" ", strip=True)
    for email in extract_emails(text):
        leads.append(mk_lead("", email, "RemoteOK", url))
    return dedupe_jobs(jobs), dedupe_leads(leads)

def wwr(url: str, ctx: Ctx):
    jobs, leads = [], []
    html = get(url, ctx)
    s = soupify(html)
    if not s: return jobs, leads
    for li in s.select("li.feature a[href]"):
        title = li.get_text(" ", strip=True)
        href = urljoin(url, li.get("href"))
        if match_keywords(title, ctx.keywords):
            company = ""
            jobs.append(mk_job(title, company, href, "WeWorkRemotely"))
    text = s.get_text(" ", strip=True)
    for email in extract_emails(text):
        leads.append(mk_lead("", email, "WeWorkRemotely", url))
    return dedupe_jobs(jobs), dedupe_leads(leads)

def unjobnet(url: str, ctx: Ctx):
    jobs, leads = [], []
    html = get(url, ctx)
    s = soupify(html)
    if not s: return jobs, leads
    for card in s.select("a.card, a[href*='/job/']"):
        title = card.get_text(" ", strip=True)
        href = urljoin(url, card.get("href"))
        if match_keywords(title, ctx.keywords):
            jobs.append(mk_job(title, "", href, "UNjobnet"))
    text = s.get_text(" ", strip=True)
    for email in extract_emails(text):
        leads.append(mk_lead("", email, "UNjobnet", url))
    return dedupe_jobs(jobs), dedupe_leads(leads)

def generic_list(url: str, ctx: Ctx, source_name: str):
    jobs, leads = [], []
    html = get(url, ctx)
    s = soupify(html)
    if not s: return jobs, leads
    for a in s.select("a[href]"):
        txt = a.get_text(" ", strip=True)
        href = urljoin(url, a.get("href"))
        if match_keywords(txt, ctx.keywords) and href.startswith("http"):
            jobs.append(mk_job(txt, "", href, source_name))
    text = s.get_text(" ", strip=True)
    for email in extract_emails(text):
        leads.append(mk_lead("", email, source_name, url))
    return dedupe_jobs(jobs), dedupe_leads(leads)

def dedupe_jobs(rows: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for r in rows:
        key = (r.get("title",""), r.get("company",""), r.get("link",""))
        if key in seen: continue
        seen.add(key)
        out.append(r)
    return out

def dedupe_leads(leads: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for L in leads:
        key = (L.get("company",""), L.get("email",""))
        if key in seen: continue
        seen.add(key)
        out.append(L)
    return out

def filter_leads(leads: List[Dict], block_domains: List[str]) -> List[Dict]:
    out = []
    for L in leads:
        em = (L.get("email") or "").lower()
        domain = em.split("@")[-1] if "@" in em else ""
        if any(b in domain for b in block_domains):
            continue
        out.append(L)
    return out

def scrape_all_sources(cfg) -> Tuple[List[Dict], List[Dict]]:
    ctx = Ctx(
        keywords=cfg["keywords"],
        timeout=cfg["timeout_seconds"],
        max_pages=cfg["max_pages_per_site"],
    )

    urls = [
        "https://us.trabajo.org/jobs?q=graphic+designer",
        "https://gb.trabajo.org/jobs?q=graphic+designer",
        "https://ke.trabajo.org/jobs?q=graphic+designer",
        "https://remote.co/remote-jobs/search/?search_keywords=graphic+designer",
        "https://www.indeed.com/q-graphic-designer-jobs.html",
        "https://www.glassdoor.com/Job/graphic-designer-jobs-SRCH_KO0,17.htm",
        "https://www.linkedin.com/jobs/search/?keywords=graphic%20designer",
        "https://remoteok.com/remote-graphic+design-jobs",
        "https://www.unjobnet.org/jobs?keywords=graphic+design&location=",
        "https://weworkremotely.com/remote-jobs/search?term=graphic+designer",
        "https://www.flexjobs.com/search?search=graphic+designer",
        "https://dribbble.com/jobs?query=graphic+designer",
        "https://www.behance.net/joblist?search=graphic+designer",
        "https://www.myjobmag.co.ke/search/jobs?q=graphic+designer",
        "https://www.brightermonday.co.ke/jobs?q=graphic+designer",
        "https://www.fuzu.com/kenya/jobs?search=graphic+designer",
        "https://www.summitrecruitment-search.com/job-search/?search=graphic+designer",
        "https://shortlist.net/jobs/?search=graphic+designer",
        "https://www.myjobsinkenya.com/search?q=graphic+designer",
        "https://www.jobsinkenya.co.ke/search?q=graphic+designer",
        "https://opportunitiesforyoungkenyans.co.ke",
        "https://www.jobwebkenya.com/?s=graphic+designer",
        "https://www.kenyajob.com/job-vacancies-kenya?f%5B0%5D=im_field_offre_metiers%3A78",
        "https://cdl.co.ke/jobs",
        "https://ngojobsinafrica.com/?s=graphic+designer",
        "https://ke.bebee.com/jobs?q=graphic+designer",
    ]

    all_jobs, all_leads = [], []

    for url in urls:
        try:
            host = urlparse(url).netloc.lower()
            if "trabajo.org" in host:
                j, L = trabajo(url, ctx)
            elif "remoteok.com" in host:
                j, L = remoteok(url, ctx)
            elif "weworkremotely.com" in host:
                j, L = wwr(url, ctx)
            elif "unjobnet.org" in host:
                j, L = unjobnet(url, ctx)
            else:
                j, L = generic_list(url, ctx, host)
            all_jobs.extend(j)
            all_leads.extend(L)
            time.sleep(1.0)  # polite
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue

    all_leads = filter_leads(all_leads, cfg["lead_email_domains_blocklist"])
    return all_jobs, all_leads
