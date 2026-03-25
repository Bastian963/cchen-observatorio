#!/usr/bin/env python3
"""Crea el formulario de ingreso del Observatorio CCHEN en Google Forms via API.

Prerequisitos:
  1. Descarga las credenciales OAuth desde Google Cloud Console como
     credentials.json y colócalas en la raíz del proyecto.
  2. Ejecuta este script una sola vez:
        python Scripts/create_intake_google_form.py
  3. Se abrirá el navegador para autorización.
  4. Al terminar imprime la URL pública del formulario creado.

Salida:
  - form_id, URL de edición y URL pública del formulario.
  - Guarda form_id en Scripts/intake_form_id.txt para uso posterior.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Configuración ────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
]

CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent.parent / "token_forms.json"
FORM_ID_FILE = Path(__file__).parent / "intake_form_id.txt"

FORM_TITLE = "Flujo de ingreso — Observatorio CCHEN"
FORM_DESCRIPTION = (
    'Este formulario está pensado para completarse rápidamente semana a semana. '
    'Si no cuentas con toda la información, selecciona "Sin información por ahora" '
    'y envía igual.'
)

# Definición completa de las 10 preguntas
QUESTIONS: list[dict] = [
    {
        "title": "Semana de reporte",
        "helpText": "Formato recomendado: YYYY-W## (ej: 2026-W14)",
        "type": "SHORT_ANSWER",
        "required": True,
    },
    {
        "title": "Unidad",
        "type": "RADIO",
        "required": True,
        "options": ["DGIn", "Vigilancia", "Transferencia", "Gobernanza", "Otra"],
    },
    {
        "title": "Nombre y correo de quien reporta",
        "helpText": "Ej: Juan Pérez - juan.perez@cchen.cl",
        "type": "SHORT_ANSWER",
        "required": True,
    },
    {
        "title": "Tipo de ingreso",
        "type": "RADIO",
        "required": True,
        "options": [
            "Solicitud nueva",
            "Seguimiento",
            "Idea de mejora",
            "Información para compartir",
        ],
    },
    {
        "title": "Título breve",
        "helpText": "Máximo 100 caracteres",
        "type": "SHORT_ANSWER",
        "required": True,
    },
    {
        "title": "Descripción breve",
        "helpText": "Explica con tus propias palabras qué necesitas o qué quieres compartir.",
        "type": "LONG_ANSWER",
        "required": True,
    },
    {
        "title": "Urgencia",
        "type": "RADIO",
        "required": True,
        "options": ["Alta", "Media", "Baja", "Sin información por ahora"],
    },
    {
        "title": "Impacto esperado",
        "type": "RADIO",
        "required": True,
        "options": ["Alto", "Medio", "Bajo", "Sin información por ahora"],
    },
    {
        "title": "Link o evidencia (opcional)",
        "helpText": "Puede ser URL, ruta de archivo o escribe 'Sin link por ahora'.",
        "type": "SHORT_ANSWER",
        "required": False,
    },
    {
        "title": "Ideas o antecedentes adicionales (opcional)",
        "helpText": "Si no hay nada adicional, escribe: Sin antecedentes adicionales.",
        "type": "LONG_ANSWER",
        "required": False,
    },
]


# ── Auth ─────────────────────────────────────────────────────────────────────

def _get_credentials() -> Credentials:
    creds: Credentials | None = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(
                    f"[ERROR] No se encontró {CREDENTIALS_FILE}\n"
                    "Descarga las credenciales OAuth desde Google Cloud Console "
                    "y guárdalas como credentials.json en la raíz del proyecto.",
                    file=sys.stderr,
                )
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"[OK] Token guardado en {TOKEN_FILE}")

    return creds


# ── Helpers para construir requests de batchUpdate ───────────────────────────

def _build_question_request(question: dict, index: int) -> dict:
    q_type = question["type"]
    title = question["title"]
    help_text = question.get("helpText", "")
    required = question.get("required", True)

    if q_type == "SHORT_ANSWER":
        question_item = {
            "question": {
                "required": required,
                "textQuestion": {"paragraph": False},
            }
        }
    elif q_type == "LONG_ANSWER":
        question_item = {
            "question": {
                "required": required,
                "textQuestion": {"paragraph": True},
            }
        }
    elif q_type == "RADIO":
        question_item = {
            "question": {
                "required": required,
                "choiceQuestion": {
                    "type": "RADIO",
                    "options": [{"value": opt} for opt in question["options"]],
                },
            }
        }
    else:
        raise ValueError(f"Tipo de pregunta no soportado: {q_type}")

    item: dict = {
        "title": title,
        "questionItem": question_item,
    }
    if help_text:
        item["description"] = help_text

    return {
        "createItem": {
            "item": item,
            "location": {"index": index},
        }
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("Autenticando con Google...")
    creds = _get_credentials()
    service = build("forms", "v1", credentials=creds)

    # 1. Crear formulario con título
    print(f"Creando formulario: '{FORM_TITLE}'...")
    new_form = {
        "info": {
            "title": FORM_TITLE,
            "documentTitle": FORM_TITLE,
        }
    }
    form = service.forms().create(body=new_form).execute()
    form_id: str = form["formId"]
    print(f"[OK] Formulario creado. ID: {form_id}")

    # 2. Añadir descripción + las 10 preguntas en un solo batchUpdate
    requests = []

    # Descripción del formulario (updateFormInfo)
    update_info_request = {
        "updateFormInfo": {
            "info": {"description": FORM_DESCRIPTION},
            "updateMask": "description",
        }
    }

    question_requests = [
        _build_question_request(q, i) for i, q in enumerate(QUESTIONS)
    ]
    requests = [update_info_request] + question_requests

    print(f"Añadiendo descripción y {len(QUESTIONS)} preguntas...")
    service.forms().batchUpdate(
        formId=form_id,
        body={"requests": requests},
    ).execute()
    print("[OK] Preguntas añadidas.")

    # 3. Publicar y abrir respuestas del formulario.
    # Desde los cambios de 2026, al actualizar publishState se deben enviar ambos
    # flags: isPublished e isAcceptingResponses.
    try:
        service.forms().setPublishSettings(
            formId=form_id,
            body={
                "publishSettings": {
                    "publishState": {
                        "isPublished": True,
                        "isAcceptingResponses": True,
                    }
                },
                "updateMask": "publishState",
            },
        ).execute()
        print("[OK] Formulario publicado y abierto para recibir respuestas.")
    except Exception as exc:
        print(f"[WARN] No se pudo publicar/abrir automáticamente: {exc}")
        print("       Puedes abrirlo manualmente con 'Seguir recopilando respuestas'.")

    # 4. Obtener estado final y URLs
    result = service.forms().get(formId=form_id).execute()
    responder_uri: str = result.get("responderUri", f"https://docs.google.com/forms/d/{form_id}/viewform")
    edit_uri = f"https://docs.google.com/forms/d/{form_id}/edit"

    # Guardar form_id para uso posterior (ingesta de respuestas)
    FORM_ID_FILE.write_text(form_id, encoding="utf-8")
    print(f"[OK] form_id guardado en {FORM_ID_FILE}")

    print("\n" + "=" * 60)
    print("FORMULARIO LISTO")
    print("=" * 60)
    print(f"  Form ID  : {form_id}")
    print(f"  Editar   : {edit_uri}")
    print(f"  Responder: {responder_uri}")
    print("=" * 60)
    print("\nPróximo paso:")
    print("  Carga la URL de responder como secret INTAKE_FLOW_FORM_URL en GitHub.")
    print(f"  gh secret set INTAKE_FLOW_FORM_URL --repo Bastian963/cchen-observatorio")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
