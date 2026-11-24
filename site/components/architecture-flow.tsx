"use client";

import { useState } from "react";
import { architectureSteps } from "@/lib/content";
import { Section } from "./section";

export function ArchitectureFlow() {
  const [active, setActive] = useState(0);
  const step = architectureSteps[active];

  return (
    <Section
      id="architecture"
      index="02 — Architecture"
      title="Nine steps, one direction of record."
      lede="Select a step. Salesforce becomes the system of record only after the PATCH commits. The subscriber is the way status gets back to the intake agent."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <ol className="glass rounded-2xl p-3">
          {architectureSteps.map((item, index) => {
            const selected = index === active;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setActive(index)}
                  className={`flex w-full items-baseline gap-3 rounded-xl px-3 py-3 text-left ${selected ? "bg-sf/15 text-paper" : "text-mute hover:text-paper"}`}
                >
                  <span className="font-mono text-xs text-cyan">{String(index + 1).padStart(2, "0")}</span>
                  <span className="font-display text-lg">{item.title}</span>
                </button>
              </li>
            );
          })}
        </ol>
        <article className="glass flex min-h-72 flex-col justify-between rounded-2xl p-6 md:p-8">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-cyan">{step.file}</p>
            <h3 className="mt-3 font-display text-3xl">{step.title}</h3>
            <p className="mt-4 max-w-xl text-lg leading-relaxed text-paper/90">{step.text}</p>
          </div>
          <p className="mt-8 text-sm text-mute">
            Step {active + 1} of {architectureSteps.length}. On a phone, the detail sits under the list.
          </p>
        </article>
      </div>
    </Section>
  );
}
