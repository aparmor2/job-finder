"""Fuentes que necesitan una clave gratuita en config.json: InfoJobs, Adzuna, Jooble."""
import base64
import json
import time
import urllib.parse

from ..text import norm
from .base import PAUSA, fetch_json, job, strip_html


def src_infojobs(cfg, log):
    k = cfg["claves_api_gratis"]
    auth = base64.b64encode(f"{k['infojobs_client_id']}:{k['infojobs_client_secret']}".encode()).decode()
    out = {}
    for term in cfg["busqueda"]["terminos"] + ["remoto informatica"]:
        for page in (1, 2):
            q = urllib.parse.urlencode({"q": term, "maxResults": 50, "page": page,
                                        "sinceDate": "_7_DAYS"})
            try:
                data = fetch_json("https://api.infojobs.net/api/9/offer?" + q, headers={"Authorization": "Basic " + auth})
            except Exception as e:
                log(f"  infojobs '{term}': {e}")
                break
            for o in data.get("offers", []):
                tele = (o.get("teleworking") or {}).get("value", "")
                loc = ", ".join(x for x in [o.get("city"), (o.get("province") or {}).get("value")] if x)
                desc = "\n".join(x for x in [
                    f"Experiencia mínima: {(o.get('experienceMin') or {}).get('value', '')}",
                    f"Modalidad: {tele}" if tele else "", o.get("requirementMin") or ""] if x)
                out[o["id"]] = job("infojobs", o["id"], o.get("title"), (o.get("author") or {}).get("name"),
                                   loc + (f" ({tele})" if tele else ""), o.get("link"), desc, o.get("published"),
                                   o.get("salaryDescription"), remote="solo teletrabajo" in norm(tele), spain=True)
            if page >= (data.get("totalPages") or 1):
                break
            time.sleep(PAUSA)
    return list(out.values())


def src_adzuna(cfg, log):
    k = cfg["claves_api_gratis"]
    b = cfg["busqueda"]
    out = {}
    for where in b["ciudades"] + [""]:
        for term in b["terminos"]:
            what = term + (" remoto" if not where else "")
            q = urllib.parse.urlencode({"app_id": k["adzuna_app_id"], "app_key": k["adzuna_app_key"],
                                        "results_per_page": 50, "what": what, "where": where,
                                        "max_days_old": 21, "content-type": "application/json"})
            try:
                data = fetch_json("https://api.adzuna.com/v1/api/jobs/es/search/1?" + q)
            except Exception as e:
                log(f"  adzuna '{what}' {where}: {e}")
                continue
            for j in data.get("results", []):
                sal = f"{int(j['salary_min'])}–{int(j.get('salary_max') or 0)} €" if j.get("salary_min") else ""
                out[j["id"]] = job("adzuna", j["id"], strip_html(j.get("title")),
                                   (j.get("company") or {}).get("display_name"),
                                   (j.get("location") or {}).get("display_name"), j.get("redirect_url"),
                                   strip_html(j.get("description")), j.get("created"), sal, spain=True)
            time.sleep(PAUSA * 3)
    return list(out.values())


def src_jooble(cfg, log):
    key = cfg["claves_api_gratis"]["jooble_key"]
    b = cfg["busqueda"]
    out = {}
    for loc in b["ciudades"] + ["remoto"]:
        for term in b["terminos"][:3]:
            try:
                data = fetch_json(f"https://es.jooble.org/api/{key}", data={"keywords": term, "location": loc})
            except Exception as e:
                log(f"  jooble '{term}' {loc}: {e}")
                continue
            for j in data.get("jobs", []):
                out[j["id"]] = job("jooble", j["id"], strip_html(j.get("title")), j.get("company"), j.get("location"),
                                   j.get("link"), strip_html(j.get("snippet")), j.get("updated"), j.get("salary"),
                                   remote="remot" in norm(j.get("type") or "") or None, spain=True)
            time.sleep(PAUSA)
    return list(out.values())
