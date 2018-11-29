from flask import current_app
from .util import render_email_template, send_or_handle_error, fill_template


def send_dreamail(simulate):
    from app.api.services import (
        audit_service,
        audit_types,
        suppliers
    )
    simulation_result = []

    result = suppliers.get_suppliers_with_rejected_price()

    for item in result:
        supplier_code = item['code']
        supplier = suppliers.find(code=item['code']).one_or_none()

        sent = audit_service.find(
            object_id=supplier.id,
            object_type='Supplier',
            type='seller_to_review_pricing_case_study_email'
        ).one_or_none()
        if sent:
            continue

        case_studies = supplier.case_studies

        option_1_aoe = []
        option_2_aoe = []
        for supplier_domain in supplier.domains:
            if supplier_domain.price_status != 'rejected':
                continue

            domain_name = supplier_domain.domain.name
            case_studies_in_domain = [cs for cs in case_studies if cs.data['service'] == domain_name]
            approved_case_studies = any((
                cs.status == 'approved' or
                cs.status == 'unassessed'
            ) for cs in case_studies_in_domain)
            if approved_case_studies:
                option_1_aoe.append('* {}'.format(domain_name))
            else:
                option_2_aoe.append('* {}'.format(domain_name))

        dreamail_option_1_content = ''
        if option_1_aoe:
            dreamail_option_1_content = fill_template(
                'dreamail_option_1.md',
                aoe='\n'.join(option_1_aoe)
            )

        dreamail_option_2_content = ''
        if option_2_aoe:
            dreamail_option_2_content = fill_template(
                'dreamail_option_2.md',
                frontend_url=current_app.config['FRONTEND_ADDRESS'],
                aoe='\n'.join(option_2_aoe)
            )

        if dreamail_option_1_content == '' and dreamail_option_2_content == '':
            continue

        email_body = render_email_template(
            'dreamail.md',
            dreamail_option_1=dreamail_option_1_content,
            dreamail_option_2=dreamail_option_2_content,
            frontend_url=current_app.config['FRONTEND_ADDRESS'],
            supplier_name=supplier.name
        )

        subject = 'Please review your pricing and/or case studies on the Marketplace'

        to_addresses = [
            e['email_address']
            for e in suppliers.get_supplier_contacts(supplier_code)
        ]
        if simulate:
            simulation_result.append({
                'to_addresses': to_addresses,
                'email_body': email_body,
                'subject': subject,
                'supplier_code': supplier_code
            })
        else:
            send_or_handle_error(
                to_addresses,
                email_body,
                subject,
                current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
                current_app.config['DM_GENERIC_SUPPORT_NAME'],
                event_description_for_errors=audit_types.seller_to_review_pricing_case_study_email
            )

            audit_service.log_audit_event(
                audit_type=audit_types.seller_to_review_pricing_case_study_email,
                user='',
                data={
                    "to_addresses": ', '.join(to_addresses),
                    "email_body": email_body,
                    "subject": subject
                },
                db_object=supplier)

    if simulate:
        return simulation_result
