"""Portales internacionales de teletrabajo: Remotive, RemoteOK, Jobicy, Himalayas, WorkingNomads."""
import html
import time

from .base import PAUSA, fetch_json, job, strip_html


def src_remotive(cfg, log):
    out = []
    for cat in cfg["busqueda"]["remotive_categorias"]:
        for j in fetch_json(f"https://remotive.com/api/remote-jobs?category={cat}").get("jobs", []):
            out.append(job("remotive", j["id"], j.get("title"), j.get("company_name"),
                           "Remoto · " + (j.get("candidate_required_location") or "Worldwide"), j.get("url"),
                           strip_html(j.get("description")), j.get("publication_date"), j.get("salary"), remote=True))
        time.sleep(PAUSA)
    return out


def src_remoteok(cfg, log):
    out = []
    for j in fetch_json("https://remoteok.com/api"):
        if not isinstance(j, dict) or "position" not in j:
            continue
        sal = f"{j['salary_min']}–{j['salary_max']} USD" if j.get("salary_max") else ""
        out.append(job("remoteok", j["id"], j.get("position"), j.get("company"),
                       "Remoto · " + (j.get("location") or "Worldwide"), j.get("url"),
                       strip_html(j.get("description")) + "\nTags: " + ", ".join(j.get("tags") or []),
                       j.get("date"), sal, remote=True))
    return out


def src_jobicy(cfg, log):
    out = {}
    for geo in ("spain", "europe", "emea"):
        try:
            data = fetch_json(f"https://jobicy.com/api/v2/remote-jobs?count=50&geo={geo}")
        except Exception as e:
            log(f"  jobicy {geo}: {e}")
            continue
        for j in data.get("jobs", []):
            out[j["id"]] = job("jobicy", j["id"], html.unescape(j.get("jobTitle") or ""), j.get("companyName"),
                               "Remoto · " + (j.get("jobGeo") or ""), j.get("url"),
                               f"Nivel: {j.get('jobLevel', '')}\n" + strip_html(j.get("jobDescription")),
                               j.get("pubDate"), remote=True)
        time.sleep(PAUSA)
    return list(out.values())


def src_himalayas(cfg, log):
    out = {}
    for page in (1, 2, 3):
        data = fetch_json(f"https://himalayas.app/jobs/api/search?country=ES&seniority=Entry-level&page={page}")
        jobs = data.get("jobs") or []
        for j in jobs:
            restr = j.get("locationRestrictions") or []
            if len(restr) > 12:
                restr = ["Spain"] if "Spain" in restr else restr[:5]
            url = j.get("applicationLink") or j.get("guid") or ""
            out[url] = job("himalayas", url, j.get("title"), j.get("companyName"),
                           "Remoto · " + (", ".join(restr) or "Worldwide"), url,
                           "Nivel: " + ", ".join(j.get("seniority") or []) + "\n" + strip_html(j.get("description")),
                           j.get("pubDate"), remote=True)
        if not jobs:
            break
        time.sleep(PAUSA)
    return list(out.values())


def src_workingnomads(cfg, log):
    out = []
    for j in fetch_json("https://www.workingnomads.com/api/exposed_jobs/"):
        out.append(job("workingnomads", j.get("url"), j.get("title"), j.get("company_name"),
                       "Remoto · " + (j.get("location") or "Worldwide"), j.get("url"),
                       strip_html(j.get("description")), j.get("pub_date"), remote=True))
    return out
