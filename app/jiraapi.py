from __future__ import unicode_literals

import io
import re
import StringIO
import pendulum

from jira import JIRA
from flask import current_app

import json
from functools import partial

import logging


INITIAL_ASSESSMENT_ISSUE_TYPE = 'Initial Assessment'
SUBSEQUENT_ASSESSMENT_ISSUE_TYPE = 'Profile Edit'

TICKET_DESCRIPTION = ("\n"
                      "Please review this potential supplier to determine if they meet the requirements. "
                      "[Click here for further information|"
                      "https://govausites.atlassian.net/wiki/display/DM/Initial+Assessment+Checklist] "
                      "on how to evaluate each item in the checklist.\n"
                      "\n\n"
                      "Applicant profile link: [%s]\n\n"
                      "----\n\n"
                      "{panel:title=Supplier Assessment Checklist|titleBGColor=#18788D|titleColor=#FFFFFF}\n\n"
                      "\n\n"
                      "# Business Name: \n"
                      "# Badges - Recruiter: \n"
                      "# Badges - Indigenous: \n"
                      "# Badges - Disability: \n"
                      "# Badges - SME: \n"
                      "# Badges - Start-up: \n"
                      "# Business Description: \n"
                      "# Website: \n"
                      "# LinkedIn: \n"
                      "# Business Contact: \n"
                      "# Case Study 1: \n"
                      "# Case Study 2: \n"
                      "# Case Study 3: \n"
                      "# Case Study 4: \n"
                      "# Product 1: \n"
                      "# Product 2: \n"
                      "# Product 3: \n"
                      "# Product 4: \n"
                      "# How we work: \n"
                      "# Company details: \n"
                      "# ABN: \n"
                      "# Location(s): \n"
                      "# Recognition: \n"
                      "# Case Study Referees: \n"
                      "# Disclosures: \n"
                      "# Documents: \n"
                      "## Financial: \n"
                      "## Public Liability: \n"
                      "## Workers Compensation: \n"
                      "# Recruiter Info: \n"
                      "\n\n"
                      "*RECOMMENDATION:* \n\n"
                      "{panel}\n"
                      "\n"
                      "----\n"
                      "\n"
                      "A snapshot of the application is attached.\n")


log = logging.getLogger('jiraapi')
log.setLevel(level=logging.INFO)

formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)

log.addHandler(console)


def to_snake(s, sep='-'):
    s = s.replace(' ', '')
    return (s[0].lower() + re.sub(
        r'([A-Z])', lambda m: sep + m.group(0).lower(), s[1:]))


class MarketplaceJIRA(object):
    def __init__(
            self,
            generic_jira,
            jira_field_codes=None):

        if not jira_field_codes:
            jira_field_codes = current_app.config.get('JIRA_FIELD_CODES')
        self.jira_field_codes = jira_field_codes

        self.generic_jira = generic_jira
        self.server_url = current_app.config['JIRA_URL']

    def make_link(self, key):
        return self.server_url + '/browse/' + key

    def create_domain_approval_task(self, assessment, application=None):
        supplier = assessment.supplier_domain.supplier
        brief = assessment.briefs[0]
        domain = assessment.supplier_domain.domain
        domain_name = domain.name
        relevant_case_studies = []
        case_study_links = ""
        for case_study in supplier.case_studies:
            if case_study.data.get('service', '').lower() == domain_name.lower():
                simple_case_study = {key: case_study.serializable[key]
                                     for key in case_study.serializable
                                     if key not in ['links', 'supplier', 'createdAt', 'created_at']}
                case_study_links += (
                    "Case study: [{}|{}/case-study/{}] (Current status: *{}*)\n"
                    .format(
                        simple_case_study['title'],
                        current_app.config['FRONTEND_ADDRESS'],
                        simple_case_study['id'],
                        case_study.status
                    )
                )
                relevant_case_studies.append(simple_case_study)

        summary = 'Domain Assessment: {}(#{})'.format(supplier.name, supplier.code)
        price_description = ''

        application_awaiting_approval = ''
        if application:
            application_awaiting_approval = (
                '---------\n\n'
                '*WARNING*: There is an awaiting profile edit.\n'
            )

        if supplier.is_recruiter == 'true' and case_study_links == '':
            summary += '[RECRUITER]'
        elif supplier.is_recruiter == 'false' or case_study_links != '':
            price_status = None
            domain_price_minimum = domain.price_minimum
            domain_price_maximum = domain.price_maximum
            max_price = None

            if application:
                pricing = application.data.get('pricing', None)
                if pricing:
                    domain_pricing = pricing[domain_name]
                    if domain_pricing:
                        max_price = float(domain_pricing['maxPrice'])
            elif 'pricing' in supplier.data:
                supplier_pricing = supplier.data.get('pricing', None)
                if domain_name in supplier_pricing:
                    max_price = float(supplier_pricing[domain_name]['maxPrice'])

            if max_price:
                if (domain_price_minimum <= max_price and
                        domain_price_maximum >= max_price):
                    price_status = 'Seller Price: (/) *{}*'.format(max_price)
                else:
                    price_status = 'Seller Price: (x) *{}*'.format(max_price)
            else:
                price_status = 'Seller Price: (!) No price provided'

            price_description_values = {
                "domain": domain_name,
                "domain_price_min": domain_price_minimum,
                "domain_price_max": domain_price_maximum,
                "max_price": max_price,
                "price_status": price_status
            }
            price_description = (
                '---------\n\n'
                'Price threshold for *{domain}*:\n'
                'Minimum Price: {domain_price_min}\n'
                'Maximum Price: *{domain_price_max}*\n'
                '{price_status}\n'
            ).format(**price_description_values)

        description_values = {
            "supplier_name": supplier.name,
            "supplier_url": current_app.config['ADMIN_ADDRESS'] + "/admin/assessments/supplier/" + str(supplier.code),
            "domain": domain_name,
            "brief_name": brief.data.get('title'),
            "brief_close_date": brief.applications_closed_at.format('%A %-d %B %Y'),
            "case_study_links": case_study_links,
            "price_description": price_description,
            "application_awaiting_approval": application_awaiting_approval
        }

        description = ('[{supplier_name}|{supplier_url}] has applied for assessment '
                       'under the "*{domain}*" domain in order to apply for the "*{brief_name}*" brief '
                       'which closes for applications on *{brief_close_date}* at 6PM.'
                       '\n\n'
                       'Please assess their suitability to be approved for '
                       'this domain based on the '
                       '[assessment criteria|https://marketplace.service.gov.au/assessment-criteria] and '
                       'clearly indicate an approve/reject recommendation in your comments.\n\n'
                       '{case_study_links}\n\n'
                       '{application_awaiting_approval}'
                       '{price_description}'
                       '---------\n\n'
                       'Once complete - please assign back to Jordan Williams'
                       ).format(**description_values)

        details = dict(
            project=self.jira_field_codes['MARKETPLACE_PROJECT_CODE'],
            summary=summary,
            description=description,
            issuetype_name='Domain Assessment',
            duedate=str(brief.applications_closing_date),
            labels=[domain_name.title().replace(" ", "_")]
        )
        existing_issues = self.get_supplier_tasks(str(supplier.code))
        new_issue = self.generic_jira.create_issue(**details)
        for issue in existing_issues:
            self.generic_jira.jira.create_issue_link('Relates', new_issue, issue)

        new_issue_update_data = {
            self.jira_field_codes['SUPPLIER_FIELD_CODE']: str(supplier.code),
            self.jira_field_codes['RANKING_ASSESSOR_1_FIELD_CODE']: {"value": "Unassessed"},
            self.jira_field_codes['RANKING_ASSESSOR_2_FIELD_CODE']: {"value": "Unassessed"}
        }

        assessor_result_codes = self.jira_field_codes['ASSESSOR_RESULT_CODES'][str(domain.id)]
        for arc in assessor_result_codes:
            new_issue_update_data[arc] = [{'value': 'No criteria met'}]

        new_issue.update(new_issue_update_data)

        attachment = StringIO.StringIO()
        attachment.write(json.dumps(relevant_case_studies))
        self.generic_jira.jira.add_attachment(new_issue.id, attachment, 'casestudies.json')

    def create_application_approval_task(self, application, domains, closing_date=None):
        if application.type != 'edit':
            summary = 'Application assessment: {} (App #{})'.format(application.data.get('name'), application.id)
            description = TICKET_DESCRIPTION % (current_app.config['ADMIN_ADDRESS'] +
                                                "/admin/applications/preview/{}".format(application.id))
            issuetype_name = INITIAL_ASSESSMENT_ISSUE_TYPE
        else:
            summary = 'Profile edit: {} (#{})'.format(application.data.get('name'), application.supplier_code)
            description = (
                "+*This is a profile edit*+\n\n"
                "Please evaluate the changes made by the seller and ensure they meet the "
                "[assessment guidelines|"
                "https://govausites.atlassian.net/wiki/display/DM/Initial+Assessment+Checklist]. \n"
                "Changes will be summarised at the top of the seller profile.\n\n"
                "Seller profile link: [%s]\n\n"
                "---\n\n"
                "A snapshot of the application is attached."
                "" % (current_app.config['ADMIN_ADDRESS'] + "/admin/applications/preview/{}".format(application.id))
            )
            issuetype_name = SUBSEQUENT_ASSESSMENT_ISSUE_TYPE

        pricing = application.data.get('pricing', None)
        competitive = True
        description += "---\n\n"
        supplier = application.supplier
        if pricing:
            for k, v in pricing.iteritems():
                max_price = float(v.get('maxPrice')) if v.get('maxPrice', None) else 0
                domain = next(d for d in domains if d.name == k)
                domain_price_min = domain.price_minimum
                domain_price_max = domain.price_maximum

                price_description = (
                    "Price threshold for *{domain_name}*:\n"
                    "Seller Price: *{max_price}*\n"
                    "Minimum Price: {domain_price_min}\n"
                    "Maximum Price: *{domain_price_max}*\n"
                ).format(
                    max_price=max_price,
                    domain_name=domain.name,
                    domain_price_min=domain_price_min,
                    domain_price_max=domain_price_max
                )
                description += price_description
                if (max_price >= domain_price_min and max_price <= domain_price_max):
                    description += "Seller is competitive\n\n"
                else:
                    competitive = False
                    description += "*Seller is less competitive*\n\n"

                if supplier:
                    current_max_price = supplier.data.get('pricing', {}).get(k, {}).get('maxPrice', max_price)
                    current_domain = next(iter([sd for sd in supplier.domains if sd.domain.name == k]), None)

                    if float(current_max_price) != float(max_price) and current_domain:
                        if current_domain.price_status == 'rejected' and competitive is True:
                            description += (
                                "Price for *{domain_name}* has been changed to within threshold. "
                                "Current status is *{price_status}*. "
                                "Please evaluate and update price status if appropriate.\n\n"
                                .format(
                                    domain_name=domain.name,
                                    price_status=current_domain.price_status
                                )
                            )
                        elif current_domain.price_status == 'approved' and competitive is False:
                            description += (
                                "Price for *{domain_name}* has been changed to now be outside of threshold. "
                                "Current status is *{price_status}*. "
                                "Please evaluate and update if appropriate.\n\n"
                                .format(
                                    domain_name=domain.name,
                                    price_status=current_domain.price_status
                                )
                            )

        description += "---\n\n"
        if supplier:
            current_recruiter = supplier.data.get('recruiter')
            new_recruiter = application.data.get('recruiter')
            if current_recruiter == 'yes' and new_recruiter != 'yes':
                description += (
                    '*This seller was previously purely a recruiter. '
                    'If approving this edit - please ensure appropriate domain assessments are conducted.*\n\n'
                    '---\n\n'
                )

            if current_recruiter != 'yes' and new_recruiter == 'yes':
                description += (
                    '*This seller was previously a hybrid recruiter (and consultancy).*\n\n'
                    '---\n\n'
                )

            case_studies = application.data.get('case_studies', [])
            for k, case_study in case_studies.iteritems():
                current_case_study = next(
                    iter(
                        [scs for scs in supplier.case_studies if scs.id == case_study.get('id')]
                    ), None)

                if not current_case_study:
                    supplier_domain = next(iter([
                        sd
                        for sd in supplier.domains
                        if sd.domain.name == case_study.get('service') and sd.price_status == 'rejected'
                    ]), None)
                    if supplier_domain:
                        description += (
                            '*Price for {} was previously rejected. '
                            'Seller has added a new case study for this domain - '
                            'please raise a domain assessment for this domain if required.*\n\n'
                            .format(case_study.get('service'))
                        )

                    continue
                elif current_case_study.status != 'rejected':
                    continue

                case_study_different = application.is_case_study_different(case_study, current_case_study.data)

                if case_study_different:
                    description += (
                        "Case study *[{title}|{link}]* is currently *rejected*. "
                        "Once this edit is approved, the status will be updated to *unassessed*. "
                        "Please review to ensure it meets the appropriate number of criteria.\n\n"
                        .format(
                            title=case_study.get('title'),
                            link='{}/admin/applications/case-study/{}/{}'.format(
                                current_app.config['ADMIN_ADDRESS'],
                                application.id,
                                case_study.get('id')
                            )
                        )
                    )

        details = dict(
            project=self.jira_field_codes['MARKETPLACE_PROJECT_CODE'],
            summary=summary,
            description=description,
            duedate=pendulum.now().add(weeks=2).to_date_string(),
            issuetype_name=issuetype_name,
            labels=[application.type] if application.type else []
        )
        existing_issues = self.generic_jira.jira.search_issues('"Marketplace Application ID" ~ "{}" '
                                                               'AND issuetype = "{}"'
                                                               .format(str(application.id), issuetype_name))
        if len(existing_issues) > 0 and application.type == 'new':
            new_issue = existing_issues[0]
            if closing_date is None:
                duedate = pendulum.now().add(weeks=2).to_date_string()
            else:
                duedate = pendulum.from_format(closing_date, '%Y-%m-%d').subtract(days=3).to_date_string()
            new_issue.update({
                'summary': summary,
                'duedate': duedate,
                self.jira_field_codes['SUPPLIER_FIELD_CODE']: str(application.supplier_code)
                if application.supplier_code else str(0)
            })
            if new_issue.fields.status.name == 'Closed':
                self.generic_jira.jira.transition_issue(new_issue, 'Reopen')
        else:
            new_issue = self.generic_jira.create_issue(**details)
            new_issue.update({self.jira_field_codes['APPLICATION_FIELD_CODE']: str(application.id),
                              self.jira_field_codes['SUPPLIER_FIELD_CODE']: str(application.supplier_code)
                              if application.supplier_code else str(0)
                              })

        steps = application.data.get('steps', None)
        if (application.type == 'edit' and
                steps is not None and
                steps.get('pricing', None) and
                len(steps.keys()) == 1 and
                competitive is True):
            from app.main.views.applications import application_approval
            application_approval(application.id, True)
            self.generic_jira.jira.transition_issue(new_issue, 'Done')

        attachment = StringIO.StringIO()
        attachment.write(json.dumps(application.json))
        self.generic_jira.jira.add_attachment(new_issue.id, attachment,
                                              'snapshot_{}.json'.format(pendulum.now().to_date_string()))

    def find_approved_application_issues(self, application_ids):
        jql = ('project = MARADMIN AND type IN ("Initial Assessment", "Profile Edit") AND status = Done AND ({})'
               .format(' OR '.join(['"Marketplace Application ID" ~ ' +
                                    str(app_id) for app_id in application_ids])))

        return self.generic_jira.jira.search_issues(jql, json_result=True)

    def find_approved_assessment_issues(self, open_assessments):
        jql = ('project = MARADMIN AND type = "Domain Assessment" AND status = Done AND ({})'
               .format(' OR '.join(['("Marketplace Supplier ID" ~ ' + str(assessment['supplier_code']) +
                                    ' AND labels IN ({}))'.format(', '.join('"' + domain.replace(' ', '_') + '"'
                                                                            for domain in assessment['domains']))
                                    for assessment in open_assessments])))

        return self.generic_jira.jira.search_issues(jql, json_result=True)

    def get_supplier_tasks(self, supplier_code):
        return self.generic_jira.jira.search_issues('"Marketplace Supplier ID" ~ "{}"'.format(supplier_code))

    def get_assessment_tasks(self):
        return self.generic_jira.issues_with_subtasks(
            self.jira_field_codes['MARKETPLACE_PROJECT_CODE'],
            INITIAL_ASSESSMENT_ISSUE_TYPE
        )

    def assessment_tasks_by_application_id(self):
        assessment_issues = self.generic_jira.issues_with_subtasks(
            self.jira_field_codes['MARKETPLACE_PROJECT_CODE'],
            INITIAL_ASSESSMENT_ISSUE_TYPE
        )

        def task_info(t):
            info = {
                'id': t['id'],
                'key': t['key'],
                'self': t['self'],
                'link': self.make_link(t['key']),
                'summary': t['fields']['summary'],
                'status': to_snake(t['fields']['status']['name'], '-'),
            }

            try:
                info['subtasks'] = [task_info(st) for st in t['fields']['subtasks']]
            except KeyError:
                pass
            return info

        return {_['fields'][self.jira_field_codes['APPLICATION_FIELD_CODE']]: task_info(_) for _ in assessment_issues}

    def custom_fields(self):
        f = self.generic_jira.get_fields()

        return {
            x['name']: x
            for x in f
            if x['custom']
        }

    def assessment_issue_type_attached(self):
        return self.generic_jira.issue_type_is_attached_to_project(INITIAL_ASSESSMENT_ISSUE_TYPE,
                                                                   self.jira_field_codes['MARKETPLACE_PROJECT_CODE'])


class GenericJIRA(object):
    def __init__(self, jira):
        self.jira = jira
        self.s = self.jira._session
        self.server_info = self.jira.server_info()

    def http(self, method, resource, url=None, data=None):
        method = getattr(self.s, method)

        if not url:
            url = self.jira._get_url(resource)

        params = dict(url=url)
        if data:
            params['data'] = data

        resp = method(**params)
        return json.loads(resp.text, indent=4)

    def __getattr__(self, name):
        return partial(self.http, name)

    def create_issue(self, project, summary, description, issuetype_name, **kwargs):
        MAX_LENGTH = 30000

        if description and len(description) > MAX_LENGTH:
            log.warning('truncating long issue description')
            description = description[:MAX_LENGTH]

        details = dict(
            project=project,
            summary=summary,
            description=description,
            issuetype={'name': issuetype_name}
        )

        details.update(**kwargs)
        new_issue = self.jira.create_issue(**details)
        return new_issue

    def get_issues_of_type(self, project_code, issuetype_name):
        SEARCH = "project={} and type='{}'".format(
            project_code,
            issuetype_name)
        results = self.jira.search_issues(SEARCH)
        return results

    def issues_with_subtasks(self, project_code, issuetype_name, full_subtasks=False):
        log.info('requesting: all issues')
        issues = self.get_issues_of_type(project_code, issuetype_name)

        def augment(issue):
            if full_subtasks:
                issue['full_subtasks'] = [
                    self.get_specific_issue(subtask['id'])
                    for subtask in issue['fields']['subtasks']
                ]
            return issue

        return [augment(_.raw) for _ in issues]

    def get_specific_issue(self, task_id):
        url = self.jira._get_url('issue/{}'.format(task_id))
        response = self.s.get(url)
        return response.json()

    def get_issue_fields(self, issue_id):
        url = self.jira._get_url('issue/{}/editmeta'.format(issue_id))
        response = self.s.get(url)
        return response.json()

    def get_issuetypes(self):
        url = self.jira._get_url('issuetype')
        response = self.s.get(url)
        return response.json()

    def get_fields(self):
        url = self.jira._get_url('field')
        response = self.s.get(url)
        return response.json()

    def create_issuetype(self, issuetype_name, description, subtask=False):
        typename = 'standard' if not subtask else 'subtask'

        url = self.jira._get_url('issuetype')

        data = {
            "name": issuetype_name,
            "description": description,
            "type": typename
        }

        response = self.s.post(url, data=json.dumps(data))
        return response.json()

    def ensure_issue_type_exists(self, issuetype_name, description):
        existing = self.get_issuetypes()

        names = [_['name'] for _ in existing]

        issuetype_exists = issuetype_name in set(names)

        if not issuetype_exists:
            its = self.create_issuetype(issuetype_name, description)
        else:
            its = next(_ for _ in existing if _['name'] == issuetype_name)
        return its

    def get_project(self, projectcode):
        url = self.jira._get_url('project/{}'.format(projectcode))
        resp = self.s.get(url)
        return resp.json()

    def issue_type_is_attached_to_project(self, issuetype, projectcode):
        proj = self.get_project(projectcode)
        issuetype_names = [_['name'] for _ in proj['issueTypes']]
        return issuetype in issuetype_names


def get_api():
    JIRA_URL = current_app.config['JIRA_URL']
    JIRA_CREDS = current_app.config['JIRA_CREDS']
    creds = JIRA_CREDS.split(':', 1)

    return JIRA(JIRA_URL, basic_auth=creds)


def get_api_oauth():
    JIRA_URL = current_app.config['JIRA_URL']
    JIRA_CREDS_OAUTH = current_app.config['JIRA_CREDS_OAUTH']

    at, ats, ck, kc = JIRA_CREDS_OAUTH.split(',', 3)

    oauth_dict = {
        'access_token': at,
        'access_token_secret': ats,
        'consumer_key': ck,
        'key_cert': kc
    }

    return JIRA(JIRA_URL, oauth=oauth_dict)


def get_marketplace_jira(oauth=True):
    if oauth:
        api = get_api_oauth()
    else:
        api = get_api()

    return MarketplaceJIRA(GenericJIRA(api))
