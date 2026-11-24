import type { Metadata } from "next";
import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";
import { architectureSteps } from "@/lib/content";

export const metadata: Metadata = {
  title: "Architecture · Intake-to-Salesforce",
  description: "The commit path from conversation to Lead or Case, and the status event back to the intake agent.",
};

export default function ArchitecturePage() {
  return (
    <>
      <Nav />
      <main className="px-5 py-16 md:px-10">
        <article className="mx-auto max-w-3xl">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-cyan">Architecture docs</p>
          <h1 className="mt-4 font-display text-4xl md:text-6xl">One reference, then the status comes back.</h1>
          <p className="mt-6 text-lg text-mute">
            Salesforce is the system of record after a successful commit. The intake agent is the system of engagement until that commit. The Python package is the commit boundary and the return path. The longer diagram set is also in docs/architecture.md in the repository.
          </p>
          <ol className="mt-12 space-y-8">
            {architectureSteps.map((step, index) => (
              <li key={step.id} className="border-t border-white/10 pt-6">
                <p className="font-mono text-xs text-cyan">
                  {String(index + 1).padStart(2, "0")} · {step.file}
                </p>
                <h2 className="mt-2 font-display text-2xl">{step.title}</h2>
                <p className="mt-2 text-mute">{step.text}</p>
              </li>
            ))}
          </ol>
          <h2 className="mt-16 font-display text-3xl">Lead, Case, and the event</h2>
          <p className="mt-4 text-mute">
            Lead Intake Handling runs when Intake Ref is set on create or when the reference changes. It assigns Inbound Sales, creates a review task, and at 24 hours creates an escalation task if status is still Open - Not Contacted. Case Intake Handling assigns Support Tier 1, creates a priority task, and adds monitoring tasks at 4 hours and 24 hours while the case is still New. A missing queue rolls the save back.
          </p>
          <p className="mt-4 text-mute">
            The status publishers run afterward. They publish Intake_Status__e when the record is created or when status or owner changes. If CometD cannot be reached, the subscriber leaves the replay cursor where it was. The next run asks for events after that cursor.
          </p>
        </article>
      </main>
      <Footer />
    </>
  );
}
