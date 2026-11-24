import Link from "next/link";
import { author } from "@/lib/content";

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-5 py-12 md:px-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-display text-2xl">{author.name}</p>
          <p className="mt-2 max-w-md text-sm text-mute">
            Author of this case study. The Salesforce metadata is source. The Python tests ran locally. This page is not a product brochure.
          </p>
        </div>
        <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <li>
            <a href={author.linkedin} className="text-cyan hover:text-paper">
              LinkedIn
            </a>
          </li>
          <li>
            <Link href="/architecture" className="text-cyan hover:text-paper">
              Architecture docs
            </Link>
          </li>
          <li>
            <Link href="/demo" className="text-cyan hover:text-paper">
              Demo walkthrough
            </Link>
          </li>
        </ul>
      </div>
    </footer>
  );
}
