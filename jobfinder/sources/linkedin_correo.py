"""LinkedIn sin scraping: lee las alertas de empleo que LinkedIn te manda a Gmail.

Requisitos: Gmail conectado (configurar-correo.bat) y, en LinkedIn, alertas de empleo con envío por email
a ese mismo Gmail (Ajustes → Direcciones de email: debe ser el principal). No entra en LinkedIn ni hace
peticiones a su web: solo lee correos que ya están en tu bandeja.
"""
import email
import html
import re
from contextlib import closing
from datetime import datetime, timedelta, timezone

from .. import db
from .base import job, strip_html

DIAS = 4  # cuántos días de correos mirar en cada búsqueda (las repetidas se ignoran)
REMITENTES = ("jobalerts-noreply@linkedin.com", "jobs-listings@linkedin.com")  # jobs-noreply = avisos de candidatura, no alertas
MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# El id es el último número del slug, justo antes de "/", "?", comillas o fin
JOB_URL = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?\s\"'<>]*-)?(\d{6,})(?=[/?\s\"'<>]|$)")
# Líneas de los bloques que no son título, empresa ni ubicación (línea completa o prefijo inequívoco)
RUIDO = re.compile(
    r"^(ver empleo|view job|solicitud sencilla|easy apply|promocionado|promoted|evaluando solicitudes|"
    r"actively recruiting|selecci[oó]n activa|esta empresa est[aá] contratando|this company is actively hiring|"
    r"s[eé] de los primeros|be an early applicant|apply with (your )?resume|solicitar con|top applicant|"
    r"antiguos? alumnos?\b|alumni$|\d+ (antiguos?|contactos?|conexi|connections?|school alum|company alum)|"
    r"tu alerta|your job alert|nuevos? empleos?\b|new jobs? match|ver todos|see all|-{3,}|={3,}|"
    r"https?://|\d+ (solicitantes|applicants)|hace \d|\d+ (days?|hours?|weeks?|months?|d[ií]as?|horas?) ago|"
    r"[€$£]|\d[\d.,]*\s*(k|mil)?\s*(€|eur|usd)|.*(coinciden con tus preferencias|match(es)? your preferences))",
    re.I)


def _partes(msg):
    plano, htm = [], []
    for part in msg.walk():
        if part.get_content_maintype() != "text" or part.get_filename():
            continue
        txt = (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", "replace")
        (plano if part.get_content_subtype() == "plain" else htm).append(txt)
    return "\n".join(plano), "\n".join(htm)


def _bloque(grupos):
    """grupos: bloques de líneas seguidas desde el enlace anterior. Usa el último con título + empresa."""
    utiles = []
    for g in reversed(grupos):
        utiles = [l for l in g if not RUIDO.search(l)]
        if len(utiles) >= 2:
            break
    if len(utiles) < 2:
        utiles = [l for g in grupos for l in g if not RUIDO.search(l)]
    if not utiles:
        return None
    titulo, empresa, lugar = (utiles + ["", ""])[:3]
    if " · " in empresa:
        empresa, lugar = empresa.split(" · ", 1)
    extra = " · ".join(l for g in grupos for l in g if re.search(r"solicitud sencilla|easy apply", l, re.I))
    return titulo, empresa, lugar, extra


def _de_texto(texto):
    """Formato texto plano: bloques 'Título / Empresa / Ubicación / Ver empleo: <url>'."""
    out, grupos = {}, [[]]
    for linea in texto.splitlines():
        linea = linea.strip()
        m = JOB_URL.search(linea)
        if m:
            datos = _bloque(grupos)
            if datos and m.group(1) not in out:
                out[m.group(1)] = datos
            grupos = [[]]
        elif not linea or re.match(r"^[-=]{3,}$", linea):
            if grupos[-1]:
                grupos.append([])
        else:
            grupos[-1].append(linea)
    return out


def _de_html(cuerpo):
    """Formato HTML: el texto del enlace a cada oferta (título) y lo que sigue hasta la siguiente (empresa · ubicación)."""
    out = {}
    cuerpo = re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", cuerpo)
    cuerpo = re.sub(r"\s+", " ", cuerpo)  # los saltos de línea del código HTML no separan nada
    cuerpo = re.sub(r"(?i)</(td|tr|table|p|div|h\d)>", r"<br>", cuerpo)
    enlaces = []
    for m in re.finditer(r"(?is)<a\b[^>]*href=([\"'])(.+?)\1[^>]*>(.*?)</a>", cuerpo):
        jm = JOB_URL.search(html.unescape(m.group(2)))
        if jm:
            enlaces.append((jm.group(1), m))
    for n, (jid, m) in enumerate(enlaces):
        dentro = [l.strip() for l in strip_html(m.group(3)).splitlines() if l.strip()]
        dentro = [l for l in dentro if not RUIDO.search(l)]
        if jid in out or not dentro or len(dentro[0]) < 4:
            continue
        fin = next((m2.start() for j2, m2 in enlaces[n + 1:] if j2 != jid), len(cuerpo))
        tramo = dentro[1:] + [l.strip() for l in strip_html(cuerpo[m.end():fin]).splitlines() if l.strip()]
        extra = " · ".join(l for l in tramo if re.search(r"solicitud sencilla|easy apply", l, re.I))
        empresa, lugar = ([l for l in tramo if not RUIDO.search(l)][:2] + ["", ""])[:2]
        if " · " in empresa:
            empresa, lugar = empresa.split(" · ", 1)
        out[jid] = (dentro[0], empresa, lugar, extra)
    return out


def parse(msg):
    """{job_id: (título, empresa, ubicación, extra)} de un correo de LinkedIn."""
    plano, htm = _partes(msg)
    ofertas = _de_texto(plano) if plano else {}
    for jid, datos in (_de_html(htm) if htm else {}).items():
        if jid not in ofertas:
            ofertas[jid] = datos
    return ofertas


def src_linkedin_correo(cfg, log):
    from .. import mail  # importación tardía: mail importa sources
    c = mail.credenciales()
    if not c:
        log("  LinkedIn (alertas): Gmail sin configurar")
        return []
    desde = datetime.now(timezone.utc) - timedelta(days=cfg["busqueda"].get("linkedin_dias_correo", DIAS))
    since = f"{desde.day:02d}-{MESES[desde.month - 1]}-{desde.year}"
    out = {}
    conocidas = db.known_ids("linkedin:")  # no pisar la descripción de las que ya tienen una real
    with closing(mail.conectar(c)) as imap:
        imap.select("INBOX", readonly=True)
        uids = set()
        for r in REMITENTES:
            typ, data = imap.uid("search", None, f'(SINCE {since} FROM "{r}")')
            uids |= set(data[0].split()) if data and data[0] else set()
        log(f"  LinkedIn (alertas): {len(uids)} correos desde {since}")
        for uid in sorted(uids):
            typ, data = imap.uid("fetch", uid, "(BODY.PEEK[])")
            raw = next((d[1] for d in data or [] if isinstance(d, tuple)), None)
            if not raw:
                continue
            msg = email.message_from_bytes(raw)
            fecha = msg.get("Date")
            asunto = mail._hdr(msg.get("Subject"))
            for jid, (titulo, empresa, lugar, extra) in parse(msg).items():
                if jid in out:
                    continue
                desc = "" if f"linkedin:{jid}" in conocidas else "\n".join(
                    x for x in (extra, f"Alerta de LinkedIn: {asunto}", "Descripción completa en LinkedIn (ábrela para leerla).") if x)
                out[jid] = job("linkedin", jid, titulo, empresa, lugar, f"https://www.linkedin.com/jobs/view/{jid}/",
                               desc, fecha, spain=True)
    return list(out.values())
