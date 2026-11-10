# Guía de portales de empleo para Claude

Lo aprendido rellenando candidaturas de verdad con `tools/nav.js` sobre el navegador de `abrir-brave.bat`. Léela antes de aplicar en un portal. Si descubres algo nuevo, añádelo aquí.

## General
- **Inicios de sesión**: los hace siempre el usuario en el navegador. Los clics y teclas por CDP **no** activan el autorrelleno de contraseñas del navegador, así que pide al usuario que elija él su contraseña guardada. Nunca leas ni descifres el almacén de contraseñas.
- **Sesiones que caducan**: algunos portales guardan la sesión en cookies que mueren al cerrar el navegador. Deja el navegador abierto y agrupa varias candidaturas en una misma sesión: al usuario le molesta repetir inicios de sesión.
- **Antes de aplicar**, comprueba que la oferta sigue viva (abre la URL; las que llevan días sin verse en `last_seen` suelen dar 404).
- **Clics que no responden**: muchos botones son componentes JavaScript. Prueba `realclick` (clic de ratón real). Si la página aún se está desplazando, haz `scrollIntoView`, espera un segundo y repite.
- **Formularios React**: si `fill` escribe pero el valor desaparece o no se valida, usa `tools/wd.js type` (clic real + `Input.insertText`).
- **Página colgada en "¿Seguro que quieres salir?"** (`beforeunload`): no intentes navegar. Cierra la pestaña con `http://127.0.0.1:9223/json/close/<id>` y abre otra.
- **Enviar**: antes del último clic, enseña al usuario un resumen (puesto, empresa, datos clave, archivos adjuntos, respuestas abiertas) y espera su confirmación.

## SAP SuccessFactors (Deloitte, Indra/Minsait, EY, Atos, Capgemini y muchas grandes)
- Cuenta por empresa (dominio `careerN.successfactors.eu` o `careerN.sapsf.eu`). La sesión vive solo en cookies de sesión: cerrar el navegador = volver a entrar.
- El botón de aplicar suele necesitar `realclick`. Algunos tienen un desplegable previo (p. ej. `button.dropdown-toggle` y después la opción "aplicar manualmente").
- **La sesión caduca tras unos 25 minutos inactiva** en el formulario: las respuestas de texto se pierden al volver a entrar, pero los archivos subidos quedan en el perfil. Rellena de una tirada.
- Reutiliza la última carta adjunta: **cámbiala en cada oferta**, o mandarás la carta de otra empresa.
- El id del botón de enviar varía (`..._submitBtn`). Búscalo con `fields`.

## Workday (Accenture, BBVA, dentsu…)
- Cuenta por empresa (`<empresa>.wdN.myworkdayjobs.com`). Suele permitir entrar con Google.
- Inputs React: usa `tools/wd.js type <css> <texto>`; `nav.js fill` no se guarda.
- Desplegables: clic en el botón y después clic en la opción `[role=option]` o `[data-automation-id=promptOption]` por texto.
- Archivos: input `[data-automation-id=file-upload-input-ref]`. Admite CV y carta con dos `upload` seguidos.
- Si entra con una cuenta de Google distinta de la del CV, el correo de contacto será el de esa cuenta. Avisa al usuario.

## Greenhouse, Lever, Ashby (startups y empresas tech)
- Formularios de una sola página, normalmente sin cuenta. `fill` y `upload` funcionan bien.
- Preguntas abiertas frecuentes ("¿por qué nosotros?"): redáctalas a partir del CV y la oferta y enséñaselas al usuario antes de enviar.

## Teamtailor (`empleo.<empresa>.com`, `talento.<empresa>.com`)
- Botón "Enviar solicitud" con `realclick` (el `click` normal no abre el formulario). Rechaza antes las cookies.
- Formulario HTML normal, sin cuenta: `fill`, radios con `.click()` y `upload '#candidate_resume_remote_url' <cv.pdf>` funcionan. La carta va en un textarea.
- Algunas empresas piden marcar `candidate[consent_given]`; otras lo dan por aceptado al enviar. El envío correcto lleva a `/applications/<id>/thanks/...`.

## Manatal (`<empresa>.careers-page.com`)
- El formulario vive dentro de un **shadowRoot**: `fields` y `fill` no lo ven. Busca los elementos con `host.shadowRoot.querySelector`, enfoca y escribe con `Input.insertText`.
- Desplegables Radix (`button[role=combobox]`): clic real en el botón y luego clic real en `[role=option]`, que aparece fuera del shadowRoot, en `document`. Los ids cambian tras cada cambio.
- CV: `DOM.setFileInputFiles` sobre el `input[type=file]` del shadowRoot. La casilla de términos es un `button[role=checkbox]`.

## Tecnoempleo
- Inicio de sesión persistente. Aplicar = botón "Inscribirme" en la oferta, a veces con preguntas de filtro.
- La ubicación "Remoto" no siempre es remoto: lee la ubicación real en la descripción.

## Michael Page / Page Personnel
- Crea cuenta automáticamente al aplicar. No tiene campo de carta.

## LinkedIn
- **Sin scraping masivo ni búsquedas automáticas**: LinkedIn lo prohíbe y restringe cuentas. Las ofertas entran solas por la fuente "LinkedIn (alertas por correo)", que lee los correos de alerta del Gmail del usuario.
- **Configuración para que lleguen las alertas** (`/empezar` la revisa):
  - Ajustes → Direcciones de email: el **email principal** debe ser el Gmail conectado a Job Finder. Si no, las alertas y las respuestas de las empresas van a otra bandeja. Cambiarlo pide la contraseña: que la escriba el usuario.
  - Ajustes → Notificaciones → En busca de empleo: "Alertas de empleo" con Email activado, y conviene activar también "Actualizaciones de solicitudes de empleo" (avisos de CV visto o descargado).
  - Alertas: `https://www.linkedin.com/jobs/jam/` las lista. Para crear una, busca en `https://www.linkedin.com/jobs/search-results/?keywords=<texto con la ciudad, p. ej. "analista funcional junior en Valencia">` y activa el interruptor "Recibir alertas de empleo para esta búsqueda" (`[componentkey^=JobSearchAlertToggleRef] input[role=switch]`). Por defecto salen diarias por email.
- **Leer una oferta**: `https://www.linkedin.com/jobs/view/<id>/` y `text`. El botón dice "Solicitud sencilla" (se aplica dentro de LinkedIn) o "Solicitar" (lleva a la web de la empresa). En la lista de resultados, cada tarjeta es `[componentkey=job-card-component-ref-<id>]`.
- **Solicitud sencilla**: formulario de varios pasos dentro de LinkedIn (contacto, CV, preguntas). El correo de contacto que propone es el principal de la cuenta: comprueba que es el bueno. Pocas al día y siempre con el "sí" del usuario.
- **Seguimiento**: el botón "Enviar mensaje" de la página de empresa (tema Empleos) no requiere conexión. En el plan gratuito la búsqueda de personas oculta los nombres. Las respuestas solo se ven en `https://www.linkedin.com/messaging/` (no siempre avisa por correo).

## Portales que bloquean bots
- Si una web devuelve 403 o un captcha (p. ej. Mercadona), no intentes saltártelo: dile al usuario que cree una alerta en el propio portal.
