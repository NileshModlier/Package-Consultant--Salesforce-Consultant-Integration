# Fault Drills

> **Evidence boundary.** The six drills ran **locally** against a `ThreadingHTTPServer` stand-in, an in-memory outbox, scripted CometD sources, and a closed TCP port. They didn't run against Salesforce. Results below are from re-running `python -m tests.test_fault_drills` on 24 November 2026, and they match the repository's demo script line for line.

---

## 1. Purpose

A fault drill injects one failure, then proves three things: the system **classifies** it correctly, it **doesn't lose or duplicate** data, and it **recovers** (or parks the work visibly) without human guesswork.

| Drill | Failure injected | Layer | Matrix signal |
| ---: | --- | --- | --- |
| 1 | Wrong client secret | Token endpoint | 7 · Dead Letter |
| 2 | Network failure | Transport | 6 · Retry |
| 3 | Validation failure | REST upsert | 5 · Dead Letter |
| 4 | Duplicate submission | Producer | Idempotency |
| 5 | API limit exceeded | REST upsert | 3 · Back off |
| 6 | Subscriber down | CometD | Defer, keep cursor |

Two related tests sit beside the six: an expired token that refreshes once, and a second 401 that dead-letters.

## 2. How to run

```bash
python -m tests.test_fault_drills                     # prints one line per drill
python -m unittest tests.test_fault_drills -v         # 3 test methods
```

## 3. Results (re-run 24 November 2026)

```text
pass  Wrong secret          Token endpoint 401 invalid_client      state=Dead Letter attempts=1 token_calls=1 patch_calls=0 dead_letter=1
pass  Network failure       Connection refused, then a live token endpoint   after_refusal=Retrying retrying=1 after_recovery=Synced synced=1 records=1
pass  Validation failure    PATCH 400 field validation             state=Dead Letter attempts=1 patch_calls=1 second_pass=0
pass  Duplicate submission  Same conversation accepted twice and replayed    enqueue=Pending duplicate_enqueue=Pending rows=1 records=1 replay=Synced replay_processed=0
pass  API limit exceeded    PATCH 429 with Retry-After 30 seconds  held=1 state=Retrying next=2026-11-24T12:00:30Z before_wait=0 after_wait=1 patch_calls=2
pass  Subscriber down       CometD connection refused, then one new event   deferred=True cursor_while_down=3 error=connection refused resumed_from=3 applied=1 status=Working - Contacted error_after=None
```

## 4. Drill by drill

### Drill 1 · Wrong secret

| | |
| --- | --- |
| Inject | Token endpoint answers 401 `invalid_client` |
| Expect | Permanent. No PATCH sent, because there's no token |
| Observed | Dead Letter on attempt 1. 1 token call. 0 PATCH calls |
| Why it's right | Retrying a bad secret can't succeed and may trip login lockouts |
| Operator action | Rotate or fix the External Client App secret, then re-queue |

### Drill 2 · Network failure

| | |
| --- | --- |
| Inject | Token URL points at a closed port (connection refused) |
| Expect | Retryable. The row waits, then succeeds when the network returns |
| Observed | Retrying, then Synced through a live stand-in. 1 record |
| Why it's right | No HTTP status means no evidence of a permanent problem |

### Drill 3 · Validation failure

| | |
| --- | --- |
| Inject | PATCH returns 400 `Priority is required` |
| Expect | Permanent, Dead Letter, one call only |
| Observed | Dead Letter after 1 attempt and 1 PATCH. The next pass processes nothing |
| Why it's right | The same payload fails the same rule every time |
| Operator action | Fix at the source. Re-queue is manual today (see [ERROR_HANDLING.md](ERROR_HANDLING.md) G4) |

### Drill 4 · Duplicate submission

| | |
| --- | --- |
| Inject | Accept the same conversation twice, deliver, accept again, deliver again |
| Expect | One outbox row, one record, the replay sends nothing |
| Observed | `rows=1 records=1 replay_processed=0` |
| Why it's right | The outbox key and canonical payload comparison absorb the duplicate before it costs an API call |

### Drill 5 · API limit exceeded (429)

| | |
| --- | --- |
| Inject | PATCH returns 429 with `Retry-After: 30` |
| Expect | Row held until the header's time. No early retry |
| Observed | Retrying until `12:00:30Z`. A pass before that processes 0. The pass at +30 s syncs. 2 PATCH calls |
| Why it's right | It honours the server's back-off hint |
| **Caveat (review)** | Salesforce's REST API reports the org's **daily API request limit as HTTP 403 `REQUEST_LIMIT_EXCEEDED`**, and its error reference doesn't list 429. This drill proves the 429 path for gateways or proxies that send it. It doesn't prove behaviour under a real Salesforce limit event, where the current matrix would **dead-letter** every row. See drill 5b |

### Drill 6 · Subscriber down

| | |
| --- | --- |
| Inject | CometD raises connection refused while the cursor is 3 |
| Expect | Deferred, cursor unchanged, error recorded. The next run resumes from 3 |
| Observed | `deferred=True`, cursor 3, error stored. The next run applies replay 4 (`Working - Contacted`). The error is cleared |
| Why it's right | Advancing the cursor without applying would lose events |

### Related tests

| Test | Observed |
| --- | --- |
| `test_expired_token_refreshes_once` | One API 401, token refreshed, synced. 2 token calls. Outbox attempts 0 |
| `test_second_401_is_dead_letter` | 401 twice. Dead Letter. 2 token calls, 2 PATCH calls |

## 5. Coverage map

| Failure class | Drilled | Unit-tested | Not covered |
| --- | :---: | :---: | --- |
| Bad credentials | ✓ | n/a | n/a |
| Token expiry | n/a | ✓ | n/a |
| Network loss | ✓ | ✓ | n/a |
| 408, 5xx | n/a | ✓ (`test_retry_408_429_and_5xx_then_one_upsert`) | n/a |
| 429 | ✓ | ✓ | n/a |
| Exhausted retries | n/a | ✓ (`test_repeated_429_becomes_dead_letter_without_a_record`) | n/a |
| Validation | ✓ | ✓ | n/a |
| Duplicate submission | ✓ | ✓ | n/a |
| Subscriber outage | ✓ | n/a | n/a |
| Replay id expired | n/a | ✓ | Expiry with refs created during the outage (P1) |
| Duplicate event | n/a | ✓ | n/a |
| **403 `REQUEST_LIMIT_EXCEEDED`** | ✗ | ✗ | Drill 5b below |
| **Record invisible to the integration user** | ✗ | ✗ | Drill 7 below |
| **Row lock (`UNABLE_TO_LOCK_ROW`)** | ✗ | ✗ | Drill 8 below |
| Converted Lead replay | ✗ | ✗ | Drill 9 below |
| Missing queue (flow Custom Error) | ✗ | ✗ | Org test T20 |

## 6. Proposed additional drills (design, not built)

| Drill | Inject | Expected with today's code | Expected after the fix |
| --- | --- | --- | --- |
| **5b · Real API limit** | PATCH 403 `[{"errorCode":"REQUEST_LIMIT_EXCEEDED","message":"TotalRequests Limit exceeded."}]` for 3 rows | All 3 Dead Letter on attempt 1 | All 3 stay Retrying. Worker pauses. Attempts not consumed |
| **7 · Invisible record** | First PATCH 201. Second PATCH with a changed payload returns 400 `DUPLICATE_VALUE` | Dead Letter. The update is lost | Prevented by a sharing rule. Drill asserts a clear `last_error` for triage |
| **8 · Row lock** | PATCH 400 `UNABLE_TO_LOCK_ROW`, then 201 | Dead Letter | Retrying, then Synced |
| **9 · Converted Lead** | PATCH 400 (cannot update converted Lead) | Dead Letter | Terminal with a reconciliation note |
| **10 · Catch-up gap** | Expired replay. Catch-up by refs. A new ref was created during the outage | The new ref is never learned | Second catch-up by `since` learns it |
| **11 · Re-queue** | Dead Letter row. The agent re-sends a corrected payload | Stays Dead Letter | Pending, then Synced |

## 7. Running drills against a sandbox

When an org exists, drills 1, 3, 4, and 6 can be repeated safely against a sandbox. Use a wrong secret, an intake Case without Priority, a duplicate delivery, and a stopped subscriber. Don't induce real API-limit exhaustion in a shared sandbox. Use drill 5b's stand-in instead.
