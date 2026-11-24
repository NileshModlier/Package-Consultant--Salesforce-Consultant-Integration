export const author = {
  name: "Nilesh P Raghavan",
  linkedin: "https://www.linkedin.com/in/nilesh-raghavan-b67615166",
  role: "Salesforce integration case study",
};

export const metrics = [
  { name: "Stories", value: 12, note: "User stories US-01 through US-12" },
  { name: "Mappings", value: 27, note: "Lead, Contact, and Case rows in the workbook" },
  { name: "Flows", value: 4, note: "Two assignment flows and two status publishers" },
  { name: "Leads", value: 10, note: "Sample conversations routed to Lead" },
  { name: "Cases", value: 10, note: "Sample conversations routed to Case" },
  { name: "Events", value: 1, note: "One platform event, four fields" },
  { name: "Retries", value: 7, note: "Signals in the retry matrix" },
  { name: "Tests", value: 22, note: "Python tests, local stand-in, 24 Nov 2026" },
] as const;

export const highlights = [
  "Sales Cloud",
  "Service Cloud",
  "Flows",
  "Platform Events",
  "Apex REST",
  "Python Integration",
  "External Client Apps",
] as const;

export const beforePath = [
  { title: "AI receptionist", text: "A conversation arrives with a name, a company, and an ask." },
  { title: "Sales inquiry or support request", text: "The two intents need different objects. Mixing them creates the wrong record." },
  { title: "Manual processing", text: "Someone rekeys a partial story from a shared inbox into Salesforce." },
  { title: "Slow handoffs", text: "Sales and support wait on each other because the request has no reference." },
  { title: "Lost leads", text: "The same person becomes a second Lead, or the request never leaves the mailbox." },
  { title: "Poor customer experience", text: "The customer cannot quote an id, and neither can the person who calls them back." },
] as const;

export const afterPath = [
  { title: "Salesforce automation", text: "The commit is a PATCH on Intake_Ref__c. A replay updates the same record." },
  { title: "Lead routing", text: "A sales inquiry becomes one Lead, owned by the Inbound Sales queue." },
  { title: "Case management", text: "A support request becomes one Case, owned by Support Tier 1." },
  { title: "Status synchronization", text: "The status event publishes after commit. The subscriber stores the replay id." },
] as const;

export const architectureSteps = [
  {
    id: "customer",
    title: "Customer",
    file: "The conversation",
    text: "The customer supplies the words, the identity, and whether sales may make contact. The agent does not invent them.",
  },
  {
    id: "agent",
    title: "AI intake agent",
    file: "Policy in docs/solution-design.md",
    text: "The agent normalizes the submission and assigns a reference shaped INT-YYYYMMDD-####. In this package the route is deterministic.",
  },
  {
    id: "qualify",
    title: "Qualification rules",
    file: "integration/outbox.py",
    text: "The sample worker looks for the phrase “sales inquiry” or “support request”, and not both. Anything else is a route error and is not stored.",
  },
  {
    id: "outbox",
    title: "Outbox pattern",
    file: "integration/outbox.py",
    text: "Pending, Retrying, Synced, Dead Letter. The unique key is the intake reference plus the object. Salesforce can be down without losing the conversation.",
  },
  {
    id: "api",
    title: "Salesforce API",
    file: "integration/sf_client.py",
    text: "Client credentials, then PATCH /sobjects/{Lead|Case}/Intake_Ref__c/{value}. Status and OwnerId are omitted so a replay cannot pull the record off its queue.",
  },
  {
    id: "clouds",
    title: "Sales Cloud and Service Cloud",
    file: "Lead and Case",
    text: "Ten sample conversations become Leads. Ten become Cases. The same reference may exist once on each object, never twice on one object.",
  },
  {
    id: "flows",
    title: "Flows",
    file: "force-app/main/default/flows",
    text: "Assignment flows run at trigger order 10. A missing queue rolls the save back. Tasks carry the follow-up. Scheduled paths escalate only by creating another task.",
  },
  {
    id: "events",
    title: "Platform events",
    file: "Intake_Status__e",
    text: "Publishers run at order 20, including after the owner changes, so the event names the queue. Publish After Commit means a rolled-back save emits nothing.",
  },
  {
    id: "sync",
    title: "Agent synchronization",
    file: "integration/subscriber.py",
    text: "One batch, stored replay id, duplicate replay ids ignored. An expired cursor is rebuilt from the Apex REST catch-up, then the subscriber continues with new events.",
  },
] as const;

export const deliverables = [
  { title: "Requirements", detail: "Twelve stories. Each has acceptance criteria, business value, and failure conditions." },
  { title: "User stories", detail: "Customer, sales representative, support agent, sales manager, support lead, and the intake agent." },
  { title: "Process maps", detail: "Swimlanes for the path from conversation to Lead or Case." },
  { title: "As-is diagram", detail: "A baseline hypothesis of the mailbox. It is not a workshop transcript." },
  { title: "To-be diagram", detail: "Lead rules L1–L9 and Case rules C1–C2. These are the route." },
  { title: "Field mapping sheet", detail: "27 rows across Lead, Contact, and Case. The workbook still shows the M1 name Intake_Id__c. The built field is Intake_Ref__c." },
  { title: "Solution design", detail: "Context, scope, assumptions, open questions, and decisions D1–D6. D1–D5 are still proposed." },
] as const;

export const salesPoints = [
  { title: "Lead creation", text: "A sales inquiry with a name, company, and email becomes one Lead. First name is sent only when the name has two parts." },
  { title: "Lead assignment", text: "Lead Intake Handling sets the owner to the Inbound Sales queue. If that queue is missing, the save rolls back." },
  { title: "Follow-up tasks", text: "A review task is created for the queue. Twenty-four hours later, if status is still Open - Not Contacted, a high escalation task is created. Status is not changed." },
  { title: "Lead qualification", text: "Qualification Reason is required only when an intake Lead is Closed - Not Converted. People qualify. The worker does not." },
  { title: "External ID upserts", text: "PATCH on Intake_Ref__c. The second call updates the same Lead. The reference cannot be changed or cleared once it is stored." },
] as const;

export const servicePoints = [
  { title: "Case creation", text: "A support request becomes one Case. Subject, priority, summary, channel, and the supplied contact fields are written. Status and OwnerId are not." },
  { title: "Contact matching", text: "Policy matches email exactly. One Contact sets ContactId. Zero or several leave it empty. The sample worker does not query Contact. It routes the twenty conversations by phrase." },
  { title: "Queue assignment", text: "High and standard cases share Support Tier 1. Priority changes the task and the clock, not the queue." },
  { title: "First response tracking", text: "High priority creates an urgent task. Any other priority creates a normal response task. Tasks use WhatId and do not require a Contact." },
  { title: "Case escalation", text: "At four hours, a High case still in New gets another task. At twenty-four hours, any intake case still in New gets a task. A case that has left New gets neither." },
] as const;

export const configuration = [
  { kind: "Custom fields", items: "Lead: Intake Ref, Intake Summary, Intake Channel, Qualification Reason. Case: Intake Ref, Intake Summary, Intake Channel. Event: reference, object type, status, owner name." },
  { kind: "Queues", items: "Inbound Sales and Support Tier 1. Both can own tasks." },
  { kind: "Permission set", items: "Intake Integration creates, reads, and edits Lead and Case, reads the event, and can call the catch-up class. It cannot delete, view all, or modify all." },
  { kind: "Flows", items: "Lead Intake Handling and Case Intake Handling at order 10. Lead Status Publisher and Case Status Publisher at order 20." },
  { kind: "Validation rules", items: "Ten rules. Format and immutability of the reference. Summary and channel required when the reference is set. Qualification Reason on a closed-lost intake Lead. Priority on an intake Case." },
] as const;

export const retryMatrix = [
  { signal: "401", action: "Refresh the token once", state: "Unchanged if the new token works. A second 401 is Dead Letter." },
  { signal: "408", action: "Retry", state: "Retrying, then Dead Letter on attempt 5." },
  { signal: "429", action: "Backoff", state: "Wait for Retry-After. Otherwise the same schedule as 408." },
  { signal: "5xx", action: "Retry", state: "Same schedule as 408." },
  { signal: "400", action: "Dead Letter", state: "Immediate. Other 4xx except 401 and 408 follow this rule." },
  { signal: "Network", action: "Retry", state: "Same schedule as 408. No HTTP status was received." },
  { signal: "Wrong secret", action: "Dead Letter", state: "The token endpoint rejects the secret. There is no token to refresh." },
] as const;

export const eventSteps = [
  { title: "Status change", text: "Create, status change, or owner change on a record that already has an intake reference." },
  { title: "Publish after commit", text: "High-volume Intake_Status__e. A rolled-back save, including a missing queue, emits nothing." },
  { title: "Replay IDs", text: "The subscriber stores the last applied id and ignores a second delivery of that id." },
  { title: "Event recovery", text: "An expired id calls GET /services/apexrest/intake/status, then the next read takes new events only." },
  { title: "Apex REST catch-up", text: "IntakeStatusResource is without sharing, because the integration user no longer owns the record after queue assignment. At most 200 references." },
] as const;

export const assistantPoints = [
  { title: "Deterministic state machine", text: "One phrase selects Lead. The other selects Case. Both, or neither, raises RouteError. The row is not stored." },
  { title: "LLM summary generation", text: "Not on the write path. Intake_Summary__c stores the conversation summary. A model is not called to invent the summary, the route, the owner, or the status." },
  { title: "No autonomous decisions", text: "A hold does not age into a create. The policy refuses Link, Update, Create, or Reject by timeout." },
  { title: "Human workflow control", text: "Flows assign the queue and the task. People change status. The upsert omits Status and OwnerId so a replay cannot take that control back." },
] as const;

export const drills = [
  { name: "Wrong secret", result: "Dead Letter, 1 token call, 0 PATCH calls." },
  { name: "Network failure", result: "Retrying, then Synced, 1 record." },
  { name: "Validation failure", result: "Dead Letter after 1 PATCH. The next pass processed nothing." },
  { name: "Duplicate submission", result: "1 outbox row, 1 Salesforce record, replay processed 0." },
  { name: "Expired token", result: "One 401 refreshes the token and syncs. A second 401 is Dead Letter." },
  { name: "Dead letter", result: "Attempt 5 of a retryable error, or the first 400, stops the row." },
  { name: "API limit", result: "429 with Retry-After 30 seconds held the row until 12:00:30 UTC, then Synced." },
  { name: "Subscriber down", result: "Cursor stayed at 3. The next run applied Working - Contacted at replay 4." },
  { name: "Duplicate events", result: "The same replay id is applied once. A restart from SQLite skips ids already seen." },
  { name: "Platform event recovery", result: "An expired replay id uses the Apex catch-up, then continues with new events." },
] as const;

export const interviewTopics = [
  {
    title: "External IDs",
    answer:
      "Intake_Ref__c is a unique external id on Lead and on Case. The client PATCHes that field, so the second call updates the first record. The same reference may exist once on each object. A second Lead or a second Case with that reference is rejected. The field is not required, so records created outside intake still save.",
  },
  {
    title: "Idempotency",
    answer:
      "The outbox unique key is the intake reference plus the object. An unchanged Synced conversation processes zero rows. A changed payload returns the row to Pending and updates the same Salesforce record. An identical replay after Dead Letter stays Dead Letter.",
  },
  {
    title: "Platform Events",
    answer:
      "Intake_Status__e carries the reference, Lead or Case, the status, and the owner name. It is high volume and publishes after commit. The subscriber stores the replay id. A duplicate id is ignored. An expired id is recovered from the Apex REST class, which is without sharing because the user lost the record to the queue.",
  },
  {
    title: "Flows vs Apex",
    answer:
      "Assignment and publish are flows, so the handover stays in one automation tool. Flows run at orders 10 and 20. Apex is only the catch-up read. There is no trigger. The Apex test class is in source and has not been executed, because the package has not been deployed.",
  },
  {
    title: "OAuth client credentials",
    answer:
      "An External Client App uses the client credentials grant and a run-as integration user. The id, secret, and token URL come from the environment. The token stays in memory and is refreshed 60 seconds early. A wrong secret is Dead Letter. There is no token to refresh. The app is not in the metadata, so the secret is not in the repository.",
  },
  {
    title: "Outbox pattern",
    answer:
      "The conversation is stored before the HTTP call. States are Pending, Retrying, Synced, and Dead Letter. 408, 429, 5xx, and network failures retry on 1, 2, 4, and 8 seconds, capped at 60, and stop at attempt 5. A 429 honors Retry-After. A 400 and a rejected secret are Dead Letter immediately. The monitor reads once. It does not poll.",
  },
] as const;

export const lessons = [
  {
    title: "Consulting discovery",
    text: "The as-is map is a hypothesis until a workshop confirms it. I wrote the failure conditions before I wrote a field, so a saved record could still be the wrong outcome.",
  },
  {
    title: "Process design",
    text: "Lead and Case needed separate decision tables. One overloaded route was willing to update a Lead when a Contact also matched. Splitting L1–L9 from C1–C2 removed that.",
  },
  {
    title: "Salesforce architecture",
    text: "The external id is per object, the reference is immutable, and the queue assignment is a flow that can roll the save back. Those three choices are what make replay safe.",
  },
  {
    title: "Integration design",
    text: "The upsert omits Status and OwnerId. The integration user loses the record on purpose. Catch-up is without sharing and returns four fields, not the Case.",
  },
  {
    title: "Reliability engineering",
    text: "A recovered 401 should not increment the outbox. A second 401 should stop. A down subscriber should keep its cursor. Each of those is a test, not a slide.",
  },
  {
    title: "Enterprise CRM",
    text: "Go-live still depends on the org’s real status values. If Open - Not Contacted or New was renamed, the flows deploy and the scheduled paths do not fire. That question is still open.",
  },
] as const;

export const demoBeats = [
  { time: "0:00", show: "The boundary", say: "Twenty conversations, ten Leads, ten Cases, one platform event, seven retry signals, twenty-two local tests. The metadata has not been deployed. The policy decisions are still proposed." },
  { time: "0:40", show: "Two conversations", say: "A transcript that says sales inquiry becomes a Lead. A transcript that says support request becomes a Case." },
  { time: "1:20", show: "The outbox key", say: "Intake reference plus object. Accepting the same conversation twice leaves one row. The call is a PATCH on Intake_Ref__c." },
  { time: "2:00", show: "What the payload leaves out", say: "Status and OwnerId stay off the request. The flow owns assignment. A replay cannot take the record off the queue." },
  { time: "2:40", show: "The two flows", say: "Inbound Sales and Support Tier 1. A missing queue rolls the save back. Escalation is a task, not a status change." },
  { time: "3:20", show: "The event", say: "Intake_Status__e publishes after commit. The subscriber stores the replay id and ignores a duplicate." },
  { time: "4:00", show: "The drills", say: "A 400 is Dead Letter on the first attempt. A 429 waits for Retry-After. A refused connection stays Retrying, then syncs. A down subscriber keeps its cursor." },
  { time: "4:40", show: "What is still open", say: "Deploy is the manifest. Go-live still depends on the org’s real Lead and Case status values." },
] as const;
