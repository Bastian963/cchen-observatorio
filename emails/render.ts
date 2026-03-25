/**
 * Renders the intake-flow-reminder template to HTML and writes to stdout.
 *
 * Usage:
 *   INTAKE_FLOW_FORM_URL="https://..." npx tsx render.ts > ../dist/emails/intake-flow-reminder.html
 */
import { render } from "@react-email/render";
import * as React from "react";
import IntakeFlowReminder from "./intake-flow-reminder";

async function main(): Promise<void> {
  const formUrl = process.env.INTAKE_FLOW_FORM_URL ?? "";
  const html = await render(
    React.createElement(IntakeFlowReminder, { formUrl })
  );
  process.stdout.write(html);
}

main().catch((e: unknown) => {
  console.error(e);
  process.exit(1);
});
