# Requirements

| | |
|---|---|
| Project | Intake-to-Salesforce CRM Integration |
| Phase | M1 — Discovery and design |
| Document | Requirements |
| Version | 0.1 |
| Status | Draft for review. Not approved for build. |
| Date | 24 November 2026 |
| Related | [As-is process](process-maps/as-is.md), [To-be process](process-maps/to-be.md), [Field mapping](field-mapping.xlsx), [Solution design](solution-design.md) |

This document is the business contract for intake into Salesforce. It defines who is served, what must be true for each story, and the rules a later phase would have to meet. It does not authorize Salesforce configuration, automation, or integration code.

No workshops, mailbox samples, or org extracts have been recorded yet. Where the current process is described, treat it as a baseline to confirm. See the as-is map.

## 1. Purpose

Give the client one front door for commercial and support inquiries, a stable reference number, and a predictable handoff into Salesforce Lead and Case. Contact remains the identity record. People, not the intake step, close the relationship.

## 2. Personas

| Role | Accountability in this process |
|---|---|
| Customer | States the request, identity, and whether sales may make contact. |
| Sales Representative | Works a Lead that has already passed the sales gates. |
| Support Agent | Works a Case and updates its status without breaking the intake reference. |
| Sales Manager | Owns qualification, sales holds, and ambiguous sales matches. |
| Support Lead | Owns case priority, queues, and visibility of failed or unlinked support intakes. |
| AI Intake Agent | Assigns the intake id, normalizes the submission, records consent, classifies, matches, and commits only when the rules allow. |

Salesforce is the system of record after a successful commit. It is not a persona and it does not decide the route.

## 3. Scope

**In scope for these requirements**

- One intake reference for every submission.
- Separation of service handling and sales contact.
- Rules for when a Lead is created, updated, or withheld.
- Rules for when a Case is created and when it may point at a Contact.
- Duplicate handling by exact email.
- A field-level mapping for the nine intake fields, held in the workbook.
- Human holds that stay visible until a named role disposes of them.

**Out of scope**

- Deploying objects, fields, layouts, flows, assignment rules, or Apex.
- API design, middleware, prompts, and model selection.
- Cleaning duplicates that already exist in Salesforce.
- Territory assignment, queue membership, and service-level targets beyond the working assumptions in the design.
- Historical backfill of old mailbox items.

## 4. Vocabulary

| Term | Meaning |
|---|---|
| Intake id | Reference assigned on first receipt. Format `INT-YYYYMMDD-####`. It does not change when the customer corrects the submission or when the record is updated. |
| Receipt | Customer-facing confirmation that the submission was received. It is not confirmation that a Lead or Case exists, that a person is assigned, or that the request is resolved. |
| Sales consent | Explicit permission for sales contact. Granted, declined, and unanswered are different. Unanswered is not granted. |
| Classification | Sales, Support, or Mixed. Mixed means both a service request and a commercial ask are present. |
| Band | Auto when classification confidence is at least 0.70. Review when it is below 0.70. The number is assumption A-07. |
| Net-new | Normalized email matches no Contact, no open Lead, and no closed Lead. A closed Lead alone is a sales hold, not a new Lead. |
| Open Lead | A Lead whose status is not closed. The closed values assumed here are Closed - Converted and Closed - Not Converted. |
| Identity unconfirmed | A Case with no Contact lookup because the email matched no Contact or more than one. |
| Commit | The moment a Lead or Case is created or an existing Lead is updated. Normalization, consent, classification, and match happen before commit. |

## 5. Functional requirements

| ID | Requirement | Stories |
|---|---|---|
| FR-1 | Every submission receives one intake id and a truthful receipt. | US-01, US-10 |
| FR-2 | Sales contact requires granted consent. A support Case does not. | US-02, US-05, US-11 |
| FR-3 | A Lead is created or updated only on the sales path in the business rules. | US-03, US-04, US-11, US-12 |
| FR-4 | A valid support request becomes a Case. Contact lookup is set only for one exact Contact match. | US-05, US-09, US-12 |
| FR-5 | Ambiguous sales matches and missing consent stay visible to the Sales Manager. They do not become Leads by timeout. | US-04, US-08 |
| FR-6 | Priority is preserved as P1–P4 and routes the Case. P1 and P2 share an urgent path. | US-05, US-09 |
| FR-7 | The intake id on a committed record stays searchable and is not replaced when status changes or a later intake is attached. | US-06, US-10, US-12 |
| FR-8 | Intake does not create Contacts or Accounts and does not overwrite Contact identity. | US-04, US-12 |

## 6. Business rules

These rules are the test basis for the stories. Rationale and rejected options are in the decision log in the solution design.

### Identity and receipt

| ID | Rule |
|---|---|
| BR-01 | Assign the intake id on first receipt. Never replace it. A correction reuses it. |
| BR-02 | The receipt confirms receipt only. |
| BR-03 | Email, name, and summary are required before an acceptance receipt. A Lead also requires company and a usable last name. |
| BR-04 | Do not invent email, last name, or company. Forbidden substitutes include Unknown, N/A, and Individual. |
| BR-30 | A validation failure creates neither a Lead nor a Case. The reason remains visible against the intake id. |
| BR-31 | If commit fails, the customer is not told that a record exists, and no partial Lead or Case is left behind. |

### Consent

| ID | Rule |
|---|---|
| BR-05 | Sales consent must be Granted before any Lead is created or updated for outreach. Declined and unanswered both block the Lead. Neither blocks a Case. |

### Classification

| ID | Rule |
|---|---|
| BR-06 | Each submission has one classification: Sales, Support, or Mixed. |
| BR-07 | Confidence of 0.70 or higher is band Auto. Below 0.70 is band Review. |
| BR-15 | Not a Fit creates no Lead. When the class is Sales, it creates no Case either. When the class is Mixed, the Case decision still runs. Disqualified is a Sales Representative outcome and is never set at intake. |
| BR-21 | On a Review-band Case, priority inferred by the intake agent is stored as P3 until a person confirms a higher value. Priority the customer explicitly stated is not capped. |

### Match and duplicates

| ID | Rule |
|---|---|
| BR-08 | The only automatic match key is normalized email: trimmed and lowercased, exact match only. Name and company never match by themselves. |
| BR-09 | The Lead decision and the Case decision in the to-be map are the authority. The first matching Lead rule wins. Case rules run only for Support and Mixed, and they do not depend on the Lead result. |
| BR-12 | Write a Lead only when the class is Sales or Mixed and a Lead rule says create or update. That write carries qualification Unqualified or Sales Ready. Not a Fit, band Review, missing consent, any Contact match, and an unresolved duplicate do not write a Lead. |
| BR-10 | Intake does not create or update Contact or Account. |
| BR-11 | A name or company that disagrees with the matched Contact is a conflict for the sales path. It does not rewrite the Contact. |
| BR-13 | Exactly one open Lead and zero Contacts, on an allowed sales path, updates that Lead. Status is not reset. The original intake id stays. The newer id is appended to history. |
| BR-14 | One or more Contacts blocks an automatic Lead create and an automatic Lead update. The commercial ask waits for the Sales Manager. |
| BR-18 | An intake id may appear on one Lead and one Case. It must not appear on two Leads or on two Cases. |
| BR-19 | Replaying an intake id that is already committed does not create another record and does not append a second copy of the same summary. |
| BR-28 | The Sales Manager dispositions an ambiguous sales hold as Link, Update, Create, or Reject. Elapsed time never creates a Lead. |

### Case, priority, and status

| ID | Rule |
|---|---|
| BR-16 | Once email, name, and summary are valid and the class is Support or Mixed, a Case is created. Low confidence and multiple Contacts do not stop the Case. Contact lookup is set only when exactly one Contact matches. |
| BR-17 | Mixed, band Auto, consent Granted, and no Contact or Lead on that email create one Case and one Lead that share the intake id. |
| BR-20 | Store priority as P1, P2, P3, or P4. Also set Lead Rating (Hot, Hot, Warm, Cold) and Case Priority (High, High, Medium, Low). The standard fields collapse P1 and P2, so the P1–P4 value is retained. |
| BR-22 | Until a topic list is approved, P1 and P2 route to the urgent path and P3 and P4 route to the standard path. |
| BR-23 | A blank Contact lookup means identity unconfirmed. The Case still routes by priority. |
| BR-24 | A new Lead starts at Open - Not Contacted. A new Case starts at New. Intake never writes a closed status. |
| BR-32 | A search by intake id must be able to find a Lead, a Case, and an id that exists only in history. |

### Write order and retention

| ID | Rule |
|---|---|
| BR-25 | The write order is assign id, normalize, validate, record consent, classify, match, then commit. |
| BR-26 | If email, last name, or company can be stored only by using a placeholder, do not write the Lead. Keep the reason with the intake id. The Case decision is unchanged. |
| BR-29 | Holds, rejections, and failures stay visible to the accountable role in the to-be handoff. P1 and P2 items are ordered first. One business day marks a sales hold overdue and does not dispose of it. |
| BR-27 | Case Subject is a plain excerpt of the summary, 120 characters, with an ellipsis if cut. Tags stay in the Description header, not in the Subject. |
| BR-33 | Lead, Contact, and Case follow the client's existing Salesforce retention. Raw intake text is assumed to be kept 24 months and then deleted, pending legal confirmation. |
| BR-34 | Intake must not ask for passwords, payment card numbers, or government identifiers. If the customer supplies them, they are removed before commit and the summary notes that they were removed. |

## 7. User stories

### US-01 — Submit once and keep a reference

**Role:** Customer

**Story:** As a Customer, I want to submit a sales or support request once and receive a receipt that quotes my intake id, so that any follow-up uses the same reference.

**Acceptance criteria:**

1. Given a first submission, when it is accepted into intake, then it is given one intake id in the form `INT-YYYYMMDD-####` and that id is never replaced later.
2. Given email, name, and summary are present, when the receipt is produced, then it quotes the intake id and states that the request was received and has not yet been assigned or resolved.
3. Given email, name, or summary is missing, when the customer submits, then no acceptance receipt is produced, no Lead or Case is created, and the response names what is missing and quotes the same intake id.
4. Given the customer corrects that submission, when it is sent again, then the original intake id is kept.
5. Given two different requests, when both are accepted, then they receive different intake ids even if the email address is the same.

**Business value:** The customer can prove the request was received without calling to check. Support and sales later speak about the same reference the customer already has.

**Failure conditions:**

- A receipt is issued with no intake id, or two live requests share one intake id.
- The receipt says a Lead or Case is open, a person is assigned, or the issue is resolved.
- A correction is given a new intake id.
- A submission with a blank email or a blank summary is treated as accepted.

### US-02 — Choose sales contact separately from getting help

**Role:** Customer

**Story:** As a Customer, I want to allow or refuse sales contact separately from having a problem handled, so that a support request is not treated as permission to sell to me.

**Acceptance criteria:**

1. Given a submission, when consent is captured, then the choices are Granted, Declined, and Unanswered, and Unanswered is the state when the customer has not chosen.
2. Given consent is Declined or Unanswered, when the request is Support, then a Case can still be created.
3. Given consent is Declined or Unanswered, when the request is Sales, then no Lead is created or updated for outreach, and the item remains Pending Consent.
4. Given consent is stored, when it is stored, then the choice, the time, the channel, and the statement version are retained as governed attributes.
5. Given a later intake for the same email, when that later intake carries its own choice, then the new choice does not rewrite the earlier record's consent history.

**Business value:** Service continues when the customer only wants help. Sales outreach rests on a recorded yes, which protects the customer and the pipeline.

**Failure conditions:**

- A blank answer is stored or acted on as Granted.
- A support Case is refused because sales consent was Declined.
- A Lead reaches a Sales Representative without Granted consent.
- A new submission overwrites the consent recorded on an earlier Lead or Case.

### US-03 — Start from a complete Lead

**Role:** Sales Representative

**Story:** As a Sales Representative, I want a commercial inquiry to arrive as a Lead that already holds the mapped intake fields, so that the first conversation is about the customer's request.

**Acceptance criteria:**

1. Given classification Sales or Mixed, band Auto, consent Granted, and an email that matches no Contact and no Lead, when the request is a commercial fit, then one Lead is created.
2. Given that Lead is created, when it is opened, then intake id, email, name split into first and last name, company, summary, qualification, priority, and status are populated under the field-mapping rules.
3. Given the sales-ready rubric is not fully met, when the Lead is still allowed, then qualification is Unqualified and status is Open - Not Contacted.
4. Given the rubric is met, when the Lead is created, then qualification is Sales Ready and status is still Open - Not Contacted.
5. Given the classifier marks Not a Fit, when processing finishes, then no Lead is created and the Sales Manager can see the rejection.

**Business value:** Representatives stop reconstructing the request from a mailbox. Qualification shows whether the Lead is ready to work without pretending that anyone has already spoken to the customer.

**Failure conditions:**

- A Lead is created with a blank last name, blank company, blank email, or blank summary.
- Company or last name is filled with Unknown, N/A, or the person's name copied into Company.
- Qualification is Sales Ready while consent, company, email, or summary is missing.
- Status on create is anything other than Open - Not Contacted.
- A Not a Fit outcome still produces a Lead in a representative's queue.

### US-04 — See that this person is already known

**Role:** Sales Representative

**Story:** As a Sales Representative, I want an email that already belongs to an open Lead or a Contact to follow the duplicate rules, so that I do not start a second pursuit.

**Acceptance criteria:**

1. Given exactly one open Lead and no Contact for that email, when an allowed sales intake arrives, then that Lead is updated, its status is left unchanged, its original intake id is kept, and the new intake id is added to history once.
2. Given one or more Contacts for that email, when the intake is commercial, then no Lead is created, no existing Lead is updated, and the item is held for the Sales Manager with the match counts visible.
3. Given more than one open Lead, or only closed Leads, when the intake is commercial, then no Lead is created or reopened and the item is held.
4. Given a hold is in place, when a representative looks for new work, then the held item is not sitting in the working queue as a second Lead.
5. Given a replay of an intake id already written to that Lead, when it is processed again, then the summary is not appended a second time.

**Business value:** One open pursuit per new logo, and no automatic second Lead when the person is already a Contact. Forecast and history stay on the record that already exists.

**Failure conditions:**

- A second open Lead is created for an email that already has one open Lead.
- A closed Lead is reopened by intake.
- A Lead is created or updated automatically for an email that matches a Contact.
- The original intake id is replaced by the newer one.
- Contact name, email, or account is overwritten from the submission.

### US-05 — Take a Case that already has the request

**Role:** Support Agent

**Story:** As a Support Agent, I want a support request to arrive as a Case with the summary, priority, status, and a Contact lookup only when the person is actually known, so that I can answer without another round of questions.

**Acceptance criteria:**

1. Given a valid email, name, and summary, and classification Support or Mixed, when processing finishes, then one Case is created even if sales consent was not granted.
2. Given the email matches exactly one Contact, when the Case is created, then Contact lookup is that Contact and the Description identity line reads Contact linked.
3. Given the email matches no Contact or more than one, when the Case is created, then Contact lookup is empty, the identity line says so, and the Case is still routed by priority.
4. Given a priority value, when the Case is created, then P1–P4 is stored and standard Priority follows the crosswalk: High, High, Medium, Low.
5. Given the Case is created, when the agent reads it, then Subject is a plain excerpt of the customer's words and Description contains the header plus the full summary.

**Business value:** The agent sees the request the customer wrote, at the urgency the rules defined, on the right person when there is exactly one match. Service is not withheld for a sales checkbox.

**Failure conditions:**

- A valid support request ends with no Case.
- Contact lookup is set when the email matched zero Contacts or more than one.
- A declined sales consent stops the Case.
- Priority exists only as free text, or a stated P1 is stored as P4.
- Subject is empty, or Subject is filled with routing tags instead of the customer's words.
- Description drops the summary that the customer sent.

### US-06 — Keep the reference stable as the Case moves

**Role:** Support Agent

**Story:** As a Support Agent, I want the Case status to change without losing the intake id, so that a customer who quotes that id can be found.

**Acceptance criteria:**

1. Given a Case created from intake, when status moves from New to a later working or closed status, then the intake id on the Case is unchanged.
2. Given a customer quotes an intake id, when an agent searches, then a Case, a Lead, or a history entry carrying that id can be found.
3. Given a Mixed intake, when both records exist, then the same intake id is present on one Case and one Lead and the search can see both.
4. Given an agent closes the Case, when closure is recorded, then intake has not already set the Case to a closed status at creation.
5. Given a later, different intake is appended to a related Lead, when that happens, then the Case's creating intake id is not replaced.

**Business value:** The number in the customer's receipt remains the number on the Case after the work has moved on. Agents do not open a second Case to recover a lost reference.

**Failure conditions:**

- A status change clears or replaces the intake id.
- Two Cases carry the same intake id.
- Search by the receipt number finds nothing even though a Case was committed.
- The Case is created already Closed.

### US-07 — See qualification and what never became a Lead

**Role:** Sales Manager

**Story:** As a Sales Manager, I want to see how commercial intakes were qualified and which ones were refused, so that I can correct the standard without hunting through a mailbox.

**Acceptance criteria:**

1. Given Leads were created from intake, when the manager reviews them, then each shows qualification, priority, status, and intake id, using the allowed values.
2. Given qualification is Unqualified or Sales Ready, when the manager inspects who may set it, then intake may set those two values and must not set Disqualified.
3. Given an intake was Not a Fit or is on a sales hold, when the manager reviews the period, then those intakes are visible and are not hidden as Leads in a representative queue.
4. Given the manager compares volume across the unassigned sales queue, when distribution is inspected, then every automatically created Lead is in that queue until a person assigns it.
5. Given a human overrides classification or qualification, when the override is recorded, then the intake value and the human value are both retained.

**Business value:** Lead quality becomes something the manager can coach. Rejected and held demand is visible, so a quiet queue is not mistaken for a quiet market.

**Failure conditions:**

- A Lead shows a qualification outside Unqualified, Sales Ready, Not a Fit, and Disqualified.
- Intake writes Disqualified.
- Not a Fit and consent holds disappear with no record.
- An automatically created Lead is owned by a named representative under a territory rule this phase has not agreed.
- An override erases the value the intake agent first wrote.

### US-08 — Dispose of an ambiguous sales match

**Role:** Sales Manager

**Story:** As a Sales Manager, I want every ambiguous commercial match to wait for a named disposition, so that representatives are not working conflicting records.

**Acceptance criteria:**

1. Given a commercial intake is ambiguous under BR-09, when processing finishes, then no Lead is inserted and the hold shows the intake id, the match counts, priority, and the summary.
2. Given the manager chooses Link, Update, Create, or Reject, when the disposition is saved, then that choice and the reason are retained.
3. Given the manager chooses Create, when the Lead is then created, then it follows the same required-field rules as an automatic Lead.
4. Given the manager chooses Update or Link, when the existing record is changed, then the new intake id is kept in history and the original intake id remains.
5. Given one business day passes with no disposition, when the clock passes, then the item stays on the hold and is visibly overdue. No Lead is created by the clock.

**Business value:** Duplicate judgment sits with the role that owns the pipeline. Urgency is visible because holds are ordered with P1 and P2 first, without letting the clock invent a record.

**Failure conditions:**

- A hold times out into a new Lead.
- The hold can be closed with no disposition.
- Create is allowed while last name, company, email, summary, or consent is missing.
- Link or Update drops the newer intake id or replaces the original one.
- A representative can pull the held item into a working queue before disposition.

### US-09 — Route support by priority

**Role:** Support Lead

**Story:** As a Support Lead, I want every valid Case to land on an urgent or standard path from its priority, so that a severe issue is not left in a general pile while a topic list is still undecided.

**Acceptance criteria:**

1. Given a Case is stored with intake priority P1 or P2, when routing is applied, then it is on the urgent path.
2. Given a Case is stored with P3 or P4, when routing is applied, then it is on the standard path.
3. Given no product or topic list has been approved, when a Case is created, then it still routes by priority and is not dropped.
4. Given Contact lookup is empty, when the Case is routed, then it remains on its priority path and is identifiable as identity unconfirmed.
5. Given inferred priority and band Review, when the Case is created, then stored priority is P3 unless the customer explicitly stated a higher urgency.

**Business value:** Response order follows severity with the fields the mapping actually fills. The absence of a topic catalog cannot erase a Case.

**Failure conditions:**

- P1 and P4 share the same path.
- An unrecognized topic results in no Case.
- An unlinked Case is excluded from the priority path.
- Inferred Review-band urgency is written as P1 without a customer statement.
- Routing depends on a field the mapping does not populate.

### US-10 — See the intakes that never committed

**Role:** Support Lead

**Story:** As a Support Lead, I want every support intake that fails validation or commit to stay visible with a reason, so that a customer request cannot vanish between the channel and Salesforce.

**Acceptance criteria:**

1. Given validation fails, when processing stops, then the intake id, the missing items, and the last step are retained, and no Case exists.
2. Given the customer can fix the submission, when the failure is returned, then the message quotes the intake id and what to correct.
3. Given commit fails after a valid support classification, when processing stops, then the customer is not told a Case is open and the Support Lead can see the id, the reason, and the priority.
4. Given a corrected submission is replayed, when it then succeeds, then the original intake id is the id on the Case.
5. Given a failure record exists, when someone retries the same intake id after success, then a second Case is not created.

**Business value:** Operations can recover a missed request without asking the customer to start again. The receipt never claims a Case that the commit did not create.

**Failure conditions:**

- A failed intake is deleted, or is kept with no reason.
- The customer is told a Case exists when the commit did not succeed.
- A partial Case remains, for example a Case in New with an empty summary.
- A successful replay mints a second intake id or a second Case.
- A P1 failure is visible only after lower-priority items.

### US-11 — Classify before any record is chosen

**Role:** AI Intake Agent

**Story:** As an AI Intake Agent, I want to classify each valid submission as Sales, Support, or Mixed and apply the consent and confidence gates, so that Lead and Case creation follow one policy on every channel.

**Acceptance criteria:**

1. Given a valid summary, when classification finishes, then the result is exactly one of Sales, Support, or Mixed, plus band Auto or Review.
2. Given band Review and the class is Sales only, when the gates are applied, then no Lead is written and the item is held.
3. Given band Review and the class is Support or Mixed, when the gates are applied, then a Case is still created under the Case rules and no Lead is created or updated.
4. Given class Sales, band Auto, and consent is not Granted, when the gates are applied, then no Lead is written.
5. Given class Mixed, band Auto, consent Granted, and an email that matches no Contact and no Lead, when the gates are applied, then one Case and one Lead are written with the same intake id.
6. Given the commercial assessment is Not a Fit, when the class is Sales, then no Lead and no Case are written and the rejection is visible. When the class is Mixed, the Case is still written and no Lead is written.

**Business value:** Channel and shift stop changing the path. Doubt holds the pipeline back and still lets a service request through.

**Failure conditions:**

- A submission is left unclassified or is given two classifications.
- Band Review still creates or updates a Lead.
- Support is stored as a Lead because company was filled in.
- Mixed writes two Leads, or writes a Lead without Granted consent.
- A human correction is overwritten when the same intake id is replayed.
- Not a Fit on a pure sales item still opens a Case or a Lead.

### US-12 — Normalize and match before writing

**Role:** AI Intake Agent

**Story:** As an AI Intake Agent, I want to normalize the nine intake fields and resolve email matches before commit, so that Salesforce receives the write the mapping describes.

**Acceptance criteria:**

1. Given a raw submission, when processing runs, then the order is assign id, normalize, validate, record consent, classify, match, and only then commit.
2. Given email, name, and company, when they are normalized, then email is trimmed and lowercased, name is split on the first space, and company whitespace is collapsed, without changing the meaning of the summary.
3. Given the match counts, when the Lead decision and the Case decision are applied, then Contact lookup is set only for exactly one Contact on a Case, a Lead is created only on L8, and a Lead is updated only on L7.
4. Given a required Lead value cannot be produced without a placeholder, when the sales path would write, then no Lead is written and the reason is retained.
5. Given the same intake id is replayed after a successful commit, when processing runs again, then the earlier write is not duplicated.

**Business value:** The workbook is the contract for a later build. The same email cannot mean one thing in a workshop and another thing at commit.

**Failure conditions:**

- A Lead or Case is written before normalization, consent, classification, or match.
- A fuzzy name or company match sets Contact lookup or chooses a Lead.
- A placeholder is written into email, last name, or company.
- Status or priority is written outside the crosswalk.
- Two Cases or two Leads are committed for one intake id.
- Contact or Account is created or updated by the intake write.

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Traceability: every committed Lead or Case carries the creating intake id. Later ids for that same record go to history and do not replace it. |
| NFR-2 | Idempotence: a replay of a committed intake id is safe to repeat. |
| NFR-3 | Privacy: sales consent defaults to Unanswered, and Unanswered does not authorize outreach. Secrets named in BR-34 are not stored. |
| NFR-4 | Audit: the value first set by intake and a later human override are both retained for classification, qualification, priority, and sales disposition. |
| NFR-5 | Order of work: P1 and P2 failures and holds are visible ahead of P3 and P4. This is an ordering rule, not a timed service promise. |
| NFR-6 | Language: this design assumes English submissions. Other languages are an open question, not a silent requirement. |
| NFR-7 | Accessibility of a future form, channel uptime, and retention tooling are later-phase requirements. They are named so they are not forgotten. They are not specified here. |

## 9. Story traceability

| Story | Role | Primary rules | Process | Objects |
|---|---|---|---|---|
| US-01 | Customer | BR-01, BR-02, BR-03, BR-30 | To-be receipt and correction | Intake id on Lead and Case |
| US-02 | Customer | BR-05 | To-be consent gate | Governed consent attributes |
| US-03 | Sales Representative | BR-03, BR-04, BR-12, BR-15, BR-24 | To-be Lead create | Lead |
| US-04 | Sales Representative | BR-08, BR-09, BR-11, BR-12, BR-13, BR-14, BR-19 | To-be Lead decision | Lead, Contact |
| US-05 | Support Agent | BR-05, BR-16, BR-20, BR-23, BR-27 | To-be Case create | Case, Contact |
| US-06 | Support Agent | BR-18, BR-24, BR-32 | To-be status | Case, Lead |
| US-07 | Sales Manager | BR-15, BR-22 | To-be holds and queue | Lead |
| US-08 | Sales Manager | BR-28, BR-29 | To-be sales hold | Lead |
| US-09 | Support Lead | BR-20, BR-21, BR-22, BR-23 | To-be routing | Case |
| US-10 | Support Lead | BR-01, BR-30, BR-31 | To-be failure | Case |
| US-11 | AI Intake Agent | BR-06, BR-07, BR-12, BR-15, BR-16, BR-17 | To-be classify | Lead, Case |
| US-12 | AI Intake Agent | BR-08, BR-09, BR-25, BR-26 | To-be write order | Lead, Contact, Case |

## 10. Approval

| Role | Name | Decision | Date |
|---|---|---|---|
| Sales Manager | | Pending | |
| Support Lead | | Pending | |
| Engagement owner | | Pending | |

Approval of this document accepts the stories and the business rules as the draft baseline. It does not approve Salesforce configuration or an integration build. Open questions in the solution design still block that later work.
