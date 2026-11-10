"""Convierte una carta en texto (.txt) a PDF con el navegador en modo sin ventana (Edge, Chrome o Brave).

Uso: python tools/carta_pdf.py candidaturas/carta_empresa.txt   → crea candidaturas/carta_empresa.pdf
"""
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NAVEGADORES = [
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def navegador():
    for p in NAVEGADORES:
        p = os.path.expandvars(p)
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        if shutil.which(n):
            return shutil.which(n)
    sys.exit("No encuentro Edge, Chrome ni Brave para generar el PDF.")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    txt = Path(sys.argv[1]).resolve()
    pdf = txt.with_suffix(".pdf")
    parrafos = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>"
                       for p in txt.read_text(encoding="utf-8").strip().split("\n\n"))
    pagina = ("<!doctype html><meta charset='utf-8'><style>@page{margin:2.2cm}"
              "body{font:11pt/1.5 Calibri,Arial,sans-serif;color:#111}p{margin:0 0 .9em}</style>" + parrafos)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp, "carta.html")
        page.write_text(pagina, encoding="utf-8")
        subprocess.run([navegador(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={Path(tmp, 'perfil')}", f"--print-to-pdf={pdf}", page.as_uri()],
                       capture_output=True, timeout=60)
    if not pdf.exists():
        sys.exit("No se pudo generar el PDF.")
    print(pdf)


if __name__ == "__main__":
    main()
