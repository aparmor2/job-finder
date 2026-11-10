import threading
import time
from contextlib import closing

from . import db, mail
from .scoring import score
from .sources import sources

state = {"running": False, "log": [], "current": "", "started": None, "finished": None}
_lock = threading.Lock()


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    state["log"] = (state["log"] + [line])[-300:]


def run(cfg):
    """Descarga todas las fuentes, guarda y re-puntúa. Bloqueante."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        state.update(running=True, log=[], started=db.now(), finished=None)
        ts = db.now()
        totals = {"new": 0, "seen": 0, "dup": 0}
        resumen = {}
        for name, fn in sources(cfg):
            state["current"] = name
            log(f"→ {name}…")
            t0 = time.time()
            try:
                jobs = fn(cfg, log)
            except Exception as e:
                log(f"  ✗ {name}: {type(e).__name__}: {e}")
                resumen[name] = {"error": str(e)}
                continue
            counts = {"new": 0, "seen": 0, "dup": 0}
            with closing(db.connect()) as con, con:
                for j in jobs:
                    if j["title"]:
                        counts[db.upsert(con, j, ts)] += 1
            for k in totals:
                totals[k] += counts[k]
            resumen[name] = {"total": len(jobs), "nuevas": counts["new"]}
            log(f"  ✓ {len(jobs)} ofertas ({counts['new']} nuevas, {counts['dup']} duplicadas) en {time.time() - t0:.0f}s")
        state["current"] = "puntuando"
        with closing(db.connect()) as con, con:
            n = db.rescore_all(con, lambda j: score(j, cfg["perfil"]))
        log(f"Listo: {totals['new']} nuevas · {n} en total puntuadas.")
        revisar_correo()
        db.meta_set("last_refresh", {"at": db.now(), "nuevas": totals["new"], "fuentes": resumen})
        return True
    finally:
        state.update(running=False, current="", finished=db.now())
        _lock.release()


def revisar_correo():
    """Lee Gmail si está configurado. Nunca rompe la búsqueda de ofertas."""
    if not mail.credenciales():
        return None
    state["current"] = "correo"
    log("→ correo…")
    try:
        return mail.check(log)
    except Exception as e:
        log(f"  ✗ correo: {type(e).__name__}: {e}")
        db.meta_set("last_mail", {"at": db.now(), "error": str(e)})
        return None


def run_async(cfg):
    if state["running"]:
        return False
    threading.Thread(target=run, args=(cfg,), daemon=True).start()
    return True


def rescore(cfg):
    with closing(db.connect()) as con, con:
        return db.rescore_all(con, lambda j: score(j, cfg["perfil"]))
