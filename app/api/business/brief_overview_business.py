import rollbar
from flask_login import current_user

from app.api.business.agreement_business import use_old_work_order_creator
from app.api.business.errors import (BriefError, NotFoundError,
                                     UnauthorisedError)
from app.api.services import (audit_service, audit_types,
                              brief_responses_service, briefs)
from app.emails import send_opportunity_closed_early_email
from app.tasks import publish_tasks
from app.tasks.s3 import create_responses_zip
from app.validation import get_sections as get_validation_sections


def can_close_opportunity_early(brief):
    seller_selector = brief.data.get('sellerSelector', '')
    invited_sellers = brief.data.get('sellers', {}).keys()
    number_of_candidates = int(brief.data.get('numberOfSuppliers', 0))

    if brief.status == 'live' and len(invited_sellers) == 1 and (
        (brief.lot.slug in ['rfx', 'training2'] and seller_selector == 'oneSeller') or
        (brief.lot.slug == 'specialist' and seller_selector == 'someSellers')
    ):
        invited_seller_code = int(invited_sellers.pop())
        response_count = brief_responses_service.find(
            brief_id=brief.id,
            supplier_code=invited_seller_code,
            status='submitted'
        ).count()

        if brief.lot.slug in ['rfx', 'training2'] and response_count == 1:
            return True

        if brief.lot.slug == 'specialist' and response_count == number_of_candidates:
            return True

    return False


def close_opportunity_early(current_user, brief_id):
    brief = briefs.get(brief_id)
    if not brief:
        raise NotFoundError('Opportunity {} does not exist'.format(brief_id))

    if not briefs.has_permission_to_brief(current_user.id, brief_id):
        raise UnauthorisedError('Not authorised to close opportunity {}'.format(brief_id))

    if not can_close_opportunity_early(brief):
        raise BriefError('Unable to close opportunity {}'.format(brief_id))

    brief = briefs.close_opportunity_early(brief)
    create_responses_zip(brief.id)
    send_opportunity_closed_early_email(brief, current_user)

    try:
        audit_service.log_audit_event(
            audit_type=audit_types.close_opportunity_early,
            data={
                'briefId': brief.id
            },
            db_object=brief,
            user=current_user.email_address
        )

        publish_tasks.brief.delay(
            publish_tasks.compress_brief(brief),
            'closed_early',
            email_address=current_user.email_address,
            name=current_user.name
        )
    except Exception as e:
        rollbar.report_exc_info()

    return brief


def get_path_for_brief_link(brief, link, paths=None):
    path = '/buyers/frameworks/{}/requirements/{}/{}'.format(brief.framework.slug, brief.lot.slug, brief.id)
    work_order_id = brief.work_order.id if brief.work_order else None
    if paths:
        return paths[link].format(path=path, work_order_id=work_order_id)

    return link.format(path=path, work_order_id=work_order_id, brief_id=brief.id)


def brief_contains_all_required_fields(brief, required_fields):
    for key in required_fields:
        if not brief.data.get(key):
            return False

    return True


def brief_contains_any_optional_fields(brief, optional_fields):
    for key in optional_fields:
        if brief.data.get(key):
            return True

    return False


def is_brief_section_complete(brief, section):
    from ...brief_utils import determine_required_fields
    if section['required']:
        required_fields = determine_required_fields(brief, section, enforce_required=False)
        return brief_contains_all_required_fields(brief, required_fields)
    else:
        return brief_contains_any_optional_fields(brief, section['optional'])


def get_publish_links(brief):
    links = []
    draft_brief = brief.status == 'draft'
    brief_builder_paths = {
        'How long your brief will be open': '{path}/edit/how-long-your-brief-will-be-open/requirementsLength',
        'Description of work': '{path}/description-of-work',
        'Location': '{path}/edit/location/location',
        'Question and answer session details': '{path}/question-and-answer-session-details',
        'Role': '{path}/edit/role/title',
        'Shortlist and evaluation process': '{path}/shortlist-and-evaluation-process',
        'Title': '{path}/edit/title/title',
        'Who can respond': '{path}/edit/who-can-respond/specifySeller',
        'Description of training': '{path}/description-of-training',
        'Timeframes, location and budget': '{path}/timeframes,-location-and-budget',
        'Evaluate responses': '{path}/evaluate-responses',
        'Additional information': '{path}/additional-information',
        'Organisation': '{path}/edit/organisation/organisation',
        'Approach to market': '{path}/approach-to-market',
        'Summary': '{path}/edit/summary/summary'
    }
    # Get the sections key from the JSON schema generated by the frameworks repo
    schema_sections = get_validation_sections('briefs-{}-{}'.format(brief.framework.slug, brief.lot.slug))
    for section in schema_sections:
        if section.get('editable', True):
            path = (get_path_for_brief_link(
                brief, section['name'], brief_builder_paths) if draft_brief else None)

            links.append(
                build_brief_link(
                    is_brief_section_complete(brief, section),
                    path,
                    section['name']))

    if brief.lot.slug == 'training':
        # Review and publish is complete if the buyer has completed all sections and published
        publish_completed = all([link['complete'] for link in links]) and not draft_brief
        publish_path = get_path_for_brief_link(brief, '{path}/publish') if draft_brief else None
        links.append(
            build_brief_link(
                publish_completed,
                publish_path,
                'Review and publish your requirements'
            )
        )

    return links


def get_live_links(brief):
    links = []

    # Answer a question is complete if the brief is closed
    answer_question_path = (
        get_path_for_brief_link(
            brief,
            '/2/brief/{brief_id}/questions') if brief.status == 'live' else None)
    links.append(
        build_brief_link(
            brief.status == 'closed',
            answer_question_path,
            'Answer a question',
            None if current_user.has_permission('answer_seller_questions') else 'answer_seller_questions'
        )
    )
    return links


def get_shortlist_links(brief):
    links = []

    view_responses_path = (
        get_path_for_brief_link(brief, '{path}/responses')
        if brief.status == 'closed' else None
    )

    links.append(
        build_brief_link(
            False,
            view_responses_path,
            'View responses',
            None if current_user.has_permission('download_responses') else 'download_responses'
        )
    )
    return links


def get_evaluation_links(brief):
    links = []

    # No green tick needed for evaluation template
    links.append(
        build_brief_link(
            False,
            get_path_for_brief_link(brief, '/static/media/documents/Scoring_Template.xlsx'),
            'Evaluation template (XLSX 13KB)'))

    return links


def get_work_order_links(brief):
    links = []
    old_work_order_creator = use_old_work_order_creator(brief.published_at)
    has_permission = current_user.has_permission('create_work_orders')
    permission_needed = None if has_permission else 'create_work_orders'

    # No need for green ticks to indicate completion
    if brief.work_order:
        if old_work_order_creator:
            links.append(
                build_brief_link(
                    False,
                    get_path_for_brief_link(brief, '/work-orders/{work_order_id}'),
                    'Edit work order',
                    permission_needed
                )
            )
        else:
            links.append(
                build_brief_link(
                    True,
                    '/2/buyer-award/{}'.format(brief.id),
                    'Download work order',
                    permission_needed
                )
            )
    else:
        if old_work_order_creator:
            start_work_order_path = (
                get_path_for_brief_link(brief, '{path}/work-orders/create')
                if brief.status == 'closed' else None
            )
            links.append(
                build_brief_link(
                    False,
                    start_work_order_path,
                    'Start a work order',
                    permission_needed
                )
            )
        else:
            links.append(
                build_brief_link(
                    False,
                    '/2/buyer-award/{}'.format(brief.id),
                    'Download work order',
                    permission_needed
                )
            )

    return links


def build_brief_link(complete, path, text, permission_needed=None):
    return {
        'complete': complete,
        'path': path,
        'text': text,
        'permissionNeeded': permission_needed
    }


def build_section(links, title):
    return {
        'links': links,
        'title': title
    }


def get_sections(brief):
    sections = []

    sections.append(build_section(get_publish_links(brief), 'Publish your brief'))
    sections.append(build_section(get_live_links(brief), 'While the opportunity is live'))
    sections.append(build_section(get_shortlist_links(brief), 'Shortlist responses'))

    if brief.lot.slug == 'digital-professionals' or brief.lot.slug == 'training':
        sections.append(build_section(get_evaluation_links(brief), 'Evaluate specialists'))
        sections.append(build_section(get_work_order_links(brief), 'Work order'))

    return sections
