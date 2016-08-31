from flask import jsonify
from .. import main
from ...models import (
    FrameworkAgreement
)


@main.route('/agreements/<int:agreement_id>', methods=['GET'])
def get_framework_agreement(agreement_id):
    framework_agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first_or_404()

    return jsonify(agreement=framework_agreement.serialize())
