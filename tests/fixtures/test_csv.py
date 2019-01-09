# coding: utf-8

import pytest
from app.api.csv import generate_brief_responses_csv

brief_response_data_1 = {
    "supplierName": "K,ev’s \"Bu,tties",
    "specialistName": "Bu,tties K,ev’s \"",
    "availability": "❝Next — Tuesday❞",
    "dayRate": "1.49",
    "essentialRequirements": [True, True],
    "niceToHaveRequirements": [True, False, False],
    "respondToEmailAddress": "test1@email.com",
}

brief_response_data_2 = {
    "supplierName": "Kev\'s \'Pies",
    "specialistName": "\'Pies Kev\'s",
    "availability": "&quot;A week Friday&rdquot;",
    "dayRate": "3.50",
    "essentialRequirements": [True, True],
    "niceToHaveRequirements": [False, True, False],
    "respondToEmailAddress": "te,st2@email.com",
}

brief_response_data_3 = {
    "supplierName": "@SUM(1+1)*cmd|' /C calc'!A0",
    "specialistName": "@SUM(1+1)*cmd|' /C calc'!A0",
    "availability": "=cmd| '/c calc'!A0",
    "dayRate": ",=2+2,",
    "essentialRequirements": [True, True],
    "niceToHaveRequirements": [False, False, True],
    "respondToEmailAddress": "+SUM(1+1)*cmd|' /C calc'!A0",
}

brief_response_data_4 = {
    "supplierName": "K,ev’s \"Bu,tties",
    "availability": "❝Next — Tuesday❞",
    "essentialRequirements": [True, True],
    "niceToHaveRequirements": [True, False, False],
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
        u'Seller name,Test Supplier1',
        u'Email,test1@email.com',
        u'Specialist Name,"Bu,tties K,ev\u2019s """',
        u'Availability Date,\u275dNext \u2014 Tuesday\u275e',
        u'Day rate,1.49',
        u'ABN,1',
        u'MS Paint,True',
        u'GIMP,True',
        u'LISP,True'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_2}], indirect=True)
def test_csv_handles_tricky_characters_2(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        u'Seller name,Test Supplier1',
        u'Email,"te,st2@email.com"',
        u"Specialist Name,'Pies Kev's",
        u'Availability Date,&quot;A week Friday&rdquot;',
        u'Day rate,3.50',
        u'ABN,1',
        u'MS Paint,True',
        u'GIMP,True',
        u'LISP,False'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_3}], indirect=True)
def test_csv_handles_tricky_characters_3(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        u'Seller name,Test Supplier1',
        u"Email,SUM(1+1)*cmd|' /C calc'!A0",
        u"Specialist Name,SUM(1+1)*cmd|' /C calc'!A0",
        u"Availability Date,cmd| '/c calc'!A0",
        u'Day rate,"2+2,"',
        u'ABN,1',
        u'MS Paint,True',
        u'GIMP,True',
        u'LISP,False'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_4}], indirect=True)
@pytest.mark.parametrize('briefs', [{'lot_slug': 'training', 'framework_slug': 'digital-marketplace'}], indirect=True)
def test_csv_training(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        u'Seller name,Test Supplier1',
        u'Email,test1@email.com',
        u'Availability Date,\u275dNext \u2014 Tuesday\u275e',
        u'Phone number,1234',
        u'ABN,1',
        u'MS Paint,True',
        u'GIMP,True',
        u'LISP,True'
    ]
    assert csvdata.splitlines() == lines


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data_5}], indirect=True)
@pytest.mark.parametrize('briefs', [{'lot_slug': 'rfx', 'framework_slug': 'digital-marketplace'}], indirect=True)
def test_csv_rfx(app, briefs, brief_responses):
    csvdata = generate_brief_responses_csv(briefs[0], brief_responses)
    lines = [
        u'Seller name,Test Supplier1',
        u'Email,test1@email.com',
        u'Phone number,1234',
        u'ABN,1'
    ]
    assert csvdata.splitlines() == lines
