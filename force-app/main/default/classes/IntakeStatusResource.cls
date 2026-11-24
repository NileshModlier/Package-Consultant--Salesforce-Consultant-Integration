/**
 * Catch-up read for intake status when a platform-event replay id is no longer available.
 * Returns only the four event fields, and only for records that already have an intake reference.
 * without sharing is required because the integration user does not own the record after the queue assignment.
 */
@RestResource(urlMapping='/intake/status')
global without sharing class IntakeStatusResource {
    private static final Integer MAX_REFS = 200;

    @HttpGet
    global static void recover() {
        RestResponse response = RestContext.response;
        response.addHeader('Content-Type', 'application/json');
        try {
            String sinceRaw = RestContext.request.params.get('since');
            String refsRaw = RestContext.request.params.get('refs');
            Datetime sinceDt = parseSince(sinceRaw);
            Set<String> refs = parseRefs(refsRaw);
            if (refs == null) {
                writeError(response, 400, 'refs accepts at most 200 intake references');
                return;
            }
            if (sinceDt == null && refs.isEmpty()) {
                writeError(response, 400, 'Provide refs or since');
                return;
            }
            List<Item> items = new List<Item>();
            items.addAll(fromLeads(selectLeads(sinceDt, refs)));
            items.addAll(fromCases(selectCases(sinceDt, refs)));
            response.statusCode = 200;
            response.responseBody = Blob.valueOf(JSON.serialize(items));
        } catch (TypeException error) {
            writeError(response, 400, 'since must be an ISO-8601 UTC datetime');
        }
    }

    private static List<Lead> selectLeads(Datetime sinceDt, Set<String> refs) {
        if (!refs.isEmpty() && sinceDt != null) {
            return [
                SELECT Intake_Ref__c, Status, Owner.Name
                FROM Lead
                WHERE Intake_Ref__c IN :refs AND LastModifiedDate >= :sinceDt
                LIMIT 200
            ];
        }
        if (!refs.isEmpty()) {
            return [
                SELECT Intake_Ref__c, Status, Owner.Name
                FROM Lead
                WHERE Intake_Ref__c IN :refs
                LIMIT 200
            ];
        }
        return [
            SELECT Intake_Ref__c, Status, Owner.Name
            FROM Lead
            WHERE Intake_Ref__c != NULL AND LastModifiedDate >= :sinceDt
            LIMIT 200
        ];
    }

    private static List<Case> selectCases(Datetime sinceDt, Set<String> refs) {
        if (!refs.isEmpty() && sinceDt != null) {
            return [
                SELECT Intake_Ref__c, Status, Owner.Name
                FROM Case
                WHERE Intake_Ref__c IN :refs AND LastModifiedDate >= :sinceDt
                LIMIT 200
            ];
        }
        if (!refs.isEmpty()) {
            return [
                SELECT Intake_Ref__c, Status, Owner.Name
                FROM Case
                WHERE Intake_Ref__c IN :refs
                LIMIT 200
            ];
        }
        return [
            SELECT Intake_Ref__c, Status, Owner.Name
            FROM Case
            WHERE Intake_Ref__c != NULL AND LastModifiedDate >= :sinceDt
            LIMIT 200
        ];
    }

    private static List<Item> fromLeads(List<Lead> leads) {
        List<Item> items = new List<Item>();
        for (Lead record : leads) {
            items.add(item(record.Intake_Ref__c, 'Lead', record.Status, record.Owner.Name));
        }
        return items;
    }

    private static List<Item> fromCases(List<Case> cases) {
        List<Item> items = new List<Item>();
        for (Case record : cases) {
            items.add(item(record.Intake_Ref__c, 'Case', record.Status, record.Owner.Name));
        }
        return items;
    }

    private static Item item(String intakeRef, String objectType, String status, String ownerName) {
        Item row = new Item();
        row.intakeRef = intakeRef;
        row.objectType = objectType;
        row.status = status;
        row.ownerName = ownerName == null ? '' : ownerName;
        return row;
    }

    private static Datetime parseSince(String raw) {
        if (String.isBlank(raw)) {
            return null;
        }
        String normalized = raw.trim().replace('T', ' ');
        if (normalized.endsWith('Z')) {
            normalized = normalized.substring(0, normalized.length() - 1);
        }
        Integer dot = normalized.indexOf('.');
        if (dot > 0) {
            normalized = normalized.substring(0, dot);
        }
        return Datetime.valueOfGmt(normalized);
    }

    private static Set<String> parseRefs(String raw) {
        Set<String> refs = new Set<String>();
        if (String.isBlank(raw)) {
            return refs;
        }
        for (String part : raw.split(',')) {
            String ref = part.trim();
            if (String.isNotBlank(ref)) {
                refs.add(ref);
            }
        }
        if (refs.size() > MAX_REFS) {
            return null;
        }
        return refs;
    }

    private static void writeError(RestResponse response, Integer status, String message) {
        response.statusCode = status;
        response.responseBody = Blob.valueOf(JSON.serialize(new Map<String, String>{ 'error' => message }));
    }

    private class Item {
        public String intakeRef;
        public String objectType;
        public String status;
        public String ownerName;
    }

}
