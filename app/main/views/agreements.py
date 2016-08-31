from flask import jsonify
from .. import main
from ... import db
from ...models import (
    FrameworkAgreement
)
from ...validation import (
    validate_supplier_json_or_400,
    validate_contact_information_json_or_400,
    is_valid_string_or_400
)


@main.route('/agreements/<int:agreement_id>', methods=['GET'])
def get_framework_agreement(agreement_id):
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()

    return jsonify(agreement=framework_agreement.serialize())
