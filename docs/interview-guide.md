# Interview guide

| | |
|---|---|
| Project | Intake-to-Salesforce CRM Integration |
| Phase | M6 — Handover |
| Document | 50 Salesforce questions, 25 integration questions, 25 consultant questions |
| Version | 0.1 |
| Date | 24 November 2026 |
| Related | [Solution design](solution-design.md), [Architecture](architecture.md), [Demo script](demo-script.md) |

Answer from this package. When the honest answer is that a step was not deployed or not decided, say that. The counts you can defend are in the README.

## Salesforce

### S1. Why does a net-new sales request become a Lead?
A Lead holds an unknown commercial contact, including Company, which a Contact does not require in the same way. A person the org already knows is not written as another Lead.

### S2. Why is support always a Case?
Service work is a Case whether or not the person is already a Contact. The Case can be linked when email matches exactly one Contact, and it can still be created when it matches none or several.

### S3. What is an external id used for here?
`Intake_Ref__c` is an external id on Lead and on Case. The client PATCHes `/sobjects/{Lead|Case}/Intake_Ref__c/{value}` so Salesforce inserts or updates that one record.

### S4. Why PATCH instead of a POST insert?
POST would create another record on replay. PATCH on the external id makes the second call an update of the first record.

### S5. Can the same intake reference exist twice?
It can exist once on a Lead and once on a Case. Uniqueness is per field. A second Lead or a second Case with that reference fails the unique constraint.

### S6. Why is Intake Ref not a required field?
Leads and Cases created outside intake must still save. Validation requires the reference format, summary, and channel only when a reference is present.

### S7. What shape is the reference?
`INT-YYYYMMDD-####`, 17 characters. The field is Text(40) so the format rule, not the field length, is the business constraint.

### S8. Is the unique external id case-sensitive?
No. The metadata sets case sensitivity off. Callers still send the canonical uppercase form.

### S9. Why use validation rules instead of making Summary required on the field?
A field-level required flag would block ordinary Leads and Cases. The rule fires only when Intake Ref is set.

### S10. What does the immutable rule protect?
Once Intake Ref is stored, a user or a replay cannot change it or clear it. History stays attached to the same reference.

### S11. What are the channel values?
A restricted picklist: Web, Email, Chat, Phone. Any other value fails before the record is saved.

### S12. Where does the conversation summary go?
`Intake_Summary__c`, long text, 5,000 characters, on Lead and on Case. Description remains available for later notes. Decision D6 records that split.

### S13. When is Qualification Reason required?
Only on a Lead that has an intake reference and is moved to Closed - Not Converted. Other statuses do not require it. The M1 picklist was not built. The field is long text.

### S14. When is Case Priority required?
When the Case has an intake reference. The worker sends High, Medium, or Low.

### S15. Which queues exist?
Inbound Sales for Leads. Support Tier 1 for Cases. Both can own Tasks, because the flows assign tasks to those queues.

### S16. Why is there one Case queue rather than an urgent queue and a standard queue?
Priority changes the task and the monitoring clock. It does not change the queue. A second queue without an agreed topic list would be another place for work to stall.

### S17. What happens if the queue is missing?
The flow raises a custom error and the save rolls back. The record is not left with the integration user.

### S18. How are tasks attached?
The Lead review task uses WhoId. The Case tasks use WhatId. A Case task does not require a Contact.

### S19. Why are the flows after-save?
They assign an owner and create tasks from the saved record. The status event is also after save, and the event itself publishes after commit.

### S20. When does the assignment flow start?
Intake Ref is not blank, and the record is new or the reference changed. A later status edit does not create a second review task.

### S21. Why do the publishers use a later trigger order?
Assignment flows are order 10. Publishers are order 20. The owner update from the queue assignment is a separate save, and that save is what publishes the queue name.

### S22. What do the scheduled paths do?
Lead: 24 hours after CreatedDate, if Status is still Open - Not Contacted, create a High escalation task. Case: at 4 hours, if Priority is High and Status is still New, create an outstanding-response task. At 24 hours, if Status is still New, create another task.

### S23. What breaks if the org renamed those statuses?
The flows still deploy. The scheduled paths do not match, so they do not fire. Confirming the live values is open question OQ-08.

### S24. Why is escalation a task rather than a status change?
The business record of "nobody worked this" should not overwrite the status a person set, and it should not look like the intake agent reopened the record.

### S25. Why a platform event instead of Change Data Capture?
The return path needs four fields, not a full record change stream. `Intake_Status__e` is the contract. CDC would publish changes the intake agent did not ask to store.

### S26. What does Publish After Commit change?
A save that rolls back, including a missing queue, does not emit the event. The subscriber never sees a status for a record that does not exist.

### S27. Why is the event high volume?
High-volume events keep a replay id. The subscriber uses that id to resume and to ignore a duplicate delivery.

### S28. What is a replay id?
The position of one event on the channel. The subscriber stores the last applied id in SQLite and requests events after it on the next run.

### S29. What is on the event?
`Intake_Ref__c`, `Object_Type__c`, `Status__c`, and `Owner_Name__c`.

### S30. Why publish when the owner changes?
The first save still shows the creating user. The flow then moves the record to the queue. Publishing the owner change is how the event names Inbound Sales or Support Tier 1.

### S31. How is the owner name resolved?
The publisher gets the User with that OwnerId. If the owner is a queue, it gets the Group and uses the queue name. If neither is found, the name is blank and the event still publishes.

### S32. What is the Apex REST class for?
`IntakeStatusResource` is the catch-up read at `/services/apexrest/intake/status`. The subscriber calls it when Salesforce no longer has the stored replay id.

### S33. Why is the class `without sharing`?
The integration user loses ownership when the flow assigns the queue, and the permission set does not grant view all. With sharing, catch-up would return an empty list for records the user can no longer see.

### S34. What limits the catch-up query?
At most 200 references. The SOQL uses LIMIT 200. The caller passes `refs`, `since`, or both. `since` is an ISO-8601 UTC datetime.

### S35. What can the integration permission set do?
Create, read, and edit Lead and Case. Read the platform event. Call `IntakeStatusResource`. It cannot delete, view all, modify all, or publish the event.

### S36. Why withhold view all and modify all?
The user should write the intake fields and then lose day-to-day ownership to the queue. Broad visibility would hide a sharing mistake and is more access than the integration needs.

### S37. Which field permissions matter?
The set includes the intake fields plus the standard fields the upsert writes, such as Lead Email, Name, Company, and Case Priority, Origin, and the Supplied fields. It does not grant view-all fields.

### S38. Which OAuth flow is specified?
Client credentials on an External Client App, with a run-as user. The Python client posts `grant_type=client_credentials` as a form body.

### S39. Why is the connected app absent from the repository?
The consumer secret would have to live with the metadata or be recreated in each org. The admin guide tells the administrator to create the app and pass the id, secret, and token URL in the environment.

### S40. Who should the run-as user be?
The integration user who has `Intake_Integration`. A system administrator would hide missing permissions.

### S41. Which API version is the project on?
62.0, in `sfdx-project.json`, the package manifest, and the Apex class metadata.

### S42. How is the metadata deployed?
`sf project deploy start --manifest manifest/package.xml`, after the CLI is authenticated. This repository has not been deployed.

### S43. What does the manifest include?
Two Apex classes, the platform event and its fields, seven Lead and Case fields, ten validation rules, two queues, one permission set, and four flows.

### S44. Why were Salesforce duplicate rules not the idempotency control?
Duplicate rules are fuzzy and org-specific. The idempotency key is the intake reference, which the caller already has and can send again.

### S45. Why does the upsert omit Status and OwnerId?
The flows own assignment, and people own later status. Sending either field on replay would put the record back to its create-time value.

### S46. How does intake priority relate to Salesforce priority?
Policy maps P1 and P2 to Lead Rating Hot and Case Priority High, P3 to Warm and Medium, and P4 to Cold and Low. The sample worker sends the Case priority directly and does not write Lead Rating.

### S47. What governor-limit concern does the catch-up class have?
It queries Lead and Case with a fixed LIMIT 200 and returns a small JSON list. It does not loop unpublished events inside Apex. The subscriber is the component that pages by replay id.

### S48. Why publish from a flow instead of an Apex trigger?
The assignment behavior is already a flow. A second automation tool for the same save would split the handover. The flow creates the event row. No trigger is in the package.

### S49. Has the Apex test run?
`IntakeStatusResourceTest` is in source. It has not been executed, because the package has not been deployed. Say that before describing the assertions.

### S50. What would you run in an org on the first day?
Deploy the manifest, run the Apex test, assign the permission set, create the External Client App, send one Lead conversation and one Case conversation, replay both, change a status, and confirm one event and one catch-up row. Compare status values with OQ-08 before trusting the scheduled paths.

## Integration

### I1. Why use an outbox?
The intake agent can accept a conversation even when Salesforce is unavailable. The worker retries from a durable row instead of holding the conversation in memory.

### I2. What are the outbox states?
Pending, Retrying, Synced, and Dead Letter.

### I3. What makes a delivery idempotent?
The database unique key is intake reference plus object. The HTTP call is a PATCH on that same reference. Replaying an unchanged Synced conversation processes zero rows.

### I4. What if the payload changes for a reference that already synced?
The row returns to Pending, the attempt count resets, and the next run updates the same Salesforce record.

### I5. What if the same payload is replayed after Dead Letter?
The row stays Dead Letter. An identical failure is not sent again. A changed payload can be queued again.

### I6. What happens on HTTP 401 from the API?
The client drops the cached token, requests a new one, and retries the PATCH once. If that call succeeds, the outbox attempt count stays unchanged.

### I7. What happens on a second 401?
The client does not refresh again. The worker dead-letters the row. The drill recorded two token calls and two PATCH calls.

### I8. What happens on HTTP 408?
The row becomes Retrying and follows the exponential schedule.

### I9. What happens on HTTP 429?
The row becomes Retrying and waits for the `Retry-After` value when Salesforce sends one. The API-limit drill waited until 30 seconds past the hour, then synced.

### I10. What happens on HTTP 5xx?
Same path as 408. The integration test covered 503 together with 408 and 429, then one successful upsert.

### I11. What happens on HTTP 400?
Dead Letter on the first attempt. The validation drill used `Priority is required`, made one PATCH, and the next pass processed nothing.

### I12. What happens when the network fails?
The client raises a network error, which is retryable. The drill pointed the token URL at a closed port, left the row Retrying, then synced it through a live stand-in.

### I13. What happens when the client secret is wrong?
The token endpoint returns 401 and the row is Dead Letter. The drill made one token call and zero PATCH calls. There is no access token to refresh.

### I14. When does retrying stop?
On attempt 5. Attempts 1 through 4 wait. Attempt 5 is Dead Letter for a retryable error.

### I15. What is the wait schedule?
1, 2, 4, and 8 seconds, capped at 60, unless a 429 header replaces it.

### I16. How are duplicate events ignored?
The subscriber stores each applied replay id. A second delivery of that id does not change the status row and is counted as a duplicate.

### I17. How does a restarted subscriber resume?
The cursor is in SQLite. A new process opens the same file and asks for events after the stored replay id.

### I18. What if Salesforce has expired the replay id?
The subscriber calls the catch-up endpoint for known references, or for the last 24 hours when it knows none, marks the cursor to continue with new events, and reads once more from replay id -1.

### I19. What if the subscriber is down?
The cursor is not moved. The error is stored. The next run requests events after the same id. The drill kept cursor 3, then applied replay id 4.

### I20. Does the monitor poll?
No. `python -m integration.monitor` prints one snapshot of queue counts, retry attempts, dead letters, status rows, the replay cursor, and the last subscriber error.

### I21. Where is the access token stored?
In memory, on the auth object, refreshed 60 seconds before expiry. It is not written to SQLite and not printed.

### I22. Where does the secret come from?
`SF_CLIENT_SECRET`, with `SF_CLIENT_ID` and `SF_TOKEN_URL`. A missing variable fails before any HTTP call.

### I23. How does classification work in the sample worker?
The lowercased transcript must contain "sales inquiry" or "support request", and not both. Anything else raises a route error and is not stored.

### I24. Which libraries does the Python package use?
The standard library: `urllib`, `sqlite3`, and `json`. Tests use `unittest`. The field-mapping workbook was built with openpyxl, which is not required to run the sync.

### I25. What would you add before a production cutover?
An org deploy, the Apex test, a secret store outside the shell environment, a scheduler for the worker, and a check that the org's status values match the flows. Those are not in this package. The package stops at a one-shot worker, a one-shot subscriber, and a one-shot monitor.

## Consultant

### C1. Is the as-is process a finding from the client?
No. It is a baseline hypothesis for a workshop. Say that before you describe the mailbox.

### C2. Why write the decision log before the flows?
The build should not invent Lead versus Contact, consent, or routing while configuring fields. M1 stopped before metadata. M2 configured only the names M1 had framed.

### C3. What belongs in a decision log entry?
The decision, the options considered, why the others were set aside, the consequence, the business rules, and the owner. Status stays Proposed until the client accepts it.

### C4. Which Lead-versus-Contact options were set aside?
Always creating a Lead inflates the funnel with support traffic and existing customers. Never using a Lead puts unqualified strangers on Contact and drops Company. The selected split is Lead for net-new sales, Case for service, and a Sales Manager hold when the person is already a Contact.

### C5. How is sales consent treated?
Opt-in. Silence is not consent. The sample worker does not yet store a consent field. That is a policy rule, not an implemented attribute.

### C6. What happens to a known Contact who asks for a demo?
The commercial portion is held for the Sales Manager. Intake does not create a Lead, an Opportunity, or a second Contact. If the same conversation is also support, the Case can still be written.

### C7. Why does intake refuse to create an Account?
Company text is not a reliable match, and creating Accounts would change the customer's hierarchy without a decision. Account creation is open question OQ-06, answered "no" as the working assumption.

### C8. What about duplicates that are already in the org?
They stay. This design protects new intakes. Cleaning old data is a separate project. Existing duplicates surface as holds or as unlinked Cases.

### C9. Which open questions would you refuse to skip at go-live?
The live Lead and Case status values, the legal basis for sales contact, and whether a known Contact should ever become an Opportunity. The full list is OQ-01 through OQ-16.

### C10. How do you talk about OQ-08 in an interview?
The flows match standard values: Open - Not Contacted, and New. If this client's org renamed them, I would change the flow conditions before UAT. I would not describe the escalation as proven.

### C11. How was scope held across phases?
Each phase had a stop. M1 had no metadata. M2 had no Python. M3 had no platform events. M4 had no monitor and no fault drills. M5 had no handover. M6 packages the work and does not add a feature.

### C12. What is a useful stop condition?
A sentence that names the work you will not start. It keeps a demo from becoming a silent redesign.

### C13. Which metrics can you defend?
20 conversations, 27 mapping rows, 10 Leads, 10 Cases, 1 platform event with 4 fields, 7 retry signals, 22 passing Python tests, and 6 fault drills. All of those are counts from this repository on 24 November 2026.

### C14. Which claims should you leave out?
A named client, a percentage improvement, a production deploy, Flow Builder screenshots, and an Apex test run. The diagrams are drawn from metadata. The tests used a local stand-in.

### C15. How would you run the discovery workshop?
Walk the as-is map lane by lane and mark each box confirmed, corrected, or unknown. Close D1 through D5 in the room. Leave channel connection and retention tooling for later if the route is agreed.

### C16. Who owns which decision?
Sales Manager owns Lead versus Contact and the sales hold. Support Lead owns case priority and the support queue. The customer owns the words and the consent choice. The intake agent does not invent them.

### C17. What is a mixed intake?
A conversation that is both commercial and service. With no existing Lead or Contact, the policy can write one Lead and one Case under the same reference. With a known Contact, it writes the Case and holds the commercial portion. The sample worker rejects a transcript that contains both phrases, because that worker implements one route per conversation.

### C18. What does a failure condition do in a user story?
It names the outcome that must not be called success. A second Lead, a Case with no reference, and a sales outreach without consent are failures even if a record was saved.

### C19. How long is raw intake text kept?
The working assumption is 24 months, then delete. Records already in Salesforce follow the client's existing retention. That assumption is not a retention job in this package.

### C20. How would you estimate the remaining work?
Separate the org confirmations, the deploy and UAT, the consent field, and the match against existing Contacts. Those are not included in the 22 local tests. I would estimate them only after OQ-08 and the duplicate sample are known.

### C21. How would you handle a request to add topic queues during the build?
Record it as a change to D5. The current decision is priority only, because no topic list is approved. I would not add the field in the same deploy that is meant to prove the reference.

### C22. What do you hand an administrator?
The admin guide, the manifest, the permission set, and the six post-deploy checks. The External Client App steps stay in the guide because the secret is not in source.

### C23. What is the business value of one reference?
A customer, a sales rep, and a support agent can ask for the same id and find the Lead, the Case, or both. The value is fewer duplicate outreaches and fewer requests that live only in a mailbox.

### C24. Why must a hold not expire into an automatic create?
A timeout would hide the queue by writing the record the policy refused to choose. Aging can display the hold. It cannot select Link, Update, Create, or Reject.

### C25. How do you know this project is complete?
The README, solution design, architecture, admin guide, demo script, interview guide, and portfolio copy all describe the same package, and the Python suite passes. Completeness here means a recruiter can trace a claim to a file. It does not mean a client has accepted the policy or that an org is live.
