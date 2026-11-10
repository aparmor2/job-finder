"""Utilidades comunes a todas las fuentes: descargas, fechas, limpieza de HTML y job()."""
import base64
import html
import json
import os
import re
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
PAUSA = 0.4  # segundos entre peticiones al mismo sitio, por educación


def fetch(url, headers=None, data=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    if data is not None and not isinstance(data, bytes):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return decode(r.read())
    except urllib.error.URLError as e:
        # Algunos servidores no envían la cadena de certificados completa; curl de Windows (Schannel) sí la resuelve
        if isinstance(getattr(e, "reason", None), ssl.SSLError):
            return _curl(url, h, data, timeout)
        raise


def decode(raw):
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def _curl(url, headers, data, timeout):
    cmd = ["curl.exe" if os.name == "nt" else "curl", "-s", "-S", "-f", "-L", "--compressed", "--max-time", str(timeout)]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["--data-binary", "@-"]
    r = subprocess.run(cmd + [url], input=data, capture_output=True, timeout=timeout + 10,
                       creationflags=0x08000000 if os.name == "nt" else 0)  # sin ventana de consola
    if r.returncode:
        raise RuntimeError(f"curl: {r.stderr.decode(errors='replace').strip()[:160]}")
    return decode(r.stdout)


def parse_rss(text):
    """Items de un RSS. Quita la declaración XML para no depender del encoding declarado."""
    return ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", text)).iter("item")


def fetch_json(url, **kw):
    return json.loads(fetch(url, **kw))


def strip_html(s):
    s = html.unescape(s or "")  # algunas APIs devuelven el HTML escapado
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "\n• ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v\xa0]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def iso(value):
    """Convierte fechas variadas (RFC822, ISO, epoch s/ms) a ISO UTC."""
    if value in (None, ""):
        return ""
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            v = float(value)
            if v > 1e12:
                v /= 1000
            return datetime.fromtimestamp(v, timezone.utc).isoformat(timespec="seconds")
        s = str(value).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            d = parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return ""


def job(source, ext_id, title, company="", location="", url="", description="",
        posted="", salary="", remote=None, spain=False):
    return {
        "source": source,
        "id": f"{source}:{ext_id}",
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "").strip(),
        "url": url or "",
        "description": (description or "").strip()[:20000],
        "posted": iso(posted),
        "salary": salary or "",
        "remote": None if remote is None else int(bool(remote)),
        "spain": int(spain),  # fuente española: si no se reconoce la ciudad, se asume España
    }
