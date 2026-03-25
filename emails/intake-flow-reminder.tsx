import {
  Body,
  Button,
  Container,
  Head,
  Heading,
  Hr,
  Html,
  Link,
  Preview,
  Section,
  Text,
} from "@react-email/components";
import * as React from "react";

export interface IntakeFlowReminderProps {
  formUrl?: string;
}

const formQuestions: string[] = [
  "Semana de reporte (YYYY-W##)",
  "Unidad",
  "Nombre y correo de quien reporta",
  "Tipo de ingreso (Solicitud nueva / Seguimiento / Idea de mejora / Información para compartir)",
  "Título breve",
  "Descripción breve",
  "Urgencia (Alta / Media / Baja / Sin información por ahora)",
  "Impacto esperado (Alto / Medio / Bajo / Sin información por ahora)",
  "Link o evidencia (opcional)",
  "Ideas o antecedentes adicionales (opcional)",
];

export default function IntakeFlowReminder({
  formUrl = "",
}: IntakeFlowReminderProps) {
  return (
    <Html lang="es">
      <Head />
      <Preview>
        Recordatorio semanal: Flujo de ingreso al Observatorio CCHEN
      </Preview>
      <Body style={main}>
        <Container style={container}>
          {/* Header */}
          <Section style={header}>
            <Text style={tagline}>Observatorio CCHEN</Text>
            <Heading as="h1" style={h1}>
              Flujo de ingreso de necesidades
            </Heading>
          </Section>

          {/* Body */}
          <Section style={bodySection}>
            <Text style={paragraph}>Hola,</Text>
            <Text style={paragraph}>
              Este es el recordatorio semanal para registrar en el Observatorio
              CCHEN cualquier necesidad, idea, oportunidad, antecedente o
              solicitud de mejora de tu unidad.
            </Text>
            <Text style={paragraph}>
              El objetivo es contar con un mecanismo simple y trazable que
              permita recibir solicitudes de manera formal, clasificarlas de
              forma consistente, priorizarlas con criterio, y darles seguimiento
              con responsable y estado.
            </Text>

            <Hr style={divider} />

            {/* Form section */}
            <Heading as="h2" style={h2}>
              Formulario de ingreso (ultra corto · 10 preguntas)
            </Heading>
            <Text style={hint}>
              Si no tienes toda la información disponible, escribe
              «Sin información por ahora» y envía igual.
            </Text>

            <ol style={list}>
              {formQuestions.map((q, i) => (
                <li key={i} style={listItem}>
                  {q}
                </li>
              ))}
            </ol>

            {formUrl ? (
              <>
                <Button href={formUrl} style={button}>
                  Abrir formulario de ingreso
                </Button>
                <Text style={linkText}>
                  Link directo:{" "}
                  <Link href={formUrl} style={linkStyle}>
                    {formUrl}
                  </Link>
                </Text>
              </>
            ) : null}

            <Hr style={divider} />

            <Text style={paragraph}>
              Si el enfoque parece adecuado, el siguiente paso sería validar el
              flujo y pilotearlo con una unidad usuaria prioritaria.
            </Text>
            <Text style={{ ...paragraph, marginBottom: 0 }}>Gracias.</Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────

const main: React.CSSProperties = {
  margin: 0,
  padding: "24px",
  backgroundColor: "#f4f1e8",
  fontFamily: "Georgia, 'Times New Roman', serif",
  color: "#1f2933",
};

const container: React.CSSProperties = {
  maxWidth: "720px",
  margin: "0 auto",
  backgroundColor: "#fffdf8",
  border: "1px solid #d8cfbf",
};

const header: React.CSSProperties = {
  padding: "28px 32px",
  borderBottom: "4px solid #6d4c41",
};

const tagline: React.CSSProperties = {
  fontSize: "12px",
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: "#7c5f52",
  margin: "0 0 8px",
};

const h1: React.CSSProperties = {
  margin: 0,
  fontSize: "28px",
  lineHeight: "1.2",
  color: "#2d3748",
};

const bodySection: React.CSSProperties = {
  padding: "28px 32px 18px",
  fontSize: "16px",
  lineHeight: "1.7",
};

const paragraph: React.CSSProperties = {
  margin: "0 0 14px",
};

const h2: React.CSSProperties = {
  fontSize: "21px",
  margin: "22px 0 10px",
  color: "#2d3748",
};

const hint: React.CSSProperties = {
  margin: "0 0 10px",
  fontSize: "14px",
  color: "#4a5568",
};

const list: React.CSSProperties = {
  paddingLeft: "20px",
  margin: "0 0 18px",
};

const listItem: React.CSSProperties = {
  marginBottom: "6px",
};

const button: React.CSSProperties = {
  backgroundColor: "#6d4c41",
  color: "#fffdf8",
  padding: "12px 18px",
  borderRadius: "6px",
  fontWeight: "bold",
  textDecoration: "none",
  display: "inline-block",
  margin: "14px 0 8px",
};

const linkText: React.CSSProperties = {
  margin: "0 0 14px",
  fontSize: "14px",
};

const linkStyle: React.CSSProperties = {
  color: "#6d4c41",
};

const divider: React.CSSProperties = {
  borderColor: "#d8cfbf",
  margin: "18px 0",
};
