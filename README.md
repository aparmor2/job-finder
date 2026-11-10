# Job Finder

**Buscar trabajo es otro trabajo. Deja que lo haga Claude.**

Job Finder junta cada día las ofertas de más de 15 webs, les pone nota según *tu* CV y te enseña solo las que encajan. Con [Claude Code](https://claude.com/claude-code) además rellena las candidaturas por ti y te prepara las entrevistas. Tú solo dices "sí".

```
/empezar              → le pasas tu CV y lo configura todo (10 min)
/revisar              → las 5 ofertas de hoy que de verdad encajan, y por qué
/aplicar <oferta>     → rellena el formulario, adjunta CV y carta, y envía cuando confirmas
/entrevista <empresa> → de qué va el puesto, qué te preguntarán y simulacro
```

- **Panel visual** en el navegador: ofertas ordenadas por nota, filtros, ★/✕ y seguimiento de candidaturas.
- **Lee tu Gmail** y marca solas las entrevistas y los rechazos.
- **Gratis y privado**: sin IA de pago para puntuar. Todo se queda en tu PC.
- **Honesto**: Claude no inventa experiencia y nunca envía nada sin tu confirmación.

| Necesitas | Para |
|---|---|
| [Python 3](https://www.python.org/downloads/) | El buscador y el panel (gratis) |
| [Claude Code](https://claude.com/claude-code) (plan Pro o superior) | `/empezar`, `/revisar`, `/aplicar`, `/entrevista` |
| [Node.js](https://nodejs.org) 22+ y Brave, Chrome o Edge | Que Claude rellene formularios (`/aplicar`) |

### Empezar en 3 pasos
1. Descarga el proyecto (**Code → Download ZIP** o `git clone`) e instala Python.
2. Abre Claude Code en la carpeta y escribe **`/empezar`**.
3. Cada día: **`/revisar`**, y **`/aplicar`** a las que te gusten.

¿Sin Claude? También funciona: doble clic en `iniciar.bat` y configúralo a mano (ver [Personalizarlo](#personalizarlo)).

---

## Cómo funciona

```
 Webs de empleo ──┐
 (Tecnoempleo,    │   1. BUSCAR        2. PUNTUAR             3. REVISAR
  InfoJobs,       ├──> descarga  ──>  nota 0-100 según  ──>  panel web en
  empresas…)      │   y guarda en     config.json            http://127.0.0.1:8765
                  │   data/jobs.db    (zona, rol, stack…)    ★ me interesa / ✕ descartar
 Tu Gmail ────────┘                                           │
 (opcional)       4. SEGUIMIENTO  <───────────────────────────┘
                  las respuestas de las empresas cambian el estado:
                  Aplicada → Entrevista / Rechazada
```

1. **Buscar**: cada fuente (una web de empleo) descarga sus ofertas. Se guardan en una base de datos SQLite y las repetidas entre webs se agrupan. Ocurre al arrancar si han pasado más de 6 horas, cada 6 horas mientras esté abierto y cuando pulsas **Buscar ofertas ahora**.
2. **Puntuar**: cada oferta recibe puntos a favor o en contra según el `perfil` de `config.json`. Por ejemplo: +30 si está cerca de casa, +18 si pide junior, −35 si es senior o −40 si es de ventas. En cada oferta el panel explica *por qué* tiene esa nota.
3. **Revisar**: en el panel filtras por nota, zona y estado, y marcas ★ (me interesa) o ✕ (descartar). Desde cada oferta puedes copiar una carta generada con tu plantilla o un prompt para que ChatGPT o Claude te adapten el CV.
4. **Seguimiento**: cuando aplicas, marcas la oferta como *Aplicada*. Si conectas Gmail, el programa reconoce los acuses de recibo, las entrevistas y los rechazos, y cambia el estado solo. A los 7 días sin respuesta te propone un mensaje de seguimiento.

---

## Instalación manual (sin Claude)

1. Instala [Python 3](https://www.python.org/downloads/) (probado con 3.14). En Windows, marca *"Add Python to PATH"*.
2. Descarga el proyecto: botón **Code → Download ZIP** (y descomprímelo) o `git clone`.
3. Doble clic en **`iniciar.bat`**. En Mac o Linux, ejecuta `python3 -m jobfinder` desde la carpeta.
   La primera vez crea tu `config.json` a partir de `config.example.json` y abre el panel en el navegador.
4. Personalízalo (siguiente apartado) y pulsa **Buscar ofertas ahora**. La primera búsqueda tarda unos 5 minutos.

---

## Personalizarlo

Todo lo personal está en dos sitios: **`config.json`** (qué buscar y cómo puntuar) y **`perfil/`** (tus textos). No hace falta tocar el código.

### 1. Tus textos: `perfil/`
Copia la carpeta `perfil_ejemplo/` con el nombre `perfil/` y rellena:

| Archivo | Para qué |
|---|---|
| `cv.txt` | Tu CV en texto. La **1.ª línea** (nombre) y la **2.ª** (titular) salen en la cabecera del panel. |
| `carta_es.txt`, `carta_en.txt` | Plantillas de carta. `{empresa}`, `{puesto}` y `{encaje}` se rellenan solos. |
| `followup.txt` | Mensaje de seguimiento a los 7 días. Usa `{empresa}` y `{puesto}`. |
| `datos_formularios.md` | Tus datos para que Claude rellene formularios (`/aplicar`). Nunca contraseñas. |

Mientras no exista `perfil/`, el panel usa las plantillas de ejemplo.

### 2. Qué buscar: `config.json → busqueda`

| Clave | Qué es |
|---|---|
| `terminos`, `ciudades` | Palabras y ciudades para InfoJobs, Adzuna y Jooble (si tienes clave). |
| `tecnoempleo_provincias` | Provincias de Tecnoempleo por su nombre: `"Madrid"`, `"Sevilla"`, `"Valencia"`… Valen las 52. |
| `tecnoempleo_tecnologias`, `ticjob_palabras` | Palabras clave para esas webs. |
| `empresas` | Empresas con portal en Greenhouse, Lever o Ashby (el nombre corto que sale en su URL). |
| `portales_empresa` | Grandes empresas en Workday o SuccessFactors y páginas a `vigilar` (te avisa cuando aparecen enlaces nuevos). Hay instrucciones dentro del propio archivo. |
| `fuentes_desactivadas` | Fuentes que no quieres usar, por nombre: `["RemoteOK", "Capgemini"]`. |
| `linkedin_dias_correo` | Cuántos días atrás mira los correos de alertas de LinkedIn (4 por defecto). |

### 3. Cómo puntuar: `config.json → perfil`

| Clave | Qué es |
|---|---|
| `ubicacion.puntos` | Puntos por zona. Las zonas de ciudad son las que tienen su lista de lugares al lado (`"cerca": [...]`, `"valencia": [...]`). **Puedes crear, renombrar o borrar zonas**, por ejemplo `"madrid": 26` junto a `"madrid": ["madrid", "alcobendas", "getafe"]`. Las fijas son `remoto`, `espana`, `extranjero` y `desconocido`. |
| `ubicacion.etiquetas` | Nombre que se ve en el panel: `{"cerca": "Cerca de casa"}`. |
| `rol_titulo`, `tope_rol` | Puntos por palabras en el título de la oferta (QA, analista, .NET…). |
| `habilidades_cv` | Tu stack: cada coincidencia con la descripción suma puntos. |
| `junior`, `senior`, `anos_experiencia` | Premia lo junior y penaliza lo senior o los años de experiencia exigidos. |
| `tecnologias_ajenas`, `no_es_mi_rol`, `idiomas_requeridos` | Penalizaciones para lo que no te encaja. |

Si cambias la puntuación, pulsa **Buscar ofertas ahora** o reinicia para recalcular las notas.

### 4. Claves gratuitas (opcional)
En `config.json → claves_api_gratis` puedes añadir claves gratuitas de [InfoJobs](https://developer.infojobs.net), [Adzuna](https://developer.adzuna.com) (incluye Indeed) y [Jooble](https://jooble.org/api/about). Cada fuente se activa sola cuando su clave está rellena.

---

## Fuentes incluidas

| Fuente | Módulo | Necesita |
|---|---|---|
| LinkedIn (alertas por correo) | `sources/linkedin_correo.py` | Gmail conectado y alertas de LinkedIn enviadas a ese Gmail |
| Tecnoempleo, Ticjob, Manfred | `sources/tecnoempleo.py`, `ticjob.py`, `manfred.py` | Nada |
| Remotive, RemoteOK, Jobicy, Himalayas, WorkingNomads (remoto) | `sources/remotos.py` | Nada |
| Empresas en Greenhouse, Lever o Ashby | `sources/ats.py` | Lista en `busqueda.empresas` |
| Workday, SuccessFactors, Capgemini, páginas vigiladas | `sources/grandes.py` | Lista en `busqueda.portales_empresa` |
| InfoJobs, Adzuna, Jooble | `sources/con_clave.py` | Clave gratuita |

**LinkedIn sin riesgo para tu cuenta**: la búsqueda automática no entra en LinkedIn (lo prohíbe y bloquea cuentas). Lee las **alertas de empleo que LinkedIn te manda al correo**. Aparte, cuando tú se lo pides, Claude puede abrir en tu navegador una oferta concreta, tus mensajes o una Solicitud sencilla: eso es navegar con tu cuenta y LinkedIn no lo permite oficialmente, así que hazlo con pocas ofertas al día y bajo tu responsabilidad. Para que funcione: en LinkedIn, el email principal tiene que ser el Gmail conectado y las alertas tienen que ir por email (diarias). Detalles en `docs/portales.md`.

---

## Gmail (opcional)

El programa lee tu bandeja de entrada por IMAP, en solo lectura: no marca nada como leído. Asocia cada correo a tu candidatura por el nombre de la empresa y lo clasifica como acuse de recibo, entrevista o rechazo.

1. Activa la verificación en 2 pasos de Google y crea una **contraseña de aplicación** en myaccount.google.com → Seguridad → Contraseñas de aplicaciones.
2. Doble clic en `configurar-correo.bat` y escribe tu Gmail y esa contraseña de 16 letras. Se guarda solo en `data/correo.json`, en tu PC.
3. Reinicia `iniciar.bat`. A partir de ahí, el correo se revisa cada hora.

Para desconectarlo, borra `data/correo.json` y revoca la contraseña de aplicación en Google.

---

## Rutina diaria (15-20 min)

1. Abre el panel. El filtro por defecto muestra nota ≥ 50, tus zonas y solo las ofertas pendientes.
2. Revisa de arriba abajo: ★ lo que te interesa y ✕ lo que no.
3. En cada ★: **Copiar prompt para IA**, pégalo en ChatGPT o Claude (gratis) y te devuelve un perfil y una carta adaptados. Aplica en la web de la empresa y marca la oferta **Aplicada**.
4. Pestaña **Seguimiento**: a los 7 días sin respuesta, **Copiar mensaje** de seguimiento.

Consejo: la nota no lo es todo. Busca también por texto (`junior`, `sin experiencia`, `recién titulado`) entre las ofertas nuevas.

---

## Uso con Claude Code

Los comandos viven en `.claude/skills/` y Claude Code los carga solos al abrir la carpeta. `CLAUDE.md` contiene las reglas que sigue Claude.

| Comando | Qué hace |
|---|---|
| `/empezar` | Lee tu CV, te hace una tanda de preguntas y crea `perfil/`, `config.json` y tu ficha de datos para formularios. |
| `/revisar` | Lanza la búsqueda, lee las ofertas nuevas y te presenta las pocas que encajan, con su porqué y lo que te falta. |
| `/aplicar <id>` | Escribe una carta adaptada (también en PDF), abre el portal en tu navegador, rellena el formulario y adjunta tus archivos. **Te enseña un resumen y solo envía si dices que sí.** En el panel, el botón **Aplicar con Claude** copia el comando. |
| `/entrevista <empresa>` | Junta la oferta, los correos y tu CV: de qué va el puesto, preguntas probables, cómo cubrir tus huecos y un simulacro. |

Para `/aplicar`:
1. Ejecuta `abrir-brave.bat`: abre un navegador aparte (`data/sesion-brave`) que Claude puede controlar. Si usas Chrome o Edge, cambia la ruta en el `.bat`.
2. Inicia sesión tú mismo en tus portales de empleo; las sesiones se guardan en ese perfil.
3. Claude rellena los formularios con `tools/nav.js` siguiendo `docs/portales.md` (trucos de SuccessFactors, Workday, Greenhouse…). Los datos salen de `perfil/datos_formularios.md`: lo que no sepa te lo pregunta una sola vez y lo apunta.

**Límites, para que nadie se lleve sorpresas**: es semiautomático. Los inicios de sesión y los captchas los haces tú, cada envío necesita tu "sí" y algunos portales cambian y hay que reintentar. Mandar candidaturas en masa sin revisarlas quema tu perfil con los reclutadores; Job Finder está pensado para aplicar a pocas ofertas y bien.

---

## Estructura

```
iniciar.bat               arranca el panel (python -m jobfinder)
configurar-correo.bat     conecta Gmail
abrir-brave.bat           navegador que Claude puede controlar (para /aplicar)
config.example.json       configuración de ejemplo → se copia a config.json
perfil_ejemplo/           plantillas de CV, cartas, seguimiento y datos de formulario → perfil/
CLAUDE.md                 reglas para Claude Code
.claude/skills/           los comandos /empezar, /revisar, /aplicar y /entrevista
docs/portales.md          cómo rellenar cada portal (SuccessFactors, Workday…)
jobfinder/
  server.py               servidor web local y API del panel
  refresh.py              ejecuta las búsquedas y recalcula notas
  scoring.py              reglas de puntuación y zonas
  mail.py                 lectura de Gmail y clasificación de respuestas
  ofertas.py              consultar y actualizar ofertas desde la terminal
  db.py                   base de datos SQLite (data/jobs.db)
  sources/                una fuente de ofertas por módulo; registro en __init__.py
web/index.html            el panel
tools/nav.js, wd.js       control del navegador por CDP
tools/carta_pdf.py        convierte una carta .txt a PDF
```

**Añadir una fuente**: crea un módulo en `jobfinder/sources/` con una función `fn(cfg, log)` que devuelva una lista de `job(...)` (de `sources/base.py`) y añádela a `FUENTES` en `sources/__init__.py`.

---

## Privacidad

`config.json`, `perfil/`, `candidaturas/` y `data/` (base de datos, contraseña del correo y sesiones del navegador) están en `.gitignore` y no se suben nunca a git.

## Búsqueda programada sin abrir el panel (opcional)

`buscar.bat` busca ofertas (y revisa el correo) sin abrir el panel. Para que se ejecute cada mañana, en una terminal:
```
schtasks /create /tn "JobFinder" /sc daily /st 08:00 /tr "\"C:\ruta\a\job-finder\buscar.bat\"" /f
```
Cambia la ruta por la de tu carpeta.
