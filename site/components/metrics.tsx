"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { metrics } from "@/lib/content";
import { Section } from "./section";

export function Metrics() {
  return (
    <Section
      id="metrics"
      index="11 — Metrics"
      title="Counts from the repository, not a dashboard in production."
      lede="Each bar is a different measure. They are not a rate and they are not org telemetry. Counted 24 November 2026. Six fault drills sit inside the test file and are not a separate bar."
    >
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(16rem,0.6fr)]">
        <div className="h-80 glass rounded-2xl p-4" role="img" aria-label="Bar chart of case study counts">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={[...metrics]} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#93a4bd", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: "#93a4bd", fontSize: 12 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip
                cursor={{ fill: "rgba(27,150,255,0.08)" }}
                contentStyle={{
                  background: "#0c1a2c",
                  border: "1px solid rgba(176,214,255,0.2)",
                  borderRadius: 12,
                  color: "#e7eef8",
                }}
                formatter={(value) => [value ?? 0, "Count"]}
              />
              <Bar dataKey="value" name="Count" fill="#1b96ff" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <dl className="space-y-3">
          {metrics.map((item) => (
            <div key={item.name} className="flex items-baseline justify-between gap-4 border-b border-white/10 pb-2">
              <dt className="text-sm text-mute">
                {item.name}
                <span className="mt-1 block text-xs">{item.note}</span>
              </dt>
              <dd className="font-display text-2xl text-paper">{item.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </Section>
  );
}
