"use client";

import { motion, useReducedMotion } from "framer-motion";
import { afterPath, beforePath } from "@/lib/content";
import { Section } from "./section";

function Rail({
  steps,
  tone,
}: {
  steps: readonly { title: string; text: string }[];
  tone: "ember" | "cyan";
}) {
  const reduce = useReducedMotion();
  return (
    <ol className="relative space-y-6 pl-8">
      <span className={`absolute bottom-2 left-[7px] top-2 w-px ${tone === "ember" ? "rail-ember" : "rail-cyan"}`} aria-hidden />
      {steps.map((step, index) => (
        <motion.li
          key={step.title}
          initial={reduce ? false : { opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ delay: reduce ? 0 : index * 0.05, duration: 0.35 }}
          className="relative"
        >
          <span
            className={`absolute -left-8 top-1.5 h-3.5 w-3.5 rounded-full border-2 border-ink ${tone === "ember" ? "bg-ember" : "bg-cyan"}`}
            aria-hidden
          />
          <h3 className="font-display text-lg">{step.title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-mute">{step.text}</p>
        </motion.li>
      ))}
    </ol>
  );
}

export function Problem() {
  return (
    <Section
      id="problem"
      index="01 — Business problem"
      title="The handoff was a person retyping a mailbox."
      lede="The left path is the failure. The right path is the integration this case study builds. The as-is side is a baseline hypothesis, not a client workshop transcript."
    >
      <div className="grid gap-12 md:grid-cols-2">
        <div>
          <p className="mb-6 font-mono text-xs uppercase tracking-[0.18em] text-ember">Before</p>
          <Rail steps={beforePath} tone="ember" />
        </div>
        <div>
          <p className="mb-6 font-mono text-xs uppercase tracking-[0.18em] text-cyan">After</p>
          <Rail steps={afterPath} tone="cyan" />
        </div>
      </div>
    </Section>
  );
}
