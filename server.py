from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import feedparser
import requests
import json
import time
import os
import io
import re
from docx import Document
from docx.shared import Pt

app = FastAPI(title="RegIntel Cross-Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FEEDS = {
    # --- US FDA openFDA Live Databases (510k, PMA, Recalls) ---
    "US FDA - 510(k) Premarket Notifications (openFDA)": "openfda://device/510k.json",
    "US FDA - PMA Premarket Approvals (openFDA)": "openfda://device/pma.json",
    "US FDA - Medical Device Recalls (openFDA)": "openfda://device/recall.json",
    "US FDA - Drug Enforcement & Recalls (openFDA)": "openfda://drug/enforcement.json",

    # --- US FDA ---
    "US FDA - CDER Newly Added Guidance & Drugs": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml",
    "US FDA - CBER Biologics & Vaccines": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/biologics/rss.xml",
    "US FDA - CDRH Medical Devices": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medical-devices/rss.xml",
    "US FDA - Warning Letters (All Centers)": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/warning-letters/rss.xml",
    "US FDA - Press Releases": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
    "US FDA - What's New (Agency-Wide)": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/whats-new/rss.xml",
    "US FDA - Drug Recalls": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drug-recalls/rss.xml",
    "US FDA - MedWatch Safety Alerts": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml",
    "US FDA - All Recalls & Safety Alerts": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls/rss.xml",
    "US FDA - Veterinary Medicine (CVM)": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/animal-veterinary/rss.xml",
    "US FDA - Consumer Health Updates": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/consumers/rss.xml",
    "US FDA - Drugs@FDA All Approvals & Supplements (openFDA)": "openfda://drug/drugsfda.json",
    "US FDA - Drugs@FDA Biologics (BLA Actions Only)": "openfda://drug/drugsfda.json?filter=application_number:BLA*",
    "US FDA - Drugs@FDA Original Approvals (ORIG)": "openfda://drug/drugsfda.json?filter=submissions.submission_type:ORIG",
    "US FDA - Complete Response Letters (CRLs) (openFDA)": "openfda://other/crl.json",
    "US FDA - Drug Shortages (openFDA)": "openfda://drug/shortages.json",

    # --- EMA (Europe) ---
    "EMA - News & Press Releases": "https://www.ema.europa.eu/en/news.xml",
    "EMA - What's New (All Updates)": "https://www.ema.europa.eu/en/whats-new.xml",
    "EMA - New Human Medicines (CHMP Opinions)": "https://www.ema.europa.eu/en/new-human-medicine-new.xml",
    "EMA - Human Medicines (EPARs & Opinions)": "https://www.ema.europa.eu/en/human-medicine-new.xml",
    "EMA - Scientific Guidelines (Human & Vet)": "https://www.ema.europa.eu/en/scientific-guidelines.xml",
    "EMA - Regulatory & Procedural Guidelines": "https://www.ema.europa.eu/en/regulatory-and-procedural-guideline.xml",
    "EMA - Committee Agendas & Minutes (CHMP/PRAC/CAT)": "https://www.ema.europa.eu/en/agendas-and-minutes.xml",
    "EMA - Orphan Designations": "https://www.ema.europa.eu/en/orphan.xml",
    "EMA - Events & Stakeholder Meetings": "https://www.ema.europa.eu/en/events.xml",

    # --- Australia TGA ---
    "TGA Australia - All Alerts": "https://www.tga.gov.au/feeds/alert.xml",
    "TGA Australia - Safety Alerts": "https://www.tga.gov.au/feeds/alert/safety-alerts.xml",
    "TGA Australia - Market Actions & Recalls": "https://www.tga.gov.au/feeds/alert/market-actions.xml",
    "TGA Australia - Medicine Shortages": "https://www.tga.gov.au/feeds/alert/medicine-shortage-alerts.xml",
    "TGA Australia - News Articles": "https://www.tga.gov.au/feeds/article/news.xml",
    "TGA Australia - Regulatory Decision Notices": "https://www.tga.gov.au/feeds/article/notices.xml",
    "TGA Australia - Safety Updates": "https://www.tga.gov.au/feeds/article/safety-updates.xml",
    "TGA Australia - All Articles": "https://www.tga.gov.au/feeds/article.xml",

    # --- Health Canada ---
    "Health Canada - Advisories, Warnings & Recalls": "https://www.canada.ca/en/health-canada/services/drugs-health-products/medeffect-canada/advisories-warnings-recalls.html",
    "Health Canada - Compliance & Enforcement Feeds": "https://www.canada.ca/en/health-canada/services/drugs-health-products/compliance-enforcement/rss-feeds.html",

    # --- UK MHRA ---
    "UK MHRA - Drug & Device Alerts / Recalls": "https://www.gov.uk/drug-device-alerts",
    "UK MHRA - Drug Safety Update": "https://www.gov.uk/drug-safety-update",

    # --- Japan PMDA ---
    "Japan PMDA - English Updates": "https://www.pmda.go.jp/english/",

    # --- India (CDSCO / PIB) ---
    "India - CDSCO / PIB Health Updates": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",

    # --- Custom RSS / Atom URL ---
    "Custom RSS / Atom URL (Enter below)": "__CUSTOM__"
}

class AnalyzeRequest(BaseModel):
    api_base: str = "https://velona.in/gateway/v1/inference/run"
    api_key: str = ""
    model: str = "deepseek/deepseek-v4-flash-0731"
    prompt: str

class ExportDocxRequest(BaseModel):
    title: str = "Regulatory Intelligence Impact Analysis"
    source: str = ""
    depth: str = ""
    content: str

def _extract_stream_text(d):
    if isinstance(d, str):
        return d
    if not isinstance(d, dict):
        return ""
    for k in ("content", "text", "output_text", "token", "chunk", "delta"):
        v = d.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, dict):
            nested = _extract_stream_text(v)
            if nested:
                return nested
    for k in ("data", "payload", "result", "response", "message"):
        if isinstance(d.get(k), dict):
            nested = _extract_stream_text(d[k])
            if nested:
                return nested
    if isinstance(d.get("choices"), list) and d["choices"]:
        return _extract_stream_text(d["choices"][0])
    return ""

@app.get("/api/feeds")
def get_feeds():
    return {"sources": list(FEEDS.keys())}

@app.get("/api/fetch")
def fetch_rss(
    source: str = Query(...),
    keywords: str = Query(""),
    custom_url: str = Query("")
):
    url = custom_url.strip() if source.startswith("Custom RSS") else FEEDS.get(source, "")
    if not url:
        return {"error": "Missing or unknown feed source URL", "items": []}

    if url.startswith("openfda://"):
        raw_target = url.replace("openfda://", "")
        base_path, _, extra_q = raw_target.partition("?")
        endpoint = "https://api.fda.gov/" + base_path
        preset_filter = extra_q.replace("filter=", "") if extra_q.startswith("filter=") else ""
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        params = {"limit": 15}
        if "510k" in url or "pma" in url:
            params["sort"] = "decision_date:desc"
        elif "recall" in url:
            params["sort"] = "event_date_initiated:desc"
        elif "enforcement" in url:
            params["sort"] = "report_date:desc"
        elif "drugsfda" in url:
            params["sort"] = "submissions.submission_status_date:desc"
        elif "shortages" in url:
            params["sort"] = "initial_posting_date:desc"

        search_clauses = []
        if preset_filter:
            search_clauses.append(preset_filter)
        if kw_list:
            q_terms = "(" + " OR ".join([f'"{k}"' for k in kw_list]) + ")"
            search_clauses.append(q_terms)
        if search_clauses:
            params["search"] = " AND ".join(search_clauses)

        try:
            r = requests.get(endpoint, params=params, timeout=20)
            if not r.ok:
                return {"source": source, "url": endpoint, "count": 0, "items": [], "note": f"openFDA returned HTTP {r.status_code} (no matching records for filter)."}
            data = r.json()
            results = []
            for rec in data.get("results", []):
                if "510k" in url:
                    k_num = rec.get("k_number", "N/A")
                    dev = rec.get("device_name", "Medical Device")
                    app_name = rec.get("applicant", "Unknown Applicant")
                    pcode = rec.get("product_code", "")
                    dec = rec.get("decision_description", rec.get("decision_code", ""))
                    dt = rec.get("decision_date", "Recent")
                    results.append({
                        "title": f"510(k) {k_num}: {dev} ({app_name})",
                        "summary": f"Applicant: {app_name} | Product Code: {pcode} | Decision: {dec} | Clearance Type: {rec.get('clearance_type', 'Traditional')}",
                        "link": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={k_num}",
                        "published": dt
                    })
                elif "pma" in url:
                    pma_num = rec.get("pma_number", "N/A")
                    supp = rec.get("supplement_number", "")
                    title_id = f"{pma_num}/{supp}" if supp else pma_num
                    dev = rec.get("trade_name") or rec.get("generic_name") or "PMA Device"
                    app_name = rec.get("applicant", "Unknown Applicant")
                    dt = rec.get("decision_date", "Recent")
                    results.append({
                        "title": f"PMA {title_id}: {dev} ({app_name})",
                        "summary": f"Applicant: {app_name} | Generic Name: {rec.get('generic_name', '')} | Advisory Committee: {rec.get('advisory_committee_description', '')} | Supplement Type: {rec.get('supplement_type', 'Original')}",
                        "link": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id={pma_num}",
                        "published": dt
                    })
                elif "drugsfda" in url:
                    app_no = rec.get("application_number", "App")
                    sponsor = rec.get("sponsor_name", "Sponsor")
                    prods = ", ".join([p.get("brand_name", "") for p in rec.get("products", []) if p.get("brand_name")]) or app_no
                    subs = rec.get("submissions", [])
                    latest_sub = subs[0] if subs else {}
                    dt = latest_sub.get("submission_status_date", "Recent")
                    results.append({
                        "title": f"{app_no}: {prods} ({sponsor})",
                        "summary": f"Sponsor: {sponsor} | Latest Action: {latest_sub.get('submission_type', '')}-{latest_sub.get('submission_number', '')} ({latest_sub.get('submission_status', '')}) | Class: {latest_sub.get('review_priority', '')}",
                        "link": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app_no.replace('NDA','').replace('BLA','').replace('ANDA','')}",
                        "published": dt
                    })
                elif "crl" in url:
                    app_no = rec.get("application_number", "NDA/BLA")
                    sponsor = rec.get("applicant_name") or rec.get("sponsor_name") or "Applicant"
                    dt = rec.get("letter_date") or rec.get("decision_date") or "Recent"
                    summary_txt = (rec.get("text") or rec.get("summary") or str(rec))[:700]
                    results.append({
                        "title": f"Complete Response Letter ({app_no}): {sponsor}",
                        "summary": summary_txt,
                        "link": "https://open.fda.gov/apis/other/crl/",
                        "published": dt
                    })
                elif "shortages" in url:
                    gen = rec.get("generic_name", "Drug Shortage")
                    status = rec.get("status", "Current")
                    dt = rec.get("initial_posting_date", "Recent")
                    results.append({
                        "title": f"Drug Shortage ({status}): {gen}",
                        "summary": f"Company: {rec.get('company_name', 'N/A')} | Therapeutic Category: {', '.join(rec.get('therapeutic_category', []))} | Reason: {rec.get('shortage_reason', 'Not specified')}",
                        "link": "https://www.accessdata.fda.gov/scripts/drugshortages/",
                        "published": dt
                    })
                else:
                    rec_num = rec.get("recall_number", "Recall")
                    firm = rec.get("recalling_firm", "Unknown Firm")
                    prod = rec.get("product_description", "")[:220]
                    reason = rec.get("reason_for_recall", "")[:600]
                    dt = rec.get("report_date") or rec.get("event_date_initiated") or "Recent"
                    results.append({
                        "title": f"{rec_num} ({rec.get('classification', '')}): {firm}",
                        "summary": f"Product: {prod} | Reason: {reason}",
                        "link": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfres/res.cfm",
                        "published": dt
                    })
            return {"source": source, "url": endpoint, "count": len(results), "items": results, "note": ""}
        except Exception as e:
            return {"source": source, "url": endpoint, "count": 0, "items": [], "note": f"openFDA query error: {e}"}

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RegIntelStudio/1.0; +https://github.com/samuelrsolomon-sudo/compliance2-tool)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        parsed = feedparser.parse(resp.content if resp.ok else url)
    except Exception:
        parsed = feedparser.parse(url)

    kw_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    results = []

    for entry in getattr(parsed, "entries", []):
        title = entry.get("title", "Untitled").strip()
        summary = re.sub(r"<[^>]+>", " ", entry.get("summary", entry.get("description", ""))).strip()
        summary = re.sub(r"\s+", " ", summary)
        link = entry.get("link", url)
        published = entry.get("published", entry.get("updated", "Recent"))

        haystack = f"{title} {summary}".lower()
        if kw_list and not any(k in haystack for k in kw_list):
            continue

        results.append({
            "title": title,
            "summary": summary[:1200],
            "link": link,
            "published": published
        })

    if not kw_list:
        results = results[:10]

    note = ""
    if not results and getattr(parsed, "bozo", 0):
        note = "Source returned non-XML/HTML or restricted feed format; try a direct .xml RSS URL in Custom RSS."

    return {"source": source, "url": url, "count": len(results), "items": results, "note": note}

@app.post("/api/analyze-stream")
def analyze_items_stream(req: AnalyzeRequest):
    resolved_key = (req.api_key or "").strip() or os.environ.get("VELONA_API_KEY", "").strip()
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json"
    }
    is_velona = "velona.in/gateway" in req.api_base
    if is_velona:
        payload = {
            "model": req.model,
            "turns": [{"role": "user", "content": req.prompt}],
            "stream": True
        }
    else:
        payload = {
            "model": req.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "stream": True
        }

    def event_generator():
        last_err = ""
        for attempt in range(1, 3):
            try:
                with requests.post(req.api_base, headers=headers, json=payload, stream=True, timeout=120) as resp:
                    if resp.status_code in (502, 503, 504):
                        last_err = f"Upstream Gateway {resp.status_code}"
                        time.sleep(2)
                        continue
                    if resp.status_code >= 400:
                        err_msg = f"HTTP {resp.status_code}: {resp.text[:400]}"
                        yield f"data: {json.dumps({'error': err_msg})}\n\n"
                        return

                    emitted_any = False
                    for raw_line in resp.iter_lines(decode_unicode=True):
                        if not raw_line:
                            continue
                        line = raw_line[6:].strip() if raw_line.startswith("data: ") else raw_line.strip()
                        if line == "[DONE]":
                            break
                        try:
                            obj = json.loads(line)
                            delta = _extract_stream_text(obj)
                            if delta:
                                emitted_any = True
                                yield f"data: {json.dumps({'delta': delta})}\n\n"
                        except json.JSONDecodeError:
                            if not raw_line.startswith(":"):
                                emitted_any = True
                                yield f"data: {json.dumps({'delta': raw_line})}\n\n"

                    if not emitted_any:
                        yield f"data: {json.dumps({'error': 'Empty stream response'})}\n\n"
                    else:
                        yield "data: [DONE]\n\n"
                    return
            except Exception as e:
                last_err = str(e)
                time.sleep(1)

        yield f"data: {json.dumps({'error': f'LLM request failed: {last_err}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

def _clean_text(s: str) -> str:
    s = re.sub(r"\*{2,}", "", s)
    s = re.sub(r"^#{1,6}\s*", "", s)
    return s.strip()

def _add_formatted_runs(p, text: str):
    cleaned = _clean_text(text)
    parts = re.split(r"(\*[^\*]+\*)", cleaned)
    for part in parts:
        if not part:
            continue
        if part.startswith("*") and part.endswith("*") and len(part) > 2:
            r = p.add_run(part[1:-1])
            r.italic = True
        else:
            p.add_run(part)

@app.post("/api/export-docx")
def export_docx(req: ExportDocxRequest):
    doc = Document()
    doc.add_heading(req.title, level=0)
    if req.source or req.depth:
        meta = doc.add_paragraph()
        meta.add_run(f"Source: {req.source}  |  Depth: {req.depth}").italic = True

    lines = req.content.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or re.fullmatch(r"[-*_]{3,}", stripped):
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_str = lines[i].strip().strip("|")
                cells = [_clean_text(c) for c in row_str.split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    table_rows.append(cells)
                i += 1
            if table_rows:
                cols = max(len(r) for r in table_rows)
                tbl = doc.add_table(rows=len(table_rows), cols=cols)
                tbl.style = "Table Grid"
                for r_idx, r_data in enumerate(table_rows):
                    for c_idx in range(cols):
                        val = r_data[c_idx] if c_idx < len(r_data) else ""
                        cell_p = tbl.cell(r_idx, c_idx).paragraphs[0]
                        _add_formatted_runs(cell_p, val)
                        if r_idx == 0:
                            for run in cell_p.runs:
                                run.bold = True
            continue

        if stripped.startswith("### "):
            doc.add_heading(_clean_text(stripped[4:]), level=3)
        elif stripped.startswith("## "):
            doc.add_heading(_clean_text(stripped[3:]), level=2)
        elif stripped.startswith("# "):
            doc.add_heading(_clean_text(stripped[2:]), level=1)
        elif stripped.startswith(("- ", "* ")):
            p = doc.add_paragraph(style="List Bullet")
            _add_formatted_runs(p, stripped[2:])
        elif re.match(r"^\d+\.\s+", stripped):
            p = doc.add_paragraph(style="List Number")
            _add_formatted_runs(p, re.sub(r"^\d+\.\s+", "", stripped))
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            _add_formatted_runs(p, stripped)
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=RegIntel_Impact_Report.docx"}
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
