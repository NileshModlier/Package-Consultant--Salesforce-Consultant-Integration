import { retryMatrix } from "@/lib/content";
import { Section } from "./section";

const pillars = [
  { title: "External Client App", text: "Created in the org, not in the repository. Client credentials flow, run-as user is the integration user." },
  { title: "OAuth", text: "The token request is a form post. The access token is cached in memory and refreshed a minute early." },
  { title: "Client credentials", text: "SF_CLIENT_ID, SF_CLIENT_SECRET, and SF_TOKEN_URL. A missing variable fails before any call. The secret is not logged." },
  { title: "Outbox pattern", text: "Accept the conversation first. Deliver later. States are Pending, Retrying, Synced, and Dead Letter." },
  { title: "Retries", text: "1, 2, 4, 8 seconds, capped at 60. A 429 uses Retry-After when Salesforce sends it." },
  { title: "Dead letter queue", text: "Attempt 5 of a retryable failure, the first validation error, or a rejected secret." },
  { title: "Idempotent upserts", text: "PATCH by Intake_Ref__c. Twenty conversations replay to twenty records, ten Leads and ten Cases." },
];

export function Integration() {
  return (
    <Section
      id="integration"
      index="07 — Integration architecture"
      title="The commit boundary is a Python outbox."
      lede="Standard library only. urllib, sqlite3, json. The retry matrix is the code path, not a slide that drifted from the client."
    >
        <ul className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2">
        {pillars.map((item) => (
          <li key={item.title} className={`bg-ink p-5 ${item.title === "Idempotent upserts" ? "sm:col-span-2" : ""}`}>
            <h3 className="font-display text-lg">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-mute">{item.text}</p>
          </li>
        ))}
      </ul>
      <h3 className="mb-4 mt-12 font-display text-2xl">Retry matrix</h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <caption className="sr-only">Retry matrix</caption>
          <thead className="text-xs uppercase tracking-[0.16em] text-mute">
            <tr>
              <th className="pb-3 pr-4 font-medium">Signal</th>
              <th className="pb-3 pr-4 font-medium">Action</th>
              <th className="pb-3 font-medium">Outbox result</th>
            </tr>
          </thead>
          <tbody>
            {retryMatrix.map((row) => (
              <tr key={row.signal} className="border-t border-white/10">
                <th className="py-3 pr-4 font-mono text-cyan">{row.signal}</th>
                <td className="py-3 pr-4">{row.action}</td>
                <td className="py-3 text-mute">{row.state}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
