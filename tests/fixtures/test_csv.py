# coding: utf-8

import pytest
from app.api.csv import generate_brief_responses_csv

brief_response_data_1 = {
    "supplierName": "K,ev’s \"Bu,tties",
    "specialistGivenNames": "Bu,tties",
    "specialistSurname": "K,ev’s \"",
    "availability": "❝Next — Tuesday❞",
    "dayRate": "1.49",
    "essentialRequirements": {
        "TEST": "x",
        "TEST 2": "y"
    },
    "niceToHaveRequirements": [],
    "respondToEmailAddress": "test1@email.com",
    "supplier": {
        "data": {
            "contact_phone": "123"
        }
    }
}

brief_response_data_2 = {
    "supplierName": "Kev\'s \'Pies",
    "specialistGivenNames": "Kev\'s",
    "specialistSurname": "\'Pies",
    "availability": "&quot;A week Friday&rdquot;",
    "dayRate": "3.50",
    "essentialRequirements": {
        "TEST": "x",
        "TEST 2": "y"
    },
    "niceToHaveRequirements": [],
    "respondToEmailAddress": "te,st2@email.com",
    "supplier": {
        "data": {
            "contact_phone": "123"
        }
    }
}

brief_response_data_3 = {
    "supplierName": "@SUM(1+1)*cmd|' /C calc'!A0",
    "specialistGivenNames": "@SUM(1+1)*cmd|'",
    "specialistSurname": "/C calc'!A0",
    "availability": "=cmd| '/c calc'!A0",
    "dayRate": ",=2+2,",
    "essentialRequirements": {
        "TEST": "x",
        "TEST 2": "y"
    },
    "niceToHaveRequirements": [],
    "respondToEmailAddress": "+SUM(1+1)*cmd|' /C calc'!A0",
    "supplier": {
        "data": {
            "contact_phone": "123"
        }
    }
}

brief_response_data_4 = {
    "supplierName": "K,ev’s \"Bu,tties",
    "availability": "❝Next — Tuesday❞",
    "essentialRequirements": {
        "TEST": "x",
        "TEST 2": "y"
    },
    "niceToHaveRequirements": [],
    "respondToEmailAddress": "test1@email.com",
    "respondToPhone": '1234'
}

brief_response_data_5 = {
    "supplierName": "K,ev’s \"Bu,tties",
    "respondToEmailAddress": "test1@email.com",
    "respondToPhone": '1234'
}


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_1}], indirect=True)
def test_csv_handles_tricky_characters_1(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1',
        'Email,test1@email.com',
        'Specialist given name(s),"Bu,tties"',
        'Specialist surname,"K,ev\u2019s """',
        'Availability date,\u275dNext \u2014 Tuesday\u275e',
        'Day rate (including GST),1.49',
        'Day rate (excluding GST),',
        'Previous agency experience,',
        'Security clearance,N/A',
        'Contact number,123',
        'TEST,x',
        'TEST 2,y',
        'LISP,',
        'Australian Capital Territory Labour hire licence,',
        'Australian Capital Territory Labour hire licence expiry,',
        'Queensland Labour hire licence,',
        'Queensland Labour hire licence expiry,',
        'Victoria Labour hire licence,',
        'Victoria Labour hire licence expiry,'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_2}], indirect=True)
def test_csv_handles_tricky_characters_2(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1',
        'Email,"te,st2@email.com"',
        "Specialist given name(s),Kev's",
        "Specialist surname,'Pies",
        'Availability date,&quot;A week Friday&rdquot;',
        'Day rate (including GST),3.50',
        'Day rate (excluding GST),',
        'Previous agency experience,',
        'Security clearance,N/A',
        'Contact number,123',
        'TEST,x',
        'TEST 2,y',
        'LISP,',
        'Australian Capital Territory Labour hire licence,',
        'Australian Capital Territory Labour hire licence expiry,',
        'Queensland Labour hire licence,',
        'Queensland Labour hire licence expiry,',
        'Victoria Labour hire licence,',
        'Victoria Labour hire licence expiry,'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_3}], indirect=True)
def test_csv_handles_tricky_characters_3(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1',
        "Email,SUM(1+1)*cmd|' /C calc'!A0",
        "Specialist given name(s),SUM(1+1)*cmd|'",
        "Specialist surname,/C calc'!A0",
        "Availability date,cmd| '/c calc'!A0",
        'Day rate (including GST),"2+2,"',
        'Day rate (excluding GST),',
        'Previous agency experience,',
        'Security clearance,N/A',
        'Contact number,123',
        'TEST,x',
        'TEST 2,y',
        'LISP,',
        'Australian Capital Territory Labour hire licence,',
        'Australian Capital Territory Labour hire licence expiry,',
        'Queensland Labour hire licence,',
        'Queensland Labour hire licence expiry,',
        'Victoria Labour hire licence,',
        'Victoria Labour hire licence expiry,'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_5}], indirect=True)
@pytest.mark.parametrize('briefs', [{'lot_slug': 'rfx', 'framework_slug': 'digital-marketplace'}], indirect=True)
def test_csv_rfx(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1',
        'Email,test1@email.com',
        'Phone number,1234'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_5}], indirect=True)
@pytest.mark.parametrize('briefs', [{'lot_slug': 'training2', 'framework_slug': 'digital-marketplace'}], indirect=True)
def test_csv_training2(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1',
        'Email,test1@email.com',
        'Phone number,1234'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': {
    'specialistGivenNames': 'foo',
    'specialistSurname': 'bar',
    'availability': 'in the future',
    'dayRateExcludingGST': '10',
    'dayRate': '11',
    'securityClearance': 'Yes',
    'visaStatus': 'AustralianCitizen',
    'previouslyWorked': 'Yes',
    'respondToEmailAddress': 'test1@email.com',
    'essentialRequirements': {
        'ess critiera 1': 'ess criteria 1 answer',
        'ess critiera 2': 'ess criteria 2 answer'
    }
}}], indirect=True)
@pytest.mark.parametrize('briefs', [{
    'lot_slug': 'specialist',
    'framework_slug': 'digital-marketplace',
    'data': {
        'preferredFormatForRates': 'dailyRate',
        'securityClearance': 'mustHave',
        'securityClearanceCurrent': 'nv1',
        'includeWeightingsEssential': False,
        'essentialRequirements': [{
            'criteria': 'ess critiera 1',
        }, {
            'criteria': 'ess critiera 2'
        }],
        'niceToHaveRequirements': []
    }
}], indirect=True)
def test_csv_specialist_daily_rate(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1', 'Email,test1@email.com',
        'Specialist given name(s),foo',
        'Specialist surname,bar',
        'Availability date,in the future',
        'Day rate (including GST),11',
        'Day rate (excluding GST),10',
        'Eligibility to work,Australian citizen',
        'Previous agency experience,Yes',
        'Holds a negative vetting level 1 security clearance,Yes',
        'Contact number,123',
        'ess critiera 1,ess criteria 1 answer',
        'ess critiera 2,ess criteria 2 answer',
        'Australian Capital Territory Labour hire licence,',
        'Australian Capital Territory Labour hire licence expiry,',
        'Queensland Labour hire licence,',
        'Queensland Labour hire licence expiry,',
        'Victoria Labour hire licence,',
        'Victoria Labour hire licence expiry,'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': {
    'specialistGivenNames': 'foo',
    'specialistSurname': 'bar',
    'availability': 'in the future',
    'hourRateExcludingGST': '10',
    'hourRate': '11',
    'securityClearance': 'Yes',
    'visaStatus': 'AustralianCitizen',
    'previouslyWorked': 'Yes',
    'respondToEmailAddress': 'test1@email.com',
    'essentialRequirements': {
        'ess critiera 1': 'ess criteria 1 answer',
        'ess critiera 2': 'ess criteria 2 answer'
    }
}}], indirect=True)
@pytest.mark.parametrize('briefs', [{
    'lot_slug': 'specialist',
    'framework_slug': 'digital-marketplace',
    'data': {
        'preferredFormatForRates': 'hourlyRate',
        'securityClearance': 'ability',
        'securityClearanceObtain': 'nv1',
        'includeWeightingsEssential': False,
        'essentialRequirements': [{
            'criteria': 'ess critiera 1',
        }, {
            'criteria': 'ess critiera 2'
        }],
        'niceToHaveRequirements': [{
            'criteria': 'nth critiera 1',
        }]
    }
}], indirect=True)
def test_csv_specialist_hourly_rate(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        'Seller name,Test Supplier1',
        'ABN,1', 'Email,test1@email.com',
        'Specialist given name(s),foo',
        'Specialist surname,bar',
        'Availability date,in the future',
        'Hourly rate (including GST),11',
        'Hourly rate (excluding GST),10',
        'Eligibility to work,Australian citizen',
        'Previous agency experience,Yes',
        'Security clearance,N/A',
        'Contact number,123',
        'ess critiera 1,ess criteria 1 answer',
        'ess critiera 2,ess criteria 2 answer',
        'nth critiera 1,',
        'Australian Capital Territory Labour hire licence,',
        'Australian Capital Territory Labour hire licence expiry,',
        'Queensland Labour hire licence,',
        'Queensland Labour hire licence expiry,',
        'Victoria Labour hire licence,',
        'Victoria Labour hire licence expiry,'
    ]
    assert csvdata.splitlines() == lines
