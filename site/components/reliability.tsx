import { drills } from "@/lib/content";
import { Section } from "./section";

export function Reliability() {
  return (
    <Section
      id="reliability"
      index="10 — Testing and reliability"
      title="Faults were injected. The row had to land in the right state."
      lede="The six named drills, plus token refresh, duplicate events, and an expired replay id, ran against a local HTTP stand-in and a closed port. They did not run inside a Salesforce org."
    >
      <ol className="grid gap-4 sm:grid-cols-2">
        {drills.map((drill) => (
          <li key={drill.name} className="rounded-2xl border border-white/10 px-4 py-4">
            <h3 className="font-display text-lg">{drill.name}</h3>
            <p className="mt-2 text-sm text-mute">{drill.result}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
