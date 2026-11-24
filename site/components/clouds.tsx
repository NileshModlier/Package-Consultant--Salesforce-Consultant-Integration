import { salesPoints, servicePoints } from "@/lib/content";
import { Section } from "./section";

function Points({ items, accent }: { items: readonly { title: string; text: string }[]; accent: string }) {
  return (
    <ol className="space-y-6">
      {items.map((item, index) => (
        <li key={item.title} className="grid grid-cols-[2.5rem_1fr] gap-3">
          <span className={`font-mono text-sm ${accent}`}>{String(index + 1).padStart(2, "0")}</span>
          <div>
            <h3 className="font-display text-xl">{item.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-mute">{item.text}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Clouds() {
  return (
    <>
      <Section
        id="sales"
        index="04 — Sales Cloud"
        title="A Lead is for a person the org does not already know."
        lede="Known Contacts with a commercial ask are a Sales Manager hold in the policy. The sample worker implements the phrase route and the upsert, not that match."
      >
        <Points items={salesPoints} accent="text-sf" />
      </Section>
      <Section
        id="service"
        index="05 — Service Cloud"
        title="Support becomes a Case even when the person is already known."
        lede="Priority changes the task and the clock. It does not change the queue. Contact linking is specified, and it is not what the twenty-conversation worker executes."
      >
        <Points items={servicePoints} accent="text-cyan" />
      </Section>
    </>
  );
}
