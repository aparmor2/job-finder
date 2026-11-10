"""Fuentes de ofertas: una por módulo de esta carpeta.

Cada fuente es una función fn(cfg, log) -> list[dict] que devuelve ofertas creadas con base.job().
Para añadir una fuente nueva: escribe la función en un módulo nuevo y añádela a FUENTES.
Para desactivar una sin tocar código: pon su nombre en config.json -> busqueda -> fuentes_desactivadas.
"""
from .base import strip_html  # noqa: F401  (lo usa mail.py)
from .ats import src_empresas
from .con_clave import src_adzuna, src_infojobs, src_jooble
from .grandes import src_capgemini, src_successfactors, src_vigilar, src_workday
from .linkedin_correo import src_linkedin_correo
from .manfred import src_manfred
from .remotos import src_himalayas, src_jobicy, src_remoteok, src_remotive, src_workingnomads
from .tecnoempleo import src_tecnoempleo
from .ticjob import src_ticjob


def _correo(cfg):
    """Condición: Gmail conectado (configurar-correo.bat)."""
    from .. import mail  # importación tardía: mail importa sources
    return bool(mail.credenciales())


def _clave(*campos):
    """Condición: la fuente solo se activa si esas claves están rellenas en claves_api_gratis."""
    return lambda cfg: all(cfg.get("claves_api_gratis", {}).get(c) for c in campos)


# (nombre, función, condición para activarse o None = siempre). El orden es el de búsqueda.
FUENTES = [
    ("InfoJobs", src_infojobs, _clave("infojobs_client_id", "infojobs_client_secret")),
    ("Adzuna", src_adzuna, _clave("adzuna_app_id", "adzuna_app_key")),
    ("Jooble", src_jooble, _clave("jooble_key")),
    ("LinkedIn (alertas por correo)", src_linkedin_correo, _correo),
    ("Tecnoempleo", src_tecnoempleo, None),
    ("Ticjob", src_ticjob, None),
    ("Manfred", src_manfred, None),
    ("Empresas (Greenhouse/Lever/Ashby)", src_empresas, None),
    ("Empresas (Workday)", src_workday, None),
    ("Empresas (SuccessFactors)", src_successfactors, None),
    ("Capgemini", src_capgemini, None),
    ("Páginas vigiladas", src_vigilar, None),
    ("Remotive", src_remotive, None),
    ("RemoteOK", src_remoteok, None),
    ("Jobicy", src_jobicy, None),
    ("Himalayas", src_himalayas, None),
    ("WorkingNomads", src_workingnomads, None),
]


def sources(cfg):
    """Lista (nombre, función) de las fuentes activas según config.json."""
    off = {n.lower() for n in cfg["busqueda"].get("fuentes_desactivadas", [])}
    return [(n, fn) for n, fn, cond in FUENTES if n.lower() not in off and (cond is None or cond(cfg))]
