# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app

from .util import render_email_template, send_or_handle_error

import rollbar


def send_brief_response_received_email(supplier, brief, brief_response):
    if brief.lot.slug in ['specialist']:
        return

    if brief.lot.slug == 'digital-outcome':
        TEMPLATE_FILENAME = 'brief_response_submitted_outcome.md'
    elif brief.lot.slug == 'training':
        TEMPLATE_FILENAME = 'brief_response_submitted_training.md'
    elif brief.lot.slug == 'rfx':
        TEMPLATE_FILENAME = 'brief_response_submitted_rfx.md'
    elif brief.lot.slug == 'atm':
        TEMPLATE_FILENAME = 'brief_response_submitted_atm.md'
    else:
        TEMPLATE_FILENAME = 'brief_response_submitted.md'

    to_address = brief_response.data['respondToEmailAddress']
    specialist_name = brief_response.data.get('specialistName', None)

    if brief.lot.slug == 'rfx' or brief.lot.slug == 'atm':
        brief_url = current_app.config['FRONTEND_ADDRESS'] + '/2/' + brief.framework.slug + '/opportunities/' \
            + str(brief.id)
    else:
        brief_url = current_app.config['FRONTEND_ADDRESS'] + '/' + brief.framework.slug + '/opportunities/' \
            + str(brief.id)
    attachment_url = current_app.config['FRONTEND_ADDRESS'] +\
        '/api/2/brief/' + str(brief.id) + '/respond/documents/' + str(supplier.code) + '/'

    ess = ""
    if brief_response.data.get('essentialRequirements', None):
        i = 0
        for req in brief.data['essentialRequirements']:
            ess += "####• {}\n{}\n\n".format(req, brief_response.data['essentialRequirements'][i])
            i += 1
    nth = ""
    if brief_response.data.get('niceToHaveRequirements', None):
        i = 0
        for req in brief.data['niceToHaveRequirements']:
            nth += "####• {}\n{}\n\n".format(
                req,
                brief_response.data.get('niceToHaveRequirements', [])[i]
                if i < len(brief_response.data.get('niceToHaveRequirements', [])) else ''
            )
            i += 1
    criteriaResponses = ""
    evaluationCriteriaResponses = brief_response.data.get('criteria', {})
    if evaluationCriteriaResponses:
        for evaluationCriteria in brief.data['evaluationCriteria']:
            if 'criteria' in evaluationCriteria and\
               evaluationCriteria['criteria'] in evaluationCriteriaResponses.keys():
                criteriaResponses += "####• {}\n{}\n\n".format(
                    evaluationCriteria['criteria'],
                    evaluationCriteriaResponses[evaluationCriteria['criteria']]
                )

    attachments = ""
    for attch in brief_response.data.get('attachedDocumentURL', []):
        attachments += "####• [{}]({}{})\n\n".format(attch, attachment_url, attch)

    subject = "We've received your application"
    response_title = "How you responded"
    if specialist_name:
        subject = "{}'s application for opportunity ID {} has been received".format(specialist_name, brief.id)
        response_title = "{}'s responses".format(specialist_name)

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        brief_url=brief_url,
        brief_name=brief.data['title'],
        essential_requirements=ess,
        nice_to_have_requirements=nth,
        criteria_responses=criteriaResponses,
        attachments=attachments,
        closing_at=brief.closed_at.to_formatted_date_string(),
        specialist_name=specialist_name,
        response_title=response_title,
        brief_response=brief_response.data,
        header='<div style="font-size: 1.8rem">'
               '<span style="color: #007554;padding-right: 1rem;">✔</span>'
               '<span>{}</span></div>'.format(subject)
    )

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response recieved'
    )


def send_specialist_brief_response_received_email(supplier, brief, brief_response):
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
                brief_response.data['essentialRequirements'][req['criteria']]
            )
            i += 1

    nth = ""
    if brief_response.data.get('niceToHaveRequirements', None):
        i = 0
        for req in brief.data['niceToHaveRequirements']:
            nth += "**{}. {}**\n\n{}\n\n".format(
                i + 1,
                req['criteria'],
                brief_response.data.get('niceToHaveRequirements', [])[req['criteria']]
                if i < len(brief_response.data.get('niceToHaveRequirements', [])) else ''
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
                    evaluationCriteriaResponses[evaluationCriteria['criteria']]
                )

    attachments = ''
    resume = ''
    for attach in brief_response.data.get('attachedDocumentURL', []):
        if not resume:
            resume = '[{}]({}{})  '.format(attach, attachment_url, attach)
        else:
            attachments += "* [{}]({}{})\n\n".format(attach, attachment_url, attach)

    if attachments:
        attachments = '**Other documents:**  \n\n  ' + attachments

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
            brief_response.data.get('securityClearance')
        )

    response_rates = ''
    response_rates_excluding_gst = ''
    if brief.data.get('preferredFormatForRates') == 'hourlyRate':
        response_rates = '**Hourly rate, including GST:** ${}'.format(
            brief_response.data.get('hourRate')
        )
        response_rates_excluding_gst = '**Hourly rate, excluding GST:** ${}'.format(
            brief_response.data.get('hourRateExcludingGST')
        )
    elif brief.data.get('preferredFormatForRates') == 'dailyRate':
        response_rates = '**Daily rate, including GST:** ${}'.format(
            brief_response.data.get('dayRate')
        )
        response_rates_excluding_gst = '**Daily rate, excluding GST:** ${}'.format(
            brief_response.data.get('dayRateExcludingGST')
        )

    response_visa_status = ''
    if brief_response.data.get('visaStatus') == 'AustralianCitizen':
        response_visa_status = 'Australian citizen'
    elif brief_response.data.get('visaStatus') == 'PermanentResident':
        response_visa_status = 'Permanent resident'
    elif brief_response.data.get('visaStatus') == 'ForeignNationalWithAValidVisa':
        response_visa_status = 'Foreign national with a valid visa'

    # prepare copy
    email_body = render_email_template(
        'specialist_brief_response_submitted.md',
        brief_url=brief_url,
        brief_name=brief.data['title'],
        brief_organisation=brief.data['organisation'],
        essential_requirements=ess,
        nice_to_have_requirements=nth,
        criteria_responses=criteriaResponses,
        resume=resume,
        attachments=attachments,
        closing_at=brief.closed_at.to_formatted_date_string(),
        specialist_name=specialist_name,
        response_rates=response_rates,
        response_rates_excluding_gst=response_rates_excluding_gst,
        response_previously_worked=brief_response.data.get('previouslyWorked'),
        response_security_clearance=response_security_clearance,
        response_start_date=brief_response.data.get('availability'),
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


def send_brief_closed_email(brief):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    if brief.lot.slug in ['specialist']:
        return

    brief_email_sent_audit_event = audit_service.find(type=audit_types.sent_closed_brief_email.value,
                                                      object_type="Brief",
                                                      object_id=brief.id).count()

    if (brief_email_sent_audit_event > 0):
        return

    to_addresses = [user.email_address for user in brief.users if user.active]

    # prepare copy
    email_body = render_email_template(
        'brief_closed.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id
    )

    subject = "Your brief has closed - please review all responses."

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

    to_addresses = [user.email_address for user in brief.users if user.active]

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

    to_addresses = [user.email_address for user in brief.users if user.active]

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

    responses = brief_responses_service.find(brief_id=brief.id).all()
    to_addresses = [user.email_address for user in brief.users if user.active]

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
