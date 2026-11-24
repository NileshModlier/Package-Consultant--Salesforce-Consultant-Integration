import Link from "next/link";

const links = [
  ["Problem", "/#problem"],
  ["Architecture", "/#architecture"],
  ["Clouds", "/#sales"],
  ["Integration", "/#integration"],
  ["Events", "/#events"],
  ["Reliability", "/#reliability"],
  ["Metrics", "/#metrics"],
  ["Interview", "/#interview"],
];

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#07111c]/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-3 md:px-10">
        <Link href="/" className="font-display text-sm tracking-wide text-paper">
          Intake-to-Salesforce
        </Link>
        <nav className="ml-auto flex gap-4 overflow-x-auto text-xs text-mute" aria-label="Case study">
          {links.map(([label, href]) => (
            <Link key={href} href={href} className="shrink-0 hover:text-paper">
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
