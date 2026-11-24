import type { ReactNode } from "react";

export function Section({
  id,
  index,
  title,
  lede,
  children,
}: {
  id: string;
  index: string;
  title: string;
  lede?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-white/10 px-5 py-16 md:px-10 md:py-24">
      <div className="mx-auto max-w-6xl">
        <p className="font-mono text-xs tracking-[0.2em] text-cyan">{index}</p>
        <h2 className="mt-3 max-w-3xl font-display text-3xl leading-tight md:text-5xl">{title}</h2>
        {lede ? <p className="mt-4 max-w-3xl text-lg text-mute">{lede}</p> : null}
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}
