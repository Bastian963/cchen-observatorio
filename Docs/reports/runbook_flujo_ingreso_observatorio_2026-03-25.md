
## 14. Descarga robusta de recursos Zenodo por afiliación institucional

**Motivación:**
No todos los recursos de la Comisión Chilena de Energía Nuclear (CCHEN) están agrupados en una comunidad Zenodo, pero sí suelen estar correctamente afiliados en los metadatos de autoría.

**Estrategia:**
- Se automatiza la búsqueda y descarga de todos los recursos donde la afiliación de algún autor contenga “Comisión Chilena de Energía Nuclear” o “CCHEN”.
- Esto permite capturar datasets, papers, patentes, software, imágenes, etc., aunque estén dispersos en Zenodo.

**Implementación:**
1. Se utiliza la API de Zenodo para buscar registros con afiliaciones relevantes.
2. Se descargan los archivos y metadatos de cada resultado, organizando por título y ID.
3. Se eliminan duplicados por ID para evitar descargas repetidas.
4. El script es extensible: se pueden agregar más variantes de afiliación si es necesario.

**Archivo de script:**
- `Scripts/download_zenodo_by_affiliation.py`

**Palabras clave usadas:**
- "comision chilena de energia nuclear"
- "cchen"

**Ventajas:**
- No depende de comunidades ni slugs.
- Captura recursos institucionales aunque estén dispersos.
- Permite auditar y mantener actualizado el repositorio local de outputs CCHEN.

**Recomendación:**

## 15. Evaluación de DSpace como alternativa/complemento a Zenodo

**Motivación:**
DSpace es una plataforma open source ampliamente utilizada para repositorios institucionales, especialmente en universidades y centros de investigación.

**Plan de estudio:**
- Analizar si DSpace podría servir como alternativa o complemento a Zenodo para la gestión, preservación y difusión de outputs institucionales de CCHEN.
- Comparar funcionalidades clave: autoarchivo, metadatos, interoperabilidad (OAI-PMH), integración con ORCID, DOI, control de acceso, personalización, costos y soporte.
- Revisar casos de uso en instituciones similares (repositorios de universidades chilenas, centros de investigación nuclear, etc.).
- Evaluar facilidad de instalación, mantenimiento y escalabilidad.
- Considerar integración con flujos actuales (automatización, dashboard, scripts de ingesta, etc.).

**Acción:**
- Incluir un informe comparativo y una recomendación en el próximo ciclo de revisión del plan de datos del Observatorio.

**Resultado esperado:**
- Decisión informada sobre si DSpace aporta valor agregado respecto a Zenodo y si conviene su adopción, integración o interoperabilidad.

## 12. Integración de ZENODO como repositorio de datos

**¿Por qué ZENODO?**
Permite publicar datasets, scripts y resultados con DOI, facilitando la preservación y citabilidad de los datos del Observatorio.

**¿Se puede usar cuenta personal?**
Sí. Puedes crear una cuenta personal (ej: Gmail) y comenzar a subir datasets. Posteriormente, puedes migrar la autoría o asociar la cuenta a la organización cuando dispongas de correo institucional.

**Recomendaciones:**
- Documentar el correo y usuario utilizado para trazabilidad.
- Usar la cuenta personal solo mientras no exista institucional.
- Solicitar el API token desde el perfil de usuario para automatizar cargas.

**Generación de token de acceso (API):**
1. Ingresa a tu perfil en ZENODO.
2. Ve a "Applications" > "New personal access token".
3. Asigna un nombre al token.
4. Marca los permisos necesarios:
  - `deposit:actions` (publicar)
  - `deposit:write` (subir archivos)
  - `user:email` (opcional, solo lectura de email)
5. Haz clic en "Create".

![Pantalla de generación de token en ZENODO](../images_reports/zenodo_token_creation.png)

**Automatización (opcional):**
Puedes usar el token para subir datasets vía API (Python, curl, etc). Documentar scripts y tokens usados en un archivo seguro, nunca en el repositorio público.

**Próximos pasos sugeridos:**
- Definir política de publicación de datasets.
- Documentar los DOIs generados y enlazarlos en el dashboard.
- Migrar a cuenta institucional cuando esté disponible.

## 13. Cómo guardar y usar el token de ZENODO de forma segura

**1. Nunca subas el token a ningún repositorio ni lo compartas por correo.**

**2. Guarda el token como variable de entorno en tu sistema (recomendado):**

**En macOS o Linux:**

Abre tu terminal y ejecuta:

```bash
export ZENODO_TOKEN="aquí_va_tu_token"
```

(Sustituye `aquí_va_tu_token` por el valor real de tu token, sin espacios ni comillas adicionales.)

Esto solo lo guarda para la sesión actual de terminal. Si cierras la terminal, deberás volver a exportarlo.

**Para hacerlo permanente:**
Agrega la línea anterior al final de tu archivo `~/.zshrc` (si usas zsh) o `~/.bashrc` (si usas bash):

```bash
echo 'export ZENODO_TOKEN="aquí_va_tu_token"' >> ~/.zshrc
```

Luego, recarga la configuración:

```bash
source ~/.zshrc
```

**3. El script Python leerá automáticamente la variable de entorno `ZENODO_TOKEN` y la usará para autenticarse.**

**Nunca guardes el token en archivos del repositorio, ni en scripts, ni lo compartas.**
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

## 11. Validación final de formulario y flujo operativo (2026-03-25)

- Se revisó el formulario Google generado y publicado por el script `Scripts/create_intake_google_form.py`.
- El formulario está abierto para respuestas (`isAcceptingResponses=true`), validado tanto en la API como en la interfaz web.
- Todas las preguntas requeridas (10) están presentes y visibles para el usuario final.
- El enlace público está correctamente cargado en el secreto `INTAKE_FLOW_FORM_URL` y es el que se envía en el correo semanal.
- Se realizó una prueba manual de acceso y envío de respuesta, confirmando funcionamiento end-to-end.
- El flujo semanal de recordatorio y acceso al formulario está operativo y cumple los requisitos definidos.

**Evidencia:**
- Captura de pantalla y revisión visual del formulario (ver historial de conversación y validación manual).
- Último correo recibido contiene el enlace funcional y el bloque de preguntas esperado.

**Observación:**
Se recomienda mantener esta validación como checklist en futuras iteraciones o cambios del flujo.
