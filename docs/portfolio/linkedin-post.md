# LinkedIn post

Post this as written, or shorten the middle. Do not add a client name, a percentage, or a claim that an org is live.

I finished a portfolio piece I can walk through end to end: Intake-to-Salesforce.

The problem I designed for is the usual one. Inbound conversations get rekeyed, the same person becomes a second Lead, and support cannot quote a reference.

The rule I kept: a sales inquiry becomes one Lead, a support request becomes one Case, and a replay updates that record instead of inserting another. The upsert is a PATCH on an external id. Status comes back on a platform event after the Salesforce save commits. A bad secret or a validation error goes to Dead Letter. A timeout, a 429, a server error, or a dropped network connection retries on a fixed schedule. If the event subscriber is down, it keeps its replay cursor.

The package has 20 sample conversations, 27 field mappings, 22 local tests, and 6 fault drills. The Salesforce metadata is source. I have not deployed it to an org, and I will say that before I say anything else in an interview.

Happy to walk the decision log, the flows, or the retry matrix.

#Salesforce #Integration #CRM
