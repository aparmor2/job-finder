---
name: entrevista
description: Prepara una entrevista de trabajo con la oferta, los correos y el CV del usuario, y ofrece un simulacro. Úsalo cuando el usuario diga /entrevista <empresa>, "tengo una entrevista" o "cómo será la entrevista".
---

# /entrevista: preparar una entrevista

Empresa u oferta: $ARGUMENTS

## 1. Reunir contexto
- `python -m jobfinder.ofertas buscar <empresa>` y luego `ver <id>`: descripción, notas y correos asociados.
- Si la descripción está vacía, abre la URL (con `node tools/nav.js` si hace falta sesión) y léela.
- El correo de la convocatoria: tipo de entrevista, fecha, hora, quién la hace (RRHH o técnico) y formato (presencial, videollamada o teléfono).
- `perfil/cv.txt` y `perfil/datos_formularios.md` (expectativa salarial, disponibilidad, respuestas honestas).
- Busca la empresa en la web: a qué se dedica, tamaño y noticias. Si no encuentras nada, dilo y no lo inventes.
- Pasa la oferta a `entrevista` si aún no lo está: `python -m jobfinder.ofertas estado <id> entrevista "<fecha y hora>"`.
- Comprueba que no choca con otra entrevista (busca en los correos recientes con `python -m jobfinder.ofertas seguimiento`).

## 2. Preparación (corta y útil)
1. **De qué va el puesto**, en sencillo: qué haría un día normal y qué tipo de empresa parece.
2. **Qué le van a preguntar** según quién entrevista: presentación de 2 minutos, por qué este puesto, sus proyectos, prueba de idioma si lo piden, salario y disponibilidad. Para cada pregunta, una pista de respuesta con **hechos reales de su CV**.
3. **Tabla "piden / tienes"**: requisitos de la oferta frente a su experiencia.
4. **Huecos**: lo que no sabe y cómo decirlo con honestidad, explicando cómo aprende. Si hay tiempo, propón algo concreto para probarlo antes (una hora con la herramienta).
5. **Preguntas para hacerles**: 3-5 que de verdad le ayuden a decidir (equipo, día a día, primeras tareas, teletrabajo, siguientes fases).
6. **Sueldo**: el rango de `datos_formularios.md`. Si no hay ninguno, da una referencia orientativa y avisa de que lo es.

Tono: tranquilizador y práctico. Si le invitan a una entrevista es porque su CV ya ha gustado.

## 3. Simulacro
Ofrece hacer de entrevistador: una pregunta cada vez y, tras cada respuesta, una mejora breve. Al final, las 3 cosas que debe pulir.
