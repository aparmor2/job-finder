---
name: empezar
description: Configura Job Finder para un usuario nuevo a partir de su CV. Crea perfil/, config.json y la ficha de formularios con unas pocas preguntas. Úsalo cuando el usuario diga /empezar, "configúralo para mí" o cuando falten perfil/ o config.json.
---

# /empezar: configurar Job Finder en 10 minutos

Objetivo: que el usuario no tenga que editar ningún archivo a mano. Tú lees su CV, le haces **una sola tanda de preguntas** y escribes todo.

## 1. Comprobar el entorno
- `python --version` (hace falta Python 3). Si no está, dile que lo instale desde python.org marcando "Add Python to PATH" y para.
- `node --version` solo hace falta para `/aplicar` (Node 22 o superior). Si falta, avísalo, pero sigue.
- Si ya existen `perfil/` o `config.json`, pregunta si quiere rehacerlos o solo ajustarlos. **No los sobrescribas sin permiso.**

## 2. Leer el CV
Pídele la ruta de su CV (PDF o Word) o que lo pegue. Léelo entero. Copia el PDF a `perfil/cv.pdf` (lo usará `/aplicar` para adjuntarlo).

## 3. Una sola tanda de preguntas
Deduce del CV todo lo que puedas y pregunta solo lo que falte, todo junto (con AskUserQuestion si está disponible):
- Dónde vive (pueblo) y qué zonas le valen, en orden de preferencia: cerca de casa, su ciudad, remoto, otras ciudades.
- Qué puestos busca (3-5 roles) y cuáles no quiere ni ver.
- Nivel: junior, prácticas o con experiencia (años reales).
- ¿Remoto sí, no o indiferente? ¿Se mudaría?
- Expectativa salarial y disponibilidad.
- Idiomas y nivel.

## 4. Escribir los archivos
Crea `perfil/` a partir de `perfil_ejemplo/`:
- `cv.txt`: el CV en texto plano. **Línea 1 = nombre, línea 2 = titular** (salen en la cabecera del panel). No cambies cifras ni inventes nada.
- `carta_es.txt` y `carta_en.txt`: plantilla de carta con `{empresa}`, `{puesto}` y `{encaje}`, con su experiencia más fuerte y cifras reales del CV. Máximo 180 palabras.
- `followup.txt`: mensaje de seguimiento con `{empresa}` y `{puesto}`.
- `datos_formularios.md`: rellena la plantilla con lo que sepas del CV y de sus respuestas. Deja vacío lo que no sepas.

Crea `config.json` copiando `config.example.json` y ajusta:
- `perfil.ubicacion`: una zona por cada lugar que le valga. Cada zona es una clave en `puntos` con su lista de pueblos o ciudades al lado (en minúsculas, con y sin tilde). Pon `cerca` = su pueblo y alrededores (unos 30 puntos) y su ciudad (unos 26). Las ciudades a las que no iría, quítalas. Usa `etiquetas` para los nombres visibles. `extranjero` en negativo, salvo que quiera irse fuera.
- `perfil.rol_titulo`: palabras de sus roles objetivo con 20-32 puntos y las cercanas con menos.
- `perfil.habilidades_cv`: su stack real, sacado del CV.
- `perfil.tecnologias_ajenas` y `no_es_mi_rol`: lo que no encaja con él.
- `busqueda.terminos`, `ciudades`, `tecnoempleo_provincias` (nombres de provincia), `tecnoempleo_tecnologias` y `ticjob_palabras`, según sus roles y zonas.
- `busqueda.empresas` y `portales_empresa`: deja los de ejemplo si encajan con su sector. Si no, vacíalos y pregúntale qué empresas le interesan.

Valida que `config.json` es JSON correcto: `python -c "import json; json.load(open('config.json', encoding='utf-8'))"`.

## 5. Primera búsqueda
- Lanza `python -m jobfinder --solo-buscar` en segundo plano (tarda unos 5 minutos).
- Mientras tanto, ofrece los extras opcionales:
  - **Gmail**: que ejecute `configurar-correo.bat` él mismo. Necesita una contraseña de aplicación de Google; nunca la pidas por el chat.
  - **LinkedIn**: si usa LinkedIn, que su email principal allí sea el Gmail conectado y que tenga alertas de empleo diarias por email (ver `docs/portales.md` → LinkedIn). Ofrécete a crear 2-3 alertas con sus roles y ciudad.
  - **Aplicar con Claude**: que abra `abrir-brave.bat` (cambiando la ruta si usa otro navegador Chromium) e inicie sesión en sus portales.
- Al terminar, abre el panel con `iniciar.bat` (o `python -m jobfinder`) y lanza `/revisar` para enseñarle las primeras ofertas.

## 6. Cierre
Resume en pocas líneas qué has configurado, qué zonas y roles puntúan más y los tres comandos del día a día: `/revisar`, `/aplicar <id>` y `/entrevista <empresa>`.
