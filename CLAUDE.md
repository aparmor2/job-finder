# Job Finder: instrucciones para Claude Code

Buscador de empleo local: Python con solo la librería estándar, SQLite y un panel en HTML puro (`web/index.html`) servido en http://127.0.0.1:8765. El README explica el uso; aquí está lo que necesitas para ayudar al usuario.

## Reglas
- **Coste cero**: no añadas dependencias, servicios de pago ni APIs con coste. Python solo con la librería estándar.
- **No inventes nada en CVs ni cartas**: usa solo lo que pone `perfil/cv.txt`. En las entrevistas preguntan por cada cifra.
- **No envíes nada sin confirmación**: candidaturas, correos o mensajes. Prepara el borrador, enséñaselo al usuario y espera a que diga que sí.
- **Nada de LinkedIn scraping** ni de saltarse bloqueos anti-bot (403, captchas). Las ofertas de LinkedIn entran por sus correos de alerta. En el navegador del usuario solo abre páginas concretas de LinkedIn (una oferta, sus mensajes, una Solicitud sencilla) cuando lo pide, pocas al día. Si una web bloquea, díselo y sugiere crear una alerta en su portal.
- **No toques sus datos personales**: `config.json`, `perfil/`, `candidaturas/` y `data/` son del usuario y no van al repo. Para cambios de ejemplo, edita `config.example.json` y `perfil_ejemplo/`.
- Datos para formularios: `perfil/datos_formularios.md`. Pregunta lo que falte una sola vez, todo junto, y guárdalo ahí.
- Nunca pidas ni leas contraseñas por el chat. El correo se configura con `configurar-correo.bat`.

## Comandos de usuario (skills en .claude/skills/)
`/empezar` (configurar desde su CV), `/revisar` (ofertas del día), `/aplicar <id>` (rellenar y enviar con confirmación) y `/entrevista <empresa>`. Cuando el usuario pida algo de eso con otras palabras, sigue la skill correspondiente.

## Comandos
- Ofertas desde la terminal: `python -m jobfinder.ofertas nuevas|buscar <texto>|ver <id>|estado <id> <estado> [nota]|seguimiento`.
- Carta en PDF: `python tools/carta_pdf.py candidaturas/carta_x.txt`.
- Panel: `python -m jobfinder`, o `python -m jobfinder --no-browser` para no abrir el navegador.
- Solo buscar: `python -m jobfinder --solo-buscar`. Tarda más de 4 minutos (Workday unas 3), así que dale al menos 6 minutos de tiempo límite. La puntuación se calcula al final.
- Recalcular notas tras cambiar `config.json`: `python -c "from jobfinder import refresh, server; print(refresh.rescore(server.load_config()))"`.
- Revisar el correo: `python -m jobfinder.mail`.
- Base de datos: `data/jobs.db`, tabla `jobs`. Columnas útiles: `title, company, location, url, description, score, bucket, reasons, status, notes, first_seen, last_seen`. Estados posibles: `nueva, interesa, aplicada, entrevista, oferta, rechazada, descartada`.

## Revisión diaria de ofertas
1. Las ofertas nuevas (`status='nueva'`, `first_seen` reciente) ordenadas por `score`.
2. **La nota no basta.** Busca también por texto (`junior`, `recien titulado`, `sin experiencia`, `graduate`, `trainee`) y descarta lo senior o lo que no sea técnico. Una oferta buena puede tener nota baja por un título raro (`-10 rol no reconocido`).
3. Lee la ubicación en la descripción antes de decir que una oferta es remota: algunas webs marcan como "Remoto" puestos híbridos.
4. Presenta pocas ofertas y bien explicadas: por qué encaja cada una y qué le falta al usuario.

## Rellenar candidaturas en el navegador
Antes de aplicar en un portal, lee `docs/portales.md`.
- El usuario abre `abrir-brave.bat`: perfil propio en `data/sesion-brave`, depuración remota en el puerto 9223. Él inicia sesión en los portales.
- Contrólalo con `node tools/nav.js <acción>`. Acciones: `goto <url>`, `text`, `fields`, `click <selector|texto>`, `realclick <selector>`, `fill <selector> <texto>`, `upload <selector> <ruta>`, `key <tecla>`, `eval <js>`, `shot`. `TAB=<trozo de url>` elige la pestaña y `SHOT=-` evita la captura.
- En formularios hechos con React (Workday), `fill` no se queda guardado. Usa `node tools/wd.js type <css> <texto>` y `click <css>`.
- Usa CDP directo: **no conectes Playwright** a ese navegador, porque cambia el tema de todas las pestañas.
- Si un clic no hace efecto mientras la página se desplaza, haz `scrollIntoView`, espera y repite con `realclick`.
- Antes de pulsar "Enviar", enséñale al usuario lo que vas a mandar y espera su confirmación.

## Código
- `jobfinder/sources/`: una fuente por módulo. Cada fuente es `fn(cfg, log) -> list[job(...)]`. Se registra en `FUENTES` de `sources/__init__.py` y se desactiva con `busqueda.fuentes_desactivadas`.
- `jobfinder/scoring.py`: reglas de nota. Las zonas de ciudad salen de `perfil.ubicacion` (cada clave de `puntos` con su lista de lugares). Las zonas fijas son remoto, espana, extranjero y desconocido.
- `jobfinder/mail.py`: Gmail por IMAP, clasificación con expresiones regulares (RECHAZO, ACUSE, ENTREVISTA).
- `web/index.html`: el panel. Lee `/api/jobs`, `/api/zonas`, `/api/perfil`, `/api/mail` y `/api/status`.
