import collections
import pendulum
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
                'message': 'You must include your business name in your profile.',
                'severity': 'error',
                'step': 'business-details',
                'id': 'S001'
            })

        return errors

    def validate_pricing(self):
        errors = []
        pricing = self.supplier.data.get('pricing', {})
        recruiter = self.supplier.data.get('recruiter')
        supplier_domains = self.supplier.domains
        frontend_url = current_app.config['FRONTEND_ADDRESS']

        if recruiter == 'no' or recruiter == 'both':
            for supplier_domain in supplier_domains:
                if supplier_domain.domain.name not in pricing:
                    errors.append({
                        'message': 'You must provide your maximum daily rate (including GST) for {domain} using '
                                   '{{Skills Framework for the Information Age (SFIA) Level 5}} '
                                   'as a guide.'
                        .format(
                            domain=supplier_domain.domain.name
                        ),
                        'links': {
                            'Skills Framework for the Information Age (SFIA) Level 5': 'https://www.sfia-online.org/en/'
                                                                                       'framework/sfia-7/busskills/'
                                                                                       'level-5'
                        },
                        'severity': 'error',
                        'step': 'pricing',
                        'id': 'S002-{}'.format(supplier_domain.domain.id)
                    })
                elif supplier_domain.price_status == 'rejected':
                    errors.append({
                        'message': 'Your daily rate for {domain} exceeds the maximum '
                                   'threshold that applies to this category. '
                                   'Update your case study to meet {{additional criteria}} '
                                   'then submit for assessment.'
                        .format(
                            domain=supplier_domain.domain.name
                        ),
                        'links': {
                            'additional criteria': 'https://marketplace1.zendesk.com/hc/en-gb/'
                                                   'articles/333757011655-Assessment-criteria'
                        },
                        'severity': 'info',  # TODO: this message needs some work. switch back when ready
                        'step': 'pricing',
                        'id': 'S003-{}'.format(supplier_domain.domain.id)
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
                        'message': 'To apply for opportunities under {}, '
                                   'you must submit a case study then '
                                   '{{request an assessment}} from the '
                                   'opportunity page.'.format(supplier_domain.domain.name),
                        'links': {
                            'request an assessment': 'https://marketplace1.zendesk.com/hc/en-gb'
                                                     '/articles/115011292847-Request-an-assessment'
                                   },
                        'severity': 'error',
                        'step': 'case-study',
                        'id': 'S004-{}'.format(supplier_domain.domain.id)
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
                'message': 'You must update {{{title}}} to demonstrate the {{minimum number of criteria}} for {domain}.'
                .format(
                    title=case_study.data.get('title', '').encode('utf-8'),
                    domain=case_study.data.get('service')
                ),
                'links': {
                    'minimum number of criteria': 'https://marketplace1.zendesk.com/hc/'
                                                  'en-gb/articles/333757011655-Assessment-criteria',
                    case_study.data.get('title'): '{}/case-study/{}'.format(frontend_url, case_study.id)
                },
                'severity': 'warning',
                'step': 'case-study',
                'id': 'S005-{}'.format(case_study.id)
            })

        return errors

    def validate_documents(self):
        documents = self.supplier.data.get('documents')
        if not documents:
            return [{
                'message': 'Your seller profile is missing required insurance and financial documents.'
                           'If you have multiple files for a document, please scan and merge as one upload.',
                'severity': 'error',
                'step': 'documents',
                'id': 'S006'
            }]

        now = pendulum.now('Australia/Canberra')
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
                'message': 'Your seller profile is missing your {document_name} document.'
                .format(
                    document_name=document_name
                ),
                'severity': 'error',
                'step': 'documents',
                'id': 'S007-{}'.format(name)
            })
            return errors

        filename = document.get('filename', '')
        if not filename and document_required:
            errors.append({
                'message': 'You must set a filename for your {document_name} document.'
                .format(
                    document_name=document_name
                ),
                'severity': 'error',
                'step': 'documents',
                'id': 'S008-{}'.format(name)
            })

        if has_expiry:
            expiry = document.get('expiry')
            if not expiry and document_required:
                errors.append({
                    'message': 'You must set an expiry date for your {document_name} document.'
                    .format(
                        document_name=document_name
                    ),
                    'severity': 'error',
                    'step': 'documents',
                    'id': 'S009-{}'.format(name)
                })
            elif document_required:
                try:
                    expiry_date = pendulum.parse(expiry)
                    if now.date() > expiry_date.date():
                        e = pendulum.instance(expiry_date)
                        delta = now.diff(e).in_days()
                        message = 'Your {document_name} document has expired. Please upload an updated version.'
                        severity = 'warning'
                        if delta > 28:
                            message = (
                                'Your {document_name} document has expired.  Please upload an updated version. '
                                'Failure to provide this documentation may result in the '
                                'suspension of your seller profile.'
                            )
                            severity = 'error'
                        errors.append({
                            'message': message
                            .format(
                                document_name=document_name
                            ),
                            'severity': severity,
                            'step': 'documents',
                            'id': 'S010-{}'.format(name)
                        })
                    elif now.add(days=28).date() > expiry_date.date():
                        errors.append({
                            'message': 'Your {document_name} document will expire on {expiry_date}. '
                                       'Please upload an updated version before the expiry date.'
                            .format(
                                document_name=document_name,
                                expiry_date=expiry_date.date()
                            ),
                            'severity': 'warning',
                            'step': 'documents',
                            'id': 'S011-{}'.format(name)
                        })
                except ValueError:
                    errors.append({
                        'message': 'Please fix the format of the expiry date for your '
                                   '{document_name} document, eg 21/09/2019'
                        .format(
                            document_name=document_name
                        ),
                        'severity': 'error',
                        'step': 'documents',
                        'id': 'S012-{}'.format(name)
                    })

        return errors
