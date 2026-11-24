import type { Metadata } from "next";
import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";
import { demoBeats } from "@/lib/content";

export const metadata: Metadata = {
  title: "Demo walkthrough · Intake-to-Salesforce",
  description: "The five-minute case study walkthrough. A recording is not included in this package.",
};

export default function DemoPage() {
  return (
    <>
      <Nav />
      <main className="px-5 py-16 md:px-10">
        <article className="mx-auto max-w-3xl">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-cyan">Demo walkthrough</p>
          <h1 className="mt-4 font-display text-4xl md:text-6xl">Five minutes, said in this order.</h1>
          <p className="mt-6 text-lg text-mute">
            A video file is not in this package. This is the script. Say the boundary in the first minute: the metadata is source, the tests ran locally, and nothing in the demo is a live org.
          </p>
          <ol className="mt-12 space-y-6">
            {demoBeats.map((beat) => (
              <li key={beat.time} className="grid gap-2 border-t border-white/10 pt-6 md:grid-cols-[5rem_1fr]">
                <p className="font-mono text-sm text-ember">{beat.time}</p>
                <div>
                  <h2 className="font-display text-2xl">{beat.show}</h2>
                  <p className="mt-2 text-mute">{beat.say}</p>
                </div>
              </li>
            ))}
          </ol>
        </article>
      </main>
      <Footer />
    </>
  );
}
