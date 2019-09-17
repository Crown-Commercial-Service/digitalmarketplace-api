import re
import six
import csvx
from io import StringIO
from collections import OrderedDict as od
import json


def csv_cell_sanitize(text):
    return re.sub(r"^(;|=|\+|-|@|!|\|{|}|\[|\]|<|,)+", '', unicode(text).strip())


def convert_to_csv(data, convertor_function, transpose=False):
    # convert the responses to a list - each row is a dict representing a brief response
    rows = [convertor_function(d) for d in data]
    # add the keys of a dict as the first element in the rows list, to be used as headers
    first = rows[0].keys() if data else []
    first = [f.replace('_', ' ').capitalize() if '_' in f else f for f in first]
    rows = [first] + [r.values() for r in rows]

    csvdata = StringIO()
    with csvx.Writer(csvdata) as csv_out:
        if transpose:
            # convert the rows to a zip'd list - this creates a structure so the csv's
            # first column is the headers and the
            # remaining columns contain the data for each header row
            transposed = list(six.moves.zip_longest(*rows))
            csv_out.write_rows(transposed)
        else:
            csv_out.write_rows(rows)
        return csvdata.getvalue()


def format_criteria(criteria):
    result = []
    for i in criteria:
        weighting = i.get('weighting', '')
        criterion = i.get('criteria')
        if criterion:
            if weighting:
                result.append(weighting + '%: ' + criterion)
            else:
                result.append(criterion)
    return ', '.join(result)


def format_response_criteria(criteria):
    if not criteria:
        return ''
    result = []
    for k, v in criteria.iteritems():
        result.append(k + ': ' + v)
    return ', '.join(result)


def format_sellers(sellers):
    if not sellers:
        return ''
    result = []
    for s in sellers:
        result.append(s.get('abn') + ': ' + s.get('name'))
    return ', '.join(result)


def generate_brief_responses_csv(brief, responses):
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
        elif brief.lot.slug in ['rfx', 'training2']:
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
            answers[k] = csv_cell_sanitize(v) if k not in ['essential_criteria'] else v

        return answers

    return convert_to_csv(responses, row, True)


def generate_seller_catalogue_csv(seller_catalogue):
    # converts a brief response into an ordered dict
    def row(r):
        answers = od()
        answers.update({'ABN': r['abn']})
        answers.update({'Seller name': r['name']})
        answers.update({'Contact email': r['contact_email']})
        answers.update({'Domain name': r['domains']})
        answers.update({'Recruiter status': r['recruiter_status']})
        answers.update({'Indigenous business': r.get('seller_type', {}).get('indigenous', '')})
        answers.update({'SME': r.get('seller_type', {}).get('sme', '')})
        number_of_employees = ''
        if r['number_of_employees'] == 'Sole trader':
            number_of_employees = '1 employee'
        elif r['number_of_employees']:
            number_of_employees = r['number_of_employees']
            number_of_employees = number_of_employees + ' employees'

        answers.update({'Number of employees': number_of_employees})
        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    return convert_to_csv(seller_catalogue, row)


def generate_seller_responses_csv(seller_responses):
    # converts a brief response into an ordered dict
    def row(r):
        answers = od()
        answers.update({'Response id': r['brief_response_id']})
        answers.update({'Opportunity id': r['brief_id']})
        answers.update({'Response type': r['slug']})
        answers.update({'Seller': r['supplier_name']})
        answers.update({'Seller ABN': r['supplier_abn']})

        if r['slug'] == 'digital-professionals':
            answers.update({'Candidate name': r['specialistName']})
            answers.update({'Availability': r['availability']})
            answers.update({'Daily rate': r['dayRate']})
            answers.update({'Hourly rate': ''})
            answers.update({'Contact number': r['respondToPhone']})
            answers.update({'Contact email': r['respondToEmailAddress']})
            ess_req_names = r.get('essentialRequirementsCriteria', [])
            ess_responses = r.get('essentialRequirements', [])
            ess_dict = dict(
                zip(
                    [er for er in ess_req_names],
                    [er for er in ess_responses or []]
                )
            )
            answers.update({'Response criteria': ess_dict})
            nth_req_names = r.get('niceToHaveRequirementsCriteria', [])
            nth_responses = r.get('niceToHaveRequirements', [])
            nth_dict = dict(
                zip(
                    [er for er in nth_req_names],
                    [er for er in nth_responses or []]
                )
            )
            answers.update({'Optional response criteria': nth_dict or {}})
            answers.update({'Work eligibility': ''})
            answers.update({'Previously worked for agency': ''})
            answers.update({'Meets clearance requirements': ''})

        elif r['slug'] == 'specialist':
            answers.update({'Candidate name': (r['specialistGivenNames'] + " " + r['specialistSurname'])})
            answers.update({'Availability': r['availability']})
            if r['preferredFormatForRates'] == 'dailyRate':
                answers.update({'Daily rate': r['dayRate']})
                answers.update({'Hourly rate': ''})
            elif r['preferredFormatForRates'] == 'hourlyRate':
                answers.update({'Daily rate': ''})
                answers.update({'Hourly rate': r['hourRate']})
            answers.update({'Contact number': ''})
            answers.update({'Contact email': r['respondToEmailAddress']})
            answers.update({'Response criteria': r['essentialRequirements']})
            answers.update({'Optional response criteria': r['niceToHaveRequirements']})
            if r['visaStatus'] == 'AustralianCitizen':
                answers.update({'Work eligibility': 'Australian citizen'})
            elif r['visaStatus'] == 'PermanentResident':
                answers.update({'Work eligibility': 'Permanent resident'})
            elif r['visaStatus'] == 'ForeignNationalWithAValidVisa':
                answers.update({'Work eligibility': 'Foreign national with a valid visa'})
            answers.update({'Previously worked for agency': r['previouslyWorked']})
            if r['securityClearance'] is None:
                answers.update({'Meets clearance requirements': 'None requested'})
            else:
                answers.update({'Meets clearance requirements': r['securityClearance']})

        elif r['slug'] == 'digital-outcome':
            answers.update({'Candidate name': ''})
            answers.update({'Availability': ''})
            answers.update({'Daily rate': ''})
            answers.update({'Hourly rate': ''})
            answers.update({'Contact number': ''})
            answers.update({'Contact email': r['respondToEmailAddress']})
            ess_req_names = r.get('essentialRequirementsCriteria', [])
            ess_responses = r.get('essentialRequirements', [])
            ess_dict = dict(
                zip(
                    [er for er in ess_req_names],
                    [er for er in ess_responses]
                )
            )
            answers.update({'Response criteria': ess_dict})

            nth_req_names = r.get('niceToHaveRequirementsCriteria') or []
            nth_responses = r.get('niceToHaveRequirements') or []
            nth_dict = dict(
                zip(
                    [er for er in nth_req_names],
                    [er for er in nth_responses]
                )
            )
            answers.update({'Optional response criteria': nth_dict})
            answers.update({'Work eligibility': ''})
            answers.update({'Previously worked for agency': ''})
            answers.update({'Meets clearance requirements': ''})

        elif r['slug'] in ['rfx']:
            answers.update({'Candidate name': ''})
            answers.update({'Availability': ''})
            answers.update({'Daily rate': ''})
            answers.update({'Hourly rate': ''})
            answers.update({'Contact number': r['respondToPhone']})
            answers.update({'Contact email': ''})
            answers.update({'Response criteria': {}})
            answers.update({'Optional response criteria': {}})
            answers.update({'Work eligibility': ''})
            answers.update({'Previously worked for agency': ''})
            answers.update({'Meets clearance requirements': ''})

        elif r['slug'] == 'atm':
            answers.update({'Candidate name': ''})
            answers.update({'Availability': r['availability']})
            answers.update({'Daily rate': ''})
            answers.update({'Hourly rate': ''})
            answers.update({'Contact number': r['respondToPhone']})
            answers.update({'Contact email': ''})
            answers.update({'Response criteria': r['criteria']})
            answers.update({'Optional response criteria': {}})
            answers.update({'Work eligibility': ''})
            answers.update({'Previously worked for agency': ''})
            answers.update({'Meets clearance requirements': ''})

        elif r['slug'] == 'training2':
            answers.update({'Candidate name': ''})
            answers.update({'Availability': ''})
            answers.update({'Daily rate': ''})
            answers.update({'Hourly rate': ''})
            answers.update({'Contact number': r['respondToPhone']})
            answers.update({'Contact email': r['respondToEmailAddress']})
            answers.update({'Response criteria': {}})
            answers.update({'Optional response criteria': {}})
            answers.update({'Work eligibility': ''})
            answers.update({'Previously worked for agency': ''})
            answers.update({'Meets clearance requirements': ''})
        answers.update({'Responded at': r['created_at']})

        answers.update({'Response criteria': format_response_criteria(answers['Response criteria'])})
        answers.update({
            'Optional response criteria': format_response_criteria(answers['Optional response criteria'])
        })

        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    return convert_to_csv(seller_responses, row)


def generate_specialist_opportunities_csv(specialist_opportunities):
    # converts a brief response into an ordered dict
    def row(r):
        answers = od()
        answers.update({'opportunity_id': r['id']})
        answers.update({'internal_reference': r['internalReference']})
        answers.update({'title': r['title']})
        answers.update({'buying_agency': r['organisation']})
        answers.update({'raised_by': r['email_address']})
        answers.update({'role_responsibilities': r['summary']})
        answers.update({'location': ', '.join(r['location'])})
        answers.update({'service': r['areaOfExpertise']})
        answers.update({'open_to': r['openTo']})
        answers.update({'number_of_sellers_approached': r['numberOfSuppliers']})
        answers.update({'sellers': format_sellers(r['sellers'])})
        answers.update({'essential_criteria': format_criteria(r.get('essentialRequirements') or '')})
        answers.update({'desirable_criteria': format_criteria(r.get('niceToHaveRequirements') or '')})
        answers.update({'evaluation_steps': ', '.join(r['evaluationType'])})
        answers.update({'rate_format': r['preferredFormatForRates']})
        answers.update({'max_rate_cap': r['maxRate']})
        answers.update({'security_clearance_requirement': r['securityClearance']})
        answers.update({'start_date': r['startDate']})
        answers.update({'contract_length': r['contractLength']})
        answers.update({'contract_extension': r['contractExtensions']})
        answers.update({'awarded_to': r['awarded_to']})
        answers.update({'time_draft_created': r['created_at']})
        answers.update({'time_published': r['published_at']})
        answers.update({'time_closed': r['closed_at']})
        answers.update({'time_awarded': r['time_awarded']})

        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    return convert_to_csv(specialist_opportunities, row)


def generate_atm_opportunities_csv(atmOpportunities):
    # converts a brief response into an ordered dict
    def row(r):
        answers = od()
        answers.update({'opportunity_id': r['id']})
        answers.update({'title': r['title']})
        answers.update({'raised_by': r['email_address']})
        answers.update({'open_to': r['openTo']})
        answers.update({'category_open_to': r['areaOfExpertise']})
        answers.update({'buying_agency': r['organisation']})
        answers.update({'summary': r['summary']})
        answers.update({'state': ', '.join(r['location'])})
        answers.update({'evaluation_steps': ', '.join(r['evaluationType'])})
        answers.update({'commence_date': r['startDate']})
        answers.update({'Response criteria': format_criteria(r.get('evaluationCriteria') or '')})
        answers.update({'awarded_to': r['awarded_to']})
        answers.update({'time_draft_created': r['created_at']})
        answers.update({'time_published': r['published_at']})
        answers.update({'time_closed': r['closed_at']})
        answers.update({'time_awarded': r['time_awarded']})
        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    return convert_to_csv(atmOpportunities, row)


def generate_rfx_opportunities_csv(rfx_opportunities):
    # converts a brief response into an ordered dict
    def row(r):
        answers = od()
        answers.update({'opportunity_id': r['id']})
        answers.update({'title': r['title']})
        answers.update({'buying_agency': r['organisation']})
        answers.update({'raised_by': r['email_address']})
        answers.update({'service': r['areaOfExpertise']})
        answers.update({'sellers': format_sellers(r['sellers'])})
        answers.update({'summary': r['summary']})
        answers.update({'state': ', '.join(r['location'])})
        answers.update({'working_arrangements': r['workingArrangements']})
        answers.update({'security_clearance': r['securityClearance']})
        answers.update({'evaluation_steps': ', '.join(r['proposalType'])})
        answers.update({'commence_date': r['startDate']})
        answers.update({'contract_length': r['contractLength']})
        answers.update({'contract_extension': r['contractExtensions']})
        # Future-proofing for when essential and nice_to_have come in
        if r['essentialRequirements'] is not None:
            answers.update({'essential_criteria': format_criteria(r.get('essentialRequirements') or '')})
            answers.update({'desirable_criteria': format_criteria(r.get('niceToHaveRequirements') or '')})
        else:
            answers.update({'essential_criteria': format_criteria(r.get('evaluationCriteria') or '')})
            answers.update({'desirable_criteria': ''})
        answers.update({'awarded_to': r['awarded_to']})
        answers.update({'time_draft_created': r['created_at']})
        answers.update({'time_published': r['published_at']})
        answers.update({'time_closed': r['closed_at']})
        answers.update({'time_awarded': r['time_awarded']})
        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    return convert_to_csv(rfx_opportunities, row)


def generate_training_opportunities_csv(training_opportunities):
    # converts a brief response into an ordered dict
    def row(r):
        answers = od()
        answers.update({'opportunity_id': r['id']})
        answers.update({'title': r['title']})
        if r['internalReference'] == '':
            answers.update({'internal_reference': ''})
        else:
            answers.update({'internal_reference': r['internalReference']})
        answers.update({'buying_agency': r['organisation']})
        answers.update({'raised_by': r['email_address']})
        answers.update({'sellers': format_sellers(r['sellers'])})
        answers.update({'summary': r['summary']})
        answers.update({'state': ', '.join(r['location'])})
        answers.update({'working_arrangements': r['workingArrangements']})
        if r['securityClearance'] == '':
            answers.update({'security_clearance': ''})
        else:
            answers.update({'security_clearance': r['securityClearance']})
        answers.update({'commence_date': r['startDate']})
        answers.update({'contract_length': r['contractLength']})
        answers.update({'contract_extension': r['contractExtensions']})
        answers.update({'evaluation_steps': ', '.join(r['evaluationType'])})
        answers.update({'proposal_types': ', '.join(r['proposalType'])})
        answers.update({'essential_criteria': format_criteria(r.get('essentialRequirements') or '')})
        answers.update({'desirable_criteria': format_criteria(r.get('niceToHaveRequirements') or '')})
        answers.update({'awarded_to': r['awarded_to']})
        answers.update({'time_draft_created': r['created_at']})
        answers.update({'time_published': r['published_at']})
        answers.update({'time_closed': r['closed_at']})
        answers.update({'time_awarded': r['time_awarded']})
        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    return convert_to_csv(training_opportunities, row)
