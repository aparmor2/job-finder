import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from .text import norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "jobs.db")

SCHEMA = """
create table if not exists jobs (
  id text primary key, source text, title text, company text, location text, url text,
  description text, posted text, salary text, remote int, spain int,
  first_seen text, last_seen text, dup_key text,
  score int default 0, bucket text, reasons text, skills text, years int,
  status text default 'nueva', notes text default '', applied_at text, status_at text
);
create index if not exists jobs_dup on jobs(dup_key);
create table if not exists meta (key text primary key, value text);
create table if not exists emails (
  msgid text primary key, job_id text, received text, sender text, subject text, snippet text, kind text, seen_at text
);
create index if not exists emails_job on emails(job_id);
"""

LIST_FIELDS = ("id, source, title, company, location, url, posted, salary, remote, first_seen, last_seen, "
               "score, bucket, reasons, skills, years, status, notes, applied_at, status_at, "
               "(select count(*) from emails e where e.job_id=jobs.id) as n_mail, "
               "(select kind from emails e where e.job_id=jobs.id order by received desc limit 1) as last_mail")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def dup_key(j):
    t = re.sub(r"\(.*?\)|[^a-z0-9 ]", " ", norm(j["title"]))
    return " ".join(t.split())[:70] + "|" + " ".join(re.sub(r"[^a-z0-9 ]", " ", norm(j["company"])).split()[:2])


def upsert(con, j, ts):
    """Inserta o actualiza. Devuelve 'new', 'seen' o 'dup' (misma oferta ya vista en otra fuente)."""
    if con.execute("select 1 from jobs where id=?", (j["id"],)).fetchone():
        con.execute("""update jobs set title=?, company=?, location=coalesce(nullif(?,''),location), url=?,
                       description=coalesce(nullif(?,''),description), posted=coalesce(nullif(?,''),posted),
                       salary=?, remote=?, spain=?, last_seen=? where id=?""",
                    (j["title"], j["company"], j["location"], j["url"], j["description"], j["posted"],
                     j["salary"], j["remote"], j["spain"], ts, j["id"]))
        return "seen"
    k = dup_key(j)
    dup = con.execute("select id from jobs where dup_key=? limit 1", (k,)).fetchone()
    if dup:
        con.execute("update jobs set last_seen=? where id=?", (ts, dup["id"]))
        return "dup"
    con.execute("""insert into jobs (id, source, title, company, location, url, description, posted, salary, remote, spain,
                   first_seen, last_seen, dup_key) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (j["id"], j["source"], j["title"], j["company"], j["location"], j["url"], j["description"],
                 j["posted"], j["salary"], j["remote"], j["spain"], ts, ts, k))
    return "new"


def known_ids(prefix):
    with closing(connect()) as con:
        return {r["id"] for r in con.execute("select id from jobs where id like ?", (prefix + "%",))}


def rescore_all(con, scorer):
    rows = con.execute("select id, title, company, location, description, remote, spain, posted from jobs").fetchall()
    for r in rows:
        res = scorer(dict(r))
        con.execute("update jobs set score=?, bucket=?, reasons=?, skills=?, years=? where id=?",
                    (res["score"], res["bucket"], json.dumps(res["reasons"], ensure_ascii=False),
                     json.dumps(res["skills"], ensure_ascii=False), res["years"], r["id"]))
    return len(rows)


def list_jobs(dias=30):
    """Ofertas vistas en los últimos `dias` días, más todas las que ya tienen seguimiento."""
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
    with closing(connect()) as con:
        rows = con.execute(f"select {LIST_FIELDS} from jobs where last_seen>=? or status not in ('nueva','descartada') "
                           "order by score desc, first_seen desc", (limite,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reasons"] = json.loads(d["reasons"] or "[]")
        d["skills"] = json.loads(d["skills"] or "[]")
        out.append(d)
    return out


def get_job(job_id):
    with closing(connect()) as con:
        r = con.execute("select * from jobs where id=?", (job_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["reasons"] = json.loads(d["reasons"] or "[]")
    d["skills"] = json.loads(d["skills"] or "[]")
    with closing(connect()) as con:
        d["emails"] = [dict(e) for e in con.execute(
            "select received, sender, subject, snippet, kind from emails where job_id=? order by received desc", (job_id,))]
    return d


def recent_emails(limit=40):
    with closing(connect()) as con:
        return [dict(r) for r in con.execute(
            "select e.received, e.sender, e.subject, e.snippet, e.kind, e.job_id, j.title, j.company "
            "from emails e left join jobs j on j.id=e.job_id order by e.received desc limit ?", (limit,))]


ESTADOS = ("nueva", "interesa", "aplicada", "entrevista", "oferta", "rechazada", "descartada")


def update_job(job_id, status=None, notes=None):
    with closing(connect()) as con, con:
        if status is not None:
            if status not in ESTADOS:
                raise ValueError("estado no válido")
            con.execute("update jobs set status=?, status_at=? where id=?", (status, now(), job_id))
            if status == "aplicada":
                con.execute("update jobs set applied_at=coalesce(applied_at, ?) where id=?", (now(), job_id))
        if notes is not None:
            con.execute("update jobs set notes=? where id=?", (notes, job_id))


def meta_get(key, default=None):
    with closing(connect()) as con:
        r = con.execute("select value from meta where key=?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def meta_set(key, value):
    with closing(connect()) as con, con:
        con.execute("insert or replace into meta (key, value) values (?, ?)", (key, json.dumps(value, ensure_ascii=False)))
