import { configuration } from "@/lib/content";
import { Section } from "./section";

export function Configuration() {
  return (
    <Section
      id="configuration"
      index="06 — Salesforce configuration"
      title="What the manifest would deploy."
      lede="API 62.0. The command is sf project deploy start --manifest manifest/package.xml. This repository has not been deployed, and the flow diagrams are drawn from metadata, not photographed in Flow Builder."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <caption className="sr-only">Salesforce metadata in the package</caption>
          <thead className="text-xs uppercase tracking-[0.16em] text-mute">
            <tr>
              <th className="pb-3 pr-6 font-medium">Metadata</th>
              <th className="pb-3 font-medium">What is in source</th>
            </tr>
          </thead>
          <tbody>
            {configuration.map((row) => (
              <tr key={row.kind} className="border-t border-white/10">
                <th className="py-4 pr-6 align-top font-display text-base font-medium text-paper">{row.kind}</th>
                <td className="py-4 text-mute">{row.items}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
