"""Consultar y actualizar ofertas desde la terminal (lo usan los comandos de Claude Code).

  python -m jobfinder.ofertas nuevas [--dias 1] [--min 40]   ofertas nuevas a revisar (por nota + barrido de texto)
  python -m jobfinder.ofertas buscar <texto>                 busca en título, empresa y ubicación
  python -m jobfinder.ofertas ver <id>                       ficha completa de una oferta
  python -m jobfinder.ofertas estado <id> <estado> [nota]    cambia el estado (y añade una nota)
  python -m jobfinder.ofertas seguimiento                    candidaturas activas y correos recientes
"""
import json
import re
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone

from . import db
from .text import norm

# Ofertas con nota baja que merece la pena mirar igualmente (títulos raros que la puntuación no reconoce)
JUNIOR_TXT = re.compile(r"junior|\bjr\b|recien titulad|recien graduad|sin experiencia|graduate|trainee|entry.level|"
                        r"early career|new grad|primer empleo|practicas|becari")
SENIOR_TXT = re.compile(r"senior|\bsr\b|lead|principal|staff|architect|arquitect|manager|head of|director|jefe")


def _arg(flag, default):
    if flag not in sys.argv:
        return default
    try:
        return type(default)(sys.argv[sys.argv.index(flag) + 1])
    except (IndexError, ValueError):
        sys.exit(f"{flag} necesita un número.\n{__doc__}")


def _linea(j):
    return (f"[{j['score']:>3}] {j['id']} | {j['title']} — {j['company'] or '?'} | {j['location'] or '?'} "
            f"| {j['status']} | {j['url']}")


def nuevas():
    dias, minimo = _arg("--dias", 1), _arg("--min", 40)
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
    with closing(db.connect()) as con:
        rows = [dict(r) for r in con.execute(
            "select id, title, company, location, url, score, status, reasons from jobs "
            "where status='nueva' and first_seen>=? order by score desc", (desde,))]
    top = [j for j in rows if j["score"] >= minimo]
    extra = [j for j in rows if j["score"] < minimo and JUNIOR_TXT.search(norm(j["title"]))
             and not SENIOR_TXT.search(norm(j["title"]))]
    print(f"{len(rows)} ofertas nuevas en {dias} día(s). Nota >= {minimo}: {len(top)}. "
          f"Nota baja pero título junior: {len(extra)}.\n")
    for titulo, lista in (("POR NOTA", top), ("POR TEXTO (revisar a mano)", extra)):
        if lista:
            print(f"== {titulo}")
            for j in lista[:80]:
                print(_linea(j))
                print("      " + " · ".join(json.loads(j["reasons"] or "[]")[:4]))
            print()


def buscar(texto):
    q = f"%{texto.lower()}%"
    with closing(db.connect()) as con:
        rows = con.execute("select id, title, company, location, url, score, status from jobs "
                           "where lower(title) like ? or lower(company) like ? or lower(location) like ? "
                           "order by last_seen desc limit 40", (q, q, q)).fetchall()
    for r in rows:
        print(_linea(dict(r)))
    if not rows:
        print("Sin resultados.")


def ver(job_id):
    j = db.get_job(job_id)
    if not j:
        sys.exit(f"No existe la oferta {job_id}")
    print(f"{j['title']} — {j['company']}\n{j['location']} · {j['source']} · nota {j['score']} · estado {j['status']}")
    print(f"URL: {j['url']}\nPublicada: {j['posted'] or '?'} · vista por última vez: {j['last_seen']}")
    if j.get("salary"):
        print(f"Salario: {j['salary']}")
    print("Por qué: " + " · ".join(j["reasons"] if isinstance(j["reasons"], list) else json.loads(j["reasons"] or "[]")))
    if j.get("notes"):
        print(f"Notas: {j['notes']}")
    print("\n" + (j["description"] or "(sin descripción: ábrela en el navegador)"))
    with closing(db.connect()) as con:
        mails = con.execute("select received, sender, subject, kind, snippet from emails where job_id=? "
                            "order by received", (job_id,)).fetchall()
    for m in mails:
        print(f"\n[correo {m['kind']}] {m['received'][:10]} {m['sender']}: {m['subject']}\n  {m['snippet']}")


def estado(job_id, nuevo, nota=None):
    j = db.get_job(job_id)
    if not j:
        sys.exit(f"No existe la oferta {job_id}")
    if nota:
        fecha = datetime.now().strftime("%d/%m/%Y")
        nota = (j.get("notes") + "\n" if j.get("notes") else "") + f"{fecha}: {nota}"
    db.update_job(job_id, nuevo, nota)
    print(f"{job_id}: {j['status']} -> {nuevo}")


def seguimiento():
    with closing(db.connect()) as con:
        rows = [dict(r) for r in con.execute(
            "select id, title, company, location, url, score, status, applied_at from jobs "
            "where status in ('interesa','aplicada','entrevista','oferta') order by status, applied_at")]
    hoy = datetime.now(timezone.utc)
    for j in rows:
        dias = (hoy - datetime.fromisoformat(j["applied_at"])).days if j["applied_at"] else None
        aviso = "  ← follow-up pendiente" if j["status"] == "aplicada" and dias is not None and dias >= 7 else ""
        print(_linea(j) + (f" | hace {dias} d" if dias is not None else "") + aviso)
    print("\nCorreos recientes:")
    for m in db.recent_emails(15):
        print(f"  {m['received'][:10]} [{m['kind']}] {m['company'] or '?'} — {m['subject']}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
    elif a[0] == "nuevas":
        nuevas()
    elif a[0] == "buscar" and len(a) > 1:
        buscar(" ".join(a[1:]))
    elif a[0] == "ver" and len(a) > 1:
        ver(a[1])
    elif a[0] == "estado" and len(a) > 2:
        estado(a[1], a[2], " ".join(a[3:]) or None)
    elif a[0] == "seguimiento":
        seguimiento()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
