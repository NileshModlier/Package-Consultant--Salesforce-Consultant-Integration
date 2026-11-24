# Project website copy

Use these blocks in order. Do not add a client logo, a testimonial, or a production claim. This package has not been deployed to a Salesforce org.

## Headline

Intake to Salesforce, with one reference and a way back.

## Subhead

A portfolio integration that turns a finished conversation into one Lead or one Case, then returns status without creating a second record.

## The problem

Inbound requests get rekeyed into Salesforce. The same person becomes a second Lead. Support cases arrive thin, or stay in a mailbox. Nobody can quote a reference that points at the record they already have.

## The approach

Write the policy before the metadata. A Lead is for a net-new commercial request. A Case is for service. Contact is not overwritten. The commit is a PATCH on an external id, so a replay updates the same row. Status returns on a platform event after the save commits. Calls that cannot succeed go to Dead Letter instead of looping.

## What is in the package

- Twelve user stories and a decision log that records the options that were turned down.
- Salesforce DX source: fields, validation, two queues, four flows, one platform event, and a catch-up Apex REST class.
- A Python outbox, client-credentials client, event subscriber, retry matrix, and a one-shot monitor.
- Twenty sample conversations, twenty-two local tests, and six fault drills.

## Proof you can check

The README table is counted from the repository. The tests run with `python -m unittest discover -s tests`. The diagrams are drawn from the metadata. They are not screenshots from a Salesforce org.

## Stack

Salesforce API 62.0, record-triggered flows, platform events, Apex REST, and Python 3.11 using the standard library.

## Close

The policy is still proposed. An administrator can deploy the manifest when an org and its real status values are confirmed.
