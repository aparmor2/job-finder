"""Portales de empleo públicos de empresas en Greenhouse, Lever y Ashby."""
import json
import re
import time

from ..text import norm
from .base import PAUSA, fetch_json, job, strip_html


ATS_BASE = ["spain", "espana", "madrid", "barcelona", "valencia", "bilbao", "remote", "remoto", "emea", "europe", "anywhere", "worldwide"]


def ats_filtro(cfg):
    """Ofertas de empresas internacionales: solo las de España, remoto o tus ciudades de config.json."""
    palabras = ATS_BASE + [norm(c) for c in cfg["busqueda"].get("ciudades", [])]
    return re.compile("|".join(re.escape(w) for w in palabras if w))


def src_empresas(cfg, log):
    filtro = ats_filtro(cfg)
    emp = cfg["busqueda"]["empresas"]
    out = []
    for slug in emp.get("greenhouse", []):
        try:
            data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
        except Exception as e:
            log(f"  greenhouse {slug}: {e}")
            continue
        for j in data.get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            if filtro.search(norm(loc)):
                out.append(job("empresa", f"gh-{j['id']}", j.get("title"), j.get("company_name") or slug, loc,
                               j.get("absolute_url"), strip_html(j.get("content")), j.get("updated_at"),
                               remote="remot" in norm(loc)))
        time.sleep(PAUSA)
    for slug in emp.get("lever", []):
        try:
            data = fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        except Exception as e:
            log(f"  lever {slug}: {e}")
            continue
        for j in data:
            cat = j.get("categories") or {}
            loc = ", ".join(cat.get("allLocations") or [cat.get("location") or ""])
            remote = j.get("workplaceType") == "remote"
            if filtro.search(norm(loc)) or remote:
                out.append(job("empresa", f"lv-{j['id']}", j.get("text"), slug.capitalize(),
                               loc + (" (remoto)" if remote else ""), j.get("hostedUrl"),
                               (j.get("descriptionPlain") or "") + "\n" + (j.get("additionalPlain") or ""),
                               j.get("createdAt"), remote=remote))
        time.sleep(PAUSA)
    for slug in emp.get("ashby", []):
        try:
            data = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        except Exception as e:
            log(f"  ashby {slug}: {e}")
            continue
        for j in data.get("jobs", []):
            locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
            country = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry", "")
            loc = ", ".join(dict.fromkeys(l.strip() for l in locs if l)) + (f" · {country}" if country else "")
            if filtro.search(norm(loc)) or j.get("isRemote"):
                out.append(job("empresa", f"ab-{j['id']}", j.get("title"), slug.capitalize(),
                               loc + (" (remoto)" if j.get("isRemote") else ""), j.get("jobUrl"),
                               j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
                               j.get("publishedAt"), remote=j.get("isRemote")))
        time.sleep(PAUSA)
    return out
