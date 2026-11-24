import { lessons } from "@/lib/content";
import { Section } from "./section";

export function Lessons() {
  return (
    <Section
      id="lessons"
      index="13 — Lessons"
      title="What I would say again in the room."
    >
      <div className="grid gap-8 md:grid-cols-2">
        {lessons.map((lesson) => (
          <article key={lesson.title}>
            <h3 className="font-display text-2xl">{lesson.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-mute">{lesson.text}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
