import { assistantPoints } from "@/lib/content";
import { Section } from "./section";

export function Assistant() {
  return (
    <Section
      id="assistant"
      index="09 — AI assistant"
      title="The receptionist classifies. It does not decide."
      lede="Hiring panels ask where the model stops. In this package the route is a state machine, the summary is a field, and people own the queue."
    >
      <div className="grid gap-6 md:grid-cols-2">
        {assistantPoints.map((item) => (
          <article key={item.title} className="border-t border-iris/40 pt-4">
            <h3 className="font-display text-2xl">{item.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-mute">{item.text}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
