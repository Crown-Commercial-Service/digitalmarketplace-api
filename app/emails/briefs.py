# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app

from .util import render_email_template, send_or_handle_error, escape_markdown

import rollbar
import pendulum


def send_brief_response_received_email(supplier, brief, brief_response, supplier_user=None, is_update=False):
    to_address = brief_response.data['respondToEmailAddress']

    if brief.lot.slug in ['rfx', 'atm', 'training2']:
        brief_url = current_app.config['FRONTEND_ADDRESS'] + '/2/' + brief.framework.slug + '/opportunities/' \
            + str(brief.id)
    else:
        brief_url = current_app.config['FRONTEND_ADDRESS'] + '/' + brief.framework.slug + '/opportunities/' \
            + str(brief.id)
    ask_question_url = '{}/login?next=%2Fsellers%2Fopportunities%2F{}%2Fask-a-question'.format(
        current_app.config['FRONTEND_ADDRESS'], brief.id
    )

    brief_response_url = '{}/2/brief/{}/{}/respond/{}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        brief.id,
        brief.lot.slug,
        brief_response.id
    )

    if is_update:
        subject = "You've updated your response for {}"
    else:
        subject = "You've applied for {} successfully!"
    brief_title = brief.data['title']
    if len(brief_title) > 30:
        brief_title = '{}...'.format(brief_title[:30])
    subject = subject.format(brief_title)

    template_file_name = 'brief_response_updated.md' if is_update else 'brief_response_submitted.md'

    # prepare copy
    email_body = render_email_template(
        template_file_name,
        brief_id=brief.id,
        brief_url=brief_url,
        brief_response_url=brief_response_url,
        ask_question_url=ask_question_url,
        closing_at=brief.closed_at.format('%d %B %Y'),
        brief_title=brief_title,
        supplier_name=supplier.name,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        organisation=brief.data['organisation'],
        supplier_user=supplier_user
    )

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response recieved'
    )


def send_specialist_brief_response_received_email(supplier, brief, brief_response, supplier_user=None,
                                                  is_update=False):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    if brief.lot.slug not in ['specialist']:
        return

    to_address = brief_response.data['respondToEmailAddress']
    specialist_name = '{} {}'.format(
        brief_response.data.get('specialistGivenNames', ''),
        brief_response.data.get('specialistSurname', '')
    )

    brief_url = '{}/2/{}/opportunities/{}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        brief.framework.slug,
        brief.id
    )

    brief_response_url = '{}/2/brief/{}/specialist2/respond/{}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        brief.id,
        brief_response.id
    )

    attachment_url = '{}/api/2/brief/{}/respond/documents/{}/'.format(
        current_app.config['FRONTEND_ADDRESS'],
        brief.id,
        supplier.code
    )

    ess = ""
    if brief_response.data.get('essentialRequirements', None):
        i = 0
        for req in brief.data['essentialRequirements']:
            ess += "**{}. {}**\n\n{}\n\n".format(
                i + 1,
                req['criteria'],
                escape_markdown(brief_response.data['essentialRequirements'][req['criteria']])
            )
            i += 1

    nth = ""
    if brief_response.data.get('niceToHaveRequirements', None):
        i = 0
        for req in brief.data['niceToHaveRequirements']:
            nth_reqs = brief_response.data.get('niceToHaveRequirements', [])
            if req['criteria'] in nth_reqs:
                nth += "**{}. {}**\n\n{}\n\n".format(
                    i + 1,
                    req['criteria'],
                    escape_markdown(nth_reqs[req['criteria']])
                )
                i += 1
        if nth:
            nth = '####Desirable criteria:  \n\n  ' + nth

    criteriaResponses = ""
    evaluationCriteriaResponses = brief_response.data.get('criteria', {})
    if evaluationCriteriaResponses:
        for evaluationCriteria in brief.data['evaluationCriteria']:
            if (
                'criteria' in evaluationCriteria and
                evaluationCriteria['criteria'] in evaluationCriteriaResponses.keys()
            ):
                criteriaResponses += "####• {}\n\n{}\n\n".format(
                    evaluationCriteria['criteria'],
                    escape_markdown(evaluationCriteriaResponses[evaluationCriteria['criteria']])
                )

    attachments = ''
    resume = ''
    for attach in brief_response.data.get('resume', []):
        if not resume:
            resume = '[{}]({}{})  '.format(attach, attachment_url, attach)
        else:
            attachments += "* [{}]({}{})\n\n".format(attach, attachment_url, attach)

    if attachments:
        attachments = '**Other documents:**  \n\n  ' + attachments

    if is_update:
        subject = "{}'s response for '{}' ({}) was updated".format(
            specialist_name,
            brief.data['title'],
            brief.id
        )
    else:
        subject = 'You submitted {} for {} ({}) successfully'.format(
            specialist_name,
            brief.data['title'],
            brief.id
        )
    response_security_clearance = ''
    if brief.data.get('securityClearance') == 'mustHave':
        must_have_clearance = ''
        if brief.data.get('securityClearanceCurrent') == 'baseline':
            must_have_clearance = 'baseline'
        elif brief.data.get('securityClearanceCurrent') == 'nv1':
            must_have_clearance = 'negative vetting level 1'
        elif brief.data.get('securityClearanceCurrent') == 'nv2':
            must_have_clearance = 'negative vetting level 2'
        elif brief.data.get('securityClearanceCurrent') == 'pv':
            must_have_clearance = 'positive vetting'

        response_security_clearance = '\n**Holds a {} security clearance:** {}  '.format(
            must_have_clearance,
            escape_markdown(brief_response.data.get('securityClearance'))
        )

    response_rates = ''
    response_rates_excluding_gst = ''
    if brief.data.get('preferredFormatForRates') == 'hourlyRate':
        response_rates = '**Hourly rate, including GST:** ${}'.format(
            escape_markdown(brief_response.data.get('hourRate'))
        )
        response_rates_excluding_gst = '**Hourly rate, excluding GST:** ${}'.format(
            escape_markdown(brief_response.data.get('hourRateExcludingGST'))
        )
    elif brief.data.get('preferredFormatForRates') == 'dailyRate':
        response_rates = '**Daily rate, including GST:** ${}'.format(
            escape_markdown(brief_response.data.get('dayRate'))
        )
        response_rates_excluding_gst = '**Daily rate, excluding GST:** ${}'.format(
            escape_markdown(brief_response.data.get('dayRateExcludingGST'))
        )

    response_visa_status = ''
    if brief_response.data.get('visaStatus') == 'AustralianCitizen':
        response_visa_status = 'Australian citizen'
    elif brief_response.data.get('visaStatus') == 'PermanentResident':
        response_visa_status = 'Permanent resident'
    elif brief_response.data.get('visaStatus') == 'ForeignNationalWithAValidVisa':
        response_visa_status = 'Foreign national with a valid visa'

    template_file_name = (
        'specialist_brief_response_updated.md' if is_update else 'specialist_brief_response_submitted.md'
    )

    # prepare copy
    email_body = render_email_template(
        template_file_name,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_url=brief_url,
        brief_id=brief.id,
        brief_name=brief.data['title'],
        brief_organisation=brief.data['organisation'],
        supplier_user=supplier_user,
        essential_requirements=ess,
        nice_to_have_requirements=nth,
        criteria_responses=criteriaResponses,
        resume=resume,
        attachments=attachments,
        closing_at=brief.closed_at.format('%d %B %Y'),
        specialist_name=escape_markdown(specialist_name),
        brief_response_url=brief_response_url,
        response_rates=response_rates,
        response_rates_excluding_gst=response_rates_excluding_gst,
        response_previously_worked=escape_markdown(brief_response.data.get('previouslyWorked')),
        response_security_clearance=response_security_clearance,
        response_start_date=escape_markdown(brief_response.data.get('availability')),
        response_visa_status=response_visa_status
    )

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response recieved'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.specialist_brief_response_received_email,
        user='',
        data={
            "to_address": to_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_specialist_brief_response_withdrawn_email(supplier, brief, brief_response, supplier_user=None):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    to_address = brief_response.data['respondToEmailAddress']

    specialist_name = '{} {}'.format(
        brief_response.data.get('specialistGivenNames', ''),
        brief_response.data.get('specialistSurname', '')
    )

    subject = "{}'s response to '{}' ({}) has been withdrawn".format(
        specialist_name,
        brief.data['title'],
        brief.id
    )

    brief_url = '{}/2/{}/opportunities/{}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        brief.framework.slug,
        brief.id
    )

    email_body = render_email_template(
        'specialist_brief_response_withdrawn.md',
        specialist_name=specialist_name,
        brief_url=brief_url,
        brief_name=brief.data['title'],
        brief_id=brief.id,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_organisation=brief.data['organisation'],
        supplier_user=supplier_user
    )

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response withdrawn'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.specialist_brief_response_withdrawn_email,
        user='',
        data={
            "to_address": to_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief_response)


def send_brief_response_withdrawn_email(supplier, brief, brief_response, supplier_user=None):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    to_address = brief_response.data['respondToEmailAddress']

    subject = "Your response for '{}' ({}) has been withdrawn".format(
        brief.data['title'],
        brief.id
    )

    brief_url = '{}/2/{}/opportunities/{}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        brief.framework.slug,
        brief.id
    )

    email_body = render_email_template(
        'brief_response_withdrawn.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_url=brief_url,
        brief_title=brief.data['title'],
        brief_id=brief.id,
        organisation=brief.data['organisation'],
        supplier_user=supplier_user
    )

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response withdrawn'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.brief_response_withdrawn_email,
        user='',
        data={
            "to_address": to_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief_response)


def send_brief_closed_email(brief):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    if brief.lot.slug in ['specialist']:
        return

    brief_email_sent_audit_event = audit_service.find(type=audit_types.sent_closed_brief_email.value,
                                                      object_type="Brief",
                                                      object_id=brief.id).count()

    if (brief_email_sent_audit_event > 0):
        return

    to_addresses = get_brief_emails(brief)

    # prepare copy
    email_body = render_email_template(
        'brief_closed.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id
    )

    subject = "Your opportunity has closed - please review all responses."

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief closed'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_closed_brief_email,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_seller_requested_feedback_from_buyer_email(brief):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    to_addresses = get_brief_emails(brief)

    # prepare copy
    email_body = render_email_template(
        'seller_requested_feedback_from_buyer_email.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id
    )

    subject = "Buyer notifications to unsuccessful sellers"

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='seller_requested_feedback_from_buyer_email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.seller_requested_feedback_from_buyer_email,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_seller_invited_to_rfx_email(brief, invited_supplier):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    if brief.lot.slug != 'rfx':
        return

    to_addresses = []
    if 'contact_email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['contact_email']]
    elif 'email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['email']]

    if len(to_addresses) > 0:
        email_body = render_email_template(
            'brief_rfx_invite_seller.md',
            frontend_url=current_app.config['FRONTEND_ADDRESS'],
            brief_name=brief.data['title'],
            brief_id=brief.id
        )

        subject = "You have been invited to respond to an opportunity"

        send_or_handle_error(
            to_addresses,
            email_body,
            subject,
            current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
            current_app.config['DM_GENERIC_SUPPORT_NAME'],
            event_description_for_errors='seller_invited_to_rfx_opportunity'
        )

        audit_service.log_audit_event(
            audit_type=audit_types.seller_invited_to_rfx_opportunity,
            user='',
            data={
                "to_addresses": ', '.join(to_addresses),
                "email_body": email_body,
                "subject": subject
            },
            db_object=brief)


def send_seller_invited_to_training_email(brief, invited_supplier):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    if brief.lot.slug != 'training2':
        return

    to_addresses = []
    if 'contact_email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['contact_email']]
    elif 'email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['email']]

    if len(to_addresses) > 0:
        email_body = render_email_template(
            'brief_training_invite_seller.md',
            frontend_url=current_app.config['FRONTEND_ADDRESS'],
            brief_name=brief.data['title'],
            brief_id=brief.id
        )

        subject = "You have been invited to respond to an opportunity"

        send_or_handle_error(
            to_addresses,
            email_body,
            subject,
            current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
            current_app.config['DM_GENERIC_SUPPORT_NAME'],
            event_description_for_errors='seller_invited_to_training_opportunity'
        )

        audit_service.log_audit_event(
            audit_type=audit_types.seller_invited_to_training_opportunity,
            user='',
            data={
                "to_addresses": ', '.join(to_addresses),
                "email_body": email_body,
                "subject": subject
            },
            db_object=brief)


def send_specialist_brief_published_email(brief):
    from app.api.services import (
        audit_service,
        audit_types,
        domain_service,
        suppliers
    )  # to circumvent circular dependency
    from app.models import Supplier

    if brief.lot.slug != 'specialist':
        return

    brief_email_sent_audit_event = audit_service.find(type=audit_types.specialist_brief_published.value,
                                                      object_type="Brief",
                                                      object_id=brief.id).count()

    if (brief_email_sent_audit_event > 0):
        return

    to_addresses = get_brief_emails(brief)

    invited_sellers = ''
    sellers_text = ''
    if brief.data.get('sellerSelector', '') == 'someSellers':
        sellers_text = ''
        seller_codes = []
        for key, value in brief.data.get('sellers', {}).iteritems():
            seller_codes.append(key)
        sellers = suppliers.filter(Supplier.code.in_(seller_codes)).all()
        for seller in sellers:
            invited_sellers += '* {}\n'.format(seller.name)
    else:
        panel_category = domain_service.get(id=brief.data.get('sellerCategory'))
        sellers_text = 'All sellers approved under {}'.format(panel_category.name)

    # prepare copy
    email_body = render_email_template(
        'specialist_brief_published.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id,
        brief_close_date=brief.closed_at.strftime('%d/%m/%Y'),
        sellers_text=sellers_text,
        invited_sellers=invited_sellers,
        number_of_suppliers=brief.data.get('numberOfSuppliers', ''),
        question_close_date=brief.questions_closed_at.strftime('%d/%m/%Y')
    )

    subject = "Your opportunity for {} has been published".format(brief.data['title'])

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief published'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.specialist_brief_published,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_specialist_brief_seller_invited_email(brief, invited_supplier):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    if brief.lot.slug != 'specialist':
        return

    to_addresses = []
    if 'contact_email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['contact_email']]
    elif 'email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['email']]

    if len(to_addresses) > 0:
        number_of_suppliers = int(brief.data['numberOfSuppliers'])
        email_body = render_email_template(
            'specialist_brief_invite_seller.md',
            frontend_url=current_app.config['FRONTEND_ADDRESS'],
            brief_name=brief.data['title'],
            brief_id=brief.id,
            brief_organisation=brief.data['organisation'],
            brief_close_date=brief.closed_at.strftime('%d/%m/%Y'),
            question_close_date=brief.questions_closed_at.strftime('%d/%m/%Y'),
            number_of_suppliers=number_of_suppliers,
            number_of_suppliers_plural='s' if number_of_suppliers > 1 else ''
        )

        subject = "You're invited to submit candidates for {}".format(brief.data['title'])

        send_or_handle_error(
            to_addresses,
            email_body,
            subject,
            current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
            current_app.config['DM_GENERIC_SUPPORT_NAME'],
            event_description_for_errors='seller_invited_to_specialist_opportunity'
        )

        audit_service.log_audit_event(
            audit_type=audit_types.seller_invited_to_specialist_opportunity,
            user='',
            data={
                "to_addresses": ', '.join(to_addresses),
                "email_body": email_body,
                "subject": subject
            },
            db_object=brief)


def send_specialist_brief_closed_email(brief):
    from app.api.services import (
        audit_service,
        audit_types,
        brief_responses_service
    )  # to circumvent circular dependency

    if brief.lot.slug != 'specialist':
        return

    audit_event = audit_service.find(type=audit_types.specialist_brief_closed_email.value,
                                     object_type="Brief",
                                     object_id=brief.id).count()

    if (audit_event > 0):
        return

    responses = brief_responses_service.get_brief_responses(brief.id, None, submitted_only=True)
    to_addresses = get_brief_emails(brief)

    # prepare copy
    email_body = render_email_template(
        'specialist_brief_closed.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id,
        number_of_responses='{}'.format(len(responses)),
        number_of_responses_plural='s' if len(responses) > 1 else ''
    )

    subject = 'Your "{}" opportunity has closed.'.format(brief.data['title'])

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief closed'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.specialist_brief_closed_email,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_brief_clarification_to_buyer(brief, brief_question, supplier):
    from app.api.services import (
        audit_service,
        audit_types
    )  # to circumvent circular dependency

    to_addresses = get_brief_emails(brief)

    # prepare copy
    email_body = render_email_template(
        'brief_question_to_buyer.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_id=brief.id,
        brief_name=escape_markdown(brief.data.get('title')),
        publish_by_date=brief.closed_at.strftime('%d/%m/%Y'),
        message=escape_markdown(brief_question.data.get('question')),
        supplier_name=escape_markdown(supplier.name)
    )

    subject = "You received a new question for ‘{}’".format(brief.data.get('title'))

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief question email sent to buyer'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_brief_question_to_buyer,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_brief_clarification_to_seller(brief, brief_question, to_address):
    from app.api.services import (
        audit_service,
        audit_types
    )  # to circumvent circular dependency

    # prepare copy
    email_body = render_email_template(
        'brief_question_to_seller.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_id=brief.id,
        brief_name=escape_markdown(brief.data.get('title')),
        brief_organisation=brief.data.get('organisation'),
        publish_by_date=brief.questions_closed_at.strftime('%d/%m/%Y'),
        message=escape_markdown(brief_question.data.get('question'))
    )

    subject = u"You submitted a question for {} ({}) successfully".format(brief.data.get('title'), brief.id)

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief question email sent to seller'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_brief_question_to_seller,
        user='',
        data={
            "to_addresses": to_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_opportunity_closed_early_email(brief, current_user):
    # to circumvent circular dependencies
    from app.api.services import audit_service, audit_types

    to_addresses = get_brief_emails(brief)
    supplier_code, seller = next(iter(brief.data.get('sellers', {}).items()))

    email_body = render_email_template(
        'opportunity_closed_early.md',
        brief_id=brief.id,
        framework=brief.framework.slug,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        possessive="'" if seller['name'].lower().endswith('s') else "'s",
        seller_name=escape_markdown(seller['name']),
        title=escape_markdown(brief.data['title']),
        user=escape_markdown(current_user.name)
    )

    subject = "'{}' has been closed early".format(brief.data['title'])

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors=audit_types.close_opportunity_early
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_opportunity_closed_early_email,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief
    )


def send_opportunity_edited_email_to_buyers(brief, current_user, edit):
    # to circumvent circular dependencies
    from app.api.business.brief import brief_edit_business
    from app.api.services import audit_service, audit_types

    to_addresses = get_brief_emails(brief)

    summary = ''
    seller_questions_message = ''
    timezone = 'Australia/Canberra'
    changes = brief_edit_business.get_changes_made_to_opportunity(brief, edit)

    if 'closingDate' in changes:
        seller_questions_message = (
            'The last day sellers can ask questions is now {}. '.format(
                brief.questions_closed_at.in_timezone(timezone).format('%-d %B %Y')
            ) +
            'You must answer all relevant questions while the opportunity is live.'
        )

        summary = '* Closing date changed from {} to {}\n'.format(
            pendulum.parse(edit.data['closed_at'], tz=timezone).format('%-d %B %Y'),
            brief.closed_at.in_timezone(timezone).format('%-d %B %Y')
        )

    if 'title' in changes:
        summary += "* Title changed from '{}' to '{}'\n".format(
            escape_markdown(edit.data['title']), escape_markdown(brief.data['title'])
        )

    if 'sellers' in changes:
        new_sellers = []
        for key, value in changes['sellers']['newValue'].items():
            if key not in changes['sellers']['oldValue']:
                new_sellers.append(value['name'])

        number_of_sellers_invited = len(new_sellers)
        seller_or_sellers = 'seller' if number_of_sellers_invited == 1 else 'sellers'
        summary += '* {} more {} invited to apply:\n'.format(number_of_sellers_invited, seller_or_sellers)

        sorted_sellers = sorted(new_sellers, key=lambda s: s.lower())
        for seller in sorted_sellers:
            summary += '    * {}\n'.format(
                escape_markdown(seller)
            )

    if 'summary' in changes:
        summary += '* Summary was updated\n'

    def generate_document_changes(old, new):
        text = ''
        removed = [x for x in old if x not in new]
        added = [x for x in new if x not in old]
        if len(removed) > 0:
            for x in removed:
                text += '* ' + escape_markdown(x) + ' removed\n'
        if len(added) > 0:
            for x in added:
                text += '* ' + escape_markdown(x) + ' added\n'
        return text

    if 'attachments' in changes:
        summary += generate_document_changes(changes['attachments']['oldValue'], changes['attachments']['newValue'])

    if 'responseTemplate' in changes:
        summary += generate_document_changes(
            changes['responseTemplate']['oldValue'], changes['responseTemplate']['newValue']
        )

    if 'requirementsDocument' in changes:
        summary += generate_document_changes(
            changes['requirementsDocument']['oldValue'], changes['requirementsDocument']['newValue']
        )

    email_body = render_email_template(
        'opportunity_edited_buyers.md',
        brief_id=brief.id,
        edit_summary=summary,
        framework=brief.framework.slug,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        seller_questions_message=seller_questions_message,
        title=escape_markdown(brief.data['title']),
        user=escape_markdown(current_user.name)
    )

    subject = "Updates made to '{}' opportunity".format(brief.data['title'])

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors=audit_types.opportunity_edited
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_opportunity_edited_email_to_buyers,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief
    )


def send_opportunity_edited_email_to_seller(brief, email_address, buyer):
    # to circumvent circular dependencies
    from app.api.services import audit_service, audit_types

    candidate_message = ''
    if brief.lot.slug == 'specialist':
        candidate_message = "candidate's "

    formatted_closing_date = (
        brief.closed_at.in_timezone('Australia/Canberra').format('%A %-d %B %Y at %-I:%M%p (in Canberra)')
    )

    email_body = render_email_template(
        'opportunity_edited_sellers.md',
        brief_id=brief.id,
        buyer=buyer,
        candidate_message=candidate_message,
        closing_date=formatted_closing_date,
        framework=brief.framework.slug,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        title=escape_markdown(brief.data['title'])
    )

    subject = "Changes made to '{}' opportunity".format(brief.data['title'])

    send_or_handle_error(
        email_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors=audit_types.opportunity_edited
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_opportunity_edited_email_to_seller,
        user='',
        data={
            "to_addresses": email_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief
    )


def send_opportunity_withdrawn_email_to_buyers(brief, current_user):
    # to circumvent circular dependencies
    from app.api.business.brief import brief_business
    from app.api.services import audit_service, audit_types

    to_addresses = get_brief_emails(brief)
    seller_message = ''
    invited_seller_codes = brief.data.get('sellers', {}).keys()

    if brief_business.is_open_to_all(brief):
        seller_message = 'We have notified sellers who have drafted or submitted responses to this opportunity'
    elif len(invited_seller_codes) == 1:
        invited_seller_code = invited_seller_codes.pop()
        seller_name = brief.data['sellers'][invited_seller_code]['name']
        seller_message = '{} has been notified'.format(seller_name)
    else:
        seller_message = 'All invited sellers have been notified'

    email_body = render_email_template(
        'opportunity_withdrawn_buyers.md',
        brief_id=brief.id,
        framework=brief.framework.slug,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        seller_message=escape_markdown(seller_message),
        title=escape_markdown(brief.data['title']),
        user=escape_markdown(current_user.name),
        withdrawal_reason=escape_markdown(brief.data['reasonToWithdraw'])
    )

    subject = "'{}' ({}) is withdrawn from the Digital Marketplace".format(
        brief.data['title'],
        brief.id
    )

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors=audit_types.withdraw_opportunity
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_opportunity_withdrawn_email_to_buyers,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief
    )


def send_opportunity_withdrawn_email_to_seller(brief, email_address, buyer):
    # to circumvent circular dependencies
    from app.api.services import audit_service, audit_types

    email_body = render_email_template(
        'opportunity_withdrawn_sellers.md',
        brief_id=brief.id,
        buyer=buyer,
        framework=brief.framework.slug,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        title=escape_markdown(brief.data['title']),
        withdrawal_reason=escape_markdown(brief.data['reasonToWithdraw'])
    )

    subject = "'{}' ({}) is withdrawn from the Digital Marketplace".format(
        brief.data['title'],
        brief.id
    )

    send_or_handle_error(
        email_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors=audit_types.withdraw_opportunity
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_opportunity_withdrawn_email_to_seller,
        user='',
        data={
            "to_addresses": email_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief
    )


def get_brief_emails(brief):
    to_addresses = [user.email_address for user in brief.users if user.active]
    to_addresses = to_addresses + [
        tb.user.email_address
        for tb in brief.team_briefs
        if tb.user.active and tb.team.status == 'completed']

    to_addresses = to_addresses + [
        tb.team.email_address
        for tb in brief.team_briefs
        if tb.team.status == 'completed' and tb.team.email_address
    ]

    return to_addresses
