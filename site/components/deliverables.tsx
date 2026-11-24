import { deliverables } from "@/lib/content";
import { Section } from "./section";

export function Deliverables() {
  return (
    <Section
      id="deliverables"
      index="03 — Consulting deliverables"
      title="The binder a reviewer can open."
      lede="Discovery is in docs/. The workbook is the field map. The solution design keeps the decisions that were turned down, not only the one that was built."
    >
      <ol className="divide-y divide-white/10 border-y border-white/10">
        {deliverables.map((item, index) => (
          <li key={item.title} className="grid gap-2 py-5 md:grid-cols-[14rem_1fr] md:gap-8">
            <h3 className="font-display text-xl">
              <span className="mr-3 font-mono text-xs text-cyan">{String(index + 1).padStart(2, "0")}</span>
              {item.title}
            </h3>
            <p className="text-mute">{item.detail}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
