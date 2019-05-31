import re
import six
import csvx
from io import StringIO
from collections import OrderedDict as od


def generate_brief_responses_csv(brief, responses):
    def csv_cell_sanitize(text):
        return re.sub(r"^(=|\+|-|@|!|\|{|}|\[|\]|<|,)+", '', unicode(text).strip())

    # converts a brief response into an ordered dict
    def row(r):
        answers = od()

        answers.update({'Seller name': r.supplier.name})
        answers.update({'ABN': r.supplier.abn})
        answers.update({'Email': r.data.get('respondToEmailAddress', 'UNKNOWN')})

        if brief.lot.slug == 'digital-professionals':
            answers.update({'Specialist name': r.data.get('specialistName', 'UNKNOWN')})
            answers.update({'Availability date': r.data.get('availability', 'UNKNOWN')})
            answers.update({'Day rate': r.data.get('dayRate', '')})
            answers.update({'Contact number': r.supplier.data.get('contact_phone', 'UNKNOWN')})
        elif brief.lot.slug == 'specialist':
            answers.update({'Specialist given name(s)': r.data.get('specialistGivenNames', 'UNKNOWN')})
            answers.update({'Specialist surname': r.data.get('specialistSurname', 'UNKNOWN')})
            answers.update({'Availability date': r.data.get('availability', 'UNKNOWN')})
            if brief.data['preferredFormatForRates'] == 'dailyRate':
                answers.update({'Day rate (including GST)': r.data.get('dayRate', '')})
                answers.update({'Day rate (excluding GST)': r.data.get('dayRateExcludingGST', '')})
            elif brief.data['preferredFormatForRates'] == 'hourlyRate':
                answers.update({'Hourly rate (including GST)': r.data.get('hourRate', '')})
                answers.update({'Hourly rate (excluding GST)': r.data.get('hourRateExcludingGST', '')})

            if r.data.get('visaStatus', '') == 'AustralianCitizen':
                answers.update({'Eligibility to work': 'Australian citizen'})
            elif r.data.get('visaStatus', '') == 'PermanentResident':
                answers.update({'Eligibility to work': 'Permanent resident'})
            elif r.data.get('visaStatus', '') == 'ForeignNationalWithAValidVisa':
                answers.update({'Eligibility to work': 'Foreign national with a valid visa'})

            answers.update({
                'Previous agency experience': r.data.get('previouslyWorked', '')
            })

            if brief.data['securityClearance'] == 'mustHave':
                securityClearance = ''
                if brief.data['securityClearanceCurrent'] == 'baseline':
                    securityClearance = 'baseline'
                elif brief.data['securityClearanceCurrent'] == 'nv1':
                    securityClearance = 'negative vetting level 1'
                elif brief.data['securityClearanceCurrent'] == 'nv2':
                    securityClearance = 'negative vetting level 2'
                elif brief.data['securityClearanceCurrent'] == 'pv':
                    securityClearance = 'positive vetting'
                answers.update({
                    'Holds a {} security clearance'.format(securityClearance): r.data.get('securityClearance', '')
                })
            else:
                answers.update({
                    'Security clearance': 'N/A'
                })

            answers.update({'Contact number': r.supplier.data.get('contact_phone', 'UNKNOWN')})
        elif brief.lot.slug == 'digital-outcome':
            answers.update({'Availability date': r.data.get('availability', 'UNKNOWN')})
            answers.update({'Day rate': r.data.get('dayRate', '')})
        elif brief.lot.slug == 'training':
            answers.update({'Availability date': r.data.get('availability', 'UNKNOWN')})
            answers.update({'Phone number': r.data.get('respondToPhone', '')})
        elif brief.lot.slug == 'rfx':
            answers.update({'Phone number': r.data.get('respondToPhone', '')})
        elif brief.lot.slug == 'atm':
            answers.update({'Availability date': r.data.get('availability', 'UNKNOWN')})
            answers.update({'Phone number': r.data.get('respondToPhone', '')})

        if brief.lot.slug in ['digital-professionals', 'digital-outcome', 'training']:
            ess_req_names = brief.data.get('essentialRequirements', [])
            nth_req_names = brief.data.get('niceToHaveRequirements', [])
            ess_responses = r.data.get('essentialRequirements', [''] * len(ess_req_names))
            nth_responses = [
                r.data.get('niceToHaveRequirements')[i]
                if i < len(r.data.get('niceToHaveRequirements', []))
                else '' for i in range(len(nth_req_names))
            ]
            answers.update(zip(ess_req_names, ess_responses))
            answers.update(zip(nth_req_names, nth_responses))

        if brief.lot.slug == 'specialist':
            for essential_requirement in brief.data['essentialRequirements']:
                essential_requirement_responses = r.data.get('essentialRequirements', {})
                key = essential_requirement['criteria']
                if (
                    essential_requirement_responses and
                    key in essential_requirement_responses.keys()
                ):
                    answers.update({key: essential_requirement_responses[key]})
                else:
                    answers.update({key: ''})

            for nice_to_have_requirement in brief.data['niceToHaveRequirements']:
                nice_to_have_requirement_responses = r.data.get('niceToHaveRequirements', None)
                key = nice_to_have_requirement['criteria']
                if (
                    nice_to_have_requirement_responses and
                    key in nice_to_have_requirement_responses.keys()
                ):
                    answers.update({key: nice_to_have_requirement_responses[key]})
                else:
                    answers.update({key: ''})

        if brief.lot.slug == 'atm':
            criteriaResponses = {}
            evaluationCriteriaResponses = r.data.get('criteria', {})
            if evaluationCriteriaResponses:
                for evaluationCriteria in brief.data['evaluationCriteria']:
                    if (
                        'criteria' in evaluationCriteria and
                        evaluationCriteria['criteria'] in evaluationCriteriaResponses.keys()
                    ):
                        criteriaResponses[evaluationCriteria['criteria']] =\
                            evaluationCriteriaResponses[evaluationCriteria['criteria']]
            if criteriaResponses:
                for criteria, response in criteriaResponses.items():
                    answers.update({criteria: response})

        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    # convert the responses to a list - each row is a dict representing a brief response
    rows = [row(_) for _ in responses]
    # add the keys of a dict as the first element in the rows list, to be used as headers
    first = rows[0].keys() if responses else []
    rows = [first] + [_.values() for _ in rows]
    # convert the rows to a zip'd list - this creates a structure so the csv's first column is the headers and the
    # remaining columns contain the data for each header row
    transposed = list(six.moves.zip_longest(*rows))
    csvdata = StringIO()
    with csvx.Writer(csvdata) as csv_out:
        csv_out.write_rows(transposed)
        return csvdata.getvalue()
