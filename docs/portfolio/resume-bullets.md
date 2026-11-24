# Resume bullets

Use the bullets that match the role. Keep the last sentence available for the interview. Do not combine these into a claim that the integration is in production.

- Designed an intake-to-Salesforce policy with 12 user stories, 34 business rules, and a decision log covering Lead versus Contact, duplicates, consent, retention, and case routing.
- Built Salesforce DX source for API 62.0: external-id fields on Lead and Case, 10 validation rules, 2 queues, 4 record-triggered flows, the platform event `Intake_Status__e`, and an Apex REST catch-up class.
- Implemented a Python outbox that upserts by `Intake_Ref__c`, so 20 sample conversations replay to 10 Leads and 10 Cases with no second record.
- Returned Salesforce status to the intake agent with replay ids, duplicate-event suppression, and catch-up when a replay id expires.
- Specified a 7-signal retry matrix and verified 6 fault drills: wrong secret, network failure, validation failure, duplicate submission, API limit, and a down subscriber.
- Automated 22 Python tests against a local HTTP stand-in. Salesforce metadata in the package has not been deployed to an org.
