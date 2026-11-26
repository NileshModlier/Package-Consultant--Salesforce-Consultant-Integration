# Resume Bullets

**Intake-to-Salesforce · accurate lines for a resume, LinkedIn, or cover letter**

> **Evidence boundary.** Every bullet below is true of the repository as it stands: built in source, tested locally, **not deployed**. Don't add "production", "deployed", "go-live", "clients", user counts, time savings, coverage percentages, "LLM-powered routing", or "MuleSoft" to any of them. Those claims aren't supported.

---

## Project line

**Intake-to-Salesforce** (portfolio project) · Sales Cloud, Service Cloud, Flows, Platform Events, Apex REST, OAuth 2.0, Python

## Salesforce Consultant or Business Analyst

- Designed an intake-to-CRM process for sales and support requests, with 34 business rules, 12 user stories, 16 tracked open questions, and a six-decision log, before any configuration was built.
- Wrote Lead and Case decision tables, as-is and to-be process maps, a RACI, and a 27-row field-mapping workbook, and traced every business rule to its build and test status.
- Reviewed the finished build against Salesforce documentation and recorded 27 findings, including the API-limit error code, integration-user sharing, and assignment-rule behaviour on REST updates, each with a fix and an org test.

## Salesforce Developer or Administrator

- Built four record-triggered flows that assign intake Leads and Cases to queues by DeveloperName, create review and escalation tasks, and publish status through a platform event, with trigger order and change-based entry conditions so replays don't duplicate work.
- Implemented an Apex REST resource (`/intake/status`) that returns intake status for Leads and Cases by reference or timestamp, with input validation and 400 responses, plus a two-method test class (not yet executed).
- Configured an external-id field, 10 validation rules, two queues, and a least-privilege permission set (no Delete, View All, or Modify All) in Salesforce DX source (API 62.0).

## Integration Engineer or Architect

- Built a Python integration (standard library only) that upserts Leads and Cases by external id through a durable SQLite outbox, using OAuth 2.0 client credentials with token caching and a single refresh on 401.
- Designed a seven-signal retry matrix with exponential backoff, `Retry-After` handling, and a Dead Letter state, and proved it with six fault drills (wrong secret, network failure, validation failure, duplicate submission, throttling, subscriber outage).
- Implemented status sync from Salesforce with a high-volume platform event published after commit, a CometD subscriber that stores its replay cursor in SQLite, and an Apex REST catch-up when the replay id has expired.
- Achieved idempotency in three layers (outbox key, external-id upsert, replay-id tracking): 20 sample conversations replayed produced exactly 10 Leads and 10 Cases in local tests.

## One-line versions

- Built a Salesforce intake integration (Flows, Platform Events, Apex REST, OAuth client credentials, Python outbox) that turns each conversation into exactly one Lead or Case; 22 local tests and 6 fault drills pass.
- Designed deterministic Lead/Case routing for an AI intake agent: the model writes the summary upstream, and Salesforce flows own the queue, owner, and status.

## Interview framing

> "It's a portfolio build. Everything is in source and tested locally against a stand-in. It isn't deployed. When I reviewed it against Salesforce documentation, I found five org-side issues the stand-in couldn't show, and I documented each fix and the org test that would prove it."

## Accuracy checklist

| Check before using a bullet | Why |
| --- | --- |
| No "production", "deployed", "go-live", or "live org" | Metadata is source only |
| No "LLM routes" or "AI decides" | Routing is a phrase match. No model is called in this repository |
| No "MuleSoft" as built | Compared as an option only |
| No coverage percentage | The Apex test hasn't run |
| No business impact numbers | No baseline was measured |
| "Transactional outbox" isn't used | It's a durable outbox |
| "22 tests" and "6 drills" are local | Say "local tests" if space allows |
| "Handled API limits" isn't used | Throttling (429) is tested. Salesforce's 403 limit error is a known gap |
