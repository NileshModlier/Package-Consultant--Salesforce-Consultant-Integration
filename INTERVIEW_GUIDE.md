# Interview Guide

**150 questions for Salesforce consultant, integration, platform event, flow, and Apex REST interviews, answered from this project**

> **Evidence boundary.** Every "In this project" answer is grounded in the repository. The metadata is **source and not deployed**. The 22 Python tests ran **locally** against a stand-in. The Apex test and org tests T1–T23 have **not run**. D1–D5 are **proposed**. No LLM is called in this repository, and no MuleSoft component was built. Say this plainly in interviews. A candidate who states the boundary first is more credible than one who claims a go-live.

---

## How to use this guide

Each answer has two parts:

1. **The principle**: what a strong Salesforce answer says regardless of project.
2. **In this project**: the concrete evidence, with a file or document to point to.

Salesforce platform facts below were checked against Salesforce documentation where they matter to the design (API limit errors, event retention, assignment-rule header, trigger retries, scheduled-path cancellation). Limits and defaults change by release and edition, so confirm numbers in the target org before quoting them to a client.

| Section | Questions | Count |
| --- | --- | ---: |
| [A. Salesforce Consultant](#a-salesforce-consultant-q1q50) | Q1–Q50 | 50 |
| [B. Salesforce Integration](#b-salesforce-integration-q51q75) | Q51–Q75 | 25 |
| [C. Platform Events](#c-platform-events-q76q100) | Q76–Q100 | 25 |
| [D. Flows](#d-flows-q101q125) | Q101–Q125 | 25 |
| [E. Apex REST](#e-apex-rest-q126q150) | Q126–Q150 | 25 |
| **Total** | | **150** |

### The 60-second project pitch

> "Intake-to-Salesforce takes a conversation that an upstream AI intake agent has already summarized, and turns it into exactly one Lead or one Case. A Python worker writes through a durable SQLite outbox using OAuth client credentials and an external-id upsert, so replays never duplicate. Salesforce flows own the queue, the tasks, and the escalation clocks. A platform event published after commit sends status back, and an Apex REST resource covers gaps beyond the event bus's retention. Routing is deterministic: one phrase picks Lead or Case, and no model is called in the write path. It's built in source and tested locally with 22 tests and six fault drills. It hasn't been deployed to an org. The review found five org-side issues that must be fixed first: Salesforce's 403 API-limit error, sharing for the integration user, API access for the run-as user, the assignment-rule header, and scheduled-path cancellation."

---

## A. Salesforce Consultant (Q1–Q50)

### Q1. How do you start discovery for an intake-to-CRM project?

**Principle.** Start with the outcome and the people, not the objects. Map the current process lane by lane, collect real examples, list every decision the new process has to make, and name who owns each one. Separate what's known from what's assumed, and record open questions with an owner and a "blocks what" column.

**In this project.** M1 produced personas, 12 user stories, 34 business rules, an as-is map labelled as a baseline hypothesis, a to-be map, 13 assumptions, 16 open questions, and decisions D1–D6 before any metadata existed ([SOLUTION_DESIGN.md](SOLUTION_DESIGN.md)).

### Q2. How do you decide whether an inbound inquiry becomes a Lead, a Contact, or a Case?

**Principle.** A Lead is an unqualified prospect, a Contact is a known person at an Account, and a Case is a service request. The decision depends on intent (buying or needing help) and identity (is this person already known). Write it as a decision table so it's testable, not as a paragraph.

**In this project.** The designed policy has Lead rules L1–L9 and Case rules C1–C2 (D1, D3). The **built** router is simpler: `classify()` returns Lead for the phrase "sales inquiry", Case for "support request", and raises `RouteError` for both or neither. Contact matching is designed, not built.

### Q3. When would you recommend Person Accounts, and how would that change this design?

**Principle.** Person Accounts suit B2C businesses where the customer is an individual. Enabling them is effectively permanent and changes the data model, reports, and integrations, so it's a discovery question, not a build detail.

**In this project.** OQ-07 asks whether the org uses Person Accounts. If yes, D1 reopens: the choice becomes Lead versus Person Account instead of Lead versus Contact, and the Case linking rules change ([CONSULTANT_PLAYBOOK.md](CONSULTANT_PLAYBOOK.md) §3.3).

### Q4. Lead assignment rules or a record-triggered flow for routing: which would you pick?

**Principle.** Assignment rules are declarative and familiar to admins, but they only set the owner and only one rule can be active per object. A flow can assign, create follow-up work, and branch on more conditions. Pick one owner of routing, and make sure the other doesn't fight it.

**In this project.** Routing is in after-save flows that assign `Inbound_Sales` or `Support_Tier_1` by `DeveloperName` and create a task. One risk was found in review: the REST API applies the org's **active assignment rules by default** unless the request sends `Sforce-Auto-Assign: FALSE`, and the client doesn't send it (finding F26 in [PROJECT_COMPLETION_REPORT.md](PROJECT_COMPLETION_REPORT.md)).

### Q5. How do you prevent duplicate Leads?

**Principle.** Use layers: a stable key from the source system, normalization (trimmed, lowercased email), matching and duplicate rules for people entering data by hand, and a clear policy for what happens on a match (block, alert, or link).

**In this project.** Same-intake duplicates are prevented three ways: the outbox key, the unique external id `Intake_Ref__c`, and replay-id tracking ([IDEMPOTENCY.md](IDEMPOTENCY.md)). Duplicate *people* with different references aren't handled yet. D2 and BR-08 design exact-email matching, and the email isn't lowercased today (F6).

### Q6. What happens to custom fields when a Lead is converted?

**Principle.** Custom Lead fields carry over only if they're mapped to Contact, Account, or Opportunity fields in the Lead field mapping. Converted Leads become read-only for most purposes, so an integration that keeps updating them will fail.

**In this project.** `Intake_Ref__c` and `Intake_Summary__c` have no conversion mapping yet, and a late upsert to a converted Lead would dead-letter (F12, gap G6). The fix is a mapping to Contact or Opportunity fields, and treating "converted" as a terminal, successful outcome with a note.

### Q7. How do queues work, and why must these queues also support Task?

**Principle.** A queue is a Group of type Queue that can own records of the objects it's configured for. Members see and claim records from list views. If a flow creates a Task owned by the queue, Task has to be a supported object on that queue.

**In this project.** `Inbound_Sales` supports Lead and Task. `Support_Tier_1` supports Case and Task. The review task is owned by the queue, so any member can pick it up. Queue emails to members are off.

### Q8. How would you design SLA tracking for support intake?

**Principle.** Entitlements and milestones are the standard Service Cloud tool for contractual SLAs, with business hours, pause conditions, and violation actions. Scheduled paths or time-based tasks are lighter and fine for internal targets.

**In this project.** The Case flow uses scheduled paths: a 4-hour check for High priority Cases still New, and a 24-hour check for any intake Case still New. Each creates a High-priority Task. There are no entitlements. If the client has contractual SLAs, recommend Entitlements instead. Review finding F27 also flags that these scheduled paths may be cancelled by ordinary edits (Q104).

### Q9. How do you handle consent capture in Salesforce?

**Principle.** Store consent as structured data with its source, timestamp, and purpose, not as text. Salesforce's consent data model (Individual, Contact Point Type Consent, Data Use Purpose) supports this. Legal decides the lawful basis, and the consultant makes it recordable and reportable.

**In this project.** Consent is **designed, not built**. D3 and governed attributes GA-01 to GA-10 define what must be captured, and risk R8 rejects any build that stores consent in Description. OQ-02 (legal basis) blocks the Lead build until Legal answers.

### Q10. How do you write a decision a client will actually sign?

**Principle.** One decision per ID, stated as a choice: the options considered, the one recommended, consequences, the rules it creates, the owner, and an approval block with name and date. Avoid "we will use best practice".

**In this project.** D1–D6 follow that shape. D1–D5 are **proposed** and unsigned. D6 records implementation choices: `Intake_Ref__c` instead of `Intake_Id__c`, and the summary in its own field instead of Description.

### Q11. How do you present as-is and to-be process maps?

**Principle.** Use swimlanes per role, mark pain points on the as-is, and make the to-be traceable to rules. Label the as-is honestly: until you've validated it with the people who do the work, it's a hypothesis.

**In this project.** The as-is map is explicitly a baseline hypothesis (R7). The to-be map is backed by decision tables and walkthroughs A–H. The playbook's rule for the room is that the decision tables win over the picture.

### Q12. Sales wants every inquiry as a Lead, but Support wants known customers as Cases. How do you resolve it?

**Principle.** Make the conflict explicit, show the consequences of each option on real examples, and let the accountable owners decide. Your job is a clean decision, not a compromise that nobody owns.

**In this project.** Walkthroughs B and E (help from a known person, existing customer asking about pricing) test exactly that. The RACI makes the Sales Manager accountable for Lead definitions and the Support Lead for Case definitions. OQ-05 (known customer asking for pricing) is still open.

### Q13. How do you prioritize scope?

**Principle.** Slice by value and dependency, not by object. Put a thin end-to-end slice first so integration risk shows up early. Use MoSCoW or similar, and record what's explicitly out.

**In this project.** Milestones M1–M6 deliver policy, org configuration, integration, status sync, reliability, and handover in that order. The solution design lists exclusions such as Contact and Account creation, territories, and a second support queue.

### Q14. How do you write acceptance criteria for a user story?

**Principle.** Make them observable and testable, usually as Given/When/Then, including the failure case. Each criterion should map to a test.

**In this project.** US-01 to US-12 have acceptance criteria. US-10 AC4 (a corrected Dead Letter can be re-sent) can't be met today without manual SQL, which is gap G4. [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) maps every criterion to a test or marks it untested.

### Q15. What is a requirements traceability matrix, and why keep one?

**Principle.** It links each requirement to its design element, build artifact, and test. It shows coverage and makes scope arguments factual.

**In this project.** The matrix shows 34 business rules: 2 built and tested, 7 built, 11 partial, 3 upstream, and 11 not built. That table is the honest answer to "is it done?"

### Q16. How do you explain "designed versus built" to a client?

**Principle.** Use explicit status tags and never let a diagram imply something exists. Demos should show only what's built.

**In this project.** Every document uses five tags: Implemented, Tested locally, Designed, Not executed, Not built. [SOLUTION_DESIGN.md](SOLUTION_DESIGN.md) §10 compares designed with built row by row.

### Q17. What sharing questions do you ask in discovery?

**Principle.** Ask for the org-wide defaults per object, the role hierarchy, how queues are used, and how integration users see records. Sharing determines what every user and integration can see and update.

**In this project.** This was the biggest gap found in review (G2). After the flow assigns a record to a queue, the integration user no longer owns it. Under Private OWD, a replay upsert can't see it, tries an insert, and fails on the unique index. The recommended fix is a criteria-based sharing rule on `Intake_Ref__c` ([IDEMPOTENCY.md](IDEMPOTENCY.md) §6).

### Q18. Profiles, permission sets, and permission set groups: how do you use them?

**Principle.** Keep profiles minimal and grant access through permission sets, bundled into permission set groups by job. That's Salesforce's stated direction, and it makes least privilege auditable.

**In this project.** `Intake_Integration` grants Create, Read, and Edit on Lead and Case, field access, Read on the event, and access to the Apex class. It grants no Delete, View All, Modify All, or API Enabled.

### Q19. How do you set up an integration user?

**Principle.** Use a dedicated user, never a named person or an admin. Salesforce provides the Salesforce Integration user licence with the "Minimum Access – API Only Integrations" profile for API-only users, with permissions added through permission sets.

**In this project.** The run-as user for the External Client App needs API Enabled, which the permission set deliberately leaves out (F3). The recommendation is the integration licence and API-only profile, plus `Intake_Integration`.

### Q20. How do you design validation rules that don't break other channels?

**Principle.** Scope every rule with a condition that identifies the records it's meant for. Otherwise a rule written for one integration blocks manual entry, Web-to-Lead, or data loads.

**In this project.** All 10 rules start with "`Intake_Ref__c` is set". Org test T8 checks that an ordinary Lead saves without intake fields.

### Q21. Validation rule, flow, or Apex for data integrity?

**Principle.** Use validation rules for field-level and cross-field checks on one record. Use before-save flows for simple defaults and normalization. Use Apex when logic is complex, needs to query broadly, or must be unit tested in depth.

**In this project.** Validation rules enforce reference format and immutability, summary and channel presence, Qualification Reason on Not Converted, and Case Priority. Flows do routing. There are no Apex triggers.

### Q22. How do you map priority across Lead and Case?

**Principle.** Define one business priority scale and crosswalk it to each object's own picklist, so reports mean the same thing.

**In this project.** The design crosswalk maps P1–P4 to Lead Rating Hot, Hot, Warm, Cold and Case Priority High, High, Medium, Low. The **build** sets only Case Priority from High, Medium, or Low input, falling back to keywords ("urgent", "outage", "critical") or Medium. P1–P4 isn't built.

### Q23. Which fields should an integration never write?

**Principle.** Fields that another system or process owns. If Salesforce automation or people own a field, the integration writing it creates overwrites on every replay.

**In this project.** The payload never includes `OwnerId` or `Status`. Flows set the owner, and people move the status. `Intake_Ref__c` is in the URL, not the body.

### Q24. Why store the AI summary in a custom field rather than Description?

**Principle.** Description is often used by email-to-case, web forms, and other processes. A dedicated, labelled field makes the source clear, can have its own field-level security, and can be governed or purged separately.

**In this project.** D6 moved the summary to `Intake_Summary__c`. The workbook still shows Description, which is finding F17.

### Q25. How do you handle personal data in AI-generated summaries?

**Principle.** Assume summaries can contain anything the customer typed. Restrict who can read them, define retention, and screen for secrets before they're stored.

**In this project.** BR-34 requires that secrets aren't stored, but the detection method isn't designed (R3). Retention is open (OQ-03, OQ-16).

### Q26. How do you plan data retention and deletion?

**Principle.** Agree on retention per data class with Legal, then implement it as scheduled deletion or archiving, with an audit trail. Don't let the CRM become the default archive.

**In this project.** Retention is **designed as a decision** (D4) and remains open. Nothing in the build deletes or archives records.

### Q27. How do you run UAT for a CRM integration?

**Principle.** Use scripted scenarios written from the business's own examples, run by real users in a full or partial copy sandbox, with defects triaged daily against acceptance criteria.

**In this project.** Walkthroughs A–H become UAT scripts. Org tests T1–T23 cover configuration. None has been executed.

### Q28. What sandbox strategy would you use?

**Principle.** Developer sandboxes for build, a partial or full copy for integration and UAT with realistic data volumes and sharing, and production deployment through a controlled pipeline.

**In this project.** The playbook defines developer → partial/full → UAT → production. The External Client App and secrets are per environment.

### Q29. How do you plan go-live and rollback?

**Principle.** Make a checklist with owners, a cutover window, smoke tests, and a rollback that doesn't lose data.

**In this project.** The rollback stops the worker and subscriber (the outbox holds Pending rows), deactivates the flows if needed, and replays safely after the fix because upserts don't duplicate ([CONSULTANT_PLAYBOOK.md](CONSULTANT_PLAYBOOK.md) §6).

### Q30. How do you measure success without a baseline?

**Principle.** Capture the baseline first. Define each measure with its data source, and don't promise percentages until there's data.

**In this project.** Measures (rekey rate, duplicate Lead rate, time to first touch, escalation rate, urgent response, integration health) are defined, with "no baseline yet" stated.

### Q31. A sponsor says "skip discovery and just build it". What do you do?

**Principle.** Offer a thin build slice in parallel with a short discovery, and show which open questions would cause rework if guessed wrong.

**In this project.** Four open questions block go-live: consent basis, known-customer pricing path, Person Accounts, and live status values. Each has a concrete rework cost if guessed.

### Q32. How do you present a risk register?

**Principle.** For each risk, give likelihood, impact, owner, mitigation, and trigger. Review it at every gate, and add risks found in testing.

**In this project.** R1–R8 came from M1. R9 (403 API limit) and R10 (sharing) were added in this review.

### Q33. How do you manage open questions without blocking everything?

**Principle.** Tag each question with what it blocks. Build the slices that are unblocked, and hold the rest.

**In this project.** OQ-02 blocks the Lead consent build, and OQ-08 blocks flow deployment. The Python worker didn't depend on either.

### Q34. How do you explain AI's role to business stakeholders?

**Principle.** Be specific about what the model decides and what it doesn't. Stakeholders trust AI more when the boundaries are clear and the deterministic parts are auditable.

**In this project.** The model upstream may write the summary. Lead versus Case is a phrase match, and owner and status come from Salesforce. No model is called in this repository.

### Q35. When would you recommend MuleSoft for this?

**Principle.** When there are many systems to connect, reusable APIs are valuable, the client already has an Anypoint platform, or governance and monitoring need a central home.

**In this project.** One source and one target don't justify MuleSoft on their own. If the client already runs it, the same contract can move into an API-led design ([ARCHITECTURE.md](ARCHITECTURE.md) §8). **Nothing was built in MuleSoft.**

### Q36. How do you handle Lead and Case status values that differ between orgs?

**Principle.** Read the live picklists before building, and avoid hard-coding values in automation where you can. Use custom metadata or labels for values that vary.

**In this project.** The flows hard-code `Open - Not Contacted` and `New` (OQ-08). If those values were renamed, the flows deploy and the scheduled checks never match.

### Q37. Would you use record types here?

**Principle.** Use record types when processes, page layouts, or picklist values genuinely differ. Don't add them just to label a source.

**In this project.** None are used. `Intake_Channel__c` and `Intake_Ref__c` identify intake records without a separate process.

### Q38. How does this design compare with Web-to-Lead and Email-to-Case?

**Principle.** The native tools are quick to set up, but they offer limited classification, no external reference by default, and only basic deduplication.

**In this project.** The design adds a customer reference, deterministic routing, idempotent writes, and status sync back to the agent. The trade-off is code and operations that must be supported.

### Q39. How do you design escalation that respects ownership?

**Principle.** Escalate by creating visible work for the current owner or a manager, rather than silently changing fields.

**In this project.** Escalations are High-priority Tasks owned by the current owner. Status, Rating, and the reference are never rewritten.

### Q40. How do you handle a support request from someone you can't identify?

**Principle.** Don't guess. A wrong Contact link exposes one customer's case to another.

**In this project.** Cases carry `SuppliedEmail`, `SuppliedName`, and `SuppliedCompany`, and stay unlinked. The Support Lead owns unlinked identity in the RACI.

### Q41. How do you train users on a new intake process?

**Principle.** Train by role, with short sessions in a sandbox on the users' own scenarios, and quick-reference cards.

**In this project.** Reps learn the queue, review task, escalation, and Qualification Reason. Agents learn the urgent and standard tasks and unlinked Cases. Admins get a runbook walkthrough. These are planned, not delivered.

### Q42. Reps resist because they lose control over how leads arrive. How do you handle it?

**Principle.** Involve them early, show the time saved and the tasks they gain, and keep a feedback route after go-live.

**In this project.** The design keeps a human decision for ambiguous sales intake (Sales Manager in the RACI), and the review task tells reps exactly what to read.

### Q43. What reports and dashboards would you build?

**Principle.** Build reports that answer operational questions: what's waiting, what's late, and where it came from.

**In this project.** Queue age by owner, escalations by day, intake records by channel, and integration health from the monitor (dead letters, retries, subscriber errors). These are proposed, not built.

### Q44. How would you estimate this project?

**Principle.** Estimate by slice, with ranges, and show which uncertainties widen the range.

**In this project.** M2–M5 are small because the policy work was done in M1. The open questions (OQ-02, OQ-05, OQ-07, OQ-08) and the two review gaps are the main sources of variance.

### Q45. How do you write a statement-of-work boundary for AI features?

**Principle.** State what the AI does, what it doesn't do, who is accountable, and what isn't in scope (for example, model selection or prompt governance).

**In this project.** The boundary is: the upstream agent writes a summary, deterministic code routes, Salesforce owns owner and status, and no model is called in this repository.

### Q46. How do you deal with existing dirty data?

**Principle.** Keep cleansing separate from the new process, and make the new process refuse to guess on ambiguous matches.

**In this project.** R1 (many duplicate Contacts) is mitigated by leaving Cases unlinked rather than guessing. Cleanse is a separate project.

### Q47. What's your approach to documentation handover?

**Principle.** Hand over documents organized by reader (admin, integration, business), with runbooks that have been walked through, not just written.

**In this project.** The documentation map in [README.md](README.md) points each reader to their documents. The admin guide and integration guide are runbooks.

### Q48. How do you decide what to automate and what to leave manual?

**Principle.** Automate what is frequent, rule-based, and low-risk. Leave judgement calls with accountable people, and make them easy.

**In this project.** Lead versus Case is automated only when the phrase is unambiguous. Everything else is rejected for a person to handle (`RouteError`).

### Q49. A client asks, "Can the AI just assign the lead to the best rep?" How do you answer?

**Principle.** Separate the recommendation from the decision. A model can suggest, but routing rules should be explainable and owned.

**In this project.** Owner assignment is in Salesforce flows, not the agent. A recommendation field could be added later, but the flow would still decide.

### Q50. What would you do differently on this project?

**Principle.** Give an honest answer with specifics.

**In this project.** Ask about sharing and API limits in the first workshop. Both gaps found in review were org settings. And build the Dead Letter re-queue command with the outbox, not after it.

---

## B. Salesforce Integration (Q51–Q75)

### Q51. Which Salesforce integration patterns does this project use?

**Principle.** Salesforce's integration patterns include Remote Process Invocation (request and reply, or fire and forget), Batch Data Synchronization, Remote Call-In, UI Update Based on Data Changes, and Data Virtualization. Name the pattern for each direction separately.

**In this project.** Writes are **Remote Call-In**: an external worker calls the REST API. Status return is event-driven, close to **fire and forget** from Salesforce's side: a platform event is published after commit and an external subscriber reads it. Catch-up is a small **batch synchronization** through Apex REST.

### Q52. Why use an external-id upsert instead of query-then-insert?

**Principle.** Query-then-insert has a race between the query and the insert, costs two API calls, and needs the caller to see the record. An upsert on a unique external id is one call, and the database enforces uniqueness.

**In this project.** `PATCH /services/data/v62.0/sobjects/{Lead|Case}/Intake_Ref__c/{ref}`. `Intake_Ref__c` is unique, case-insensitive, and an external id. Note that the upsert still has to *see* the existing record to update it, which is the sharing dependency in Q17.

### Q53. Why the sObject REST API rather than Composite or Bulk?

**Principle.** Use sObject REST for single records in near real time. Composite batches related calls into one round trip. Bulk API 2.0 suits large asynchronous loads.

**In this project.** One intake creates one record, so sObject REST fits. At high volume (OQ-13 is open), the Composite API's sObject Collections could upsert many records in one call.

### Q54. Explain the OAuth 2.0 client credentials flow. When would you use JWT bearer instead?

**Principle.** Client credentials exchanges a client id and secret for a token that acts as a configured run-as user. There's no browser and no refresh token. JWT bearer signs an assertion with a private key, so there's no shared secret, and it can act as different users.

**In this project.** `sf_auth.py` posts `grant_type=client_credentials` and caches the token until 60 seconds before expiry. JWT bearer is a reasonable upgrade if the client's security policy prefers certificates to secrets.

### Q55. What is an External Client App, and how is it different from a Connected App?

**Principle.** External Client Apps are Salesforce's newer framework for apps that integrate through OAuth. They separate the app's settings from the org's policies and are designed to be packaged and deployed more cleanly. Connected Apps are the long-standing equivalent.

**In this project.** The design uses an External Client App with client credentials enabled and a run-as user. It hasn't been created in an org. The setup steps are in [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md).

### Q56. Why does the run-as user matter in client credentials?

**Principle.** Every API call runs as that user. Its profile, permission sets, and sharing decide what the integration can see and do, and it appears in audit fields like CreatedBy.

**In this project.** The run-as user needs API Enabled (F3), the `Intake_Integration` permission set, and visibility of queue-owned intake records (G2).

### Q57. How do you store and rotate the client secret?

**Principle.** Keep it in a secrets manager, never in source or logs. Rotate on a schedule and on staff changes, with an overlap window if the platform allows two valid secrets.

**In this project.** The worker reads `SF_CLIENT_ID` and `SF_CLIENT_SECRET` from the environment. Drill 1 shows that a wrong secret dead-letters on the first attempt without calling the record API.

### Q58. How do you handle token expiry?

**Principle.** Cache the token, refresh before expiry where the lifetime is known, and on a 401 refresh once and retry once. A second 401 means a real authorization problem.

**In this project.** The token is cached until expiry minus 60 seconds. Salesforce token responses don't necessarily include `expires_in`, so the code defaults to 3,600 seconds, while the real lifetime comes from the org's session settings (F15). The 401 path is therefore the real safeguard: refresh once, retry once (`test_expired_token_refreshes_once`), and dead-letter a second 401 (`test_second_401_is_dead_letter`).

### Q59. What is the outbox pattern, and why use it here?

**Principle.** The producer records each message in a durable store before delivery. A separate worker delivers and records the outcome. The message survives crashes and network failures, and delivery can be retried safely.

**In this project.** `accept_conversation` writes a row to SQLite keyed by `(intake_ref, object_api_name)`, with canonical JSON. `OutboxWorker.run_once` delivers ready rows, with states Pending, Retrying, Synced, and Dead Letter.

### Q60. What's the difference between a durable outbox and a transactional outbox?

**Principle.** A transactional outbox writes the business state and the outbox row in one database transaction, so they can't disagree. A durable outbox only guarantees that once a row is written, it isn't lost.

**In this project.** It's a durable outbox. The agent's state lives upstream, so a crash between the agent's decision and `accept_conversation` loses the hand-off unless the agent resends. Resending is safe because of the outbox key ([IDEMPOTENCY.md](IDEMPOTENCY.md) §2.3).

### Q61. How do you decide which errors to retry?

**Principle.** Retry transient failures (network, timeouts, 5xx, throttling) with backoff. Don't retry permanent failures (validation, authorization, not found), because they fail the same way every time.

**In this project.** `retry_matrix.py` has 7 signals: 401 (refresh the token once), 408 (retry), 429 (back off), 5xx (retry), 400 validation and other 4xx (Dead Letter), network failure (retry), and wrong client secret (Dead Letter). 2xx is success. Backoff is 1, 2, 4, 8 seconds, capped at 60, with Dead Letter at attempt 5.

### Q62. Why is a 400 dead-lettered immediately?

**Principle.** A 400 usually means the payload breaks a rule. Retrying the same payload burns API calls and delays the alert.

**In this project.** Drill 3 shows one attempt and one PATCH, then Dead Letter. The exception is a transient condition inside a 4xx body, such as `UNABLE_TO_LOCK_ROW`, which should be retried (G3).

### Q63. How does Salesforce signal that the org's API limit is exceeded, and what does your design do?

**Principle.** The REST API returns **HTTP 403 with `errorCode: REQUEST_LIMIT_EXCEEDED`** when the org's API request limit is exceeded. A client should parse the error body, pause, and alert, not treat it as an authorization failure.

**In this project.** This is the top review finding (G1, F1). The matrix maps 403 to Dead Letter, so a real limit event would dead-letter the whole queue. The fault drill simulates 429 with `Retry-After`, which proves the back-off path for gateways that send 429 but not Salesforce's limit behaviour. Proposed drill 5b covers it ([FAULT_DRILLS.md](FAULT_DRILLS.md)).

### Q64. How do you implement backoff with `Retry-After`?

**Principle.** Use the server's hint when present, otherwise exponential backoff with a cap and ideally jitter. Cap the hint too, so a bad header can't park work forever.

**In this project.** `Retry-After` is honoured exactly (drill 5: held until `12:00:30Z`), without a ceiling (G7). Otherwise it's `min(60, 2**(attempts-1))` seconds. There's no jitter, which matters little with one worker.

### Q65. What is a dead letter, and how should operators handle one?

**Principle.** A dead letter is a message that can't be delivered without a change. It needs visibility, a reason, an owner, and a supported way to fix and resend.

**In this project.** Dead Letter rows keep `last_error`, and `monitor.py` lists them. Re-queuing needs manual SQL today, and a changed payload doesn't reopen a Dead Letter row (G4). The runbook is in [ERROR_HANDLING.md](ERROR_HANDLING.md).

### Q66. How do you guarantee idempotency end to end?

**Principle.** Give every unit of work a stable business key and enforce it at every boundary: producer, transport, target, and the return path.

**In this project.** Three layers: the outbox key, the Salesforce external id, and the replay-id seen set. The duplicate submission drill shows one row and one record, and the replay sends nothing.

### Q67. What happens if two workers run at once?

**Principle.** Workers need a claim step (an atomic status change or a lease) so they don't pick the same row.

**In this project.** There's no claim (F21). Two workers could send the same row twice. The upsert makes that harmless to data, but attempt counts could be wrong. Run one worker, or add `UPDATE … RETURNING` claiming.

### Q68. How would you design this on MuleSoft?

**Principle.** API-led connectivity: a System API over Salesforce, a Process API for routing and orchestration, and an Experience API for the consumer. Use Anypoint MQ with a dead-letter queue for durable delivery, and Object Store for idempotency keys.

**In this project.** This is a design option in [ARCHITECTURE.md](ARCHITECTURE.md) §8. The System API would wrap the upsert, the Process API would hold `classify()` and the retry matrix, and a subscriber flow would replace the CometD client. **Nothing was built in MuleSoft.**

### Q69. MuleSoft or custom code: how do you decide?

**Principle.** Weigh the number of systems, reuse, the client's existing skills and licences, operational tooling, and cost. Custom code is cheaper to start, and a platform is cheaper to run at scale.

**In this project.** With one source, one target, and no existing platform assumed, standard-library Python is enough. The contract (external id, event, catch-up) is platform-neutral, so it can move.

### Q70. How do you secure an integration like this?

**Principle.** Least privilege for the integration user, secrets in a vault, TLS everywhere, narrow data exposure, and audit.

**In this project.** No Delete, View All, or Modify All. The event carries 4 fields. The catch-up endpoint returns 4 fields of intake records only. The one deliberate widening is `without sharing` on the catch-up class (F10, Q129).

### Q71. How do you monitor this integration?

**Principle.** Monitor both sides: queue depth, retries, dead letters, and subscriber lag on the client, and API usage and event allocations in Salesforce. Alert on thresholds, not just dashboards.

**In this project.** `monitor.py` prints outbox counts, retry attempts, dead letters, the replay cursor, and the last subscriber error. There's no alerting (G8).

### Q72. What responses can an upsert return?

**Principle.** 201 when a record is created, 200 or 204 when an existing record is updated (depending on API version), 300 when the external id matches more than one record, 400 for validation errors, and 404 when the object or field isn't found or isn't accessible.

**In this project.** `sf_client.py` accepts 200, 201, and 204. Uniqueness means a 300 can't happen. A 404 could mean the field isn't visible to the integration user, which the smoke test should rule out.

### Q73. Why doesn't the payload include Status or OwnerId? Is that enough to protect the owner?

**Principle.** Leaving fields out of the payload protects them from the integration, but other automation can still change them.

**In this project.** Leaving them out stops replays from undoing a rep's work. But the REST API defaults `Sforce-Auto-Assign` to TRUE, so an org with an **active Lead or Case assignment rule** would run it on the integration's creates and updates (F26). The flow's assignment would win on insert, but a changed-payload update could reassign a worked record. The fix is to send `Sforce-Auto-Assign: FALSE`.

### Q74. How do you test an integration without an org?

**Principle.** Use a contract-faithful stand-in for the target, inject failures, and be explicit that it proves your client logic, not the platform's behaviour.

**In this project.** A `ThreadingHTTPServer` imitates the token endpoint and the upsert. Scripted CometD sources and a closed port cover the rest. The stand-in returned 429 where Salesforce would return 403, which is exactly the kind of gap a stand-in can hide.

### Q75. How do you version an integration contract?

**Principle.** Pin the API version, version custom endpoints, and document the payload. Change versions deliberately, with regression tests.

**In this project.** The REST path pins `v62.0` and CometD uses `/cometd/62.0`. The Apex endpoint is `/intake/status` with no version segment, so adding `/v1/` is recommended before external consumers depend on it.

---

## C. Platform Events (Q76–Q100)

### Q76. What is a platform event, and how is it different from an sObject?

**Principle.** A platform event is a message on Salesforce's event bus, defined like an object (API name ending `__e`) but not stored as a record. It can't be queried with SOQL, updated, or deleted. Publishers fire it, and subscribers receive it in near real time.

**In this project.** `Intake_Status__e` carries four fields (`Intake_Ref__c`, `Object_Type__c`, `Status__c`, `Owner_Name__c`) from Salesforce to the intake agent's subscriber ([PLATFORM_EVENTS.md](PLATFORM_EVENTS.md)).

### Q77. Why a custom platform event rather than Change Data Capture?

**Principle.** CDC publishes changes for every record of a selected object, with the changed fields. That's great for replication but too broad when a consumer needs a few fields for a subset of records. A custom event lets you control the payload and when it fires.

**In this project.** The agent needs status and owner for intake records only. CDC on Lead and Case would also stream every non-intake record and every field change.

### Q78. What's the difference between high-volume and standard-volume events?

**Principle.** High-volume events are built for scale, with longer retention and asynchronous publishing, and they're the type for new definitions. Standard-volume is the legacy type.

**In this project.** `Intake_Status__e` is `HighVolume`, so events are retained for 72 hours for replay.

### Q79. Publish After Commit or Publish Immediately?

**Principle.** Publish After Commit sends the event only if the transaction commits, which is right for state changes others act on. Publish Immediately sends even if the transaction later rolls back, which suits logging and telemetry.

**In this project.** Publish After Commit. If a validation rule or a flow Custom Error rolls back the save, the agent never hears about a status that doesn't exist.

### Q80. What is a replay id, and how do you use it?

**Principle.** Each event on a channel gets a replay id. A subscriber stores the last id it processed and resubscribes from it. `-1` means new events only, and `-2` means all retained events. Replay ids increase but aren't guaranteed to be contiguous.

**In this project.** `StatusStore` keeps `replay_cursor` and `seen_replay` in SQLite. `apply_event` writes the status row, the seen id, and the new cursor in one commit.

### Q81. What happens when the replay id is older than the retention window?

**Principle.** The subscription is rejected because the event is no longer available. The subscriber needs a recovery path that reads current state from another source, then resumes from new events.

**In this project.** On an expired replay, `StatusSubscriber` calls the Apex REST catch-up, applies the snapshots, marks "resume new", and subscribes with `-1`. Review gaps P1 (only known refs are asked for) and P2 (the window between the snapshot and the new subscription) are documented with fixes.

### Q82. How do you subscribe from outside Salesforce?

**Principle.** Use the Pub/Sub API (gRPC over HTTP/2, Avro payloads, flow control) or the older CometD-based Streaming API. Inside Salesforce, use Apex triggers, flows, or `lightning/empApi` in components.

**In this project.** `SalesforceEventSource` implements the CometD cycle (handshake, subscribe with the replay extension, connect, disconnect) against `/cometd/62.0` with standard-library HTTP.

### Q83. CometD or the Pub/Sub API?

**Principle.** The Pub/Sub API is Salesforce's current recommended API for external publishing and subscribing. It gives explicit flow control and efficient binary payloads. CometD still works, and it's simpler with no gRPC dependency.

**In this project.** CometD was chosen to stay within the standard library. Migrating to the Pub/Sub API behind the same `take(channel, replay_from)` interface is gap P5.

### Q84. How do you handle duplicate event delivery?

**Principle.** Delivery is at least once, so make the consumer idempotent with a seen set keyed on replay id, or by applying state with "latest wins" semantics.

**In this project.** `seen_replay` has a primary key on `(channel, replay_id)`. `test_duplicate_replay_id_is_applied_once` and `test_restart_from_sqlite_skips_events_already_seen` cover it. The seen set is never pruned (P6).

### Q85. Is event ordering guaranteed?

**Principle.** Within one channel, events are delivered in replay-id order. Don't rely on ordering across channels or between different publishers' transactions.

**In this project.** There's one channel. The subscriber applies events in replay order, and the latest event wins per `(intake_ref, object_type)`.

### Q86. What are the ways to publish a platform event?

**Principle.** A flow's Create Records element, Apex `EventBus.publish`, the REST or SOAP API (insert on the event object), and the Pub/Sub API's publish call.

**In this project.** Two record-triggered flows, `Lead_Status_Publisher` and `Case_Status_Publisher`, use Create Records at trigger order 20.

### Q87. What permissions do publishers and subscribers need?

**Principle.** Publishing through the API needs Create on the event. Subscribing needs Read. Flows that run in system context can publish without the running user holding Create.

**In this project.** `Intake_Integration` grants Read only, so the integration user can subscribe but can't publish fake statuses. The flows publish in system context.

### Q88. Why does a new intake record publish more than one event?

**Principle.** An after-save flow that updates the triggering record starts another save, and other automation can see that change.

**In this project.** On insert, the publisher fires for `ISNEW()`. The assignment flow then sets `OwnerId` to the queue, which meets the publisher's `ISCHANGED(OwnerId)` condition, so a second event names the queue. The expected count is about two per create, which org test T18 should confirm (F13).

### Q89. How do you plan event allocations?

**Principle.** Estimate events per business transaction and per day, then check against the org's hourly publishing and daily delivery allocations, which depend on edition and add-ons. Delivery counts multiply by the number of subscribers.

**In this project.** About 1–2 events per create plus one per status or owner change, times one subscriber. Volumes are open (OQ-13), so the numbers aren't sized yet.

### Q90. How do Apex platform event triggers differ from record triggers?

**Principle.** They run asynchronously after the event is published, by default as the Automated Process user, in batches. Only after-insert is supported. They can resume from a checkpoint with `setResumeCheckpoint`, and they can throw `EventBus.RetryableException` to retry the batch. Salesforce allows up to 9 retries, after which the trigger moves to an error state.

**In this project.** There's no Apex subscriber. The subscriber is external. An Apex trigger would be the choice if Salesforce itself needed to react to the event.

### Q91. What happens if your subscriber is down?

**Principle.** Events stay on the bus for the retention period. A subscriber that comes back within that window resumes from its stored replay id.

**In this project.** Drill 6 injects "connection refused" with the cursor at 3. The run is deferred, the cursor stays at 3, and the error is stored. The next run resumes from 3 and applies replay 4 (`Working - Contacted`).

### Q92. How would you recover after an outage longer than the retention window?

**Principle.** Read current state from a query or API, apply it, then subscribe to new events. Close the gap between the snapshot and the subscription.

**In this project.** The catch-up resource returns status by `refs` or `since`. The review recommends three fixes: a second catch-up by `since` so new references are learned (P1), a `since` sweep after subscribing (P2), and ordering with a continuation cursor (P3).

### Q93. Can you query or roll back a platform event?

**Principle.** No. Events can't be queried with SOQL or deleted, and a published event can't be recalled. Publish After Commit is how you avoid publishing something that later rolls back.

**In this project.** That's why the catch-up reads Lead and Case, not the event, and why the event is Publish After Commit.

### Q94. What belongs in an event payload?

**Principle.** The minimum a subscriber needs to act, with a stable key. Avoid personal data and large text. A subscriber that needs more can call back with the key.

**In this project.** Four fields, with the owner's display name as the only personal data. No email address and no summary.

### Q95. How do you test platform events in Apex?

**Principle.** In a test, events published inside `Test.startTest()` are delivered at `Test.stopTest()`, or explicitly with `Test.getEventBus().deliver()`. Then assert on what the subscriber did.

**In this project.** The publishers are flows, and the subscriber is Python, so no Apex test covers the event. Org test T18 counts events per create. A flow test or a small Apex test that inserts an intake Lead and asserts the event could be added.

### Q96. How do you monitor event usage?

**Principle.** Use the platform event allocation and usage information in Setup, and the `PlatformEventUsageMetric` object, to track publishing and delivery against allocations.

**In this project.** Not set up. It's an item for hypercare once volumes exist.

### Q97. How do platform events work with flows?

**Principle.** Flows can publish events (Create Records), and platform event–triggered flows can subscribe to them. That gives a fully declarative publish-subscribe option.

**In this project.** Flows publish. Nothing in Salesforce subscribes, because the consumer is external.

### Q98. Why send the owner's name instead of the owner's Id?

**Principle.** Shape the payload for the consumer. An external system can't resolve a Salesforce Id without another API call and the permission to make it.

**In this project.** The agent can tell the customer "Support Tier 1 has your request" without a lookup. The flow resolves User first, then Group, otherwise blank.

### Q99. How would you scale to more consumers?

**Principle.** Each subscriber consumes delivery allocation. For many consumers, relay events to an external bus (Salesforce Event Relay supports Amazon EventBridge) or fan out through middleware.

**In this project.** One consumer today. A second consumer would be a design change, and MuleSoft or Event Relay are the options to consider.

### Q100. What are the risks of using platform events for status sync?

**Principle.** At-least-once delivery, finite retention, allocations, and the need for a recovery path. Design the consumer to be idempotent and to catch up.

**In this project.** Seven gaps are recorded (P1–P7), covering catch-up completeness, the snapshot window, truncation, test coverage, CometD versus Pub/Sub, seen-set growth, and unmeasured event counts.

---

## D. Flows (Q101–Q125)

### Q101. Before-save or after-save record-triggered flow: how do you choose?

**Principle.** Before-save flows update fields on the triggering record cheaply, without another DML. After-save flows can create or update other records, publish events, and use the saved record's Id. Use before-save for field defaults and normalization, and after-save for everything else.

**In this project.** All four flows are after-save, because they create Tasks, update `OwnerId` with a queue they've looked up, and publish an event ([FLOW_DESIGN.md](FLOW_DESIGN.md)).

### Q102. Why use a formula entry condition with `ISNEW()` and `ISCHANGED()`?

**Principle.** Entry conditions decide which saves start the flow. Without a change-based guard, every edit reruns the flow and duplicates its work.

**In this project.** Assignment runs only when the record is new or `Intake_Ref__c` changed, so a replayed upsert or an ordinary edit doesn't create a second review task. Publishers run on new, Status change, or Owner change.

### Q103. How does trigger order work between flows?

**Principle.** For record-triggered flows on the same object and timing, the Trigger Order value sets the sequence. Ties and flows without a value follow platform rules, so check the effective order in Flow Trigger Explorer rather than assuming it.

**In this project.** Assignment flows use 10 and publishers use 20, so the publisher runs after the queue assignment.

### Q104. How do scheduled paths work, and what's the catch in this design?

**Principle.** A scheduled path runs a branch at a time relative to a date field or the trigger time, asynchronously. Salesforce documents that if a later update makes the record **stop meeting the entry conditions**, pending scheduled paths are **cancelled**.

**In this project.** The scheduled paths sit in flows whose entry formula is `ISNEW() OR ISCHANGED(Intake_Ref__c)`. On any later save, that formula is false. So the 24-hour escalation and the 4- and 24-hour Case checks are at risk of being cancelled by the first ordinary edit, possibly including the flow's own owner update. This is finding F27. It's unverified, because no org has run the flows. The fix is to move the scheduled paths into a separate flow whose condition stays true for the record's life (`Intake_Ref__c` is not blank, run only when updated to meet the condition), and to add org test T22.

### Q105. Why are there no fault paths, and when would you add them?

**Principle.** Without a fault path, an unhandled flow error rolls back the whole transaction. That's sometimes the right strictness. A fault path can log and continue, or show a clearer message.

**In this project.** The choice is strict: if a task can't be created, the record isn't saved and the outbox dead-letters with the flow error (G9). That's acceptable for a small flow, and fault paths that log to an error object are the alternative.

### Q106. How do you assign to a queue in a flow without hard-coding Ids?

**Principle.** Look up the Group by `DeveloperName` and `Type = 'Queue'`, check that it was found, then use its Id. Ids differ between orgs, and labels can be renamed.

**In this project.** `Get_Inbound_Sales_Queue` and its Case equivalent do exactly that, then check `Queue_Found`.

### Q107. What does a flow Custom Error do?

**Principle.** The Custom Error element stops the save and shows a message on the page or a field, rolling back the transaction, just like a validation rule. It works in record-triggered flows.

**In this project.** If the queue isn't found, the flow raises "The Inbound Sales queue is not available…", the save rolls back, and the REST upsert returns 400 with that message. Org test T20 covers it.

### Q108. Flow or Apex trigger: how do you choose?

**Principle.** Use flows for declarative logic admins can maintain. Use Apex for complex logic, heavy data volumes, reusable services, or deep unit testing. Avoid mixing both on the same object without a clear order.

**In this project.** There are no Apex triggers. The logic is a lookup, an update, a task, a decision, and a publish, which suits flows well.

### Q109. How are flows bulkified?

**Principle.** Record-triggered flows run per record, but the platform batches their DML and queries across the records in one transaction. You still avoid queries and DML inside loops, because those don't batch.

**In this project.** No loops. Each interview does one Get Records, one update, and one create, which the platform batches during bulk upserts.

### Q110. How do you avoid recursion in record-triggered flows?

**Principle.** An after-save flow that updates its own record starts another save, which can rerun flows. Change-based entry conditions stop the rerun.

**In this project.** The assignment flow updates `OwnerId`. On the second save, the reference hasn't changed, so assignment doesn't rerun, but the publisher does, by design.

### Q111. How do you test flows?

**Principle.** Flow Builder's debug and flow tests for paths, Apex tests that insert records and assert outcomes for regression and deployment coverage, and scripted sandbox tests for scheduled paths.

**In this project.** Org tests T1–T23 are written and **not executed**. T13–T16 require shortened offsets on a sandbox copy. No flow tests or Apex tests cover the flows yet.

### Q112. How do you deploy flows safely?

**Principle.** Deploy through the metadata API with versioning. Know how the target org treats active flows on deploy, and verify activation afterwards. Never shorten production time offsets for testing.

**In this project.** The flows are active in source. The deployment command is in [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md). Check that they're active in the target org after deploy.

### Q113. How does the order of execution affect this design?

**Principle.** Before-save flows run before before-triggers, then validation rules, then the save, after-triggers, assignment rules, and later after-save flows. All of it commits together or not at all.

**In this project.** Validation rules reject bad intake data before any flow runs. An active assignment rule (if one exists and the API header isn't set to FALSE) runs before the after-save flow, which then overwrites the owner (F26).

### Q114. Where would a before-save flow help here?

**Principle.** For cheap normalization on the same record.

**In this project.** Lowercasing `Email` on intake Leads (F6) is a good candidate, although fixing it at the producer is better, because the outbox comparison uses the payload.

### Q115. Why create Tasks for escalation instead of updating fields?

**Principle.** Tasks are visible work with an owner and a due date, and they appear in activity history. Field flags are easy to miss and can confuse reporting.

**In this project.** Escalation and monitoring tasks are High priority for the current owner, which may be a queue. Status, Rating, and the reference are never rewritten.

### Q116. How do you make status values configurable?

**Principle.** Use custom metadata types or custom labels for values that vary by org, and read them in the flow.

**In this project.** `Open - Not Contacted` and `New` are literals (OQ-08). Custom metadata is the recommended change.

### Q117. What are platform event–triggered flows, and would you use one here?

**Principle.** They start when a specific platform event is received, running asynchronously as the Automated Process user. They're the declarative alternative to an Apex event trigger.

**In this project.** Not needed, because the consumer is external. One could be used for in-org reactions, for example logging Dead Letter notifications if they were published as events.

### Q118. What is `$Record__Prior`, and how does it compare with `ISCHANGED()`?

**Principle.** `$Record__Prior` holds the record's values before the update, so a flow can compare any field. `ISCHANGED()` answers the same question in a formula. `$Record__Prior` isn't available in scheduled paths.

**In this project.** Entry formulas use `ISCHANGED()`. The scheduled paths check current values (`Status`, `Priority`) only.

### Q119. What happens if a Lead is converted while its escalation is pending?

**Principle.** Converted Leads have a converted status, so a status check in the scheduled path stops the escalation.

**In this project.** `Still_Unworked` requires `Open - Not Contacted`, so a converted Lead doesn't escalate. With F27 the path may already have been cancelled anyway.

### Q120. Who does a scheduled path run as?

**Principle.** Scheduled paths run in system context. Salesforce documents that the running user for the path's actions is the user who originally changed the record.

**In this project.** That would be the integration user for inserts. Tasks it creates are owned by `$Record.OwnerId`, so ownership is correct regardless.

### Q121. How do you document a flow for admins?

**Principle.** An inventory (object, trigger, order, entry condition), a diagram, an element table, the test plan, and known limitations.

**In this project.** [FLOW_DESIGN.md](FLOW_DESIGN.md) has all of these. The SVG diagrams in the repository are drawn from the metadata, not captured in Flow Builder.

### Q122. What governor limits apply to flows?

**Principle.** Record-triggered flows share the transaction's limits with Apex: SOQL queries, DML statements, rows, and CPU time. Bulk loads multiply each interview's consumption.

**In this project.** A new intake record uses a handful of queries (the queue lookup, plus owner lookups in each publisher run) and a few DML operations (the owner update, the task, and the events). That's small per record, but it should be measured for bulk upserts.

### Q123. How would you reduce duplication between the two publisher flows?

**Principle.** Move shared logic into an autolaunched subflow that record-triggered flows call, passing the values in.

**In this project.** Both publishers resolve the owner name the same way. A subflow taking `OwnerId`, the reference, status, and object type would remove the duplication.

### Q124. How would you migrate old Workflow Rules or Process Builder automation into this design?

**Principle.** Salesforce has ended support for Workflow Rules and Process Builder and provides the Migrate to Flow tool. Migrate object by object, consolidating into a few flows per object with explicit trigger order.

**In this project.** A discovery item: existing automation on Lead and Case must be inventoried so it doesn't conflict with the intake flows.

### Q125. What would you improve in these flows before go-live?

**Principle.** Fix correctness risks first, then maintainability.

**In this project.** Split the scheduled paths into a flow with a stable condition (F27), move status values to custom metadata, add a decision on fault paths, add a subflow for owner names, and map `Intake_Ref__c` on Lead conversion (F12).

---

## E. Apex REST (Q126–Q150)

### Q126. What is Apex REST, and when do you build one instead of using the standard REST API?

**Principle.** Apex REST exposes a custom endpoint under `/services/apexrest/` with your own logic and response shape. Build one when the standard API can't do the job in one call, needs visibility the caller doesn't have, or would expose more data than you want.

**In this project.** `IntakeStatusResource` returns status for Leads and Cases in one call, shaped as four fields, even when the integration user doesn't own the records.

### Q127. Walk me through `IntakeStatusResource`.

**Principle.** Describe the contract first, then the implementation.

**In this project.** `GET /services/apexrest/intake/status?refs=…&since=…`. It parses `refs` (comma-separated, at most 200) and `since` (ISO-8601 UTC). It returns 400 if neither is given, if there are more than 200 refs, or if `since` is malformed. It queries Leads, then Cases, each `LIMIT 200`, and returns a JSON array of `{intakeRef, objectType, status, ownerName}`.

### Q128. Why are the class and method `global`?

**Principle.** Apex REST requires the class and its HTTP methods to be `global`, because they're called from outside the namespace.

**In this project.** `global without sharing class IntakeStatusResource` with `@HttpGet global static void recover()`.

### Q129. Why `without sharing`, and what's the risk?

**Principle.** `without sharing` ignores record-level sharing for the class's queries. It's a deliberate widening, so it needs a narrow scope and a documented reason.

**In this project.** After queue assignment, the integration user doesn't own the records, so a sharing-respecting query could return nothing. The scope is narrow: only records with `Intake_Ref__c`, and only four fields. The risk is that field-level security isn't enforced either (F10). If a sharing rule is added for G2, the class could switch to `with sharing` and user-mode queries.

### Q130. What's the difference between `with sharing`, `without sharing`, and `inherited sharing`?

**Principle.** `with sharing` enforces the running user's record access. `without sharing` ignores it. `inherited sharing` uses the caller's mode, and runs as `with sharing` when it's an entry point. None of them enforces object or field permissions.

**In this project.** `without sharing` is explicit. An entry-point class with `inherited sharing` would behave as `with sharing`, which would break the catch-up under Private sharing.

### Q131. How do you enforce object and field permissions in Apex?

**Principle.** Use user-mode database operations (`WITH USER_MODE` in SOQL, `AccessLevel.USER_MODE` in Database methods) or `Security.stripInaccessible`. `WITH SECURITY_ENFORCED` is the older option.

**In this project.** Not enforced. The integration user has Read on the four fields through `Intake_Integration`, so user mode would work for fields. Record visibility is the real problem (Q129).

### Q132. How do you read parameters and set the response?

**Principle.** Use `RestContext.request` for `params`, headers, and `requestBody`, and `RestContext.response` for `statusCode`, headers, and `responseBody` as a `Blob`.

**In this project.** `RestContext.request.params.get('since')` and `get('refs')`. The response sets `Content-Type: application/json`, a status code, and `Blob.valueOf(JSON.serialize(items))`.

### Q133. Should a method return an object or `void` with a response body?

**Principle.** Returning a value lets Apex serialize it with a 200 status. `void` with `RestContext.response` gives full control of status codes and error bodies.

**In this project.** `void`, so validation failures return 400 with `{"error": "…"}` instead of an exception.

### Q134. How do you handle errors in Apex REST?

**Principle.** Validate input and return a 4xx with a clear body for caller errors. Catch expected exceptions. An unhandled exception returns a 500 with Salesforce's error format, which callers should treat as retryable only if it's transient.

**In this project.** A `TypeException` from a bad `since` becomes 400. Other exceptions, such as a query exception, would surface as 500, which the Python catch-up treats as `CatchUpError` and defers.

### Q135. How does the endpoint validate the `since` timestamp?

**Principle.** Parse strictly, accept a documented format, and reject anything else with a 400.

**In this project.** `parseSince` replaces `T` with a space, drops a trailing `Z` and any fractional seconds, then calls `Datetime.valueOfGmt`. So `2026-11-24T12:00:00Z` works. A value with an offset like `+05:30` fails parsing and returns 400, which should be documented in the contract.

### Q136. What governor limits apply to an Apex REST request?

**Principle.** Synchronous transaction limits, including 100 SOQL queries, 50,000 rows retrieved, 10 seconds of CPU, and 6 MB of heap. The request also counts against the org's API request limit.

**In this project.** Two queries and at most 400 rows, which is far below the limits.

### Q137. Why `LIMIT 200`, and what's wrong with it?

**Principle.** A hard limit protects the endpoint, but without ordering and a continuation token, the caller can't tell it was truncated or fetch the rest.

**In this project.** Both queries have `LIMIT 200` with no `ORDER BY` and no cursor (P3, F9). After a large outage, a `since` catch-up could silently miss records.

### Q138. How would you add pagination?

**Principle.** Use keyset pagination: order by a stable key, return the last key, and let the caller ask for "after this key". Avoid `OFFSET`, which is capped and slow.

**In this project.** `ORDER BY LastModifiedDate, Id`, with a response that includes `nextSince` and `lastId`. The Python catch-up would loop until no continuation is returned.

### Q139. How do you test Apex REST?

**Principle.** Build `RestRequest` and `RestResponse`, set `requestURI`, `httpMethod`, and `params`, assign them to `RestContext`, call the method, and assert on `statusCode` and the parsed body. Production deployment needs at least 75% org-wide coverage.

**In this project.** `IntakeStatusResourceTest` does this in two methods. It has **not been run**, so coverage isn't measured.

### Q140. What does the test class cover, and what's missing?

**Principle.** Cover each branch and the boundaries, including invalid input.

**In this project.** Covered: refs returning a Lead and a Case, a future `since` returning nothing, and no filter returning 400. Missing: combined `refs` and `since`, more than 200 refs, a malformed `since`, and a blank owner (P4).

### Q141. How does authentication work for Apex REST?

**Principle.** The same as the standard API: an OAuth access token in the `Authorization: Bearer` header. The user needs API access, and Apex class access through a profile or permission set.

**In this project.** The worker uses its client-credentials token. `Intake_Integration` grants access to `IntakeStatusResource`.

### Q142. Do Apex REST calls count against API limits?

**Principle.** Yes. Each inbound Apex REST call counts as an API request.

**In this project.** Catch-up calls are rare (only after an expired replay), so they barely register. Upserts are the main consumer.

### Q143. How would you version an Apex REST endpoint?

**Principle.** Put the version in the URL mapping (for example `/v1/intake/status`) and keep old versions while callers migrate. A breaking change becomes a new class or mapping.

**In this project.** There's no version segment yet. Adding `/v1/` before any external consumer depends on the endpoint is recommended.

### Q144. Which HTTP methods would you support here?

**Principle.** Only what the use case needs. Each additional method widens the attack surface and the test burden.

**In this project.** Only `GET`, because writes go through the standard upsert. An Apex write endpoint is one option if sharing can't be fixed declaratively ([IDEMPOTENCY.md](IDEMPOTENCY.md) §6).

### Q145. If you built an Apex REST write endpoint, how would you design it?

**Principle.** Make it idempotent on the business key, validate the input, run in an explicit sharing mode with a reason, return structured errors, and log.

**In this project.** A `PATCH /v1/intake/{ref}` that upserts by `Intake_Ref__c` `without sharing`, never touches Owner or Status, and maps errors to the same retry matrix. It's not built, and the recommended fix is still a sharing rule.

### Q146. How do you design the JSON response?

**Principle.** Use a stable, documented shape with consistent names and types. Serialize from a small inner class, not from sObjects, so internal field names don't leak.

**In this project.** A private inner class `Item` with `intakeRef`, `objectType`, `status`, and `ownerName`. A missing owner name becomes an empty string, not null.

### Q147. How does `Owner.Name` work when the owner can be a user or a queue?

**Principle.** `OwnerId` on Lead and Case is polymorphic (User or Group). `Owner.Name` resolves through the polymorphic relationship for both.

**In this project.** SOQL `Owner.Name` covers both in one query. The flows need two lookups (User, then Group), because Get Records works on one object at a time.

### Q148. What would a security reviewer ask about this endpoint?

**Principle.** Who can call it, what data it exposes, whether sharing and field security are bypassed and why, and whether input is bounded.

**In this project.** Callers need class access through `Intake_Integration`. It exposes four fields of intake records. Sharing is bypassed by design, and field-level security isn't enforced. Input is bounded at 200 refs.

### Q149. Why not just run SOQL through the REST query endpoint for catch-up?

**Principle.** `/query` runs with the caller's sharing and returns raw sObject JSON. It's fine when the caller can see the records.

**In this project.** Under Private sharing, the integration user can't see queue-owned records, so `/query` would return nothing. Apex REST also returns both objects in one call and shapes the output.

### Q150. What would you change in `IntakeStatusResource` before production?

**Principle.** Close correctness gaps first, then security and operability.

**In this project.** Add `ORDER BY` and a continuation cursor (P3), add tests for every branch and measure coverage (P4), version the URL, document the accepted `since` format, and revisit `without sharing` once the sharing rule for G2 exists.

---

## Quick reference: numbers to quote accurately

| Fact | Value | Status |
| --- | --- | --- |
| Sample conversations | 20 (10 Lead, 10 Case) | Tested locally |
| Field-mapping rows | 27 (L-01–09, C-01–09, CS-01–09) | Designed. Build matches 4 fully |
| Validation rules | 10 (5 Lead, 5 Case) | Implemented, not executed |
| Flows | 4 (2 assignment, 2 publishers) | Implemented, not executed |
| Platform event | 1, with 4 fields | Implemented, not executed in an org |
| Retry signals | 7 | Tested locally |
| Python tests | 22 | Passed locally, 24 November 2026 |
| Fault drills | 6 | Passed locally |
| Apex test methods | 2 | Not executed |
| Orgs deployed | 0 | n/a |
| LLM calls in this repository | 0 | n/a |

## Answers to avoid

| Don't say | Say instead |
| --- | --- |
| "We went live" or "in production" | "Built in source and tested locally. Not deployed." |
| "The AI routes Leads and Cases" | "A deterministic phrase match routes. The upstream agent writes the summary." |
| "It uses a transactional outbox" | "A durable SQLite outbox. The agent's state is upstream." |
| "We handled API limits" | "We handled 429. Salesforce sends 403 `REQUEST_LIMIT_EXCEEDED`, and that's a known gap." |
| "Built on MuleSoft" | "Designed so the contract could move to MuleSoft. Nothing was built there." |
| "100% coverage" or any coverage number | "The Apex test hasn't run, so coverage isn't measured." |
