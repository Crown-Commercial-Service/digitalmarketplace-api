from flask import jsonify, abort, request, current_app

from .. import main
from ...models import Supplier
from ...utils import pagination_links


@main.route('/suppliers', methods=['GET'])
def list_suppliers():


    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    prefix = request.args.get('prefix', '')

    suppliers = Supplier.query

    if prefix:
        # case insensitive LIKE comparison for matching supplier names
        suppliers = suppliers.filter(
            Supplier.name.ilike(prefix + '%'))

    suppliers = suppliers.paginate(
        page=page,
        per_page=current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'],
        error_out=False,
    )

    if not suppliers.items:
        if page > 1:
            abort(404, "Page number out of range")
        else:
            abort(404, "No suppliers found for '{0}'".format(prefix))

    return jsonify(
        suppliers=[supplier.serialize() for supplier in suppliers.items],
        links=pagination_links(
            suppliers,
            '.list_suppliers',
            request.args
        ))


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=supplier.serialize())

# Route to insert new Suppliers, yeah?
@main.route('/suppliers', methods=['POST'])
def import_supplier():

    html_string = ''

    supplier_data = get_json_from_request()

    html_string += '<h1>received json</h1><pre>' + dump(supplier_data) + '</pre><br><br>'

    json_has_required_keys(supplier_data, ['clientsString', 'contactInformation'])

    # Break the 'clientsString' into an array, because this is what our model (will) expect
    supplier_data['clientsString'] = supplier_data['clientsString'].split(',')

    # address is nested an extra level.  No longer.
    for index, val in enumerate(supplier_data['contactInformation']):
        supplier_data['contactInformation'][index] = un_nest_key_value_pairs(
            supplier_data['contactInformation'][index],
            'address'
        )

    validate_supplier_json_or_400(supplier_data)

    html_string += '<h1>processed json</h1><pre>' + dump(supplier_data) + '</pre><br><br>'

    return html_string

    """

    # Graceless way to imply that this is a placeholder.
    supplier = Supplier(supplier_id=19999191919191919191911982918291829182918)
    supplier.name = supplier_data['name']

    db.session.add(supplier)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.message)

    """
    return "", 201


def un_nest_key_value_pairs(obj, key_of_nested_obj):

    if key_of_nested_obj not in obj.keys():
        abort(400, "No '{0}' key found to un-nest.".format(key_of_nested_obj))

    nested_obj = obj[key_of_nested_obj]

    obj = drop_foreign_fields(
        obj,
        [key_of_nested_obj]
    )

    for key in nested_obj.keys():
        obj[key] = nested_obj[key]

    return obj

# @see http://stackoverflow.com/questions/15785719/how-to-print-a-dictionary-line-by-line-in-python
def dump(obj, nested_level=0):
    output_string = ''
    spacing = '   '
    if type(obj) == dict:
        output_string += '<br>%s{' % ((nested_level) * spacing)
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                output_string += '<br>%s%s:' % ((nested_level + 1) * spacing, k)
                output_string += dump(v, nested_level + 1)
            else:
                output_string += '<br>%s%s: %s' % ((nested_level + 1) * spacing, k, v)
        output_string += '<br>%s}' % (nested_level * spacing)
    elif type(obj) == list:
        output_string += '<br>%s[' % ((nested_level) * spacing)
        for v in obj:
            if hasattr(v, '__iter__'):
                output_string += dump(v, nested_level + 1)
            else:
                output_string += '<br>%s%s' % ((nested_level + 1) * spacing, v)
        output_string += '<br>%s]' % ((nested_level) * spacing)
    else:
        output_string += '<br>%s%s' % (nested_level * spacing, obj)

    return output_string
