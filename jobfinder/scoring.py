"""Puntuación 0-100 por reglas, sin IA. Todo configurable en config.json -> perfil."""
import re
from datetime import datetime, timezone

from .text import found, has, norm

# Zonas fijas (siempre existen). Las zonas de ciudad son las demás claves de ubicacion.puntos
# que tengan su lista de lugares en ubicacion, p. ej. "cerca": [...], "valencia": [...].
FIJAS = {"remoto": "Remoto", "espana": "Otra ciudad España", "extranjero": "Extranjero", "desconocido": "Sin ubicación"}


def zonas(u):
    """Zonas de ciudad definidas en config.json, en el orden de ubicacion.puntos."""
    return [z for z in u["puntos"] if z not in FIJAS and not z.startswith("_") and isinstance(u.get(z), list)]


def etiqueta(u, z):
    return u.get("etiquetas", {}).get(z) or FIJAS.get(z) or z.replace("_", " ").title()


def lista_zonas(u):
    """Para el dashboard: todas las zonas en orden, con su nombre y si se ven por defecto (ciudades + remoto)."""
    ids = list(dict.fromkeys([z for z in u["puntos"] if not z.startswith("_") and (z in FIJAS or z in zonas(u))] + list(FIJAS)))
    ciudades = set(zonas(u))
    return [{"id": z, "nombre": etiqueta(u, z), "visible": z in ciudades or z == "remoto"} for z in ids]

EXP_RE = re.compile(
    r"(?:(?:al menos|minimo|mas de|over|at least|min\.?)\s*)?(\d{1,2})\s*(?:\+|-\s*\d{1,2})?\s*(?:anos|ano|years|year|yrs)\b")
EXP_CTX = re.compile(r"experien|exp\b|trayectoria")



def bucket(job, p):
    u = p["ubicacion"]
    loc = norm(job["location"])
    title = norm(job["title"])
    hibrido = re.search(r"hibrid|hybrid|presencial|on-?site", loc)
    is_remote = not hibrido and (job.get("remote") == 1 or found(loc, u["remoto"]) or found(title, u["remoto"]))
    if is_remote:
        # Lo que queda al quitar las palabras de "remoto" es la restricción geográfica, si la hay
        restr = loc
        for t in u["remoto"]:
            restr = re.sub(r"(?<![a-z0-9])" + re.escape(norm(t)) + r"(?![a-z0-9])", " ", restr)
        restr = re.sub(r"\b(en|100%|only|based)\b|[^a-z ,]", " ", restr).strip(" ,")
        if (not restr or found(restr, u["remoto_ok"]) or found(restr, u["espana"])
                or any(found(restr, u[c]) for c in zonas(u))):
            return "remoto"
        return "extranjero"
    for b in zonas(u):
        if found(loc, u[b]):
            return b
    if found(loc, u["espana"]) or (job.get("spain") and loc):
        return "espana"
    if not loc:
        return "desconocido" if job.get("spain") else "extranjero"
    return "extranjero"


def years_required(desc):
    best = None
    for m in EXP_RE.finditer(desc):
        ctx = desc[max(0, m.start() - 60): m.end() + 60]
        if EXP_CTX.search(ctx):
            n = int(m.group(1))
            if n <= 15:
                best = n if best is None else max(best, n)
    return best


def score(job, p):
    title = norm(job["title"])
    desc = norm(job["description"])
    full = title + " \n " + desc
    s = p["base"]
    why = []

    def add(pts, txt):
        nonlocal s
        if pts:
            s += pts
            why.append(("+" if pts > 0 else "") + f"{pts} {txt}")

    b = bucket(job, p)
    add(p["ubicacion"]["puntos"].get(b, 0), etiqueta(p["ubicacion"], b))

    rol = {t: w for t, w in p["rol_titulo"].items() if not t.startswith("_")}
    hits = sorted(((w, t) for t, w in rol.items() if has(title, t)), reverse=True)
    if hits:
        add(min(sum(w for w, _ in hits), p["tope_rol"]), "rol: " + ", ".join(t for _, t in hits[:3]))
    else:
        add(-10, "rol no reconocido en el título")

    skills = found(desc, p["habilidades_cv"])
    add(min(len(skills) * p["puntos_por_habilidad"], p["tope_habilidades"]), "tu stack: " + ", ".join(skills[:6]))

    jt = found(title, p["junior"])
    if jt:
        add(p["puntos_junior_titulo"], "junior en título")
    elif found(desc, p["junior"]):
        add(p["puntos_junior_texto"], "menciona junior/sin experiencia")

    st = found(title, p["senior"])
    if st and not jt:
        add(p["puntos_senior_titulo"], "senior: " + ", ".join(st[:2]))

    yrs = years_required(desc)
    if yrs is not None:
        tabla = sorted(((int(k), v) for k, v in p["anos_experiencia"].items()), reverse=True)
        pts = next((v for k, v in tabla if yrs >= k), 0)
        add(pts, f"pide {yrs} año(s) de experiencia")

    if job.get("posted"):
        posted = datetime.fromisoformat(job["posted"])
        if posted.tzinfo is None:  # las fechas añadidas a mano (fuentes manuales) no llevan zona horaria
            posted = posted.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - posted).days
        tabla = sorted(((int(k), v) for k, v in p.get("antiguedad_dias", {}).items()), reverse=True)
        add(next((v for k, v in tabla if age >= k), 0), f"publicada hace {age} días")

    # Trampas habituales que el título no revela
    if not jt and re.search(r"(buscamos|seeking|looking for|incorporar)[^.\n]{0,40}\bsenior", desc):
        add(-20, "la descripción busca senior")
    for m in re.finditer(r"estudiante|matriculad|practicas curriculares|convenio de practicas|currently enrolled|"
                         r"enrolled in|pursuing a (?:bachelor|degree)|working student", desc):
        if not re.search(r"graduad|titulad|recien|graduate", desc[max(0, m.start() - 60): m.end() + 60]):
            add(-20, "pide ser estudiante")
            break
    if b == "remoto":
        if re.search(r"relocat|reubicaci", desc) and not re.search(r"relocat\w*[^.\n]{0,60}(spain|espana|madrid|barcelona|valencia)", desc):
            add(-25, "pide mudarse fuera de España")
        if (re.search(r"(modelo|formato|regimen|trabajo) hibrido|hybrid (model|working|work|setup)|\d dias? (de )?(teletrabajo|presencial)"
                      r"|modalidad:? (presencial|hibrid)|on-?site", desc)
                and not re.search(r"100 ?% (en )?remot|full(y)? remote|totalmente remot", full)):
            add(-15, "parece híbrido/presencial, no remoto")

    ajenas = found(title, p["tecnologias_ajenas"])
    if ajenas:
        add(p["puntos_tecnologia_ajena"], "tecnología fuera de tu CV: " + ", ".join(ajenas[:2]))

    otro = found(title, p["no_es_mi_rol"])
    if otro:
        add(p["puntos_no_es_mi_rol"], "no es tu perfil: " + otro[0])

    idi = found(title, p["idiomas_requeridos"])
    if idi:
        add(p["puntos_idioma_titulo"], "idioma: " + idi[0])
    else:
        idd = [i for i in found(desc, p["idiomas_requeridos"])
               if re.search(r"(fluent|native|nativo|fluido|required|imprescindible|c1|c2)[^.\n]{0,40}" + re.escape(i)
                            + r"|" + re.escape(i) + r"[^.\n]{0,40}(fluent|native|nativo|fluido|required|imprescindible|c1|c2)", desc)]
        if idd:
            add(p["puntos_idioma_texto"], "pide idioma: " + idd[0])

    return {"score": max(0, min(100, round(s))), "bucket": b, "reasons": why, "skills": skills, "years": yrs}


EN_WORDS = re.compile(r"\b(the|and|you|with|our|we|will|for|team|experience)\b")
ES_WORDS = re.compile(r"\b(el|la|los|las|con|para|nuestro|equipo|experiencia|de|y)\b")


def language(job):
    t = norm(job["title"] + " " + job["description"][:1500])
    return "en" if len(EN_WORDS.findall(t)) > len(ES_WORDS.findall(t)) else "es"
