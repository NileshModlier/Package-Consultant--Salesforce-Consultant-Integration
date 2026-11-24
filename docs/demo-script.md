# Demo script

| | |
|---|---|
| Project | Intake-to-Salesforce CRM Integration |
| Phase | M6 — Handover |
| Document | Five-minute demo, architecture walkthrough, and failure recovery |
| Version | 0.1 |
| Date | 24 November 2026 |
| Related | [Architecture](architecture.md), [Admin guide](admin-guide.md), [README](../README.md) |

Say the boundary in the first minute. The metadata is source. The tests ran locally. Nothing in this demo is a live org.

## 1. Five-minute demo

| Time | Show | Say |
|---|---|---|
| 0:00 | README metrics | Twenty conversations, ten Leads, ten Cases, one platform event, seven retry signals, twenty-two local tests, six fault drills. The policy decisions are still proposed. |
| 0:40 | `tests/sample_conversations.py`, first and twelfth items | A transcript that says "sales inquiry" becomes a Lead. A transcript that says "support request" becomes a Case. Jordan Lee is a Lead. The twelfth conversation is a High Case. |
| 1:20 | `integration/outbox.py`, the unique key | The outbox key is intake reference plus object. Accepting the same conversation twice leaves one row. The upsert is a PATCH on `Intake_Ref__c`. |
| 2:00 | Architecture diagram, section 1 of `docs/architecture.md` | The worker never sends Status or OwnerId. The flow owns assignment. A replay cannot take the record off the queue. |
| 2:40 | Lead and Case diagrams | Inbound Sales and Support Tier 1. A missing queue rolls the save back. Lead escalation and case response monitoring are tasks, not status changes. |
| 3:20 | Platform-event diagram | `Intake_Status__e` publishes after commit, with the reference, Lead or Case, status, and owner name. The subscriber stores the replay id and ignores a duplicate. |
| 4:00 | Fault-drill results in `tests/test_fault_drills.py` | A 400 is Dead Letter on the first attempt. A 429 waits for Retry-After. A refused connection stays Retrying, then syncs when the network returns. A down subscriber keeps its cursor. |
| 4:40 | Admin guide, open question OQ-08 | Deploy is `sf project deploy start --manifest manifest/package.xml`. Go-live still depends on the org's real Lead and Case status values. |

Stop at five minutes. The two walkthroughs below are for a longer conversation.

## 2. Architecture walkthrough

Start from the customer, not from the code.

1. The customer submits one request. The intake agent assigns a reference shaped `INT-YYYYMMDD-####` and classifies the text. Two intents, or neither, is an error. The agent does not create Contacts, Accounts, or Opportunities.
2. `Outbox.accept_conversation` stores the payload. An identical replay of a Synced row does not send again. A changed payload for the same reference becomes Pending again.
3. `OutboxWorker` calls `SalesforceClient.upsert`. Authentication is the client credentials grant. The token stays in memory. `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, and `SF_TOKEN_URL` come from the environment.
4. Salesforce writes one Lead or one Case. `Intake_Ref__c` is a unique external id on each object, so one reference can exist on one Lead and one Case, and cannot exist twice on the same object. Validation keeps the reference, summary, and channel together, and freezes the reference once it is set.
5. `Lead_Intake_Handling` or `Case_Intake_Handling` runs at trigger order 10. The owner becomes the queue. A task is created. Scheduled paths add a later task if the record is still unworked.
6. The status publisher runs at trigger order 20, including after the owner change, and publishes `Intake_Status__e` only after the transaction commits.
7. `StatusSubscriber.run_once` reads one CometD batch from the stored replay id. A replay id already in `seen_replay` is ignored. An expired id is rebuilt from `GET /services/apexrest/intake/status`, then the subscriber continues with new events.
8. `python -m integration.monitor` prints Pending, Retrying, Synced, Dead Letter, the sum of attempts on Retrying rows, each dead letter, the status-row count, the replay cursor, and the last subscriber error.

Close on what is deliberately absent: no polling loop, no Contact write, no Account create, and no claim that an org has executed the flows.

## 3. Failure recovery walkthrough

Use the measured results from `python -m tests.test_fault_drills`. Each line below is what that run printed.

**Wrong secret.** The token endpoint returns 401 `invalid_client`. The outbox goes to Dead Letter on attempt 1. Token calls: 1. PATCH calls: 0. There is no token to refresh.

**Network failure.** The token URL is a closed port. The row becomes Retrying. The same row is then delivered through a live stand-in and becomes Synced, with one stored record.

**Validation failure.** PATCH returns 400 with `Priority is required`. The row is Dead Letter after one attempt and one PATCH. The next worker pass processes nothing.

**Duplicate submission.** The same conversation is accepted twice, delivered, accepted again, and delivered again. The outbox has one row. The stand-in has one record. The replay processes zero rows.

**API limit exceeded.** PATCH returns 429 with `Retry-After: 30`. The row stays Retrying until `2026-11-24T12:00:30Z`. A pass before that time processes nothing. The pass at 30 seconds syncs the row. PATCH calls: 2.

**Subscriber down.** CometD raises connection refused while the cursor is 3. The run is deferred, the cursor stays 3, and the error is stored. The next run resumes from 3 and applies `Working - Contacted` at replay id 4. The stored error is cleared.

Two related cases sit next to the six drills. A single API 401 refreshes the token and syncs, with two token calls and an outbox attempt count of 0. A second 401 on the same call is Dead Letter, with two token calls and two PATCH calls.

The schedule for 408, 5xx, and a 429 without a header is 1, 2, 4, and 8 seconds, capped at 60. Attempt 5 is Dead Letter.
