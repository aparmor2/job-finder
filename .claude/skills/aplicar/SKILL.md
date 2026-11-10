---
name: aplicar
description: Aplica a una oferta de Job Finder rellenando el formulario del portal en el navegador del usuario (CDP), con carta adaptada y confirmación antes de enviar. Úsalo cuando el usuario diga /aplicar <id o empresa>, "aplica a esta" o "envía la candidatura".
---

# /aplicar: rellenar y enviar una candidatura

Oferta: $ARGUMENTS (un id de Job Finder, p. ej. `tecnoempleo:abc123`, o un nombre de empresa o puesto).

## Reglas que no se rompen
- **Nunca envíes sin un "sí" explícito** del usuario tras ver el resumen final.
- **No inventes nada**: experiencia, años, certificados ni habilidades. Si un campo obligatorio pide algo que no tiene, díselo y que decida.
- **Los inicios de sesión los hace el usuario.** Nunca pidas ni escribas contraseñas.
- Los datos salen de `perfil/datos_formularios.md`. Si falta algo, pregunta **todo lo que falte de una vez** y guárdalo en ese archivo al momento, para no volver a preguntarlo.

## 1. La oferta
- Si te dan un id: `python -m jobfinder.ofertas ver <id>`. Si es un nombre: `python -m jobfinder.ofertas buscar <texto>` y confirma cuál.
- Lee la descripción y compárala con `perfil/cv.txt`. Si no encaja (seniority, requisitos imprescindibles), dilo antes de seguir.

## 2. Carta (si el portal la admite o la pide)
- Escríbela en `candidaturas/carta_<empresa>_<puesto>.txt` partiendo de `perfil/carta_es.txt` o `carta_en.txt` (según el idioma de la oferta). Adáptala a la oferta: máximo 180 palabras, con cifras reales del CV y sin frases vacías.
- PDF: `python tools/carta_pdf.py candidaturas/carta_<...>.txt`.
- Enséñale la carta al usuario mientras preparas el navegador.

## 3. Navegador
- Comprueba que está abierto: `curl -s http://127.0.0.1:9223/json/version`. Si no, pide al usuario que ejecute `abrir-brave.bat`.
- Lee `docs/portales.md` y busca la sección del portal (SuccessFactors, Workday, Greenhouse…).
- `node tools/nav.js goto <url>` y luego `node tools/nav.js text` para ver la página. Si la oferta ya no existe, márcala `descartada` con la nota "caducada" y para.
- Si hay que iniciar sesión, dile al usuario en qué web y espera a que te avise.

## 4. Rellenar
- `node tools/nav.js fields` lista los campos. Rellena con `fill`, `click` y `realclick`, o con `tools/wd.js` en Workday.
- Adjunta el CV (ruta en `datos_formularios.md`, por defecto `perfil/cv.pdf`) y la carta en PDF con `upload`.
- Preguntas abiertas: redáctalas con el CV y la oferta, cortas y concretas.
- Preguntas de sí/no o de años de experiencia: la verdad, según `datos_formularios.md`.
- Revisa cada paso con `text` o `fields` antes de pasar al siguiente.

## 5. Confirmar y enviar
Enseña un resumen: puesto, empresa, archivos adjuntos, respuestas a preguntas abiertas y cualquier dato dudoso. **Espera el "sí".** Envía y comprueba la página de confirmación con `text`.

## 6. Registrar
- `python -m jobfinder.ofertas estado <id> aplicada "<portal y referencia, si la hay>"`.
- Añade una línea a `candidaturas/AAAA-MM-DD.md`: "✅ ENVIADA <fecha> (<portal>)".
- Si has aprendido algo nuevo del portal, añádelo a `docs/portales.md`.
