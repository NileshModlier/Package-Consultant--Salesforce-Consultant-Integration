"use client";

import { useState } from "react";
import { interviewTopics } from "@/lib/content";
import { Section } from "./section";

export function Interview() {
  const [open, setOpen] = useState(0);
  return (
    <Section
      id="interview"
      index="12 — Interview readiness"
      title="Six answers an architect will actually ask."
      lede="The full set is 50 Salesforce questions, 25 integration questions, and 25 consultant questions, with answers, in docs/interview-guide.md. These six are the ones that carry the design."
    >
      <div className="divide-y divide-white/10 border-y border-white/10">
        {interviewTopics.map((topic, index) => {
          const expanded = open === index;
          return (
            <div key={topic.title}>
              <button
                type="button"
                aria-expanded={expanded}
                onClick={() => setOpen(expanded ? -1 : index)}
                className="flex w-full items-center justify-between gap-4 py-4 text-left"
              >
                <span className="font-display text-2xl">{topic.title}</span>
                <span className="font-mono text-xs text-cyan">{expanded ? "Close" : "Open"}</span>
              </button>
              {expanded ? <p className="max-w-3xl pb-5 text-sm leading-relaxed text-mute">{topic.answer}</p> : null}
            </div>
          );
        })}
      </div>
    </Section>
  );
}
