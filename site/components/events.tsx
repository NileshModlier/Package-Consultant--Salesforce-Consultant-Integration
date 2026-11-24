import { eventSteps } from "@/lib/content";
import { Section } from "./section";

export function Events() {
  return (
    <Section
      id="events"
      index="08 — Platform events"
      title="Status leaves Salesforce only after the save survives."
      lede="Four fields: intake reference, object type, status, owner name. The owner-change publish is how the event names Inbound Sales or Support Tier 1 instead of the integration user."
    >
      <ol className="grid gap-4 md:grid-cols-5">
        {eventSteps.map((step, index) => (
          <li key={step.title} className="glass rounded-2xl p-4">
            <p className="font-mono text-xs text-iris">{String(index + 1).padStart(2, "0")}</p>
            <h3 className="mt-3 font-display text-lg leading-snug">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-mute">{step.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
