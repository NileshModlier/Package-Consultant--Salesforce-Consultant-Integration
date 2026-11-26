# Requirements Traceability Matrix

> **Evidence boundary.** Requirements come from `docs/requirements.md` (M1, *Draft, not approved for build*). Status reflects the source in this repository on 24 November 2026. **Tested locally** means the Python suite exercised it against stand-ins. Org tests (T1–T23) and the Apex test are **not executed**, so no row is marked "verified in org".

---

## 1. Legend

| Status | Meaning |
| --- | --- |
| **Built · tested** | Implemented and exercised by a passing Python test |
| **Built** | Implemented in metadata or Python. Only org tests cover it, and they haven't run |
| **Partial** | Part of the rule is implemented. The rest is named |
| **Upstream** | Belongs to the AI intake agent, which isn't in this repository |
| **Not built** | Designed only |

## 2. Summary

| Set | Total | Built · tested | Built | Partial | Upstream | Not built |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Business rules (BR) | 34 | 2 | 7 | 11 | 3 | 11 |
| Functional requirements (FR) | 8 | 1 | 1 | 4 | 0 | 2 |
| Non-functional requirements (NFR) | 7 | 1 | 0 | 2 | 0 | 4 |

The build (M2–M5) concentrates on **commit integrity**: reference, idempotency, assignment, status return, and failure handling. The **policy gates** (consent, confidence, match, Mixed, P-scale) are designed and wait on open questions OQ-02, OQ-05, OQ-07, and OQ-08.

## 3. Business rules

### Identity and receipt

| Rule | Statement (short) | Status | Evidence |
| --- | --- | --- | --- |
| BR-01 | Assign the id once, never replace it | Partial | Assignment is upstream. `Intake_Ref_Immutable` blocks change or clearing. `_valid_ref` enforces the format before queueing |
| BR-02 | Receipt confirms receipt only | Upstream | Customer messaging |
| BR-03 | Email, name, and summary required. A Lead also needs company and last name | Partial | `build_payload`: summary always, and a Lead needs name, company, and email. A Case accepts a missing email or name |
| BR-04 | Don't invent email, last name, or company | Built | `build_payload` raises `RouteError` instead of substituting |
| BR-30 | Validation failure creates no record. The reason stays visible | Partial | `RouteError` is raised synchronously and nothing is stored. A Salesforce 400 becomes a Dead Letter with `last_error`. The `RouteError` reason isn't persisted |
| BR-31 | No partial record if commit fails | Built | Salesforce save is atomic. Flow Custom Error rolls back. The outbox only marks Synced after 2xx |

### Consent and classification

| Rule | Statement (short) | Status | Evidence |
| --- | --- | --- | --- |
| BR-05 | Granted consent before any Lead write | Not built | No consent attribute |
| BR-06 | Exactly one of Sales, Support, Mixed | Partial | `classify` returns Lead or Case. Both or neither raises `RouteError`. **Mixed isn't supported** |
| BR-07 | Confidence ≥ 0.70 is Auto, otherwise Review | Not built | n/a |
| BR-15 | Not a Fit creates no Lead | Not built | n/a |
| BR-21 | Review-band inferred priority capped at P3 | Not built | n/a |

### Match and duplicates

| Rule | Statement (short) | Status | Evidence |
| --- | --- | --- | --- |
| BR-08 | Normalized email is the only match key | Not built | Email trimmed, not lowercased, and never matched |
| BR-09 | Lead and Case decision tables are the authority | Not built | n/a |
| BR-10 | Intake never creates or updates Contact or Account | Built | No code path, and `Intake_Integration` has no Contact or Account permission |
| BR-11 | A name disagreement is a sales conflict, never a rewrite | Not built | n/a |
| BR-12 | Write a Lead only on an allowed sales path | Partial | Every "sales inquiry" with name, company, and email writes a Lead |
| BR-13 | One open Lead and no Contact updates that Lead | Not built | Upsert is by reference, not by email |
| BR-14 | Any Contact blocks the automatic Lead | Not built | n/a |
| BR-18 | One Lead and one Case may share an id. Never two of one object | Built · tested | Unique external id per object (metadata). Outbox `UNIQUE(intake_ref, object_api_name)`. `test_twenty_conversations_route_and_replay_without_duplicates` |
| BR-19 | A replay creates no second record or append | Built · tested | External-id upsert. `test_oauth_and_twenty_conversations_replay_to_one_record_each`, duplicate-submission drill |
| BR-28 | Sales Manager disposition. A timeout never creates a Lead | Not built | No hold store (OQ-04) |

### Case, priority, and status

| Rule | Statement (short) | Status | Evidence |
| --- | --- | --- | --- |
| BR-16 | A valid support request becomes a Case. Contact lookup on exactly one match | Partial | Case route built and tested. Contact lookup not built |
| BR-17 | Mixed with all gates passed gives one Case and one Lead | Not built | Mixed raises `RouteError` |
| BR-20 | Store P1–P4, plus the Rating and Priority crosswalk | Partial | Case `Priority` High, Medium, or Low only. No P-scale, no Lead Rating |
| BR-22 | P1 and P2 urgent path, P3 and P4 standard | Partial | High → urgent task and the 4-hour clock. One queue for all (D6) |
| BR-23 | A blank Contact lookup still routes by priority | Built | `Case_Intake_Handling` routes every intake Case to Support Tier 1 |
| BR-24 | Lead starts Open - Not Contacted, Case starts New. Never a closed status | Built | `Status` is never sent. Org defaults apply. Depends on OQ-08 |
| BR-32 | Search by id finds a Lead, a Case, and history | Partial | `Intake_Ref__c` is an indexed external id on both objects. No history field |

### Write order and retention

| Rule | Statement (short) | Status | Evidence |
| --- | --- | --- | --- |
| BR-25 | Assign → normalize → validate → consent → classify → match → commit | Partial | Normalize, validate, classify, and commit are built. Consent and match aren't |
| BR-26 | A placeholder would be needed, so no Lead | Built | `RouteError` |
| BR-27 | Subject is a 120-character excerpt with an ellipsis | Built | `_subject` |
| BR-29 | Holds and failures visible, P1 and P2 first | Partial | Dead Letter rows and the monitor. No priority ordering, no hold store |
| BR-33 | Retention: CRM per client, raw text 24 months | Upstream | No raw text is stored in Salesforce. Outbox payloads hold the summary only. No purge job |
| BR-34 | Never ask for secrets. Remove them before commit | Upstream | No redaction in this repository |

## 4. Functional requirements

| ID | Requirement | Stories | Status | Note |
| --- | --- | --- | --- | --- |
| FR-1 | One id per submission, truthful receipt | US-01, US-10 | Partial | Id format and immutability built. Receipt upstream |
| FR-2 | Sales contact needs consent. Support doesn't | US-02, US-05, US-11 | Not built | n/a |
| FR-3 | Lead only on the allowed sales path | US-03, US-04, US-11, US-12 | Partial | Route by phrase only |
| FR-4 | Valid support becomes a Case. Contact lookup on a single match | US-05, US-09, US-12 | Partial | Case built. Lookup not |
| FR-5 | Ambiguous matches and missing consent stay visible | US-04, US-08 | Not built | n/a |
| FR-6 | P1–P4 preserved and routes the Case | US-05, US-09 | Partial | Three-level Priority drives the task and clock |
| FR-7 | Id stays searchable and is never replaced | US-06, US-10, US-12 | Built · tested | Immutable validation (metadata). Replay keeps one record (tested) |
| FR-8 | No Contact or Account create or overwrite | US-04, US-12 | Built | Permission set and code |

## 5. Non-functional requirements

| ID | Requirement | Status | Note |
| --- | --- | --- | --- |
| NFR-1 | Traceability: every committed record carries its creating id | Partial | Creating id yes. History of later ids no |
| NFR-2 | Idempotence: a replay is safe | Built · tested | Three layers. See [IDEMPOTENCY.md](IDEMPOTENCY.md) |
| NFR-3 | Privacy: consent default Unanswered, no secrets stored | Partial | Secrets (client secret, token) never persisted. Consent not built |
| NFR-4 | Audit: intake value and human override both retained | Not built | Field History Tracking or a governed attribute is the likely fix |
| NFR-5 | P1 and P2 failures and holds shown first | Not built | The monitor lists dead letters in id order |
| NFR-6 | English assumed | Not built | Assumption A-03. No language handling exists |
| NFR-7 | Accessibility, uptime, retention tooling are later-phase | Not built | Named only |

## 6. User stories

| Story | Role | Built acceptance criteria | Gaps |
| --- | --- | --- | --- |
| US-01 Submit once, keep a reference | Customer | AC1 format and immutability. AC4 the same id on correction (outbox accepts a changed payload for the same reference) | AC2 and AC3 receipt wording (upstream). AC5 id uniqueness across requests (upstream) |
| US-02 Separate consent | Customer | None | Consent not built |
| US-03 Start from a complete Lead | Sales Rep | AC2 name split, company, email, summary. No placeholders | Qualification, priority, explicit status. AC1 match gates |
| US-04 Already known | Sales Rep | AC5 replay doesn't duplicate | AC1–AC4 match rules |
| US-05 Case with the request | Support Agent | AC1 Case regardless of consent. AC5 Subject excerpt | AC2 and AC3 Contact lookup and identity line. AC4 P-scale |
| US-06 Stable reference | Support Agent | AC1 the id survives status changes (immutable rule). AC3 a shared id across Lead and Case is allowed. AC4 never created closed | AC2 history search. AC5 appended ids |
| US-07 Qualification visibility | Sales Manager | AC4 all intake Leads land in Inbound Sales | AC1–AC3, AC5 |
| US-08 Ambiguous disposition | Sales Manager | None | Hold store (OQ-04) |
| US-09 Route by priority | Support Lead | AC3 no topic is needed. AC4 blank Contact still routed | AC1 and AC2 on the P-scale (High is the only urgent signal). AC5 cap |
| US-10 Failures stay visible | Support Lead | AC5 a retry after success makes no second Case. AC3 no Case is claimed on failure (Dead Letter) | AC4 **a corrected payload can't re-queue a Dead Letter row** (finding F5) |
| US-11 Classify first | AI Intake Agent | AC1 exactly one route (Lead or Case) | Bands, Mixed, Not a Fit |
| US-12 Normalize and match | AI Intake Agent | AC2 name split and company collapse. AC4 placeholder refusal. AC5 replay | AC2 email lowercase. AC3 match |

## 7. Integration capabilities (M3–M5) to tests

| Capability | Test | Result |
| --- | --- | --- |
| OAuth client credentials, 20 conversations, one record each | `test_integration.test_oauth_and_twenty_conversations_replay_to_one_record_each` | Pass |
| 408, 429, and 5xx retry then one upsert | `test_integration.test_retry_408_429_and_5xx_then_one_upsert` | Pass |
| Retryable vs network failure classification | `test_integration.test_client_classifies_retryable_and_network_failures` | Pass |
| Route 20 and replay without duplicates | `test_idempotency.test_twenty_conversations_route_and_replay_without_duplicates` | Pass |
| Retryable failure then success keeps one record | `test_idempotency.test_retryable_failure_then_success_keeps_one_record` | Pass |
| `Retry-After` honoured | `test_idempotency.test_retry_after_waits` | Pass |
| Repeated 429 ends in Dead Letter with no record | `test_idempotency.test_repeated_429_becomes_dead_letter_without_a_record` | Pass |
| Permanent error is Dead Letter at once | `test_idempotency.test_permanent_error_is_dead_letter_immediately` | Pass |
| Changed payload updates the same external id | `test_idempotency.test_changed_payload_updates_the_same_external_id` | Pass |
| HTTP upsert updates in place | `test_idempotency.UpsertHttpTests.test_same_external_id_is_updated_in_place` | Pass |
| Matrix: each signal maps to one action | `test_retry_matrix.test_each_listed_signal_maps_to_one_action` | Pass |
| Backoff doubles. 429 uses `Retry-After` | `test_retry_matrix.test_429_uses_retry_after_and_other_retries_double` | Pass |
| Monitor counts | `test_retry_matrix.DashboardTests.test_snapshot_counts_queue_retries_and_dead_letters` | Pass |
| Duplicate replay id applied once | `test_status_sync.test_duplicate_replay_id_is_applied_once` | Pass |
| Replay continues after the cursor | `test_status_sync.test_replay_continues_after_the_stored_cursor` | Pass |
| Restart from SQLite skips seen events | `test_status_sync.test_restart_from_sqlite_skips_events_already_seen` | Pass |
| Expired replay id: catch-up, then new events | `test_status_sync.test_expired_replay_id_uses_catch_up_then_new_events` | Pass |
| CometD batch parsing, old cursor rejected | `test_status_sync.test_cometd_batch_parses_replay_id_and_rejects_an_old_cursor` | Pass |
| Catch-up calls the Apex resource | `test_status_sync.test_catch_up_request_reads_the_apex_resource` | Pass |
| Six fault drills | `test_fault_drills.test_each_fault_recovers_as_the_matrix_requires` | Pass |
| Expired token refreshes once | `test_fault_drills.test_expired_token_refreshes_once` | Pass |
| Second 401 is Dead Letter | `test_fault_drills.test_second_401_is_dead_letter` | Pass |

22 of 22 passed on the re-run of 24 November 2026.

## 8. Org-side verification still owed

| Area | Test | Status |
| --- | --- | --- |
| Assignment, tasks, validation, uniqueness, immutability, least privilege | T1–T12, T17 in [FLOW_DESIGN.md](FLOW_DESIGN.md) | Not executed |
| Scheduled paths | T13–T16 | Not executed |
| Catch-up endpoint | `IntakeStatusResourceTest` (2 methods) | Not executed |
| Event publish after commit, owner name after assignment | Admin guide §8 step 3 | Not executed |
| Replay upsert on a queue-owned record | INTEGRATION_GUIDE §9 step 7 (added in review) | Not executed |
