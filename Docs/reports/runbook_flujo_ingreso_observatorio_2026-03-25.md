# Runbook operativo - Flujo de ingreso Observatorio CCHEN

Fecha: 2026-03-25
Responsable de implementación: Operación Observatorio

## 1. Estado actual (implementado)

- Correo de recordatorio semanal activo en GitHub Actions.
- Envío real por Brevo validado localmente y en Actions.
- Plantilla migrada a React Email para mayor mantenibilidad.
- Formulario Google creado por API y publicado.
- Enlace público del formulario cargado en secret de GitHub.

## 2. Componentes y archivos clave

- Workflow de envío semanal:
  - `.github/workflows/intake_flow_reminder.yml`
- Script de envío por Brevo:
  - `Scripts/send_intake_flow_email.py`
- Script de creación del formulario por API:
  - `Scripts/create_intake_google_form.py`
- Plantilla React Email:
  - `emails/intake-flow-reminder.tsx`
- Render de plantilla a HTML:
  - `emails/render.ts`
- Configuración Node/TypeScript para templates:
  - `emails/package.json`
  - `emails/tsconfig.json`

## 3. Secrets requeridos en GitHub

- `BREVO_API_KEY`
- `BREVO_FROM_EMAIL`
- `INTAKE_FLOW_FORM_URL`

## 4. Flujo semanal real

1. GitHub Actions ejecuta `intake_flow_reminder.yml` cada jueves.
2. Se compila plantilla React Email a HTML.
3. Script Python toma HTML compilado y envía por Brevo.
4. Correo llega con:
   - formulario de 10 preguntas en el cuerpo,
   - boton/enlace al Google Form real desde `INTAKE_FLOW_FORM_URL`.

## 5. Prueba manual (on-demand)

Para enviar una prueba real inmediata:

```bash
gh workflow run intake_flow_reminder.yml --repo Bastian963/cchen-observatorio -f send_real_email=true
```

Para revisar estado:

```bash
gh run list --repo Bastian963/cchen-observatorio --workflow intake_flow_reminder.yml --limit 1
gh run view <RUN_ID> --repo Bastian963/cchen-observatorio | cat
```

## 6. Evidencia de validación reciente

- Run exitoso: `23541304621`
- Resultado envío: `Brevo envio HTTP 201`
- Message ID: `<202603251236.47089947329@smtp-relay.mailin.fr>`

## 7. Errores encontrados y como evitarlos

### 7.1 Error 400 `redirect_uri_mismatch`

Causa:
- Se usó credencial OAuth tipo `web` en lugar de `installed`.

Prevención:
- Crear cliente OAuth en Google Cloud como "App para computadoras".
- Verificar que `credentials.json` tenga llave `installed`.

### 7.2 Error 403 `access_denied` (app no verificada)

Causa:
- App en modo Testing sin usuario agregado en "Usuarios de prueba".

Prevención:
- En Google Auth Platform -> Publico -> Usuarios de prueba:
  - agregar correo operador (ej: `b.ayalainostroza@gmail.com`).

### 7.3 `ModuleNotFoundError: No module named 'google.auth'`

Causa:
- Script ejecutado con Python distinto al entorno donde se instalaron dependencias.

Prevención:
- Ejecutar siempre con Python del workspace:

```bash
/Users/bastianayalainostroza/Dropbox/CCHEN/.venv/bin/python Scripts/create_intake_google_form.py
```

### 7.4 Falla en Actions al compilar template

Error observado:
- `No such file or directory` al generar `../dist/emails/intake-flow-reminder.html`.

Causa:
- Carpeta creada en ruta equivocada (`dist/emails` en vez de `../dist/emails`).

Prevención:
- Mantener coherencia con `working-directory: emails`:
  - crear `../dist/emails`
  - escribir salida en `../dist/emails/...`

### 7.5 Correo llegaba sin formulario visible

Causa:
- Plantilla inicial solo describía el flujo, no mostraba bloque de preguntas.

Corrección aplicada:
- Template ahora incluye 10 preguntas en cuerpo.
- Boton/link se muestra cuando existe `INTAKE_FLOW_FORM_URL`.

### 7.6 Formulario publicado pero cerrado para respuestas

Causa:
- En `setPublishSettings`, se envió solo `isPublished=true`.
- Desde cambios recientes de Forms API, al actualizar `publishState` deben enviarse ambos campos.

Corrección aplicada:
- Publicar con:
  - `isPublished=true`
  - `isAcceptingResponses=true`
  - `updateMask=publishState`

Señal de validación:
- `publishSettings.publishState.isAcceptingResponses` debe quedar en `true`.

## 8. Uso de React Email (guia corta)

### Render local de plantilla

```bash
cd emails
npm install
npx tsx render.ts > ../dist/emails/intake-flow-reminder.html
```

### Envio local usando HTML compilado

```bash
cd /Users/bastianayalainostroza/Dropbox/CCHEN
python Scripts/send_intake_flow_email.py --send-brevo --confirm-send --html-file dist/emails/intake-flow-reminder.html
```

### Crear nuevas plantillas para otros modulos

1. Crear archivo `emails/<nombre-template>.tsx`.
2. Crear renderer `emails/<nombre-render>.ts`.
3. Agregar paso en workflow para compilar a `dist/emails/<archivo>.html`.
4. Reusar `Scripts/send_intake_flow_email.py --html-file ...`.

## 9. Seguridad y control

- `credentials.json` y `token_forms.json` estan en `.gitignore`.
- No subir nunca secretos a git ni a documentación.
- Revisar periódicamente expiración/rotación de llaves Brevo.

## 10. Backlog recomendado

- Migrar entorno Python operativo a 3.11+ para eliminar warnings de EOL.
- Crear script de ingesta de respuestas Google Forms -> dataset interno.
- Integrar respuestas a pipeline dashboard/Supabase.
- Añadir test CI que valide presencia de `INTAKE_FLOW_FORM_URL` en workflow de recordatorio.
