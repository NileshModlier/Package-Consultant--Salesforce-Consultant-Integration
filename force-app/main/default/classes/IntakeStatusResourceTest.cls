@IsTest
private class IntakeStatusResourceTest {
    @IsTest
    static void returnsLeadAndCaseForRefs() {
        insert new Lead(
            LastName = 'Lee',
            Company = 'Northline Analytics',
            Intake_Ref__c = 'INT-20261124-0001',
            Intake_Summary__c = 'Pricing for 40 seats',
            Intake_Channel__c = 'Email',
            Status = 'Working - Contacted'
        );
        insert new Case(
            Subject = 'Cannot log in',
            Priority = 'High',
            Intake_Ref__c = 'INT-20261124-0011',
            Intake_Summary__c = 'Cannot log in',
            Intake_Channel__c = 'Email',
            Status = 'New'
        );

        RestContext.request = new RestRequest();
        RestContext.response = new RestResponse();
        RestContext.request.params.put('refs', 'INT-20261124-0001,INT-20261124-0011');

        IntakeStatusResource.recover();

        System.assertEquals(200, RestContext.response.statusCode);
        List<Object> body = (List<Object>) JSON.deserializeUntyped(RestContext.response.responseBody.toString());
        System.assertEquals(2, body.size());
        Set<String> types = new Set<String>();
        for (Object row : body) {
            Map<String, Object> item = (Map<String, Object>) row;
            types.add((String) item.get('objectType'));
            System.assertNotEquals(null, item.get('status'));
            System.assertNotEquals(null, item.get('ownerName'));
        }
        System.assertEquals(new Set<String>{ 'Lead', 'Case' }, types);
    }

    @IsTest
    static void sinceExcludesOlderRecordsAndRejectsAMissingFilter() {
        Lead created = new Lead(
            LastName = 'Patel',
            Company = 'Harbor Co',
            Intake_Ref__c = 'INT-20261124-0002',
            Intake_Summary__c = 'Demo request',
            Intake_Channel__c = 'Web'
        );
        insert created;

        RestContext.request = new RestRequest();
        RestContext.response = new RestResponse();
        RestContext.request.params.put('since', '2099-01-01T00:00:00Z');
        IntakeStatusResource.recover();
        System.assertEquals(200, RestContext.response.statusCode);
        List<Object> future = (List<Object>) JSON.deserializeUntyped(RestContext.response.responseBody.toString());
        System.assertEquals(0, future.size());

        RestContext.request = new RestRequest();
        RestContext.response = new RestResponse();
        IntakeStatusResource.recover();
        System.assertEquals(400, RestContext.response.statusCode);
    }
}
