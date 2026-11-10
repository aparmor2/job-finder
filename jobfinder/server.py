import json
import os
import shutil
import sys
import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from . import db, mail, refresh
from .scoring import language, lista_zonas

ROOT = db.ROOT
WEB = os.path.join(ROOT, "web")
PERFIL = os.path.join(ROOT, "perfil")
PERFIL_EJEMPLO = os.path.join(ROOT, "perfil_ejemplo")


def load_config():
    path = os.path.join(ROOT, "config.json")
    if not os.path.exists(path):  # primera vez: parte del ejemplo
        shutil.copyfile(os.path.join(ROOT, "config.example.json"), path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(name):
    """Lee perfil/<name>; si no existe aún, la plantilla de perfil_ejemplo/."""
    for base in (PERFIL, PERFIL_EJEMPLO):
        try:
            with open(os.path.join(base, name), encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            pass
    return ""


class Handler(BaseHTTPRequestHandler):
    cfg = None

    def log_message(self, fmt, *args):  # silencio en consola
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(os.path.join(WEB, "index.html"), "rb") as f:
                return self.send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/jobs":
            return self.send(200, db.list_jobs())
        if path.startswith("/api/jobs/"):
            j = db.get_job(unquote(path[len("/api/jobs/"):]))
            if not j:
                return self.send(404, {"error": "no existe"})
            j["lang"] = language(j)
            return self.send(200, j)
        if path == "/api/status":
            return self.send(200, {**refresh.state, "last": db.meta_get("last_refresh")})
        if path == "/api/mail":
            return self.send(200, {"configurado": bool(mail.credenciales()), "last": db.meta_get("last_mail"),
                                   "correos": db.recent_emails()})
        if path == "/api/zonas":
            return self.send(200, lista_zonas(load_config()["perfil"]["ubicacion"]))
        if path == "/api/perfil":
            return self.send(200, {"cv": read_text("cv.txt"), "carta_es": read_text("carta_es.txt"),
                                   "carta_en": read_text("carta_en.txt"), "followup": read_text("followup.txt")})
        self.send(404, {"error": "no encontrado"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/refresh":
            Handler.cfg = load_config()
            return self.send(200, {"started": refresh.run_async(Handler.cfg)})
        if path == "/api/rescore":
            Handler.cfg = load_config()
            return self.send(200, {"rescored": refresh.rescore(Handler.cfg)})
        if path == "/api/mail":
            if refresh.state["running"]:
                return self.send(409, {"error": "Hay una búsqueda en marcha; el correo se revisa al terminar."})
            return self.send(200, {"result": refresh.revisar_correo(), "configurado": bool(mail.credenciales())})
        if path.startswith("/api/jobs/"):
            data = self.body()
            try:
                db.update_job(unquote(path[len("/api/jobs/"):]), data.get("status"), data.get("notes"))
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            return self.send(200, {"ok": True})
        self.send(404, {"error": "no encontrado"})


def needs_refresh(cfg):
    last = db.meta_get("last_refresh")
    if not last:
        return True
    at = datetime.fromisoformat(last["at"])
    return datetime.now(timezone.utc) - at > timedelta(hours=cfg["servidor"]["auto_refresco_horas"])


def needs_mail():
    last = db.meta_get("last_mail")
    return not last or datetime.now(timezone.utc) - datetime.fromisoformat(last["at"]) > timedelta(hours=1)


def auto_refresh_loop(cfg):
    while True:
        if needs_refresh(cfg):
            refresh.run(load_config())
        elif not refresh.state["running"] and needs_mail():
            refresh.revisar_correo()  # el correo se mira cada hora, las ofertas cada X horas
        threading.Event().wait(600)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = Handler.cfg = load_config()
    if "--solo-buscar" in sys.argv:  # para el Programador de tareas de Windows
        refresh.run(cfg)
        return
    port = cfg["servidor"]["puerto"]
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Job Finder en {url}  (Ctrl+C para cerrar)")
    threading.Thread(target=auto_refresh_loop, args=(cfg,), daemon=True).start()
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
