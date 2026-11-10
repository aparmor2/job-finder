"""Lee Gmail por IMAP (contraseña de aplicación, sin API) y asocia los correos a tus candidaturas.

Configurar:  python -m jobfinder.mail --configurar   (o configurar-correo.bat)
Revisar ya:  python -m jobfinder.mail
"""
import email
import getpass
import html as htmllib
import imaplib
import json
import os
import re
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

from . import db
from .sources import strip_html
from .text import norm

CRED = os.path.join(db.ROOT, "data", "correo.json")
HOST = "imap.gmail.com"
SEGUIMIENTO = ("aplicada", "entrevista", "oferta", "rechazada")
MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# Plataformas que envían correos en nombre de las empresas
PORTALES = ("greenhouse", "ashbyhq", "lever.co", "workday", "myworkday", "successfactors", "sapsf", "sap.com",
            "tecnoempleo", "infojobs", "ticjob", "getmanfred", "smartrecruiters", "teamtailor", "personio",
            "recruitee", "workable", "bamboohr", "welcometothejungle", "jobandtalent", "indeed", "linkedin")
# Palabras del nombre de empresa que no sirven para identificarla
GENERICAS = {"group", "grupo", "consulting", "technologies", "technology", "solutions", "spain", "espana", "software",
             "digital", "services", "talent", "the", "and", "s.l", "s.a", "sl", "sa", "inc", "ltd", "gmbh", "company"}

RECHAZO = re.compile(
    r"lamentablemente|lamentamos|sentimos (comunicarte|informarte)|no (has|ha) sido seleccionad|no continuar|"
    r"no (vamos a )?seguir adelante|otr[oa]s candidat|otros perfiles|(hemos )?cubierto (el|la) (puesto|vacante)|"
    r"unfortunately|regret to inform|not (to )?(be )?mov(e|ing) forward|decided to (move forward|proceed|pursue|go ahead) with other|"
    r"not been selected|position has been filled|will not be progressing|not be taking your application")
ACUSE = re.compile(
    r"hemos recibido|recibido (correctamente )?tu (candidatura|solicitud|cv)|gracias por (tu|su) (interes|candidatura|solicitud)|"
    r"thank(s| you)( so much| very much)? for (applying|your application|your interest)|thanks again for applying|"
    r"application (has been |was )?received|(we'?ve|we have|we) received your application|we have received|"
    r"(candidatura|solicitud|inscripcion) (ha sido )?(registrada|enviada|recibida|completada)|cv (enviado|recibido)|"
    r"nueva solicitud de empleo recibida")
ENTREVISTA = re.compile(
    r"entrevista|interview|videollamada|llamada (telefonica|rapida)|agendar|reunion|prueba tecnica|"
    r"technical (test|assessment|challenge)|coding challenge|case study|schedule (a|an|your)|book a (time|slot)|calendly|"
    r"siguiente(s)? (paso|fase)|next (step|stage|round)")
BOLETIN = re.compile(r"alerta|nuevas ofertas|ofertas (de empleo|para ti|que)|job alert|jobs? for you|new jobs|empleos (que|para)|"
                     r"recomendad|newsletter|boletin|semanal|weekly|nuevos puestos|new (positions|openings)|job notification")
# Correos de gestión de cuenta en los portales: no aportan nada al seguimiento
# Remitentes de alertas y recomendaciones de empleo (no son respuestas de empresas)
ALERTAS = {"jobalerts-noreply@linkedin.com", "jobs-listings@linkedin.com"}
CUENTA = re.compile(r"cuenta creada|bienvenid|welcome to|verifica|confirm (your )?email|restablec|reset (your )?password|contrasena")
LABORAL = re.compile(r"candidatura|puesto|position|\brole\b|\bjob\b|empleo|vacante|proceso de seleccion|recruit|hiring|entrevista|interview")
TIPOS = {"rechazo": "Rechazo", "entrevista": "Entrevista", "recibida": "Acuse de recibo", "otro": "Correo"}


# ---------- Credenciales

def credenciales():
    if os.environ.get("JOBFINDER_GMAIL_PASS"):
        return {"usuario": os.environ.get("JOBFINDER_GMAIL_USER", ""), "contrasena_app": os.environ["JOBFINDER_GMAIL_PASS"]}
    try:
        with open(CRED, encoding="utf-8") as f:
            c = json.load(f)
        return c if c.get("usuario") and c.get("contrasena_app") else None
    except FileNotFoundError:
        return None


def configurar():
    print("Conectar Gmail al Job Finder (solo lectura, por IMAP).")
    print("Necesitas una contraseña de aplicación: myaccount.google.com -> Seguridad -> Contraseñas de aplicaciones.\n")
    usuario = input("Tu Gmail: ").strip()
    clave = getpass.getpass("Contraseña de aplicación (no se ve al escribir): ").replace(" ", "").strip()
    try:
        conectar({"usuario": usuario, "contrasena_app": clave}).logout()
    except imaplib.IMAP4.error as e:
        print(f"\nNo se pudo entrar: {e}\nRevisa que IMAP esté activo y que la contraseña sea la de aplicación (16 letras).")
        return
    os.makedirs(os.path.dirname(CRED), exist_ok=True)
    with open(CRED, "w", encoding="utf-8") as f:
        json.dump({"usuario": usuario, "contrasena_app": clave}, f)
    print(f"\nListo. Guardado en {CRED} (solo en este PC). El dashboard revisará el correo en cada búsqueda.")


def conectar(c):
    con = imaplib.IMAP4_SSL(HOST, timeout=30)
    con.login(c["usuario"], c["contrasena_app"])
    return con


# ---------- Lectura

def _hdr(v):
    try:
        return str(make_header(decode_header(v or ""))).strip()
    except Exception:
        return (v or "").strip()


def _cuerpo(msg):
    plano, html = [], []
    for part in msg.walk():
        if part.get_content_maintype() != "text" or part.get_filename():
            continue
        raw = part.get_payload(decode=True) or b""
        txt = raw.decode(part.get_content_charset() or "utf-8", errors="replace")
        (plano if part.get_content_subtype() == "plain" else html).append(txt)
    sin_estilos = re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", "\n".join(html))
    texto = "\n".join(plano) if plano else strip_html(sin_estilos)
    for _ in range(2):  # CSS suelto que algunos portales (Tecnoempleo) meten en el texto plano
        texto = re.sub(r"(@media[^{]*)?[^{}\n]{0,200}\{[^{}]*\}", " ", texto)
    return re.sub(r"\s+", " ", htmllib.unescape(texto)).strip()


def _fecha(v):
    try:
        return parsedate_to_datetime(v).astimezone(timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return db.now()


def _cabeceras(con, uids):
    """{uid: Message con From/Subject/Date/Message-ID} sin marcar como leído."""
    out = {}
    for i in range(0, len(uids), 200):
        typ, data = con.uid("fetch", b",".join(uids[i:i + 200]), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])")
        for item in data or []:
            if isinstance(item, tuple):
                m = re.search(rb"UID (\d+)", item[0])
                if m:
                    out[m.group(1)] = email.message_from_bytes(item[1])
    return out


# ---------- Asociación con candidaturas

def claves_empresa(nombre):
    """'Indra / Minsait' -> ['indra', 'minsait']; 'Power Electronics S.L.' -> ['power electronics']."""
    out = []
    for parte in re.split(r"/|\||\(|\)|,", norm(nombre)):
        palabras = [w for w in re.findall(r"[a-z0-9&.]+", parte) if w.strip(".") not in GENERICAS]
        frase = " ".join(palabras).strip(" .")
        if len(frase) >= 3:
            out.append(frase)
    return out


def _aparece(frase, texto):
    return re.search(r"(?<![a-z0-9])" + re.escape(frase) + r"(?![a-z0-9])", texto) is not None


def _en_dominio(frase, dominio):
    return len(frase) >= 4 and frase.replace(" ", "") in dominio.replace("-", "").replace(".", "")


def asociar(cand, de_nombre, de_dir, asunto, cuerpo):
    """Devuelve el job_id más probable o None. cand: [(job, claves)]."""
    dominio = norm(de_dir.split("@")[-1])
    cab = norm(de_nombre) + " | " + norm(asunto)
    txt = norm(cuerpo[:6000])
    # Coincidencia exacta: el enlace a la oferta lleva su id (Tecnoempleo rf-…, Greenhouse /jobs/…)
    for job, _ in cand:
        ref = re.findall(r"[0-9a-f]{10,}", job["id"].split(":", 1)[-1])
        if ref and ref[-1] in txt:
            return job
    portal = any(p in dominio for p in PORTALES)
    laboral =bool(re.search(r"candidatura|solicitud|application|proceso|entrevista|interview|oferta|puesto|position|role|vacante", cab + " " + txt))
    hits = []
    for job, claves in cand:
        if any(_en_dominio(k, dominio) or _aparece(k, cab) for k in claves) or \
           ((portal or laboral) and any(_aparece(k, txt) for k in claves)):
            titulo = [w for w in re.findall(r"[a-z0-9#+.]{4,}", norm(job["title"]))]
            hits.append((sum(_aparece(w, cab + " " + txt) for w in titulo), job["applied_at"] or "", job))
    if not hits:
        return None
    hits.sort(key=lambda h: (h[0], h[1]), reverse=True)
    elegido = dict(hits[0][2])
    # Varias candidaturas de la misma empresa con la misma puntuación: se asocia a la más reciente,
    # pero sin cambiar su estado automáticamente (podría ser otra de esa empresa).
    elegido["_dudoso"] = len(hits) > 1 and hits[1][0] == hits[0][0]
    return elegido


def clasificar(asunto, cuerpo):
    t = norm(asunto + " \n " + cuerpo[:5000]).replace("’", "'")
    if RECHAZO.search(t):
        return "rechazo"
    if ACUSE.search(t):
        return "recibida"
    if ENTREVISTA.search(t):
        return "entrevista"
    return "otro"


def check(log=print, dias_max=90):
    """Revisa la bandeja de entrada. Devuelve un resumen o None si no hay correo configurado."""
    c = credenciales()
    if not c:
        return None
    with closing(db.connect()) as con:
        jobs = [dict(r) for r in con.execute(
            f"select id, title, company, status, applied_at from jobs where status in ({','.join('?' * len(SEGUIMIENTO))})",
            SEGUIMIENTO)]
        vistos = {r[0] for r in con.execute("select msgid from emails")}
    cand = [(j, claves_empresa(j["company"])) for j in jobs if j["company"]]
    desde = datetime.now(timezone.utc) - timedelta(days=dias_max)
    # Fechas sin zona (editadas a mano en la BD) se tratan como UTC para poder compararlas.
    fechas = [datetime.fromisoformat(j["applied_at"]) for j in jobs if j["applied_at"]]
    fechas = [f if f.tzinfo else f.replace(tzinfo=timezone.utc) for f in fechas]
    if fechas:
        desde = max(desde, min(fechas) - timedelta(days=2))
    since = f"{desde.day:02d}-{MESES[desde.month - 1]}-{desde.year}"

    imap = conectar(c)
    try:
        imap.select("INBOX", readonly=True)
        typ, data = imap.uid("search", None, f"(SINCE {since})")
        uids = data[0].split() if data and data[0] else []
        nuevos, cambios = [], []
        for uid, h in _cabeceras(imap, uids).items():
            msgid = (h.get("Message-ID") or f"uid-{uid.decode()}").strip()
            if msgid in vistos:
                continue
            de_nombre, de_dir = parseaddr(_hdr(h.get("From")))
            asunto = _hdr(h.get("Subject"))
            dominio = norm(de_dir.split("@")[-1])
            # Filtro barato con cabeceras antes de descargar el cuerpo
            cab = norm(de_nombre + " " + de_dir + " " + asunto)
            posible = any(p in dominio for p in PORTALES) or \
                any(any(_aparece(k, cab) or _en_dominio(k, dominio) for k in ks) for _, ks in cand) or \
                re.search(r"candidatura|solicitud|application|entrevista|interview|proceso de seleccion", cab)
            if not posible or BOLETIN.search(norm(asunto)) or CUENTA.search(norm(asunto)) or \
                    de_dir.lower() in ALERTAS:  # alertas de empleo: las lee la fuente LinkedIn, no son respuestas
                continue
            typ, d = imap.uid("fetch", uid, "(BODY.PEEK[])")
            raw = next((x[1] for x in d or [] if isinstance(x, tuple)), None)
            if not raw:
                continue
            cuerpo = _cuerpo(email.message_from_bytes(raw))
            job = asociar(cand, de_nombre, de_dir, asunto, cuerpo)
            tipo = clasificar(asunto, cuerpo)
            if not job and (tipo == "otro" or not LABORAL.search(norm(asunto + " " + cuerpo[:3000]))):
                continue  # ruido de portales o correos que no son de procesos de selección
            nuevos.append({"msgid": msgid, "job_id": job["id"] if job else None, "received": _fecha(h.get("Date")),
                           "sender": f"{de_nombre} <{de_dir}>" if de_nombre else de_dir, "subject": asunto,
                           "snippet": cuerpo[:700], "kind": tipo, "seen_at": db.now()})
            if job and job.get("_dudoso"):
                log(f"  ? {job['company']}: hay varias candidaturas de esta empresa; revisa a cuál corresponde «{asunto[:60]}»")
            elif job:
                nuevo = {"rechazo": "rechazada", "entrevista": "entrevista"}.get(tipo)
                if nuevo == "rechazada" and job["status"] in ("aplicada", "entrevista") or \
                   nuevo == "entrevista" and job["status"] == "aplicada":
                    job["status"] = nuevo
                    cambios.append((job, nuevo, asunto))
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    with closing(db.connect()) as con, con:
        for m in nuevos:
            con.execute("insert or ignore into emails (msgid, job_id, received, sender, subject, snippet, kind, seen_at) "
                        "values (:msgid, :job_id, :received, :sender, :subject, :snippet, :kind, :seen_at)", m)
    for job, estado, asunto in cambios:
        db.update_job(job["id"], status=estado)
        log(f"  ✉ {job['company']} · {job['title'][:50]} → {estado} («{asunto[:60]}»)")
    asociados = sum(1 for m in nuevos if m["job_id"])
    log(f"  ✓ correo: {len(nuevos)} correos nuevos de candidaturas ({asociados} asociados, {len(cambios)} cambios de estado)")
    res = {"at": db.now(), "nuevos": len(nuevos), "asociados": asociados, "cambios": len(cambios)}
    db.meta_set("last_mail", res)
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--configurar" in sys.argv:
        return configurar()
    if not credenciales():
        print("Correo sin configurar. Ejecuta: python -m jobfinder.mail --configurar")
        return
    check()


if __name__ == "__main__":
    main()
