import { Braces, Cloud, Code2, KeyRound, Radio, Workflow } from "lucide-react";
import { highlights } from "@/lib/content";

const icons = [Cloud, Cloud, Workflow, Radio, Braces, Code2, KeyRound];

export function Hero() {
  return (
    <section className="hero-glow px-5 pb-20 pt-16 md:px-10 md:pt-24">
      <div className="mx-auto max-w-6xl">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-cyan">
          Technical case study · for hiring managers and architects
        </p>
        <h1 className="mt-5 max-w-4xl font-display text-5xl leading-[0.95] text-paper md:text-7xl">
          Intake-to-Salesforce
        </h1>
        <p className="mt-6 max-w-2xl text-xl text-paper/90 md:text-2xl">
          AI receptionist to Salesforce CRM integration platform
        </p>
        <p className="mt-6 max-w-2xl text-base leading-relaxed text-mute">
          One conversation becomes one Lead or one Case. A replay updates that record. Status comes back on a platform event after the save commits. Twenty-two Python tests passed against a local stand-in. The org deploy has not been run.
        </p>
        <ul className="mt-8 flex flex-wrap gap-2" aria-label="Platforms in the case study">
          {highlights.map((item, index) => {
            const Icon = icons[index];
            return (
              <li key={item} className="glass flex items-center gap-2 rounded-full px-3 py-1 text-xs tracking-wide text-paper">
                <Icon className="h-3.5 w-3.5 text-cyan" aria-hidden />
                {item}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

