"""Tecnoempleo (RSS de alertas): provincias y tecnologías de config.json."""
import html
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

from ..text import norm
from .base import PAUSA, fetch, job, strip_html


# Provincias de Tecnoempleo: el id es su posición alfabética desde 231 (A Coruña) hasta 282 (Zaragoza)
TE_PROVINCIAS = [
    "A Coruña", "Álava", "Albacete", "Alicante", "Almería", "Asturias",
    "Ávila", "Badajoz", "Baleares", "Barcelona", "Bizkaia", "Burgos",
    "Cáceres", "Cádiz", "Cantabria", "Castellón", "Ceuta", "Ciudad Real",
    "Córdoba", "Cuenca", "Gipuzkoa", "Girona", "Granada", "Guadalajara",
    "Huelva", "Huesca", "Jaén", "La Rioja", "Las Palmas", "León",
    "Lugo", "Lleida", "Madrid", "Málaga", "Melilla", "Murcia",
    "Navarra", "Ourense", "Palencia", "Pontevedra", "Salamanca", "Sta. Cruz de Tenerife",
    "Segovia", "Sevilla", "Soria", "Tarragona", "Teruel", "Toledo",
    "Valencia", "Valladolid", "Zamora", "Zaragoza",
]
TE_PROV = {norm(n): (str(231 + i), n) for i, n in enumerate(TE_PROVINCIAS)}
TE_PROV.update({"vizcaya": TE_PROV["bizkaia"], "guipuzcoa": TE_PROV["gipuzkoa"], "alava": TE_PROV["alava"],
                "tenerife": TE_PROV["sta. cruz de tenerife"], "la coruna": TE_PROV["a coruna"], "coruna": TE_PROV["a coruna"],
                "castellon de la plana": TE_PROV["castellon"], "islas baleares": TE_PROV["baleares"], "mallorca": TE_PROV["baleares"]})
TE_MODALIDAD = {"hibrido": "híbrido", "presencial": "presencial", "remoto": "remoto", "teletrabajo": "remoto"}


def _te_field(d, name):
    m = re.search(name + r":</b>&nbsp;(.*?)(?:<br\s*/?>|$)", d, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def src_tecnoempleo(cfg, log):
    b = cfg["busqueda"]
    combos = []
    for p in b["tecnoempleo_provincias"]:
        if norm(p) not in TE_PROV:
            log(f"  tecnoempleo: provincia desconocida '{p}' (ver TE_PROVINCIAS en sources/tecnoempleo.py)")
            continue
        pid, pname = TE_PROV[norm(p)]
        combos.append((f"pr=,{pid},", pname))
        combos += [(f"te={urllib.parse.quote(t)}&pr=,{pid},", pname) for t in b["tecnoempleo_tecnologias"]]
    combos.append(("en_remoto=,1,", "Remoto"))
    combos += [(f"te={urllib.parse.quote(t)}&en_remoto=,1,", "Remoto") for t in b["tecnoempleo_tecnologias"]]

    out = {}
    for q, hint in combos:
        try:
            root = ET.fromstring(fetch("https://www.tecnoempleo.com/alertas-empleo-rss.php?" + q).encode())
        except Exception as e:
            log(f"  tecnoempleo {q}: {e}")
            continue
        for it in root.iter("item"):
            link = (it.findtext("link") or "").strip()
            m = re.search(r"rf-([0-9a-f]+)", link)
            ext = m.group(1) if m else link
            if ext in out:
                continue
            d = it.findtext("description") or ""
            prov, pob = _te_field(d, "Provincia"), _te_field(d, "Población")
            modalidad = TE_MODALIDAD.get(norm(prov), "")
            lugar = pob or ("" if modalidad else prov)
            if "remoto" in norm(lugar):  # Población = "100% En remoto"
                hint, lugar = "Remoto", hint if hint != "Remoto" else ""
            if hint == "Remoto":
                loc = "Remoto" + (f" · {lugar}" if lugar else "")
            else:
                loc = (lugar or hint) + (f" ({modalidad})" if modalidad else "")
                if lugar and norm(hint) not in norm(lugar):
                    loc += f" · {hint}"
            desc = d.split("Descripción:</b>&nbsp;", 1)[-1] if "Descripción:" in d else d
            out[ext] = job("tecnoempleo", ext, it.findtext("title"), _te_field(d, "Empresa"), loc, link,
                           strip_html(desc), it.findtext("pubDate"),
                           remote=hint == "Remoto" or modalidad == "remoto", spain=True)
        time.sleep(PAUSA)
    return list(out.values())
