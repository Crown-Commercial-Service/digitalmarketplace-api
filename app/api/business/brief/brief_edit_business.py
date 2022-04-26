import copy

import pendulum
import rollbar
from flask import current_app
from workdays import workday

from app.api.business.brief import brief_business
from app.api.business.errors import (BriefError, NotFoundError,
                                     UnauthorisedError)
from app.api.services import (agency_service, audit_service, audit_types,
                              brief_history_service, domain_service)
from app.api.services import briefs as brief_service
from app.api.services import suppliers as supplier_service
from app.api.services import users as user_service
from app.api.business.validators import (ATMDataValidator, RFXDataValidator,
                                         SpecialistDataValidator,
                                         TrainingDataValidator, brief_lockout_validator)
from app.datetime_utils import combine_date_and_time, parse_time_of_day
from app.emails import (send_opportunity_edited_email_to_buyers,
                        send_opportunity_edited_email_to_seller,
                        send_seller_invited_to_rfx_email,
                        send_seller_invited_to_training_email,
                        send_specialist_brief_seller_invited_email)
from app.models import Brief, BriefHistory, ValidationError
from app.tasks import publish_tasks


def get_opportunity_to_edit(user_id, brief_id):
    brief = brief_service.get(brief_id)
    if not brief:
        raise NotFoundError('Opportunity {} does not exist'.format(brief_id))

    if not brief_service.has_permission_to_brief(user_id, brief_id):
        raise UnauthorisedError('Not authorised to edit opportunity {}'.format(brief_id))

    if brief.status != 'live':
        raise BriefError('Unable to edit opportunity {}'.format(brief_id))

    domains = []
    for domain in domain_service.get_active_domains():
        domains.append({
            'id': str(domain.id),
            'name': domain.name
        })

    return {
        'brief': brief.serialize(with_users=False),
        'domains': domains,
        'isOpenToAll': brief_business.is_open_to_all(brief),
        'lockout_period': brief_business.get_lockout_dates(formatted=True)
    }


def calculate_new_questions_closed_at(brief):
    from app.api.business.brief.brief_business import get_lockout_dates, get_lockout_question_close_date
    # Logic taken from publish function on the Brief class
    DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']
    DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']
    time_of_day = parse_time_of_day(DEADLINES_TIME_OF_DAY)

    closed_at_parsed = combine_date_and_time(
        brief.closed_at, time_of_day, DEADLINES_TZ_NAME
    ).in_tz('UTC')

    now_plus_three_days = combine_date_and_time(
        pendulum.now().add(days=3), time_of_day, DEADLINES_TZ_NAME
    ).in_tz('UTC')

    if closed_at_parsed <= now_plus_three_days:
        questions_closed_at = workday(closed_at_parsed, -1)
    else:
        questions_closed_at = workday(closed_at_parsed, -2)

    lockout_period = get_lockout_dates()
    if lockout_period['startDate'] and lockout_period['endDate']:
        questions_closed_at = get_lockout_question_close_date(
            questions_closed_at,
            closed_at_parsed.date(),
            lockout_period
        )

    if questions_closed_at > closed_at_parsed:
        questions_closed_at = closed_at_parsed

    return combine_date_and_time(
        questions_closed_at,
        time_of_day, DEADLINES_TZ_NAME
    ).in_tz('UTC')


def get_sellers_to_invite(brief, sellers_to_invite):
    new_sellers = {}

    if brief.lot.slug == 'atm':
        return new_sellers

    invited_seller_codes = list(brief.data.get('sellers', {}).keys())
    new_seller_codes = list(sellers_to_invite.keys())

    for code in new_seller_codes:
        if code not in invited_seller_codes:
            new_sellers[code] = sellers_to_invite[code]

    return new_sellers


def edit_opportunity(user_id, brief_id, edits):
    brief = brief_service.get(brief_id)
    if not brief:
        raise NotFoundError('Opportunity {} does not exist'.format(brief_id))

    if not brief_service.has_permission_to_brief(user_id, brief_id):
        raise UnauthorisedError('Not authorised to edit opportunity {}'.format(brief_id))

    if brief.status != 'live':
        raise BriefError('Unable to edit opportunity {}'.format(brief_id))

    user = user_service.get(user_id)
    if not user:
        raise NotFoundError('User {} does not exist'.format(user_id))

    previous_data = copy.deepcopy(brief.data)
    previous_data['closed_at'] = brief.closed_at.to_iso8601_string()

    edit_title(brief, edits['title'])
    edit_summary(brief, edits['summary'])
    edit_closing_date(brief, edits['closingDate'])

    if 'documentsEdited' in edits and edits['documentsEdited']:
        if 'attachments' in edits:
            edit_attachments(brief, edits['attachments'])
        if 'requirementsDocument' in edits and 'requirementsDocument' in brief.data:
            edit_requirements_document(brief, edits['requirementsDocument'])
        if 'responseTemplate' in edits and 'responseTemplate' in brief.data:
            edit_response_template(brief, edits['responseTemplate'])

    organisation = None
    sellers_to_contact = []
    if (
        title_was_edited(brief.data['title'], previous_data['title']) or
        summary_was_edited(brief.data['summary'], previous_data['summary']) or
        closing_date_was_edited(brief.closed_at.to_iso8601_string(), previous_data['closed_at']) or
        documents_were_edited(brief.data.get('attachments', []), previous_data.get('attachments', [])) or
        documents_were_edited(
            brief.data.get('requirementsDocument', []), previous_data.get('requirementsDocument', [])
        ) or
        documents_were_edited(brief.data.get('responseTemplate', []), previous_data.get('responseTemplate', []))
    ):
        organisation = agency_service.get_agency_name(user.agency_id)
        # We need to find sellers to contact about the current incoming edits before sellers are edited as we're
        # not sending additional sellers emails about the current edits that have been made.
        sellers_to_contact = brief_service.get_sellers_to_notify(brief, brief_business.is_open_to_all(brief))

    sellers_to_invite = {}
    if 'sellers' in edits and sellers_were_edited(edits['sellers'], brief.data.get('sellers', {})):
        sellers_to_invite = get_sellers_to_invite(brief, edits['sellers'])
        edit_sellers(brief, sellers_to_invite)
        edit_seller_selector(brief, sellers_to_invite)

    # strip out any data keys not whitelisted
    brief = brief_business.remove_keys_not_whitelisted(brief)

    data_to_validate = copy.deepcopy(brief.data)
    # only validate the sellers being added in the edit
    if 'sellers' in edits and len(edits['sellers'].keys()) > 0:
        data_to_validate['sellers'] = copy.deepcopy(edits.get('sellers', {}))

    validator = None
    if brief.lot.slug == 'rfx':
        validator = RFXDataValidator(data_to_validate)
    elif brief.lot.slug == 'training2':
        validator = TrainingDataValidator(data_to_validate)
    elif brief.lot.slug == 'atm':
        validator = ATMDataValidator(data_to_validate)
    elif brief.lot.slug == 'specialist':
        validator = SpecialistDataValidator(data_to_validate)

    if validator is None:
        raise ValidationError('Validator not found for {}'.format(brief.lot.slug))

    errors = []
    if (
        title_was_edited(brief.data['title'], previous_data['title']) and
        not validator.validate_title()
    ):
        errors.append('You must add a title')

    if (
        summary_was_edited(brief.data['summary'], previous_data['summary']) and
        not validator.validate_summary()
    ):
        message = (
            'You must add what the specialist will do'
            if brief.lot.slug == 'specialist' else
            'You must add a summary of work to be done'
        )

        errors.append(message)

    if (
        brief.lot.slug != 'atm' and
        'sellers' in edits and
        sellers_were_edited(edits['sellers'], brief.data.get('sellers', {})) and
        not validator.validate_sellers()
    ):
        message = (
            'You must select some sellers'
            if brief.lot.slug == 'specialist' else
            'You must select at least one seller and each seller must be assessed for the chosen category'
        )

        errors.append(message)

    if (
        closing_date_was_edited(brief.closed_at.to_iso8601_string(), previous_data['closed_at']) and
        not validator.validate_closed_at(minimum_days=1)
    ):
        message = (
            'The closing date must be at least 1 day into the future or not more than one year long'
            if brief.lot.slug == 'specialist' else
            'The closing date must be at least 1 day into the future'
        )

        errors.append(message)

    if (
        closing_date_was_edited(brief.closed_at.to_iso8601_string(), previous_data['closed_at']) and
        not brief_lockout_validator.validate_closed_at_lockout(brief.closed_at.to_iso8601_string())
    ):
        lockout_dates = brief_business.get_lockout_dates()
        if lockout_dates['startDate'] and lockout_dates['endDate']:
            message = (
                'The closing date cannot be between ' + lockout_dates['startDate'].strftime('%d %B') + ' and ' +
                lockout_dates['endDate'].strftime('%d %B %Y') + ', as Digital Marketplace is moving to BuyICT.'
            )
        else:
            message = ('The blockout period dates are not valid')

        errors.append(message)

    if len(errors) > 0:
        raise ValidationError(', '.join(errors))

    brief_service.save(brief, do_commit=False)

    edit = BriefHistory(
        brief_id=brief.id,
        user_id=user_id,
        data=previous_data
    )

    brief_history_service.save(edit, do_commit=False)
    brief_service.commit_changes()

    if len(sellers_to_contact) > 0 and organisation:
        for email_address in sellers_to_contact:
            send_opportunity_edited_email_to_seller(brief, email_address, organisation)

    for code, data in sellers_to_invite.items():
        supplier = supplier_service.get_supplier_by_code(code)
        if supplier:
            if brief.lot.slug == 'rfx':
                send_seller_invited_to_rfx_email(brief, supplier)
            elif brief.lot.slug == 'specialist':
                send_specialist_brief_seller_invited_email(brief, supplier)
            elif brief.lot.slug == 'training':
                send_seller_invited_to_training_email(brief, supplier)

    send_opportunity_edited_email_to_buyers(brief, user, edit)

    try:
        audit_service.log_audit_event(
            audit_type=audit_types.opportunity_edited,
            data={
                'briefId': brief.id
            },
            db_object=brief,
            user=user.email_address
        )

        publish_tasks.brief.delay(
            publish_tasks.compress_brief(brief),
            'edited',
            email_address=user.email_address,
            name=user.name
        )
    except Exception as e:
        rollbar.report_exc_info()

    return brief


def edit_title(brief, new_title):
    if new_title and new_title != brief.data['title']:
        brief.data['title'] = new_title


def edit_sellers(brief, sellers_to_invite):
    if brief.lot.slug != 'atm' and sellers_to_invite:
        new_data = copy.deepcopy(brief.data)
        for code, data in sellers_to_invite.items():
            new_data['sellers'][code] = data

        brief.data = new_data


def edit_seller_selector(brief, sellers_to_invite):
    if brief.lot.slug != 'atm' and sellers_to_invite:
        seller_selector = brief.data.get('sellerSelector', '')

        if len(sellers_to_invite.keys()) > 0 and seller_selector and seller_selector == 'oneSeller':
            brief.data['sellerSelector'] = 'someSellers'


def edit_attachments(brief, documents):
    brief.data['attachments'] = documents


def edit_requirements_document(brief, documents):
    if len(documents) > 0:
        brief.data['requirementsDocument'] = documents


def edit_response_template(brief, documents):
    if len(documents) > 0:
        brief.data['responseTemplate'] = documents


def edit_closing_date(brief, new_closing_date):
    if new_closing_date:
        parsed_closing_date = pendulum.parse(new_closing_date, tz='Australia/Canberra')
        parsed_closing_date = parsed_closing_date.add(hours=18)
        parsed_closing_date = parsed_closing_date.in_timezone('utc')

        if parsed_closing_date > pendulum.now('utc') and parsed_closing_date != brief.closed_at:
            brief.questions_closed_at = None
            brief.closed_at = parsed_closing_date
            brief.data['closedAt'] = new_closing_date
            brief.questions_closed_at = calculate_new_questions_closed_at(brief)


def edit_summary(brief, new_summary):
    if new_summary and new_summary != brief.data['summary']:
        brief.data['summary'] = new_summary


def title_was_edited(title, previous_title):
    return True if title != previous_title else False


def sellers_were_edited(sellers, previous_sellers):
    invited_sellers = list(sellers.keys())
    previous_invited_sellers = list(previous_sellers.keys())

    for code in invited_sellers:
        if code not in previous_invited_sellers:
            return True

    return False


def summary_was_edited(summary, previous_summary):
    return True if summary != previous_summary else False


def closing_date_was_edited(closing_date, previous_closing_date):
    closing_date = pendulum.parse(closing_date) if isinstance(closing_date, str) else closing_date
    previous_closing_date = (
        pendulum.parse(previous_closing_date)
        if isinstance(previous_closing_date, str) else previous_closing_date
    )

    return True if closing_date != previous_closing_date else False


def documents_were_edited(current, previous):
    return True if current != previous else False


def get_changes_made_to_opportunity(source, previous):
    data = {}

    if title_was_edited(source.data['title'], previous.data['title']):
        data['title'] = {
            'oldValue': previous.data['title'],
            'newValue': source.data['title']
        }

    if (
        'sellers' in source.data and
        'sellers' in previous.data and
        sellers_were_edited(source.data['sellers'], previous.data['sellers'])
    ):
        data['sellers'] = {
            'oldValue': previous.data['sellers'],
            'newValue': source.data['sellers']
        }

    if summary_was_edited(source.data['summary'], previous.data['summary']):
        data['summary'] = {
            'oldValue': previous.data['summary'],
            'newValue': source.data['summary']
        }

    if isinstance(source, Brief):
        closed_at_edited = closing_date_was_edited(source.closed_at, previous.data['closed_at'])
        if closed_at_edited:
            data['closingDate'] = {
                'oldValue': previous.data['closed_at'],
                'newValue': source.closed_at
            }
    else:
        closed_at_edited = closing_date_was_edited(source.data['closed_at'], previous.data['closed_at'])
        if closed_at_edited:
            data['closingDate'] = {
                'oldValue': previous.data['closed_at'],
                'newValue': source.data['closed_at']
            }

    if documents_were_edited(source.data.get('attachments', []), previous.data.get('attachments', [])):
        data['attachments'] = {
            'oldValue': previous.data.get('attachments', []),
            'newValue': source.data.get('attachments', [])
        }

    if documents_were_edited(
        source.data.get('requirementsDocument', []), previous.data.get('requirementsDocument', [])
    ):
        data['requirementsDocument'] = {
            'oldValue': previous.data.get('requirementsDocument', []),
            'newValue': source.data.get('requirementsDocument', [])
        }

    if documents_were_edited(source.data.get('responseTemplate', []), previous.data.get('responseTemplate', [])):
        data['responseTemplate'] = {
            'oldValue': previous.data.get('responseTemplate', []),
            'newValue': source.data.get('responseTemplate', [])
        }

    return data


def get_opportunity_history(brief_id, show_documents=False, include_sellers=True):
    brief = brief_service.get(brief_id)
    if not brief:
        raise NotFoundError('Opportunity {} does not exist'.format(brief_id))

    response = {
        'brief': {
            'framework': brief.framework.slug,
            'id': brief.id,
            'title': brief.data['title'] if 'title' in brief.data else ''
        }
    }

    edits = []
    changes = brief_history_service.get_edits(brief.id)

    for i, change in enumerate(changes):
        source = brief if i == 0 else changes[i - 1]
        edit_data = get_changes_made_to_opportunity(source, change)

        if edit_data:
            edit_data['editedAt'] = change.edited_at
            if not include_sellers and 'sellers' in edit_data:
                del edit_data['sellers']
            if not brief_business.is_open_to_all(brief) and not show_documents:
                if 'attachments' in edit_data:
                    del edit_data['attachments']
                if 'requirementsDocument' in edit_data:
                    del edit_data['requirementsDocument']
                if 'responseTemplate' in edit_data:
                    del edit_data['responseTemplate']
            edits.append(edit_data)

    response['edits'] = edits

    return response


def only_sellers_were_edited(brief_id):
    history = get_opportunity_history(brief_id, show_documents=True)
    only_sellers_edited = False

    for edit in history['edits']:
        for key, value in edit.items():
            if key != 'editedAt' and key != 'sellers':
                return False
            elif key == 'sellers':
                only_sellers_edited = True

    return only_sellers_edited
