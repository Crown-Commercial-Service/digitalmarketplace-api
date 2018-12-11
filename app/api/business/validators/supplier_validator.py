import collections
import pendulum
from pendulum.parsing.exceptions import ParserError
from flask import current_app


class SupplierValidator(object):

    def __init__(self, supplier):
        self.supplier = supplier

    def validate_all(self):
        result = (
            self.validate_basics() +
            self.validate_documents() +
            self.validate_case_studies() +
            self.validate_pricing()
        )
        warnings = [n for n in result if n.get('severity', 'error') == 'warning']
        errors = [n for n in result if n.get('severity', 'error') == 'error']
        validation_result = collections.namedtuple('Notification', ['warnings', 'errors'])
        return validation_result(warnings=warnings, errors=errors)

    def validate_basics(self):
        errors = []
        if not self.supplier.name:
            errors.append({
                'message': 'Your seller profile is missing the name of your business.',
                'severity': 'error',
                'step': 'business-details'
            })

        return errors

    def validate_pricing(self):
        errors = []
        pricing = self.supplier.data.get('pricing', {})
        recruiter = self.supplier.data.get('recruiter')
        supplier_domains = self.supplier.domains

        if recruiter == 'no' or recruiter == 'both':
            for supplier_domain in supplier_domains:
                if supplier_domain.domain.name not in pricing:
                    errors.append({
                        'message': 'You have not supplied the maximum daily rate in your seller profile '
                                   'for "{domain}".'
                        .format(
                            domain=supplier_domain.domain.name
                        ),
                        'severity': 'error',
                        'step': 'pricing'
                    })
                elif supplier_domain.price_status == 'rejected':
                    errors.append({
                        'message': 'The price you supplied for area of expertise "{domain}" '
                                   'has not been accepted as value for money. To rectify this, '
                                   'you will need to either lower your maximum daily price to '
                                   'within the suggested level or update your supporting case studies '
                                   'so that they exceed the minimum number of '
                                   'required {{assessment criteria}}.'
                        .format(
                            domain=supplier_domain.domain.name
                        ),
                        'links': {
                            'assessment criteria': 'https://marketplace1.zendesk.com/hc/en-gb/'
                                                   'articles/333757011655-Assessment-criteria'
                        },
                        'severity': 'warning',
                        'step': 'pricing'
                    })

        return errors

    def validate_case_studies(self):
        errors = []
        case_studies = self.supplier.case_studies
        recruiter = self.supplier.data.get('recruiter')
        supplier_domains = self.supplier.domains

        if recruiter == 'no' or recruiter == 'both':
            for supplier_domain in supplier_domains:
                domain_case_studies = []
                if isinstance(case_studies, list):
                    domain_case_studies = [
                        cs for cs in case_studies
                        if cs.data.get('service') == supplier_domain.domain.name
                    ]
                else:
                    domain_case_studies = [
                        cs for i, cs in case_studies.iteritems()
                        if cs.data.get('service') == supplier_domain.domain.name
                    ]

                if len(domain_case_studies) == 0:
                    errors.append({
                        'message': 'Your seller profile is missing a case study for '
                                   '{}. From January 2019, you will no longer '
                                   'be able to apply for opportunities without a '
                                   'supporting case study.'.format(supplier_domain.domain.name),
                        'severity': 'warning',
                        'step': 'case-study'
                    })
                else:
                    for domain_case_study in domain_case_studies:
                        errors = errors + self.__validate_case_study(domain_case_study)

        return errors

    def __validate_case_study(self, case_study):
        errors = []
        frontend_url = current_app.config['FRONTEND_ADDRESS']
        if case_study.status == 'rejected':
            errors.append({
                'message': 'Case study "{{{title}}}" has not passed assessment for the area of expertise "{domain}". '
                           'Please review the '
                           '{{assessment criteria}} '
                           'and update your case study to ensure the required number of criteria are met.'
                .format(
                    title=case_study.data.get('title', '').encode('utf-8'),
                    domain=case_study.data.get('service'),
                    cs_link=''
                ),
                'links': {
                    'assessment criteria': 'https://marketplace1.zendesk.com/hc/'
                                           'en-gb/articles/333757011655-Assessment-criteria',
                    case_study.data.get('title'): '{}/case-study/{}'.format(frontend_url, case_study.id)
                },
                'severity': 'warning',
                'step': 'case-study'
            })

        return errors

    def validate_documents(self):
        documents = self.supplier.data.get('documents')
        if not documents:
            return [{
                'message': 'Your seller profile is missing required insurance and financial documents.',
                'severity': 'warning',
                'step': 'documents'
            }]

        now = pendulum.now().date()
        return (self.__validate_document(documents, 'liability', now) +
                self.__validate_document(documents, 'workers', now) +
                self.__validate_document(documents, 'financial', now, False))

    def __validate_document(self, documents, name, now, has_expiry=True):
        errors = []
        document = documents.get(name)
        document_required = (
            (
                name == 'workers' and
                (
                    document and
                    document.get('noWorkersCompensation', False) is False
                )
            ) or (
                document and
                'noWorkersCompensation' not in document
            )
        )

        name_translation = {
            'liability': 'Professional Indemnity and Public Liability Insurance',
            'workers': 'Workers Compensation Insurance',
            'financial': 'Financial statement'
        }
        document_name = name_translation.get(name)

        if not document:
            errors.append({
                'message': 'Your seller profile is missing the following document: '
                           '{document_name}.'
                .format(
                    document_name=document_name
                ),
                'severity': 'warning',
                'step': 'documents'
            })
            return errors

        filename = document.get('filename', '')
        if not filename and document_required:
            errors.append({
                'message': 'Your seller profile has no filename for the '
                           '{document_name} document you uploaded.'
                .format(
                    document_name=document_name
                ),
                'severity': 'warning',
                'step': 'documents'
            })

        if has_expiry:
            expiry = document.get('expiry')
            if not expiry and document_required:
                errors.append({
                    'message': 'Your seller profile has no expiry date for the '
                               '{document_name} document you uploaded.'
                    .format(
                        document_name=document_name
                    ),
                    'severity': 'warning',
                    'step': 'documents'
                })
            elif document_required:
                try:
                    expiry_date = pendulum.parse(expiry)
                    if now > expiry_date.date():
                        errors.append({
                            'message': 'The {document_name} document you uploaded as part of your '
                                       'seller profile has expired.'
                            .format(
                                document_name=document_name
                            ),
                            'severity': 'warning',
                            'step': 'documents'
                        })
                    elif now.add(months=1) > expiry_date.date():
                        errors.append({
                            'message': 'The {document_name} document you uploaded as part of your '
                                       'seller profile is about to expire.'
                            .format(
                                document_name=document_name
                            ),
                            'severity': 'warning',
                            'step': 'documents'
                        })
                except ParserError:
                    errors.append({
                        'message': 'The {document_name} document you uploaded as part of your seller profile '
                                   'has an expiration date that is incorrectly formatted.'
                        .format(
                            document_name=document_name
                        ),
                        'severity': 'warning',
                        'step': 'documents'
                    })

        return errors
