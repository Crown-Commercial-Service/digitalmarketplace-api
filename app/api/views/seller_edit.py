from flask import jsonify, Response
from flask_login import login_required, current_user
from app.api import api
from app.api.business import seller_edit_business
from app.api.helpers import role_required, abort, forbidden
from ...utils import get_json_from_request
from app.api.business.errors import (
    DeletedError,
    NotFoundError,
    UnauthorisedError,
    ValidationError
)


@api.route('/supplier/<int:supplier_code>/edit', methods=['GET'])
@login_required
@role_required('supplier')
def supplier_edit(supplier_code):
    """Seller edit (role=supplier)
    ---
    tags:
      - seller edit
    definitions:
      SellerEdit:
        type: object
        properties:
            supplier:
              type: object
              properties:
                abn:
                  type: string
                code:
                  type: string
                name:
                  type: string
                data:
                  type: object
            agreementStatus:
              type: object
              properties:
                canSign:
                    type: boolean
                canUserSign:
                    type: boolean
                show:
                    type: boolean
                signed:
                    type: boolean
                startDate:
                    type: string
    parameters:
      - name: supplier_code
        in: path
        type: number
        required: true
    responses:
      200:
        description: Supplier edit info
        schema:
          $ref: '#/definitions/SellerEdit'
      403:
        description: Unauthorised to get info.

    """

    if current_user.supplier_code != supplier_code:
        return forbidden('Unauthorised to get info')

    info = seller_edit_business.get_supplier_edit_info({
        'supplier_code': current_user.supplier_code,
        'email_address': current_user.email_address
    })
    return jsonify(info), 200


@api.route('/supplier/<int:supplier_code>/edit', methods=['PATCH'])
@login_required
@role_required('supplier')
def update_supplier(supplier_code):
    """Update supplier (role=supplier)
    ---
    tags:
      - seller edit
    parameters:
      - name: supplier_code
        in: path
        type: number
        required: true
      - name: body
        in: body
        required: true
        schema:
            $ref: '#/definitions/SellerEdit'
    responses:
        200:
            description: Supplier updated successfully.
            schema:
                $ref: '#/definitions/SellerEdit'
        400:
            description: Bad request.
        403:
            description: Unauthorised to update supplier.
        404:
            description: Supplier not found.
        500:
            description: Unexpected error.
    """

    if current_user.supplier_code != supplier_code:
        return forbidden('Unauthorised to update supplier')

    try:
        data = get_json_from_request()
        seller_edit_business.update_supplier(data, {
            'supplier_code': current_user.supplier_code,
            'email_address': current_user.email_address,
            'name': current_user.name,
            'role': current_user.role
        })
    except NotFoundError as nfe:
        not_found(nfe.message)
    except DeletedError as de:
        abort(de.message)
    except ValidationError as ve:
        abort(ve.message)

    info = seller_edit_business.get_supplier_edit_info({
        'supplier_code': current_user.supplier_code,
        'email_address': current_user.email_address
    })
    return jsonify(info), 200


@api.route('/supplier/<int:supplier_code>/edit/accept-agreement', methods=['POST'])
@login_required
@role_required('supplier')
def accept_agreement(supplier_code):
    """Accept agreement (role=supplier)
    ---
    tags:
      - seller edit
    parameters:
      - name: supplier_code
        in: path
        type: number
        required: true
    responses:
        200:
            description: Supplier edit info
            schema:
                $ref: '#/definitions/SellerEdit'
        400:
            description: Bad request.
        403:
            description: Unauthorised to accept agreement.
        404:
            description: Supplier not found.
        500:
            description: Unexpected error.
    """

    if current_user.supplier_code != supplier_code:
        return forbidden('Unauthorised to accept agreement')

    try:
        seller_edit_business.accept_agreement({
            'supplier_code': current_user.supplier_code,
            'email_address': current_user.email_address,
            'user_id': current_user.id
        })
    except NotFoundError as nfe:
        not_found(nfe.message)
    except DeletedError as de:
        abort(de.message)
    except ValidationError as ve:
        abort(ve.message)
    except UnauthorisedError as ue:
        abort(ue.message)

    info = seller_edit_business.get_supplier_edit_info({
        'supplier_code': current_user.supplier_code,
        'email_address': current_user.email_address
    })
    return jsonify(info), 200


@api.route('/supplier/<int:supplier_code>/edit/decline-agreement', methods=['POST'])
@login_required
@role_required('supplier')
def decline_agreement(supplier_code):
    """Decline agreement (role=supplier)
    ---
    tags:
      - seller edit
    parameters:
      - name: supplier_code
        in: path
        type: number
        required: true
    responses:
        200:
            description: Agreement declined.
        400:
            description: Bad request.
        403:
            description: Unauthorised to decline agreement.
        404:
            description: Supplier not found.
        500:
            description: Unexpected error.
    """

    if current_user.supplier_code != supplier_code:
        return forbidden('Unauthorised to decline agreement')

    try:
        seller_edit_business.decline_agreement({
            'supplier_code': current_user.supplier_code,
            'email_address': current_user.email_address
        })
    except NotFoundError as nfe:
        not_found(nfe.message)
    except DeletedError as de:
        abort(de.message)
    except UnauthorisedError as ue:
        abort(ue.message)

    return Response(status=200)


@api.route('/supplier/<int:supplier_code>/edit/notify-auth-rep', methods=['POST'])
@login_required
@role_required('supplier')
def notify_auth_rep(supplier_code):
    """Notify auth rep (role=supplier)
    ---
    tags:
      - seller edit
    parameters:
      - name: supplier_code
        in: path
        type: number
        required: true
    responses:
        200:
            description: Supplier edit info
            schema:
                $ref: '#/definitions/SellerEdit'
        400:
            description: Bad request.
        403:
            description: Unauthorised to notify authorised representative.
        404:
            description: Supplier not found.
        500:
            description: Unexpected error.
    """

    if current_user.supplier_code != supplier_code:
        return forbidden('Unauthorised to notify authorised representative')

    try:
        seller_edit_business.notify_auth_rep({
            'supplier_code': current_user.supplier_code,
            'email_address': current_user.email_address
        })
    except NotFoundError as nfe:
        not_found(nfe.message)
    except DeletedError as de:
        abort(de.message)

    info = seller_edit_business.get_supplier_edit_info({
        'supplier_code': current_user.supplier_code,
        'email_address': current_user.email_address
    })
    return jsonify(info), 200
