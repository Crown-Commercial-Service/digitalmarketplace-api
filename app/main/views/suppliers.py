from datetime import datetime

from flask import abort, current_app, jsonify, request, url_for
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.sql.expression import true
from sqlalchemy.sql import cast
from sqlalchemy import Boolean, select, column, or_
from sqlalchemy.dialects.postgresql import ARRAY, array
from sqlalchemy.dialects import postgresql as postgres
from sqlalchemy import String, literal
from sqlalchemy.types import TEXT
from sqlalchemy.orm import noload, joinedload

from .. import main
from ... import db
from ...models import (
    Supplier, AuditEvent, SupplierFramework, Framework, PriceSchedule, User, Domain, Application,
    ServiceRole, SupplierDomain, Product, CaseStudy, Contact, SupplierContact
)

from sqlalchemy.sql import func, desc, or_, asc, and_
from functools import reduce

from app.utils import (
    get_json_from_request, get_nonnegative_int_or_400, get_positive_int_or_400,
    get_valid_page_or_1, json_has_required_keys, pagination_links,
    validate_and_return_updater_request
)
from ...supplier_utils import validate_agreement_details_data
from dmapiclient.audit import AuditTypes
from dmutils.logging import notify_team
from app.emails import send_assessment_approval_notification
import json
from itertools import groupby, chain
from operator import itemgetter
from app.api.business.validators import ApplicationValidator
from app.tasks import publish_tasks


@main.route('/suppliers', methods=['GET'])
def list_suppliers():
    page = get_valid_page_or_1()

    prefix = request.args.get('prefix', '')
    name = request.args.get('name', None)

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_SUPPLIERS_PAGE_SIZE']
    )

    if name is None:
        suppliers = Supplier.query.filter(Supplier.abn.is_(None) | (Supplier.abn != Supplier.DUMMY_ABN))
    else:
        suppliers = Supplier.query.filter((Supplier.name == name) | (Supplier.long_name == name))

    suppliers = suppliers.filter(Supplier.status != 'deleted')

    if prefix:
        if prefix == 'other':
            suppliers = suppliers.filter(
                Supplier.name.op('~')('^[^A-Za-z]'))
        else:
            suppliers = suppliers.outerjoin(SupplierContact).outerjoin(Contact)
            # case insensitive LIKE comparison for matching supplier names, supplier email and contact email
            suppliers = suppliers.filter(or_(
                Supplier.name.ilike(prefix + '%'),
                Supplier.data['email'].astext.ilike('%{}%'.format(prefix)),
                Contact.email.ilike('%{}%'.format(prefix))
            ))

    suppliers = suppliers.distinct(Supplier.name, Supplier.code)

    try:
        if results_per_page > 0:
            paginator = suppliers.paginate(
                page=page,
                per_page=results_per_page,
            )
            links = pagination_links(
                paginator,
                '.list_suppliers',
                request.args
            )
            supplier_results = paginator.items
        else:
            links = {
                'self': url_for('.list_suppliers', _external=True, **request.args),
            }
            supplier_results = suppliers.all()
        supplier_data = [supplier.serializable for supplier in supplier_results]
    except DataError:
        abort(400, 'invalid framework')
    return jsonify(suppliers=supplier_data, links=links)


@main.route('/suppliers/<int:code>', methods=['GET'])
def get_supplier(code):
    supplier = (
        Supplier
        .query
        .filter(
            Supplier.code == code,
            Supplier.status != 'deleted'
        )
        .options(
            joinedload('domains.domain'),
            noload('domains.supplier'),
            noload('domains.assessments'),
            joinedload('domains.recruiter_info')
        )
        .first_or_404()
    )

    supplier.get_service_counts()
    return jsonify(supplier=supplier.serializable)


@main.route('/suppliers/<int:code>', methods=['DELETE'])
def delete_supplier(code):
    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()
    supplier.status = 'deleted'
    try:
        db.session.commit()
        publish_tasks.supplier.delay(
            publish_tasks.compress_supplier(supplier),
            'deleted'
        )
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(message="done"), 200


@main.route('/suppliers/count', methods=['GET'])
def get_suppliers_stats():
    q = db.session.query(Supplier).outerjoin(SupplierFramework).outerjoin(Framework)

    suppliers = {
        "total": q.filter(Supplier.abn != Supplier.DUMMY_ABN, Supplier.status != 'deleted',
                          or_(Framework.slug == 'digital-marketplace', ~Supplier.frameworks.any())).count()
    }

    return jsonify(suppliers=suppliers)


def _is_seller_type(typecode):
    return cast(Supplier.data[('seller_type', typecode)].astext, Boolean) == True  # noqa


@main.route('/products/search', methods=['GET', 'POST'])
def product_search():

    search_query = get_json_from_request()

    offset = get_nonnegative_int_or_400(request.args, 'from', 0)
    result_count = get_positive_int_or_400(request.args, 'size', current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'])

    sort_dir = search_query.get('sort_dir', 'asc')
    sort_by = search_query.get('sort_by', None)
    domains = search_query.get('domains', None)
    seller_types = search_query.get('seller_types', None)
    search_term = search_query.get('search_term', None)
    framework_slug = request.args.get('framework', 'digital-marketplace')

    q = db.session.query(Product).join(Supplier).outerjoin(SupplierDomain).outerjoin(Domain) \
        .outerjoin(SupplierFramework).outerjoin(Framework)
    q = q.filter(Supplier.status != 'deleted', or_(Framework.slug == framework_slug, ~Supplier.frameworks.any()))
    tsquery = None
    if search_term:
        if ' ' in search_term:
            tsquery = func.plainto_tsquery(search_term)
        else:
            tsquery = func.to_tsquery(search_term + ":*")
        q = q.add_column(func.ts_headline(
            'english',
            Product.summary,
            tsquery,
            'MaxWords=150, MinWords=75, ShortWord=3, HighlightAll=FALSE, MaxFragments=1, FragmentDelimiter=" ... " '
        ))
    else:
        q = q.add_column("''")
    q = q.add_column(Supplier.name)
    q = q.add_column(Supplier.data)
    q = q.group_by(Product.id, Supplier.id)

    if domains:
        d_agg = postgres.array_agg(cast(Domain.name, TEXT))
        q = q.having(d_agg.contains(array(domains)))

    if seller_types:
        selected_seller_types = select(
            [postgres.array_agg(column('key'))],
            from_obj=func.json_each_text(Supplier.data[('seller_type',)]),
            whereclause=cast(column('value'), Boolean)
        ).as_scalar()

        q = q.filter(selected_seller_types.contains(array(seller_types)))

    if sort_dir in ('desc', 'z-a'):
        ob = [desc(Product.name)]
    else:
        ob = [asc(Product.name)]

    if search_term:
        ob = [desc(func.ts_rank_cd(func.to_tsvector(func.concat(Product.name,
                                                                Product.summary, Supplier.name)), tsquery))] + ob

        condition = func.to_tsvector(func.concat(Product.name, Product.summary, Supplier.name)) \
            .op('@@')(tsquery)
        q = q.filter(condition)
    q = q.order_by(*ob)

    raw_results = list(q)
    results = []

    for x in range(len(raw_results)):
        result = raw_results[x][0].__dict__
        result.pop('_sa_instance_state', None)
        if raw_results[x][1] is not None and raw_results[x][1] != '':
            result['summary'] = raw_results[x][1]
        if raw_results[x][2] is not None:
            result['supplierName'] = raw_results[x][2]
        if raw_results[x][3] is not None:
            result['seller_type'] = raw_results[x][3].get('seller_type')
        results.append(result)

    total_results = len(results)

    sliced_results = results[offset:(offset + result_count)]

    result = {
        'hits': {
            'total': total_results,
            'hits': [{'_source': r} for r in sliced_results]
        }
    }

    try:
        return jsonify(result), 200
    except Exception as e:
        return jsonify(message=str(e)), 500


@main.route('/casestudies/search', methods=['GET', 'POST'])
def casestudies_search():
    search_query = get_json_from_request()

    offset = get_nonnegative_int_or_400(request.args, 'from', 0)
    result_count = get_positive_int_or_400(request.args, 'size', current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'])

    sort_dir = search_query.get('sort_dir', 'asc')
    sort_by = search_query.get('sort_by', None)
    domains = search_query.get('domains', None)
    seller_types = search_query.get('seller_types', None)
    search_term = search_query.get('search_term', None)
    framework_slug = request.args.get('framework', 'digital-marketplace')

    q = db.session.query(CaseStudy).join(Supplier).outerjoin(SupplierDomain).outerjoin(Domain) \
        .outerjoin(SupplierFramework).outerjoin(Framework)
    q = q.filter(Supplier.status != 'deleted', or_(Framework.slug == framework_slug, ~Supplier.frameworks.any()))
    tsquery = None
    if search_term:
        if ' ' in search_term:
            tsquery = func.plainto_tsquery(search_term)
        else:
            tsquery = func.to_tsquery(search_term + ":*")
        q = q.add_column(func.ts_headline(
            'english',
            func.concat(
                CaseStudy.data['approach'].astext,
                ' ',
                CaseStudy.data['role'].astext),
            tsquery,
            'MaxWords=150, MinWords=75, ShortWord=3, HighlightAll=FALSE, FragmentDelimiter=" ... " '
        ))
    else:
        q = q.add_column("''")
    q = q.add_column(Supplier.name)
    q = q.add_column(postgres.array_agg(Supplier.data))
    q = q.group_by(CaseStudy.id, Supplier.name)

    if domains:
        d_agg = postgres.array_agg(cast(Domain.name, TEXT))
        q = q.having(d_agg.contains(array(domains)))

    if seller_types:
        selected_seller_types = select(
            [postgres.array_agg(column('key'))],
            from_obj=func.json_each_text(Supplier.data[('seller_type',)]),
            whereclause=cast(column('value'), Boolean)
        ).as_scalar()

        q = q.filter(selected_seller_types.contains(array(seller_types)))

    if sort_dir in ('desc', 'z-a'):
        ob = [desc(CaseStudy.data['title'].astext)]
    else:
        ob = [asc(CaseStudy.data['title'].astext)]

    if search_term:
        ob = [desc(func.ts_rank_cd(func.to_tsvector(
            func.concat(Supplier.name, CaseStudy.data['title'].astext,
                        CaseStudy.data['approach'].astext)), tsquery))] + ob

        condition = func.to_tsvector(func.concat(Supplier.name,
                                                 CaseStudy.data['title'].astext,
                                                 CaseStudy.data['approach'].astext)).op('@@')(tsquery)

        q = q.filter(condition)
    q = q.order_by(*ob)

    raw_results = list(q)
    results = []

    for x in range(len(raw_results)):
        result = raw_results[x][0].serialize()
        if raw_results[x][1] is not None and raw_results[x][1] != '':
            result['approach'] = raw_results[x][1]
        if raw_results[x][2] is not None:
            result['supplierName'] = raw_results[x][2]
        if raw_results[x][3] is not None and raw_results[x][3][0] is not None:
            result['seller_type'] = raw_results[x][3][0].get('seller_type')
        results.append(result)

    total_results = len(results)

    sliced_results = results[offset:(offset + result_count)]

    result = {
        'hits': {
            'total': total_results,
            'hits': [{'_source': r} for r in sliced_results]
        }
    }

    try:
        response = jsonify(result), 200
    except Exception as e:
        response = jsonify(message=str(e)), 500

    return response


def do_search(search_query, offset, result_count, new_domains, framework_slug):
    try:
        sort_dir = list(search_query['sort'][0].values())[0]['order']
    except (KeyError, IndexError):
        sort_dir = 'asc'

    try:
        sort_by = list(search_query['sort'][0].values())[0]['sort_by']
    except (KeyError, IndexError):
        sort_by = None

    try:
        terms = search_query['query']['filtered']['filter']['terms']
    except (KeyError, IndexError):
        terms = {}

    roles_list = None
    seller_types_list = None

    if terms:
        new_domains = 'prices.serviceRole.role' not in terms

        try:
            if new_domains:
                roles_list = terms['domains.assessed']
            else:
                roles = terms['prices.serviceRole.role']
                roles_list = set(_['role'][7:] for _ in roles)
        except KeyError:
            pass

        try:
            seller_types_list = terms['seller_types']
        except:  # noqa
            pass

    try:
        search_term = search_query['query']['match_phrase_prefix']['name']
    except KeyError:
        search_term = ''

    EXCLUDE_LEGACY_ROLES = not current_app.config['LEGACY_ROLE_MAPPING']

    if new_domains:
        q = db.session.query(Supplier).outerjoin(SupplierDomain).outerjoin(Domain) \
            .outerjoin(SupplierFramework).outerjoin(Framework)
    else:
        q = db.session.query(Supplier).outerjoin(PriceSchedule).outerjoin(ServiceRole) \
            .outerjoin(SupplierFramework).outerjoin(Framework)

    q = q.filter(Supplier.status != 'deleted', Supplier.abn != Supplier.DUMMY_ABN,
                 or_(Framework.slug == framework_slug, ~Supplier.frameworks.any()))

    tsquery = None
    if search_term:
        if any(c in search_term for c in ['#', '-', '_', '/', '\\']):
            tsquery = func.phraseto_tsquery(search_term)
        elif ' ' in search_term:
            tsquery = func.plainto_tsquery(search_term)
        else:
            tsquery = func.to_tsquery(search_term + ":*")
        q = q.add_column(func.ts_headline(
            'english',
            func.concat(Supplier.summary,
                         ' ',
                         Supplier.data['tools'].astext,
                         ' ',
                         Supplier.data['methodologies'].astext,
                         ' ',
                         Supplier.data['technologies'].astext, ''),
            tsquery,
            'MaxWords=25, MinWords=20, ShortWord=3, HighlightAll=FALSE, MaxFragments=1'
        ))

    q = q.group_by(Supplier.id)

    try:
        code = search_query['query']['term']['code']
        q = q.filter(Supplier.code == code)
    except KeyError:
        pass

    if roles_list is not None:
        if new_domains:
            if EXCLUDE_LEGACY_ROLES:
                d_agg = postgres.array_agg(cast(Domain.name, TEXT))
                q = q.filter(SupplierDomain.status == 'assessed')
                q = q.having(d_agg.contains(array(roles_list)))
        else:
            sr_agg = postgres.array_agg(cast(func.substring(ServiceRole.name, 8), TEXT))
            q = q.having(sr_agg.contains(array(roles_list)))

    if seller_types_list is not None and 'recruiter' in seller_types_list:
        q = q.filter(Supplier.is_recruiter == 'true')
        seller_types_list.remove('recruiter')
        if len(seller_types_list) == 0:
            seller_types_list = None

    if seller_types_list is not None:
        selected_seller_types = select(
            [postgres.array_agg(column('key'))],
            from_obj=func.json_each_text(Supplier.data[('seller_type',)]),
            whereclause=cast(column('value'), Boolean)
        ).as_scalar()

        q = q.filter(selected_seller_types.contains(array(seller_types_list)))

    if sort_by:
        if sort_by == 'latest':
            ob = [desc(Supplier.last_update_time)]
        else:
            ob = [asc(Supplier.name)]
    else:
        if sort_dir == 'desc':
            ob = [desc(Supplier.name)]
        else:
            ob = [asc(Supplier.name)]

    if search_term:
        ob = [desc(func.ts_rank_cd(Supplier.text_vector, tsquery))] + ob

        q = q.filter(Supplier.text_vector.op('@@')(tsquery))

    q = q.order_by(*ob)

    raw_results = list(q)
    results = []

    for x in range(len(raw_results)):
        if type(raw_results[x]) is Supplier:
            result = raw_results[x]
        else:
            result = raw_results[x][0]
            if raw_results[x][1] is not None and raw_results[x][1] != '':
                result.summary = raw_results[x][1]
        results.append(result)

    sliced_results = results[offset:(offset + result_count)]

    q = db.session.query(Supplier.code, Supplier.name, Supplier.summary, Supplier.is_recruiter,
                         Supplier.data, Domain.name.label('domain_name'),
                         SupplierDomain.status.label('domain_status'))\
        .outerjoin(SupplierDomain, Domain)\
        .filter(Supplier.id.in_([sr.id for sr in sliced_results]))\
        .order_by(Supplier.name)

    suppliers = [r._asdict() for r in q]

    sliced_results = []
    for key, group in groupby(suppliers, key=itemgetter('code')):
        supplier = group.next()

        supplier['seller_type'] = supplier.get('data') and supplier['data'].get('seller_type')

        supplier['domains'] = {'assessed': [], 'unassessed': []}
        for s in chain([supplier], group):
            domain, status = s['domain_name'], s['domain_status']
            if domain:
                if status == 'assessed':
                    supplier['domains']['assessed'].append(domain)
                else:
                    supplier['domains']['unassessed'].append(domain)

        for e in ['domain_name', 'domain_status', 'data']:
            supplier.pop(e, None)

        sliced_results.append(supplier)

    return sliced_results, len(results)


@main.route('/suppliers/search', methods=['GET'])
def supplier_search():
    search_query = get_json_from_request()
    new_domains = False

    offset = get_nonnegative_int_or_400(request.args, 'from', 0)
    result_count = get_positive_int_or_400(request.args, 'size', current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'])
    framework_slug = request.args.get('framework', 'digital-marketplace')
    sliced_results, count = do_search(search_query, offset, result_count, new_domains, framework_slug)

    result = {
        'hits': {
            'total': count,
            'hits': [{'_source': r} for r in sliced_results]
        }
    }

    try:
        return jsonify(result), 200
    except Exception as e:
        return jsonify(message=str(e)), 500


def update_supplier_data_impl(supplier, supplier_data, success_code):
    try:
        if 'prices' in supplier_data:
            db.session.query(PriceSchedule).filter(PriceSchedule.supplier_id == supplier.id).delete()

        supplier.update_from_json(supplier_data)

        db.session.add(supplier)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(supplier=supplier.serializable), success_code


@main.route('/suppliers', methods=['POST'])
def create_supplier():
    request_data = get_json_from_request()
    if 'supplier' in request_data:
        supplier_data = request_data.get('supplier')
    else:
        abort(400)

    supplier = Supplier()
    return update_supplier_data_impl(supplier, supplier_data, 201)


@main.route('/suppliers/<int:code>', methods=['POST', 'PATCH'])
def update_supplier(code):
    request_data = get_json_from_request()
    if 'supplier' in request_data:
        supplier_data = request_data.get('supplier')
    else:
        abort(400)

    if request.method == 'POST':
        supplier = Supplier(code=code)
    else:
        assert request.method == 'PATCH'
        supplier = Supplier.query.filter(
            Supplier.code == code
        ).first_or_404()

    return update_supplier_data_impl(supplier, supplier_data, 200)


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>/declaration', methods=['PUT'])
def set_a_declaration(code, framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        code, framework_slug
    )
    supplier = None
    if supplier_framework is not None:
        status_code = 200 if supplier_framework.declaration else 201
    else:
        supplier = Supplier.query.filter(
            Supplier.code == code
        ).first_or_404()

        supplier_framework = SupplierFramework(
            supplier_code=supplier.code,
            framework_id=framework.id,
            declaration={}
        )
        status_code = 201

    request_data = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(request_data, ['declaration'])

    supplier_framework.declaration = request_data['declaration'] or {}
    db.session.add(supplier_framework)
    db.session.add(
        AuditEvent(
            audit_type=AuditTypes.answer_selection_questions,
            db_object=supplier_framework,
            user=updater_json['updated_by'],
            data={'update': request_data['declaration']})
    )

    try:
        db.session.commit()
        if supplier:
            publish_tasks.supplier.delay(
                publish_tasks.compress_supplier(supplier),
                'set_declaration',
                updated_by=updater_json['updated_by']
            )
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {}".format(e))

    return jsonify(declaration=supplier_framework.declaration), status_code


@main.route('/suppliers/<int:code>/frameworks/interest', methods=['GET'])
def get_registered_frameworks(code):
    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.supplier_code == code
    ).all()
    slugs = []
    for framework in supplier_frameworks:
        framework = Framework.query.filter(
            Framework.id == framework.framework_id
        ).first()
        slugs.append(framework.slug)

    return jsonify(frameworks=slugs)


@main.route('/suppliers/<int:code>/frameworks', methods=['GET'])
def get_supplier_frameworks_info(code):
    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    service_counts = SupplierFramework.get_service_counts(code)

    supplier_frameworks = (
        SupplierFramework
        .query
        .options(
            joinedload('framework'),
            noload('framework.lots')
        )
        .filter(
            SupplierFramework.supplier == supplier
        )
        .all()
    )

    return jsonify(frameworkInterest=[
        framework.serialize({
            'drafts_count': service_counts.get((framework.framework_id, 'not-submitted'), 0),
            'complete_drafts_count': service_counts.get((framework.framework_id, 'submitted'), 0),
            'services_count': service_counts.get((framework.framework_id, 'published'), 0)
        })
        for framework in supplier_frameworks]
    )


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>', methods=['GET'])
def get_supplier_framework_info(code, framework_slug):
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        code, framework_slug
    )
    if supplier_framework is None:
        abort(404)

    return jsonify(frameworkInterest=supplier_framework.serialize())


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>', methods=['PUT'])
def register_framework_interest(code, framework_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_payload.pop('updated_by')
    if json_payload:
        abort(400, "This PUT endpoint does not take a payload.")

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_code == supplier.code,
        SupplierFramework.framework_id == framework.id
    ).first()
    if interest_record:
        return jsonify(frameworkInterest=interest_record.serialize()), 200

    if framework.status != 'open':
        abort(400, "'{}' framework is not open".format(framework_slug))

    interest_record = SupplierFramework(
        supplier_code=supplier.code,
        framework_id=framework.id,
        declaration={}
    )
    audit_event = AuditEvent(
        audit_type=AuditTypes.register_framework_interest,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.code, 'frameworkSlug': framework_slug},
        db_object=supplier
    )

    try:
        db.session.add(interest_record)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(frameworkInterest=interest_record.serialize()), 201


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>', methods=['POST'])
def update_supplier_framework_details(code, framework_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(json_payload, ["frameworkInterest"])
    update_json = json_payload["frameworkInterest"]

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_code == supplier.code,
        SupplierFramework.framework_id == framework.id
    ).first()

    if not interest_record:
        abort(404, "code '{}' has not registered interest in {}".format(code, framework_slug))

    # `agreementDetails` shouldn't be passed in unless the framework has framework_agreement_details
    if 'agreementDetails' in update_json and framework.framework_agreement_details is None:
        abort(400, "Framework '{}' does not accept 'agreementDetails'".format(framework_slug))

    if (
            (framework.framework_agreement_details and framework.framework_agreement_details.get('frameworkAgreementVersion')) and  # noqa
            ('agreementDetails' in update_json or update_json.get('agreementReturned'))
    ):
        required_fields = ['signerName', 'signerRole']
        if update_json.get('agreementReturned'):
            required_fields.append('uploaderUserId')

        # Make a copy of the existing agreement_details with our new changes to be added and validate this
        # If invalid, 400
        agreement_details = interest_record.agreement_details.copy() if interest_record.agreement_details else {}

        if update_json.get('agreementDetails'):
            agreement_details.update(update_json['agreementDetails'])
        if update_json.get('agreementReturned'):
            agreement_details['frameworkAgreementVersion'] = framework.framework_agreement_details['frameworkAgreementVersion']  # noqa

        validate_agreement_details_data(
            agreement_details,
            enforce_required=False,
            required_fields=required_fields
        )

        if update_json.get('agreementDetails') and update_json['agreementDetails'].get('uploaderUserId'):
            user = User.query.filter(User.id == update_json['agreementDetails']['uploaderUserId']).first()
            if not user:
                abort(400, "No user found with id '{}'".format(update_json['agreementDetails']['uploaderUserId']))

        interest_record.agreement_details = agreement_details or None

    uniform_now = datetime.utcnow()

    if 'onFramework' in update_json:
        interest_record.on_framework = update_json['onFramework']
    if 'agreementReturned' in update_json:
        if update_json["agreementReturned"] is False:
            interest_record.agreement_returned_at = None
            interest_record.agreement_details = None
        else:
            interest_record.agreement_returned_at = uniform_now
    if update_json.get('countersigned'):
        interest_record.countersigned_at = uniform_now

    audit_event = AuditEvent(
        audit_type=AuditTypes.supplier_update,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.code, 'frameworkSlug': framework_slug, 'update': update_json},
        db_object=supplier
    )

    try:
        db.session.add(interest_record)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(frameworkInterest=interest_record.serialize()), 200


@main.route('/domain/<domain_id>', methods=['GET'])
def get_domain(domain_id):
    if domain_id.isdigit():
        domain_id = int(domain_id)
    result = Domain.get_by_name_or_id(domain_id)
    return jsonify(domain={'id': result.id, 'name': result.name})


@main.route('/domains', methods=['GET'])
def get_domains_list():
    result = [d.get_serializable() for d in Domain.query.order_by('ordering').all()]

    return jsonify(domains=result)


@main.route('/suppliers/<int:code>/applications', methods=['GET'])
def get_supplier_applications(code):
    result = [a.serializable for a in Application.query.filter(
        Application.supplier_code == code).all()]

    return jsonify(applications=result)


@main.route('/suppliers/<int:code>/application', methods=['POST'])
@main.route('/suppliers/<int:code>/application/<application_type>', methods=['POST'])
def create_application_from_supplier(code, application_type=None):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["current_user"])
    current_user = json_payload["current_user"]

    supplier = Supplier.query.options(
        joinedload('domains'),
        joinedload('domains.assessments'),
        joinedload('domains.domain'),
        joinedload('domains.recruiter_info'),
        noload('domains.supplier'),
        noload('domains.assessments.briefs')
    ).filter(
        Supplier.code == code
    ).first_or_404()

    # hotfix for exception. shouldn't need to do this
    supplier.data = supplier.data or {}
    application_type = application_type or 'upgrade'
    existing_application = Application.query.options(
        joinedload('supplier')
    ).filter(
        Application.supplier_code == supplier.code,
        or_(Application.status == 'submitted', Application.status == 'saved')
    ).first()
    if existing_application:
        errors = ApplicationValidator(existing_application).validate_all()
        return jsonify(application=existing_application.serializable,
                       application_errors=errors)

    data = json.loads(supplier.json)

    data['status'] = 'saved'
    data = {key: data[key] for key in data if key not in ['id', 'contacts', 'domains', 'links',
                                                          'prices', 'frameworks', 'steps', 'signed_agreements']}
    if data.get('products'):
        for product in data['products']:
            if product.get('links'):
                del product['links']
    application = Application()
    application.update_from_json(data)
    application.type = application_type

    db.session.add(application)
    db.session.flush()

    audit_type = application_type == 'edit' and AuditTypes.supplier_update or AuditTypes.create_application
    db.session.add(AuditEvent(
        audit_type=audit_type,
        user='',
        data={},
        db_object=application
    ))
    db.session.flush()

    if application_type != 'edit':
        notification_message = '{}\nApplication Id:{}\nBy: {} ({})'.format(
            data['name'],
            application.id,
            current_user['name'],
            current_user['email_address']
        )

        notification_text = 'An existing seller has started a new application'

        notify_team(notification_text, notification_message)

    # TODO stop using application_id on user
    supplier.update_from_json({'application_id': application.id})
    users = User.query.options(
        noload('supplier'),
        noload('application')
    ).filter(
        User.supplier_code == code and User.active == true()
    ).all()

    for user in users:
        user.application_id = application.id

    db.session.commit()

    publish_tasks.application.delay(
        publish_tasks.compress_application(application),
        'created',
        name=current_user['name'],
        email_address=current_user['email_address'],
        from_expired=False
    )
    return jsonify(application=application)


@main.route('/suppliers/<int:supplier_id>/domains/<int:domain_id>/<string:status>', methods=['POST'])
def assess_supplier_for_domain(supplier_id, domain_id, status):
    updater_json = validate_and_return_updater_request()

    supplier = Supplier.query.get(supplier_id)

    if supplier is None:
        abort(404, "Supplier '{}' does not exist".format(supplier_id))

    supplier.update_domain_assessment_status(domain_id, status, updater_json['updated_by'])
    db.session.commit()

    if status == 'assessed':
        send_assessment_approval_notification(supplier_id, domain_id)

    supplier_domain = SupplierDomain.query.filter_by(supplier_id=supplier.id, domain_id=domain_id).one_or_none()
    if supplier_domain:
        publish_tasks.supplier_domain.delay(
            publish_tasks.compress_supplier_domain(supplier_domain),
            'domain_assessed',
            status=status,
            domain_id=domain_id,
            supplier_code=supplier.code
        )

    db.session.refresh(supplier)
    return jsonify(supplier=supplier.serializable), 200


@main.route('/suppliers/<int:supplier_code>/domain/<int:supplier_domain_id>', methods=['POST'])
def update_supplier_domain(supplier_code, supplier_domain_id):
    json_payload = get_json_from_request()

    supplier_id = (
        db
        .session
        .query(Supplier.id)
        .filter(Supplier.code == supplier_code)
        .one_or_none()
    )

    supplier_domain = (
        db
        .session
        .query(SupplierDomain)
        .filter(SupplierDomain.supplier_id == supplier_id)
        .filter(SupplierDomain.id == supplier_domain_id)
        .one_or_none()
    )

    if not supplier_domain:
        abort(404, "Supplier {} does not have domain '{}' does not exist".format(supplier_id, supplier_domain_id))

    user = ''
    dirty = False
    if 'update_details' in json_payload:
        user = json_payload['update_details']['updated_by']

    if 'status' in json_payload:
        supplier_domain.status = json_payload['status']
        dirty = True

    if 'price_status' in json_payload:
        supplier_domain.price_status = json_payload['price_status']
        dirty = True

    if dirty is True:
        db.session.add(AuditEvent(
            audit_type=AuditTypes.assessed_domain,
            user=user,
            data={
                'payload': json_payload
            },
            db_object=supplier_domain
        ))
        db.session.commit()

        publish_tasks.supplier_domain.delay(
            publish_tasks.compress_supplier_domain(supplier_domain),
            'updated',
            supplier_code=supplier_code
        )

    supplier = (
        db
        .session
        .query(Supplier)
        .filter(Supplier.code == supplier_code)
        .one_or_none()
    )

    return jsonify(supplier=supplier.serializable), 200
