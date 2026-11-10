---
name: revisar
description: Revisión diaria de ofertas de Job Finder. Busca, filtra y presenta las pocas que encajan de verdad, con su porqué. Úsalo cuando el usuario diga /revisar, "qué ofertas hay hoy" o "revisa las nuevas".
---

# /revisar: las ofertas de hoy que merecen la pena

Argumentos opcionales: $ARGUMENTS (p. ej. "3 días" para mirar más atrás).

## 1. Datos frescos
- Lee `perfil/cv.txt` y `perfil/datos_formularios.md` para saber qué busca el usuario y qué no sabe hacer.
- Si la última búsqueda tiene más de 6 horas (`python -c "from jobfinder import db; print(db.meta_get('last_refresh'))"`), lanza `python -m jobfinder --solo-buscar` con al menos 6 minutos de tiempo límite. Si no, usa lo que hay.
- La búsqueda ya revisa el correo. Si no has lanzado búsqueda y hay Gmail configurado, revisa el correo aparte: `python -m jobfinder.mail`.

## 2. Candidatas
`python -m jobfinder.ofertas nuevas --dias 1` (o los días que pida). Saca dos listas:
- **Por nota**: ordenadas de mayor a menor.
- **Por texto**: títulos junior con nota baja. La nota no lo es todo: un título raro resta 10 puntos aunque el puesto encaje.

Para cada candidata prometedora, `python -m jobfinder.ofertas ver <id>` y lee la descripción entera. Descarta con criterio:
- Seniority real (años exigidos, "lidera", "experto").
- Requisitos imprescindibles que el usuario no tiene. Lo que solo "se valora" sí cuenta como opción.
- Ubicación real: lee la descripción; "Remoto" a veces es híbrido en otra ciudad.
- Idiomas que no habla, sector que no le interesa, oferta caducada (`last_seen` antiguo).

## 3. Presentar
Muestra **como mucho 5-8 ofertas**, de mejor a peor. De cada una:
- Puesto, empresa, ubicación real y enlace.
- **Por qué encaja**, en una o dos líneas y con hechos de su CV.
- **Ojo**: lo que le falta o lo que puede ser un problema.
- Comando para aplicar: `/aplicar <id>`.

Después, una lista corta de "no aplicar" con el motivo en media línea, para que vea que se han mirado.

Guarda el resumen en `candidaturas/AAAA-MM-DD.md` (crea la carpeta si no existe) y marca las recomendadas: `python -m jobfinder.ofertas estado <id> interesa`.

## 4. Seguimiento
- **Ofertas de LinkedIn**: entran solas por las alertas de correo (fuente `linkedin`, sin descripción). Para las que pasen el primer filtro, abre `https://www.linkedin.com/jobs/view/<id>/` en el navegador y lee la descripción antes de recomendarlas. Si hoy no ha llegado ningún correo de alerta, revisa la configuración (`docs/portales.md` → LinkedIn).
- **Mensajes de LinkedIn**: LinkedIn no siempre avisa por correo, así que las respuestas a los mensajes de seguimiento solo se ven dentro. Si el navegador de `abrir-brave.bat` está abierto (`curl -s http://127.0.0.1:9223/json/version`), abre `https://www.linkedin.com/messaging/?filter=unread` con `node tools/nav.js goto` y lee los no leídos con `text`. Mira también `https://www.linkedin.com/notifications/` por si hay vistas de perfil de reclutadores o alertas que encajen. Si no hay sesión iniciada, díselo al usuario y sigue.
- `python -m jobfinder.ofertas seguimiento`. Si hay candidaturas con 7 días o más sin respuesta, ofrécete a preparar los mensajes de seguimiento con `perfil/followup.txt`. Si hay correos de entrevista, sugiere `/entrevista <empresa>`.
