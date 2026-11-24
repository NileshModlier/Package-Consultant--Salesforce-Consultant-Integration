# Architecture

| | |
|---|---|
| Project | Intake-to-Salesforce CRM Integration |
| Phase | M6 — Handover |
| Document | Architecture and the five project diagrams |
| Version | 0.1 |
| Date | 24 November 2026 |
| Related | [Solution design](solution-design.md), [Flow design](flow-design.md), [Admin guide](admin-guide.md) |

Salesforce is the system of record after a successful commit. The intake agent is the system of engagement until that commit. The Python package is the commit boundary and the status return path. The as-is mailbox process in the process maps is a baseline hypothesis, not a workshop transcript.

## 1. Architecture

A conversation is classified, stored once in the outbox, and upserted by `Intake_Ref__c`. Salesforce flows assign the queue and publish `Intake_Status__e` after the save commits. The subscriber writes the latest status back to SQLite. The monitor reads both databases once.

```mermaid
flowchart TB
  customer["Customer"]
  agent["Intake agent"]
  outbox["Outbox SQLite"]
  worker["Outbox worker"]
  auth["Client-credentials token"]
  api["Salesforce REST upsert"]
  lead["Lead"]
  caseRec["Case"]
  leadFlow["Lead Intake Handling"]
  caseFlow["Case Intake Handling"]
  event["Intake_Status__e"]
  sub["Status subscriber"]
  statusDb["Status SQLite"]
  monitor["Monitor"]

  customer --> agent
  agent --> outbox
  outbox --> worker
  worker --> auth
  auth --> api
  api --> lead
  api --> caseRec
  lead --> leadFlow
  caseRec --> caseFlow
  leadFlow --> event
  caseFlow --> event
  event --> sub
  sub --> statusDb
  outbox --> monitor
  statusDb --> monitor
```

Sales inquiry text becomes a Lead. Support request text becomes a Case. The same reference may exist on one of each. A second record of the same object is rejected by the unique external id.

The upsert body omits Status and OwnerId. Replay cannot pull a record off the queue the flows assigned.

## 2. Sequence

One successful delivery, then the status event. Token caching is omitted. A 401 on the API call refreshes the token once before this sequence continues.

```mermaid
sequenceDiagram
  participant Agent as Intake agent
  participant Outbox as Outbox
  participant Worker as Worker
  participant SF as Salesforce REST
  participant Flow as Assignment flow
  participant Pub as Status publisher
  participant Sub as Subscriber

  Agent->>Outbox: accept conversation
  Worker->>Outbox: read Pending or Retrying
  Worker->>SF: PATCH by Intake_Ref__c
  SF-->>Worker: 201 created or 204 updated
  Worker->>Outbox: Synced
  SF->>Flow: after save, trigger order 10
  Flow->>SF: set owner to queue and create task
  SF->>Pub: after save, trigger order 20
  Pub->>SF: publish Intake_Status__e after commit
  Sub->>SF: CometD from stored replay id
  SF-->>Sub: event
  Sub->>Sub: ignore a replay id already seen
```

## 3. Lead flow

`Lead_Intake_Handling` runs only when Intake Ref is set and the record is new or the reference changed. `Lead_Status_Publisher` also runs when status or owner changes, so the event after queue assignment carries the queue name.

```mermaid
flowchart TD
  start["Lead saved with Intake Ref"]
  getQ["Get queue Inbound_Sales"]
  missing{"Queue found?"}
  stop["Roll the save back"]
  own["Owner becomes Inbound Sales"]
  task["Task: Review intake ref"]
  wait["24 hours after CreatedDate"]
  still{"Status still Open - Not Contacted?"}
  esc["High task for the current owner"]
  done["Stop"]
  pub["Publish Intake_Status__e"]

  start --> getQ --> missing
  missing -->|No| stop
  missing -->|Yes| own --> task --> wait --> still
  still -->|Yes| esc
  still -->|No| done
  own --> pub
```

The 24-hour path does not change Status, Rating, or Intake Ref. The escalation is a task. If the org does not use the status `Open - Not Contacted`, the scheduled path does not fire. That value is still open question OQ-08.

## 4. Case flow

High and standard cases share Support Tier 1. Priority changes the task and the clock.

```mermaid
flowchart TD
  start["Case saved with Intake Ref"]
  getQ["Get queue Support_Tier_1"]
  missing{"Queue found?"}
  stop["Roll the save back"]
  own["Owner becomes Support Tier 1"]
  high{"Priority is High?"}
  urgent["High task: urgent response"]
  normal["Normal task: respond"]
  four["4 hours"]
  day["24 hours"]
  stillHigh{"High and Status still New?"}
  stillNew{"Status still New?"}
  t4["Task: urgent response still outstanding"]
  t24["Task: response still outstanding"]
  pub["Publish Intake_Status__e"]

  start --> getQ --> missing
  missing -->|No| stop
  missing -->|Yes| own --> high
  high -->|Yes| urgent --> four --> stillHigh
  high -->|No| normal --> day
  stillHigh -->|Yes| t4 --> day
  stillHigh -->|No| day
  day --> stillNew
  stillNew -->|Yes| t24
  stillNew -->|No| pub
  own --> pub
```

A case that has left New gets neither monitoring task. Tasks use WhatId. They do not require a Contact.

## 5. Platform events

`Intake_Status__e` is high volume and publishes after commit. A rolled-back save produces no event. The subscriber stores the replay id. A repeated replay id is ignored. An expired cursor is recovered from `IntakeStatusResource`, then the subscriber continues with new events only.

```mermaid
flowchart TD
  save["Lead or Case commit"]
  criteria{"Intake Ref set and create, status change, or owner change?"}
  skip["No event"]
  name["Resolve owner name from User, else Group"]
  publish["Publish after commit"]
  take["Subscriber reads from the stored replay id"]
  expired{"Replay id still available?"}
  apply["Apply once and advance the cursor"]
  catchup["GET intake status by refs or since"]
  resume["Next read uses new events only"]

  save --> criteria
  criteria -->|No| skip
  criteria -->|Yes| name --> publish --> take --> expired
  expired -->|Yes| apply
  expired -->|No| catchup --> resume
```

If CometD cannot be reached, the cursor stays put and the error is stored for the monitor. The next run requests events after that same cursor.

The catch-up class is `without sharing`. After queue assignment the integration user no longer owns the record, and the permission set does not grant view all. The response is limited to intake reference, object type, status, and owner name.
