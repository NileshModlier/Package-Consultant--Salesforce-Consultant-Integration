# Admin guide

| | |
|---|---|
| Project | Intake-to-Salesforce CRM Integration |
| Phase | M6 — Handover |
| Document | What an administrator deploys and how the worker is run |
| Version | 0.1 |
| Date | 24 November 2026 |
| Related | [Architecture](architecture.md), [Flow design](flow-design.md), [Solution design](solution-design.md) |

This guide is the runbook for a Salesforce administrator and the person who starts the Python worker. The metadata in this repository has not been deployed. The commands below are the ones to use when an org is authorized. A successful read of the XML is not a passing org test.

## 1. Before deploy

Confirm these points with the business. They are still open in the solution design.

- Lead Status and Case Status match the values the flows test. The lead escalation looks for `Open - Not Contacted`. The case clocks look for `New`. If the org renamed those values, the flows deploy and the scheduled paths do not fire.
- Sales consent, duplicate matching against existing Contacts, and Account creation are policy. They are not implemented in the Python upsert. The sample worker classifies on the phrases "sales inquiry" and "support request" and writes the payload fields only.
- API version in `sfdx-project.json` and `manifest/package.xml` is 62.0.

Create a dedicated integration user. Assign the permission set `Intake_Integration` after deploy. Do not use a system administrator as the run-as user for the connected app.

## 2. Deploy

From the repository root, with the Salesforce CLI authenticated to the target org:

```text
sf project deploy start --manifest manifest/package.xml
```

The manifest deploys:

| Metadata | Names |
|---|---|
| Apex classes | `IntakeStatusResource`, `IntakeStatusResourceTest` |
| Platform event | `Intake_Status__e` and its four fields |
| Lead fields | `Intake_Ref__c`, `Intake_Summary__c`, `Intake_Channel__c`, `Qualification_Reason__c` |
| Case fields | `Intake_Ref__c`, `Intake_Summary__c`, `Intake_Channel__c` |
| Validation rules | Five on Lead, five on Case |
| Queues | `Inbound_Sales`, `Support_Tier_1` |
| Permission set | `Intake_Integration` |
| Flows | `Lead_Intake_Handling`, `Case_Intake_Handling`, `Lead_Status_Publisher`, `Case_Status_Publisher` |

Then run `IntakeStatusResourceTest` in the org. The class inserts one Lead and one Case and calls the catch-up endpoint. That run has not happened in this package.

The diagrams in `docs/flow-design.md` and `docs/architecture.md` are drawn from the metadata. They are not Flow Builder screenshots.

## 3. What the flows do

`Lead_Intake_Handling` and `Case_Intake_Handling` run after save, trigger order 10, when Intake Ref is set on create or when the reference changes. A missing queue rolls the save back. The lead queue is Inbound Sales. The case queue is Support Tier 1. Each path creates a task. Lead escalation is a task at 24 hours if the status is still Open - Not Contacted. Case monitoring is a task at 4 hours for a High case still New, and at 24 hours for any intake case still New.

`Lead_Status_Publisher` and `Case_Status_Publisher` run at trigger order 20. They publish `Intake_Status__e` when an intake record is created or when status or owner changes. Publish behavior on the event is Publish After Commit.

## 4. Permission set

`Intake_Integration` can create, read, and edit Lead and Case, including the intake fields. It can read `Intake_Status__e` and call `IntakeStatusResource`. It cannot delete, view all, or modify all. It cannot create the platform event. The publisher flows run in system context, so the integration user does not need create rights on the event.

The catch-up class is `without sharing` because the user loses the record when the flow moves it to a queue.

## 5. External Client App

Create an External Client App in the org. Enable the client credentials flow and set the run-as user to the integration user. The app is not in the metadata. Store the client id and secret outside the repository. This project reads them only from the environment:

| Variable | Purpose |
|---|---|
| `SF_CLIENT_ID` | Consumer key |
| `SF_CLIENT_SECRET` | Consumer secret |
| `SF_TOKEN_URL` | Token endpoint, usually `https://<my-domain>/services/oauth2/token` |
| `SF_API_VERSION` | Optional. Defaults to 62.0 |
| `INTAKE_OUTBOX_PATH` | Optional. Defaults to `intake_outbox.sqlite` |
| `INTAKE_STATUS_PATH` | Optional. Defaults to `intake_status.sqlite` |

The secret is not written to the outbox and is not printed by the worker.

## 6. Run the worker and the subscriber

Python 3.11 is enough. The integration uses the standard library.

Deliver ready outbox rows once:

```text
python -m integration.outbox
```

The worker prints `processed`, `synced`, `retrying`, and `dead_letter`. Rows in Retrying wait until `next_attempt_at`. A 429 uses the `Retry-After` header when Salesforce sends one. Other retries wait 1, 2, 4, then 8 seconds, capped at 60. Attempt 5 is Dead Letter. A validation error and a rejected secret are Dead Letter on the first failure. A 401 on the API refreshes the token once inside the client.

Read one batch of status events:

```text
python -c "from integration.sf_auth import SalesforceAuth; from integration.subscriber import SalesforceCatchUp, SalesforceEventSource, StatusStore, StatusSubscriber; store = StatusStore(); stats = StatusSubscriber(store, SalesforceEventSource(SalesforceAuth.from_env()), SalesforceCatchUp(SalesforceAuth.from_env())).run_once(); print(stats); store.close()"
```

That call is one batch. It is not a daemon. If the stream is down, the replay cursor stays where it was.

Print the current counts:

```text
python -m integration.monitor
```

The monitor reads once. It does not poll, page, or restart a worker.

SQLite files are gitignored. Delete a local file only when you intend to drop the cursor and the outbox history.

## 7. What the upsert writes

Lead: FirstName when present, LastName, Company, Email, Intake Summary, Intake Channel.

Case: Subject, Priority, Intake Summary, Intake Channel, and Supplied Email, Name, and Company when the conversation has them.

Neither payload sends Status, OwnerId, or Intake Ref in the body. The reference is the external id on the URL. A second PATCH with the same reference updates that record.

## 8. Checks after the first deploy

Use one sales conversation and one support conversation from `tests/sample_conversations.py`.

1. The Lead is owned by Inbound Sales and has a review task. The Case is owned by Support Tier 1 and has the task that matches its priority.
2. A second run of the same conversation does not create a second Lead or Case.
3. Changing the Lead status publishes an `Intake_Status__e` with that status and the owner name.
4. `GET /services/apexrest/intake/status?refs=INT-20261124-0001` returns the Lead. Add the Case reference in the same parameter when you want both.
5. A bad Intake Ref format, or a cleared reference, fails validation.
6. Closing an intake Lead as Closed - Not Converted without Qualification Reason fails validation.

Stop there. Do not treat the local Python suite as a substitute for these org checks.
