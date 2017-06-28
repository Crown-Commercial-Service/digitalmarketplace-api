from flask import jsonify, request, current_app, abort
from sqlalchemy.exc import IntegrityError

from app.main import main
from app.models import db, Agreement, SignedAgreement, User
from app.utils import (get_json_from_request, json_has_required_keys,
                       pagination_links, get_valid_page_or_1, get_positive_int_or_400)


@main.route('/agreements', methods=['GET'])
def list_agreements():
    current_only = request.args.get('current_only', False)
    page = get_valid_page_or_1()

    agreements = Agreement.query
    if current_only:
        agreements = agreements.filter(Agreement.is_current)

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_PAGE_SIZE']
    )

    agreements = agreements.paginate(
        page=page,
        per_page=results_per_page
    )

    return jsonify(
        agreements=[agreement.serialize() for agreement in agreements.items],
        links=pagination_links(
            agreements,
            '.list_agreements',
            request.args
        )
    )


@main.route('/agreements/signed', methods=['POST'])
def sign_agreement():
    signed_agreement_json = get_json_from_request()
    json_has_required_keys(signed_agreement_json, ['signed_agreement'])

    user_id = signed_agreement_json['signed_agreement']['user_id']

    user = User.query.get(user_id)

    if user.supplier_code != signed_agreement_json['signed_agreement']['supplier_code']:
        abort(400, 'User is not authorized to submit application')

    signed_agreement = SignedAgreement()
    signed_agreement.update_from_json(signed_agreement_json['signed_agreement'])

    db.session.add(signed_agreement)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    db.session.commit()

    return jsonify(signed_agreement=signed_agreement.serializable), 201


@main.route('/agreements/signed/<int:supplier_code>', methods=['GET'])
def list_agreements_signed(supplier_code):
    current_only = request.args.get('current_only', False)
    page = get_valid_page_or_1()

    agreements = SignedAgreement.query.filter(SignedAgreement.supplier_code == supplier_code)
    if current_only:
        agreements = agreements.outerjoin(Agreement, Agreement.id == SignedAgreement.agreement_id)\
            .filter(Agreement.is_current)

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_PAGE_SIZE']
    )

    agreements = agreements.paginate(
        page=page,
        per_page=results_per_page
    )

    return jsonify(
        agreements=[agreement.serialize() for agreement in agreements.items],
        links=pagination_links(
            agreements,
            '.list_agreements',
            request.args
        )
    )
