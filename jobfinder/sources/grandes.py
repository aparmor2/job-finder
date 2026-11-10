"""Grandes empresas: Workday, SuccessFactors, Capgemini y páginas vigiladas."""
import html
import re
import time
import urllib.parse

from ..text import norm
from .base import PAUSA, fetch, fetch_json, job, parse_rss, strip_html


ES_CODES = re.compile(r"(?:^|,\s*)(?:ES|ESP)(?:\s*,|\s*$)|spain|espana")


def src_workday(cfg, log):
    """API JSON que usa la propia web de empleo de Workday (myworkdayjobs.com)."""
    from .. import db
    p = cfg["busqueda"]["portales_empresa"]
    out = {}
    for emp in p.get("workday", []):
        u = urllib.parse.urlparse(emp["url"])
        tenant = u.netloc.split(".")[0]
        site = [s for s in u.path.split("/") if s and not re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", s)][0]
        api = f"https://{u.netloc}/wday/cxs/{tenant}/{site}"
        paths = {}
        for term in p["palabras"]:
            for offset in range(0, 100, 20):
                try:
                    data = fetch_json(api + "/jobs", data={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term})
                except Exception as e:
                    log(f"  workday {emp['nombre']} '{term}': {e}")
                    break
                posts = data.get("jobPostings") or []
                for j in posts:
                    if j.get("externalPath"):
                        paths.setdefault(j["externalPath"], j)
                if offset + 20 >= (data.get("total") or 0):
                    break
                time.sleep(PAUSA)
        known = db.known_ids(f"empresa:wd-{tenant}-")
        for path, j in paths.items():
            jid = f"wd-{tenant}-{path}"
            if "empresa:" + jid in known:  # ya descargada: solo refrescar "vista por última vez"
                out[jid] = job("empresa", jid, j.get("title"), emp["nombre"], url=f"https://{u.netloc}/{site}{path}", spain=True)
                continue
            try:
                info = fetch_json(api + path).get("jobPostingInfo", {})
            except Exception as e:
                log(f"  workday {emp['nombre']} detalle: {e}")
                continue
            country = (info.get("country") or {}).get("descriptor", "")
            locs = [info.get("location") or j.get("locationsText") or ""] + (info.get("additionalLocations") or [])
            remote = bool(re.search(r"(?i)remot|teletrab", " ".join(locs) + (info.get("remoteType") or "")))
            if country and not ES_CODES.search(norm(country)) and not remote:
                continue
            out[jid] = job("empresa", jid, info.get("title") or j.get("title"),
                                         emp["nombre"], ", ".join(dict.fromkeys(l for l in locs if l)) + (f" · {country}" if country else ""),
                                         info.get("externalUrl") or f"https://{u.netloc}/{site}{path}",
                                         strip_html(info.get("jobDescription")), info.get("startDate"),
                                         remote=remote, spain=True)
            time.sleep(PAUSA)
    return list(out.values())


def src_successfactors(cfg, log):
    """RSS público de los portales SAP SuccessFactors (/services/rss/job/)."""
    p = cfg["busqueda"]["portales_empresa"]
    out = {}
    for emp in p.get("successfactors", []):
        base = emp["url"].rstrip("/")
        for term in p["palabras"]:
            try:
                items = list(parse_rss(fetch(f"{base}/services/rss/job/?locale=es_ES&keywords={urllib.parse.quote(term)}")))
            except Exception as e:
                log(f"  successfactors {emp['nombre']} '{term}': {e}")
                continue
            for it in items:
                link = (it.findtext("link") or "").strip()
                raw = html.unescape(it.findtext("title") or "").strip()
                m = re.match(r"^(.*)\(([^()]*)\)\s*$", raw)
                title, loc = (m.group(1).strip(), m.group(2)) if m else (raw, "")
                if not link or link in out or (loc and not ES_CODES.search(loc) and not ES_CODES.search(norm(loc))):
                    continue
                loc = ", ".join(x.strip() for x in loc.split(",") if x.strip() not in ("ES", "ESP") and not x.strip().isdigit())
                out[link] = job("empresa", "sf-" + re.sub(r"\W+", "-", link.split("/job/")[-1])[:120], title, emp["nombre"],
                                loc, link, strip_html(it.findtext("description")), it.findtext("pubDate"), spain=True)
            time.sleep(PAUSA)
    return list(out.values())


def src_capgemini(cfg, log):
    out = {}
    for page in range(1, 6):
        data = fetch_json(f"https://cg-job-search-microservices.azurewebsites.net/api/job-search?country_code=es-es&size=100&page={page}")
        for j in data.get("data") or []:
            out[j["id"]] = job("empresa", "cg-" + j["id"], j.get("title"), "Capgemini" + (f" ({j['brand']})" if j.get("brand") and j["brand"] != "Capgemini" else ""),
                               j.get("location"), j.get("apply_job_url"),
                               f"Nivel: {j.get('experience_level', '')}\n" + (j.get("description_stripped") or strip_html(j.get("description"))),
                               j.get("updated_at"), spain=True)
        if page * 100 >= (data.get("count") or 0):
            break
        time.sleep(PAUSA)
    return list(out.values())


def src_vigilar(cfg, log):
    """Páginas de empleo sin API: guarda los enlaces y avisa de los que aparecen nuevos."""
    from .. import db
    out = []
    for p in cfg["busqueda"]["portales_empresa"].get("vigilar", []):
        try:
            page = fetch(p["url"])
        except Exception as e:
            log(f"  vigilar {p['nombre']}: {e}")
            continue
        links = {}
        for href, txt in re.findall(r"""<a\s[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>""", page, re.S | re.I):
            t = strip_html(txt).replace("\n", " ")
            if 8 <= len(t) <= 140:
                links[urllib.parse.urljoin(p["url"], html.unescape(href))] = t
        key = "vigilar:" + p["url"]
        prev = db.meta_get(key)
        db.meta_set(key, sorted(set(links) | set(prev or [])))
        if prev is None:
            log(f"  {p['nombre']}: primera visita, {len(links)} enlaces guardados como referencia")
            continue
        for u in set(links) - set(prev):
            out.append(job("web", u, links[u], p["nombre"], p.get("ubicacion", ""), u,
                           f"Enlace nuevo en la página de empleo de {p['nombre']} ({p['url']}). Ábrelo para ver si es una oferta.",
                           db.now(), spain=True))
        time.sleep(PAUSA)
    return out
