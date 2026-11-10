"""Ticjob (RSS por palabra clave)."""
import html
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

from .base import PAUSA, fetch, job, strip_html


def src_ticjob(cfg, log):
    urls = ["https://www.ticjob.es/rss"] + [
        "https://ticjob.es/esp/rss?keywords=" + urllib.parse.quote(k) for k in cfg["busqueda"]["ticjob_palabras"]]
    out = {}
    for u in urls:
        try:
            root = ET.fromstring(fetch(u).encode())
        except Exception as e:
            log(f"  ticjob {u}: {e}")
            continue
        for it in root.iter("item"):
            link = (it.findtext("link") or "").strip()
            ext = link.rstrip("/").rsplit("/", 1)[-1]
            if ext in out:
                continue
            raw = html.unescape(it.findtext("title") or "")
            parts = raw.rsplit(" - ", 2)
            title, company, loc = (parts + ["", ""])[:3] if len(parts) == 3 else (raw, "", "")
            loc_parts = [p for p in loc.split(",") if p and not p.isdigit() and p != "ES"]
            loc = ", ".join(dict.fromkeys(loc_parts))
            remote = bool(re.search(r"(?i)remoto|teletrabajo", title))
            out[ext] = job("ticjob", ext, title, company, loc + (" (remoto)" if remote else ""), link,
                           strip_html(it.findtext("description")), it.findtext("pubDate"), remote=remote, spain=True)
        time.sleep(PAUSA)
    return list(out.values())
