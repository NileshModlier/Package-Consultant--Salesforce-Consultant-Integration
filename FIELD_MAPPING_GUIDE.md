# Field Mapping Guide

> **Evidence boundary.** The 27-row workbook (`docs/field-mapping.xlsx`) is the **designed** M1 field contract. It is marked *Draft, do not import* and isn't approved. The **as-built** payload in `integration/outbox.py` implements part of it, under the M2 names from decision D6. This guide shows both and every difference. Sample people and companies are illustrative, and addresses use `example.com`.

---

## 1. How to read this guide

| Column | Meaning |
| --- | --- |
| **ID** | Workbook row: `L-` Lead, `C-` Contact, `CS-` Case |
| **Intake field** | One of the nine intake fields: `intake_id`, `email`, `name`, `company`, `summary`, `qualification`, `priority`, `status`, `contact_lookup` |
| **Designed target** | Salesforce field in the workbook (M1 names) |
| **As built** | What the M3 payload or M2 metadata actually does |
| **Gap** | ✓ matches · ◐ partly · ✗ not built · — deliberately not stored |

Write order every time, per BR-25: assign id → normalize → validate → record consent → classify → match → commit.

## 2. Lead (L-01 to L-09)

| ID | Intake field | Designed target | Designed rule | As built | Gap |
| --- | --- | --- | --- | --- | :---: |
| L-01 | intake_id | `Intake_Id__c`, Text(40), unique | Assign once, never replace. Later ids go to history | `Intake_Ref__c` external id, unique, case-insensitive, immutable by validation. Sent on the URL, not in the body. No history field | ◐ |
| L-02 | email | `Email` | Trim and lowercase. Reject blank or no `@`. No placeholder | Trimmed only. Blank raises `RouteError`. **Not lowercased**, no `@` check | ◐ |
| L-03 | name | `FirstName`, `LastName` | Collapse spaces, split on the first space. A single token is LastName only | As designed | ✓ |
| L-04 | company | `Company` | Collapse spaces. Required. No placeholder. No Account | As designed. Blank raises `RouteError` | ✓ |
| L-05 | summary | `Description` with a 4-line header | Header, divider, customer's words. Append on L7. Remove secrets | `Intake_Summary__c` (D6), whitespace collapsed. No header. No secret removal in this repository | ◐ |
| L-06 | qualification | `Qualification__c` picklist | Intake sets only Unqualified or Sales Ready | Not built. `Qualification_Reason__c` exists for the rep at Closed - Not Converted | ✗ |
| L-07 | priority | `Intake_Priority__c` and `Rating` | P1–P4 stored. Rating Hot, Hot, Warm, Cold | Not sent for Leads | ✗ |
| L-08 | status | `Status` | Create at Open - Not Contacted. Never reset on update | Not sent. The org default applies on create, and a replay can't reset it | ◐ |
| L-09 | contact_lookup | Not written | Blank. Don't write `ConvertedContactId` | Not written | — |

## 3. Contact (C-01 to C-09): compare only, never written

| ID | Intake field | Designed rule | As built | Gap |
| --- | --- | --- | --- | :---: |
| C-01 | intake_id | Not stored on Contact | Not stored | — |
| C-02 | email | Normalize and exact-match as the match key. Never update | Matching not built | ✗ |
| C-03 | name | Compare only. A disagreement is a sales conflict | Not built | ✗ |
| C-04 | company | No Account create, no AccountId choice | Not touched | — |
| C-05 | summary | Not stored | Not stored | — |
| C-06 | qualification | Not stored | Not stored | — |
| C-07 | priority | Not stored | Not stored | — |
| C-08 | status | Not stored | Not stored | — |
| C-09 | contact_lookup | Contact Id is the output of exactly one match, used for `Case.ContactId` | Not built | ✗ |

Every Contact row says "do not write". The as-built integration has no Contact permission and never queries Contact, so it can't violate BR-10. It also can't link a Case to a Contact yet.

## 4. Case (CS-01 to CS-09)

| ID | Intake field | Designed target | Designed rule | As built | Gap |
| --- | --- | --- | --- | --- | :---: |
| CS-01 | intake_id | `Intake_Id__c` | Creating id, unique per Case | `Intake_Ref__c`, same constraints as Lead | ✓ |
| CS-02 | email | `SuppliedEmail` | Normalized email, even when ContactId is set | Trimmed email if present. Not lowercased | ◐ |
| CS-03 | name | `SuppliedName` | Full name as submitted | Whitespace-collapsed full name if present | ✓ |
| CS-04 | company | `SuppliedCompany`. `AccountId` copied from a linked Contact only | Company may be blank | `SuppliedCompany` if present. AccountId never set | ◐ |
| CS-05 | summary | `Subject` and `Description` | Subject is the first 120 characters with an ellipsis. Description has the header and the summary | Subject as designed. Summary in `Intake_Summary__c` (D6) | ◐ |
| CS-06 | qualification | Not stored | n/a | Not stored | — |
| CS-07 | priority | `Intake_Priority__c` and `Priority` | P1–P4. Priority High, High, Medium, Low. Review-band inference capped at P3 | `Priority` High, Medium, or Low from input, else keywords, else Medium. Required by validation. No P1–P4 | ◐ |
| CS-08 | status | `Status` | Create at New. Never set later states | Not sent. The org default applies | ◐ |
| CS-09 | contact_lookup | `ContactId` | Exactly one Contact match, otherwise blank | Not built. Always blank | ✗ |

## 5. Coverage summary

| Object | Rows | ✓ | ◐ | ✗ | — |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lead | 9 | 2 | 4 | 2 | 1 |
| Contact | 9 | 0 | 0 | 3 | 6 |
| Case | 9 | 2 | 5 | 1 | 1 |
| **Total** | **27** | **4** | **9** | **6** | **8** |

The as-built payload covers the **commit mechanics** (reference, identity text, summary, channel, priority for Cases). It leaves out the **policy attributes** (consent, qualification, P1–P4, Contact match). Those depend on the upstream agent and on open questions OQ-02, OQ-05, OQ-07, and OQ-08.

## 6. Fields the integration never sends

| Field | Why |
| --- | --- |
| `OwnerId` | The assignment flow owns it. A replay must not pull a record off its queue |
| `Status` | Salesforce owns the lifecycle. A replay must not move a record backward |
| `Intake_Ref__c` (in the body) | It's the external id on the URL |
| `ContactId`, `AccountId` | Matching isn't built. BR-10 forbids Account creation |
| `Description` | Reserved for people (D6) |

## 7. Value crosswalks (designed)

| Topic | From | To |
| --- | --- | --- |
| Priority | P1 · P2 · P3 · P4 | Lead Rating Hot · Hot · Warm · Cold. Case Priority High · High · Medium · Low |
| Lead status | Create (L8) | Open - Not Contacted |
| Lead status | Update (L7) | Unchanged |
| Lead status | Closed Lead found (L6) | No write, no reopen |
| Case status | Create | New |
| Qualification | Rubric met / not met / Not a Fit | Sales Ready / Unqualified / no Lead. Never Disqualified |
| Name | `Jordan Lee` · `Lee` | Jordan / Lee · (blank) / Lee |
| Email | `  Jordan.Lee@Example.com  ` | `jordan.lee@example.com` |
| Company | `Northline   Analytics` | `Northline Analytics` |
| Subject | Summary longer than 120 characters | First 117 characters + `...` |
| Consent | Granted · Declined · Unanswered | Lead rules continue · L3 (no Lead) · L3 (no Lead). The Case is unaffected |

As built: name, company, and Subject transformations match. Email isn't lowercased. Priority uses three values without the P-scale.

## 8. Governed attributes (designed, not built)

These don't fit the nine-field matrix, but a build must not drop them.

| ID | Attribute | Values | Owner |
| --- | --- | --- | --- |
| GA-01 | Sales consent status | Granted, Declined, Unanswered | Customer |
| GA-02 | Consent timestamp | Date/time | AI Intake Agent |
| GA-03 | Consent channel | Web, Email, Chat, Phone | AI Intake Agent |
| GA-04 | Consent statement version | Text | Sales Manager |
| GA-05 | Classification | Sales, Support, Mixed | AI Intake Agent |
| GA-06 | Band and priority source | Auto or Review. Customer stated or agent inferred | AI Intake Agent |
| GA-07 | Intake value and human override | Value pair | Sales Manager |
| GA-08 | Intake id history | Later ids, each once | AI Intake Agent |
| GA-09 | Review disposition and reason | Link, Update, Create, Reject | Sales Manager |
| GA-10 | Failure reason and last step | Text | Support Lead |

The as-built Dead Letter row (`last_error`, `attempts`) partly covers GA-10 for commit failures.

## 9. Metadata reference (as built)

| Object | Field | Type | Constraints |
| --- | --- | --- | --- |
| Lead, Case | `Intake_Ref__c` | Text(40) | External id. Unique. Not case-sensitive. Not required. Format rule `^INT-[0-9]{8}-[0-9]{4}$`. Immutable once set |
| Lead, Case | `Intake_Summary__c` | Long text 5,000 | Required when the reference is set |
| Lead, Case | `Intake_Channel__c` | Restricted picklist | Web, Email, Chat, Phone. Required when the reference is set |
| Lead | `Qualification_Reason__c` | Long text 5,000 | Required when an intake Lead is Closed - Not Converted |
| Case | `Priority` (standard) | Picklist | Required when the reference is set |
| `Intake_Status__e` | `Intake_Ref__c`, `Object_Type__c` | Text(40) | n/a |
| `Intake_Status__e` | `Status__c`, `Owner_Name__c` | Text(255) | n/a |

Validation rules apply only when `Intake_Ref__c` is populated, so Leads and Cases created outside intake are unaffected.

## 10. Recommended mapping changes before build

| # | Change | Rows | Rationale |
| ---: | --- | --- | --- |
| 1 | Lowercase email in `build_payload` | L-02, CS-02 | BR-08 makes the normalized email the only match key |
| 2 | Map `Intake_Channel__c` to standard `Case.Origin` (and `Lead.LeadSource` if the business agrees) | CS-05 adjunct | Standard reports, assignment, and Omni-Channel use Origin. The permission set already grants both fields |
| 3 | Add `Intake_Priority__c` (P1–P4) and Lead `Rating` | L-07, CS-07 | Standard fields collapse P1 and P2 |
| 4 | Lead field mapping for `Intake_Ref__c` on conversion (to a non-unique Contact or Opportunity text field) | L-01 | The reference otherwise stays on a read-only converted Lead, and BR-32 search loses it |
| 5 | Update the workbook to the D6 names (`Intake_Ref__c`, `Intake_Summary__c`) | All | The workbook still shows `Intake_Id__c` and Description |
