# Project Completion Report

**Intake-to-Salesforce · status at 24 November 2026**

> **Evidence boundary.** This report records what exists in the repository and what was verified for this documentation set. "Complete" here means **complete in source and tested locally**. It doesn't mean deployed, accepted by a client, or running in production. No org was available. The Apex test and org tests T1–T23 have not run. D1–D5 are proposed and unsigned.

---

## 1. Summary

| Dimension | Status |
| --- | --- |
| Scope M1–M6 | Delivered in source. M1 policy is ahead of the build in several rules |
| Python integration | **22 of 22 tests pass** locally (re-run 24 November 2026, Python 3.13). **6 of 6 fault drills pass** |
| Salesforce metadata | 32 XML files parse cleanly. **Not deployed**. Apex test **not executed** |
| Client decisions | D1–D5 **proposed**. Four open questions block go-live |
| Review findings | **27 findings**: 5 high, 9 medium, 13 low. All five high findings are org-side settings or platform behaviour that a stand-in can't show |
| Readiness | **Ready for a sandbox deployment** once F1, F2, F3, F26, and F27 are addressed. **Not ready for production** |

## 2. Brief reconciled with the repository

The documentation brief described the project in summary terms. Each claim was checked against the code.

| Brief says | Repository shows | How the documents state it |
| --- | --- | --- |
| "AI Intake Agent integrated with Salesforce" | The agent is upstream and not in the repository. Twenty sample conversations stand in for it | "The intake agent is upstream. This repository is the Salesforce side of the integration" |
| "Deterministic state machine drives decisions" | `classify()` matches two phrases. The outbox has four states (Pending, Retrying, Synced, Dead Letter) driven by a seven-signal retry matrix | "Deterministic routing and a four-state outbox" |
| "LLM only generates summaries" | No model is called. The summary arrives as an input field and is stored in `Intake_Summary__c` | "The upstream agent may write the summary with a model. No model is called in this repository" |
| "Sales inquiries become Leads. Support requests become Cases" | True for the two phrases. Both or neither raises `RouteError` | As stated, plus the rejection path |
| "Platform Events synchronize status" | `Intake_Status__e`, two publisher flows, a CometD subscriber | Implemented. Subscriber tested locally. No event published in an org |
| "Apex REST provides catch-up" | `IntakeStatusResource` with 2 test methods | Implemented. Test **not executed** |
| "External Client Apps provide OAuth" | Client-credentials code and setup steps | Code tested against a stand-in. The app isn't created |
| "Outbox Pattern, SQLite" | SQLite outbox with a unique business key | "Durable outbox", not "transactional outbox" (the agent's state is elsewhere) |
| MuleSoft Architect perspective | No MuleSoft artefacts | Compared as an option in [ARCHITECTURE.md](ARCHITECTURE.md) §8. **Nothing built** |

### 2.1 Repository numbers confirmed

| Number | Source | Confirmed by |
| --- | --- | --- |
| 20 sample conversations, 10 Lead and 10 Case | `tests/sample_conversations.py` | Count and test run |
| 27 field-mapping rows | `docs/field-mapping.xlsx` | Sheet count (L-01–09, C-01–09, CS-01–09) |
| 1 platform event with 4 fields | `objects/Intake_Status__e` | File count |
| 7 retry signals | `integration/retry_matrix.py` | Rule count |
| 22 Python tests | `tests/` (3 + 7 + 3 + 3 + 6) | `python -m unittest discover -s tests`: OK |
| 6 fault drills | `tests/test_fault_drills.py` | `python -m tests.test_fault_drills`: 6 pass |
| 10 validation rules, 4 flows, 2 queues, 1 permission set, 7 custom fields on Lead and Case | `force-app/` | File count and XML parse |
| 2 Apex classes (resource and test) | `classes/` | File count. Not compiled |

## 3. Verification performed for this documentation

| Check | Method | Result |
| --- | --- | --- |
| Python suite | `python -m unittest discover -s tests` | 22 passed |
| Fault drills | `python -m tests.test_fault_drills` | 6 passed. Output recorded in [FAULT_DRILLS.md](FAULT_DRILLS.md) |
| Metadata well-formed | Parsed all 32 XML files | 0 errors |
| Code read line by line | `outbox.py`, `retry_matrix.py`, `sf_auth.py`, `sf_client.py`, `subscriber.py`, `monitor.py`, the Apex class and test, all flows, rules, and the permission set | Basis for findings F1–F27 |
| Field mapping | The 27 workbook rows compared with `build_payload` | 4 match, 9 partial, 6 differ, 8 not stored by design ([FIELD_MAPPING_GUIDE.md](FIELD_MAPPING_GUIDE.md)) |
| Requirements | 34 BR, 8 FR, 7 NFR, 12 user stories traced | [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) |
| Salesforce behaviour | Salesforce documentation | Daily API limit returns 403 `REQUEST_LIMIT_EXCEEDED`. High-volume events are retained for 72 hours. `Sforce-Auto-Assign` defaults to TRUE when missing. Updates that stop meeting entry conditions cancel scheduled paths. Platform event triggers retry at most 9 times |
| Not possible | Deploy, Apex test run, org tests, live CometD, real token issuance | No org available |

## 4. Deliverables by milestone

| Milestone | Deliverable | Status |
| --- | --- | --- |
| M1 Discovery and policy | Requirements, process maps, decision log D1–D6, workbook, 13 assumptions, 16 open questions | Written. D1–D5 not approved |
| M2 Org configuration | Fields, 10 validation rules, 2 queues, permission set, 2 assignment flows | Source. Not deployed |
| M3 Integration | Outbox, OAuth client, upsert client | Tested locally |
| M4 Status sync | Event, 2 publisher flows, subscriber, Apex catch-up | Subscriber tested locally. Apex not executed |
| M5 Reliability | Retry matrix, 6 fault drills, monitor | Tested locally |
| M6 Handover | Admin guide, demo script, flow diagrams, this documentation set | Written |

## 5. Findings

Severity: **High** blocks a safe go-live. **Medium** should be fixed before production. **Low** is an improvement or a documentation fix.

| ID | Severity | Area | Finding | Effect | Recommendation | Detail |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | High | Retry | Salesforce reports the daily API limit as **403 `REQUEST_LIMIT_EXCEEDED`**. The matrix dead-letters every 403. The drill simulates 429 | A limit event dead-letters the whole queue | Classify by `errorCode`, back off, pause the worker | [ERROR_HANDLING.md](ERROR_HANDLING.md) G1 |
| F2 | High | Sharing | Replay upserts need the integration user to see queue-owned records | Under Private OWD, updates fail with `DUPLICATE_VALUE` and are lost | Criteria-based sharing rule on `Intake_Ref__c` | [IDEMPOTENCY.md](IDEMPOTENCY.md) §6 |
| F3 | High | Identity | The run-as user needs API Enabled, which the permission set doesn't grant | Token and API calls fail | Integration licence and the "Minimum Access – API Only Integrations" profile | [ARCHITECTURE.md](ARCHITECTURE.md) §5 |
| F4 | Medium | Retry | Transient errors inside a 4xx (for example `UNABLE_TO_LOCK_ROW`) are dead-lettered | Spurious dead letters | Classify by `errorCode` | G3 |
| F5 | Medium | Operations | Dead Letter rows can't be re-queued, even with a corrected payload | US-10 AC4 unmet | `--requeue` command. Reopen on a changed payload | G4 |
| F6 | Medium | Data quality | Email is stripped but not lowercased | Weakens the designed exact-email match (BR-08) | Lowercase at the producer | [FIELD_MAPPING_GUIDE.md](FIELD_MAPPING_GUIDE.md) |
| F7 | Medium | Status sync | After an expired replay, catch-up asks only for known references | Records created during the outage are never learned | Add a `since` catch-up | [PLATFORM_EVENTS.md](PLATFORM_EVENTS.md) P1 |
| F8 | Low | Status sync | Gap between the catch-up snapshot and the `-1` subscription | A change in the window is missed until the next change | `since` sweep after subscribing | P2 |
| F9 | Medium | Apex REST | `LIMIT 200` per object, no `ORDER BY`, no continuation | Silent truncation after a big outage | Keyset pagination | P3 |
| F10 | Low | Security | The catch-up class is `without sharing` and doesn't enforce field-level security | Acceptable for 4 fields. Needs a documented reason | Revisit after F2 | [ARCHITECTURE.md](ARCHITECTURE.md) §5 |
| F11 | Low | Flows | No fault paths | A task failure rolls back the record | Keep strict, or log and continue | G9 |
| F12 | Medium | Lifecycle | Converted Leads reject updates, and `Intake_Ref__c` isn't mapped on conversion | Late replays dead-letter. The reference is lost after conversion | Conversion mapping. Treat converted as terminal | G6, T21 |
| F13 | Low | Events | About two events per create (insert, then owner change). Not measured | Allocation planning | Measure with T18 | P7 |
| F14 | Low | Events | CometD rather than the Pub/Sub API | Works, but isn't the current recommended API | Migrate behind the same interface | P5 |
| F15 | Low | Auth | Token lifetime defaults to 3,600 s when `expires_in` is absent | The real lifetime follows session settings. The 401 refresh covers it | Document. Optionally read the org's timeout | [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) §3.1 |
| F16 | Medium | Scope | M1 policy is ahead of the build: consent, confidence bands, Mixed, P1–P4, Contact match, history | A demo could over-promise | Keep the designed-versus-built table current | [SOLUTION_DESIGN.md](SOLUTION_DESIGN.md) §10 |
| F17 | Low | Documentation | The workbook still uses `Intake_Id__c` and maps the summary to Description | Conflicts with D6 | Update the workbook | [FIELD_MAPPING_GUIDE.md](FIELD_MAPPING_GUIDE.md) |
| F18 | Low | Documentation | `docs/flow-design.md` §5 says there are no Apex classes or events | Stale after M4 | Update | [FLOW_DESIGN.md](FLOW_DESIGN.md) §8 |
| F19 | Low | Retry | `Retry-After` has no ceiling | A large value parks a row | Cap at one hour | G7 |
| F20 | Low | Status sync | `seen_replay` is never pruned | Slow growth | Prune beyond retention | P6 |
| F21 | Low | Concurrency | No row claim for concurrent workers | Duplicate sends (harmless to data), wrong attempt counts | Run one worker, or claim rows | [IDEMPOTENCY.md](IDEMPOTENCY.md) §7 |
| F22 | Low | Data | Case `Origin` isn't set. The channel goes to `Intake_Channel__c` | Standard Case reports by Origin miss intake | Map channel to Origin, if values align | [FIELD_MAPPING_GUIDE.md](FIELD_MAPPING_GUIDE.md) |
| F23 | Medium | Dependency | Flows hard-code `Open - Not Contacted` and `New` (OQ-08) | If renamed, scheduled checks never match | Confirm values. Custom metadata | [FLOW_DESIGN.md](FLOW_DESIGN.md) §8 |
| F24 | Medium | Operations | No alerting | Dead letters are seen only when someone looks | Alert on Dead Letter > 0 and a stale subscriber | G8 |
| F25 | Low | Traceability | `RouteError` reasons aren't persisted | BR-30 relies on the agent | Store rejections | G5 |
| F26 | High | Integration | The client doesn't send `Sforce-Auto-Assign: FALSE`. Salesforce runs active Lead and Case assignment rules on REST creates and updates when the header is missing | In an org with an active rule, an update could reassign a worked record. On insert the flow overrides it, at the cost of extra owner changes and events | Send the header on every upsert. Org test T23 | [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) §5.1 |
| F27 | High (unverified) | Flows | The scheduled paths share the entry formula `ISNEW() OR ISCHANGED(Intake_Ref__c)`, which is false on every later save. Salesforce documents that pending scheduled paths are cancelled when an update stops meeting the entry conditions | Escalation and Case monitoring may never fire after any edit, possibly including the flow's own owner update | Separate scheduled-path flows with a stable condition. Org test T22 | [FLOW_DESIGN.md](FLOW_DESIGN.md) §8 |

### 5.1 Pattern behind the high findings

All five high findings (F1's real error code, F2, F3, F26, F27) are about **how Salesforce behaves in an org**, which a local stand-in can't show. The code is sound for the contract it was tested against. The lesson is that a stand-in should be built from the platform's documented error codes and automation rules, and that the first sandbox run is where these must be proven.

## 6. Readiness gates

| Gate | Criteria | Status |
| --- | --- | --- |
| G-A Policy | D1–D5 signed. OQ-02, OQ-05, OQ-07, OQ-08 closed for the slices going live | Not met |
| G-B Sandbox deploy | F1, F2, F3, F26, F27 fixed or designed. Live status values confirmed | Not met |
| G-C Sandbox verified | Apex test passes. T1–T23 recorded. Smoke test steps 1–7 pass. Drills 1, 3, 4, 6 repeated | Not started |
| G-D UAT | Walkthroughs A–H pass with reps and agents | Not started |
| G-E Production | Alerting (F24), re-queue (F5), runbook walkthrough, training done | Not started |

## 7. Recommended next sprint

| Order | Item | Findings | Size |
| ---: | --- | --- | --- |
| 1 | Send `Sforce-Auto-Assign: FALSE`. Add a test asserting the header | F26 | Small |
| 2 | Classify 403 `REQUEST_LIMIT_EXCEEDED` and lock errors by `errorCode`. Add drills 5b and 8 | F1, F4 | Small |
| 3 | Split scheduled paths into their own flows with a stable condition | F27 | Small |
| 4 | Sharing rule and integration user profile in the deploy package and runbook | F2, F3 | Small |
| 5 | Re-queue command and reopen-on-change | F5 | Small |
| 6 | Catch-up by `since`, ordering, continuation | F7, F8, F9 | Medium |
| 7 | Lowercase email. Map channel to Case Origin | F6, F22 | Small |
| 8 | Deploy to a developer sandbox, run the Apex test and T1–T23 | All org-side | Medium |
| 9 | Alerting on the monitor output | F24 | Medium |

## 8. Documentation set delivered

| Document | Purpose |
| --- | --- |
| [README.md](README.md) | Entry point, evidence tags, run and deploy commands, known gaps |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Problem, outcomes, stakeholders, phases |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Context, components, sequence, security, order of execution, platform options |
| [SOLUTION_DESIGN.md](SOLUTION_DESIGN.md) | Decisions, decision tables, designed versus built, risks |
| [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) | Org setup, auth, contracts, operations, smoke test |
| [FIELD_MAPPING_GUIDE.md](FIELD_MAPPING_GUIDE.md) | 27 rows compared with the build |
| [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) | BR, FR, NFR, and user stories to build and test |
| [ERROR_HANDLING.md](ERROR_HANDLING.md) | Taxonomy, retry matrix, runbook, gaps G1–G9 |
| [IDEMPOTENCY.md](IDEMPOTENCY.md) | Three layers and their configuration dependencies |
| [PLATFORM_EVENTS.md](PLATFORM_EVENTS.md) | Event design, subscriber, catch-up, gaps P1–P7 |
| [FLOW_DESIGN.md](FLOW_DESIGN.md) | Flow inventory, diagrams, validation rules, T1–T23 |
| [CONSULTANT_PLAYBOOK.md](CONSULTANT_PLAYBOOK.md) | Workshops, RACI, go-live checklist, training |
| [FAULT_DRILLS.md](FAULT_DRILLS.md) | Six drills with recorded output, coverage map, proposed drills |
| [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) | 150 questions across five areas |
| [PORTFOLIO_SUMMARY.md](PORTFOLIO_SUMMARY.md) | One-page summary for reviewers |
| [RESUME_BULLETS.md](RESUME_BULLETS.md) | Accurate resume lines with an accuracy checklist |
| PROJECT_COMPLETION_REPORT.md | This report |

## 9. Sign-off

| Role | Name | Decision | Date |
| --- | --- | --- | --- |
| Prepared by | Nilesh P Raghavan | Submitted | 24 November 2026 |
| Sales Manager (D1, D2, Lead rules) | | Pending | |
| Support Lead (D5, Case rules) | | Pending | |
| Legal / Privacy (D3, D4) | | Pending | |
| Salesforce Admin (deploy readiness) | | Pending | |
| Integration owner (F1, F2, F3, F26, F27) | | Pending | |

This is a portfolio project. The sign-off block shows the approvals a client engagement would need. None has been given.
