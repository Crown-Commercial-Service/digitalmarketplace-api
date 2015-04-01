from flask import jsonify, abort, request
from flask import url_for as base_url_for

from .. import main
from ...models import Supplier

# TODO: This should probably not be here
API_FETCH_PAGE_SIZE = 100


API_FETCH_PAGE_SIZE = 2

# get this copy+pasted code outta here
def link(rel, href):
    if href is not None:
        return {
            "rel": rel,
            "href": href,
        }

def url_for(*args, **kwargs):
    kwargs.setdefault('_external', True)
    return base_url_for(*args, **kwargs)


def pagination_links(pagination, endpoint, args):
    return [
        link(rel, url_for(endpoint,
                          **dict(list(args.items()) +
                                 list({'page': page}.items()))))
        for rel, page in [('next', pagination.next_num),
                          ('prev', pagination.prev_num)]
        if 0 < page <= pagination.pages
    ]


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
        per_page=API_FETCH_PAGE_SIZE,
        error_out=False,
    )

    if not suppliers.items:
        if page > 1:
            abort(404, "Page number out of range")
        else:
            abort(404, "No suppliers found for '{0}'".format(prefix))

    return jsonify(
        suppliers=[supplier.serialize() for supplier in suppliers.items],
        links=Supplier.pagination_links(
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
