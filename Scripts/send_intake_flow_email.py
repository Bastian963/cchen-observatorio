#!/usr/bin/env python3
"""Envía un correo breve sobre el flujo de ingreso al Observatorio usando Brevo.

Uso seguro (no envía):
  python Scripts/send_intake_flow_email.py --to b.ayalainostroza@gmail.com --dry-run

Envío real:
  BREVO_API_KEY=... BREVO_FROM_EMAIL=observatory@cchen.cl \
  python Scripts/send_intake_flow_email.py \
    --to b.ayalainostroza@gmail.com \
    --send-brevo --confirm-send
"""

from __future__ import annotations

import argparse
import json
import os
from html import escape
from urllib.request import Request, urlopen


DEFAULT_SUBJECT = "Propuesta breve - Flujo de ingreso de necesidades al Observatorio CCHEN"
DEFAULT_FROM_NAME = "Observatorio CCHEN"
DEFAULT_TO = "b.ayalainostroza@gmail.com"
DEFAULT_FORM_URL = ""


def _split_emails(raw: str) -> list[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def build_html(form_url: str = "") -> str:
    objective_items = [
        "recibir solicitudes de manera formal,",
        "clasificarlas de forma consistente,",
        "priorizarlas con criterio,",
        "y darles seguimiento con responsable y estado.",
    ]
    sharing_items = [
        "ideas de mejora,",
        "informacion util,",
        "antecedentes,",
        "archivos o fuentes disponibles,",
        "y senales tempranas que podrian transformarse en una mejora concreta del Observatorio.",
    ]
    flow_items = [
        "deteccion de la necesidad,",
        "correo breve de convocatoria,",
        "formulario estandar de ingreso,",
        "recepcion y clasificacion por el Observatorio,",
        "e incorporacion al backlog, piloto o flujo de datos correspondiente.",
    ]
    form_questions = [
        "Semana de reporte (YYYY-W##)",
        "Unidad",
        "Nombre y correo de quien reporta",
        "Tipo de ingreso (Solicitud nueva / Seguimiento / Idea de mejora / Informacion para compartir)",
        "Titulo breve",
        "Descripcion breve",
        "Urgencia (Alta / Media / Baja / Sin informacion por ahora)",
        "Impacto esperado (Alto / Medio / Bajo / Sin informacion por ahora)",
        "Link o evidencia (opcional)",
        "Ideas o antecedentes adicionales (opcional)",
    ]

    def _list(items: list[str]) -> str:
        return "".join(f"<li>{escape(item)}</li>" for item in items)

    form_url_clean = form_url.strip()
    button_html = ""
    link_html = ""
    if form_url_clean:
        safe_url = escape(form_url_clean)
        button_html = (
            f"<p style=\"margin:14px 0 8px;\">"
            f"<a href=\"{safe_url}\" style=\"display:inline-block;background:#6d4c41;color:#fffdf8;text-decoration:none;padding:12px 18px;border-radius:6px;font-weight:bold;\">"
            "Abrir formulario de ingreso"
            "</a></p>"
        )
        link_html = f"<p style=\"margin:0 0 14px;\">Link directo: <a href=\"{safe_url}\">{safe_url}</a></p>"

    return f"""<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\">
  <title>{escape(DEFAULT_SUBJECT)}</title>
</head>
<body style=\"margin:0;padding:24px;background:#f4f1e8;font-family:Georgia,'Times New Roman',serif;color:#1f2933;\">
  <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:720px;margin:0 auto;background:#fffdf8;border:1px solid #d8cfbf;\">
    <tr>
      <td style=\"padding:28px 32px;border-bottom:4px solid #6d4c41;\">
        <div style=\"font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#7c5f52;\">Observatorio CCHEN</div>
        <h1 style=\"margin:10px 0 0;font-size:28px;line-height:1.2;color:#2d3748;\">Propuesta breve de flujo de ingreso</h1>
      </td>
    </tr>
    <tr>
      <td style=\"padding:28px 32px 18px;font-size:16px;line-height:1.7;\">
        <p style=\"margin-top:0;\">Hola,</p>
        <p>Quisiera presentar una propuesta breve para ordenar el ingreso de nuevas necesidades, ideas, oportunidades, antecedentes o solicitudes de mejora al Observatorio CCHEN.</p>
        <p>El objetivo es contar con un mecanismo simple y trazable que permita:</p>
        <ul style=\"padding-left:20px;margin:0 0 18px;\">{_list(objective_items)}</ul>
        <p>La idea no es solo recibir pedidos. Tambien busca abrir un canal para que las unidades puedan compartir:</p>
        <ul style=\"padding-left:20px;margin:0 0 18px;\">{_list(sharing_items)}</ul>
        <p>La propuesta considera un flujo simple:</p>
        <ol style=\"padding-left:20px;margin:0 0 18px;\">{''.join(f'<li>{escape(item)}</li>' for item in flow_items)}</ol>
                <p>El formulario propuesto esta pensado para ser explicativo y simple de responder, incluyendo un campo especifico para registrar ideas o informacion que la unidad pueda compartir aunque todavia no exista un requerimiento formal completamente definido.</p>

                <h2 style=\"font-size:21px;margin:22px 0 10px;color:#2d3748;\">Formulario de ingreso (ultra corto)</h2>
                <p style=\"margin:0 0 10px;\">Si no tienes toda la informacion disponible, marca o escribe \"Sin informacion por ahora\" y envia igual.</p>
                <ol style=\"padding-left:20px;margin:0 0 18px;\">{''.join(f'<li>{escape(item)}</li>' for item in form_questions)}</ol>
                {button_html}
                {link_html}
        <p>Si el enfoque parece adecuado, el siguiente paso seria validar el flujo y pilotearlo con una unidad usuaria prioritaria.</p>
        <p style=\"margin-bottom:0;\">Gracias.</p>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def send_via_brevo(
    html: str,
    subject: str,
    to_emails: list[str],
    from_email: str,
    from_name: str,
    api_key: str,
    reply_to: str = "",
    dry_run: bool = True,
) -> bool:
    payload = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": email} for email in to_emails],
        "subject": subject,
        "htmlContent": html,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}

    if dry_run:
        print("[DRY-RUN] Brevo habilitado, pero no se enviara correo real.")
        print(f"[DRY-RUN] Destinatarios: {', '.join(to_emails)}")
        print(f"[DRY-RUN] Asunto: {subject}")
        print(f"[DRY-RUN] Tamano HTML: {len(html):,} caracteres")
        return True

    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
            "user-agent": "CCHEN-Observatorio/0.2",
        },
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8", errors="replace")
        print(f"[OK] Brevo envio HTTP {response.status}")
        print(f"[OK] Respuesta: {body[:220]}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Enviar correo del flujo de ingreso por Brevo")
    parser.add_argument("--to", default=DEFAULT_TO, help="Destinatario o lista separada por comas")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Asunto del correo")
    parser.add_argument("--form-url", default=DEFAULT_FORM_URL, help="URL del formulario (opcional, ignorado si se usa --html-file)")
    parser.add_argument("--html-file", default="", help="Ruta a HTML precompilado por React Email (omite build_html)")
    parser.add_argument("--send-brevo", action="store_true", help="Intentar envio por Brevo")
    parser.add_argument("--dry-run", action="store_true", help="Validar sin enviar correo real")
    parser.add_argument("--confirm-send", action="store_true", help="Confirma envio real")
    args = parser.parse_args()

    html_file = (args.html_file or os.getenv("INTAKE_EMAIL_HTML_FILE", "")).strip()
    if html_file:
        with open(html_file, encoding="utf-8") as fh:
            html = fh.read()
        print(f"[INFO] HTML cargado desde React Email: {html_file}")
    else:
        form_url = (args.form_url or os.getenv("INTAKE_FLOW_FORM_URL", "")).strip()
        html = build_html(form_url=form_url)
    to_emails = _split_emails(args.to) or _split_emails(os.getenv("BREVO_TO_EMAILS", DEFAULT_TO))

    if not args.send_brevo:
        print("[INFO] Correo generado localmente. Usa --send-brevo para envio via Brevo.")
        print(f"[INFO] Destinatarios: {', '.join(to_emails)}")
        print(f"[INFO] Asunto: {args.subject}")
        return 0

    api_key = os.getenv("BREVO_API_KEY", "").strip()
    from_email = os.getenv("BREVO_FROM_EMAIL", "").strip()
    from_name = os.getenv("BREVO_FROM_NAME", DEFAULT_FROM_NAME).strip()
    reply_to = os.getenv("BREVO_REPLY_TO", "").strip()

    missing = []
    if not api_key:
        missing.append("BREVO_API_KEY")
    if not from_email:
        missing.append("BREVO_FROM_EMAIL")
    if not to_emails:
        missing.append("BREVO_TO_EMAILS/--to")
    if missing:
        print("[WARN] Envio Brevo omitido. Faltan variables:")
        for item in missing:
            print(f"  - {item}")
        return 1

    dry_run = True
    if args.confirm_send:
        dry_run = False
    if args.dry_run:
        dry_run = True

    send_via_brevo(
        html=html,
        subject=args.subject,
        to_emails=to_emails,
        from_email=from_email,
        from_name=from_name,
        api_key=api_key,
        reply_to=reply_to,
        dry_run=dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
