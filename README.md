# Intake-to-Salesforce

An intake conversation becomes one Salesforce Lead or one Case, and status changes come back to the intake agent.

The sales path is a Lead for a net-new commercial request. The support path is a Case. Both are upserted on `Intake_Ref__c`, so a replay updates the same record. After the save commits, `Intake_Status__e` carries the reference, the object, the status, and the owner name. A failed call follows a fixed retry matrix. A call the matrix cannot recover goes to Dead Letter.

This repository is the portfolio package for that design. The Salesforce metadata is source. It has not been deployed to an org. The Python tests ran against a local HTTP stand-in. Decisions D1–D5 in the solution design are still proposed, and the as-is process is a baseline to confirm in a workshop.

## Metrics

Counted from this repository on 24 November 2026.

| Measure | Count |
|---|---|
| Sample conversations | 20 |
| Field-mapping rows | 27 |
| Conversations routed to Lead | 10 |
| Conversations routed to Case | 10 |
| Platform event | 1, with 4 fields |
| Retry-matrix signals | 7 |
| Python tests | 22, all passing locally |
| Fault drills | 6 |

The Apex test class is in source and has not been run. Details and the boundary of each count are in [docs/solution-design.md](docs/solution-design.md).

## Layout

| Path | What it is |
|---|---|
| [docs/solution-design.md](docs/solution-design.md) | Policy, decision log, and phases M1–M6 |
| [docs/architecture.md](docs/architecture.md) | Architecture, sequence, Lead, Case, and platform-event diagrams |
| [docs/admin-guide.md](docs/admin-guide.md) | Deploy, permission set, and how to run the worker |
| [docs/demo-script.md](docs/demo-script.md) | Five-minute demo, architecture walkthrough, failure recovery |
| [docs/interview-guide.md](docs/interview-guide.md) | 50 Salesforce, 25 integration, and 25 consultant questions |
| [docs/flow-design.md](docs/flow-design.md) | M2 flow inventory |
| [docs/requirements.md](docs/requirements.md) | Twelve user stories |
| [docs/field-mapping.xlsx](docs/field-mapping.xlsx) | Lead, Contact, and Case mapping |
| [force-app/](force-app/) | Salesforce DX source, API 62.0 |
| [integration/](integration/) | Auth, client, outbox, subscriber, retry matrix, monitor |
| [tests/](tests/) | Sample conversations and the Python suite |

Portfolio wording for a site, a LinkedIn post, a resume, and the GitHub About line is in [docs/portfolio/](docs/portfolio/).

## Run the tests

Python 3.11. No third-party packages are required for the suite.

```text
python -m unittest discover -s tests
```

Deliver ready outbox rows when `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, and `SF_TOKEN_URL` are set:

```text
python -m integration.outbox
```

Print queue counts, retry attempts, and dead letters:

```text
python -m integration.monitor
```

## Deploy

When an org is authorized:

```text
sf project deploy start --manifest manifest/package.xml
```

Then follow [docs/admin-guide.md](docs/admin-guide.md). The External Client App is created in the org. It is not in the metadata.
