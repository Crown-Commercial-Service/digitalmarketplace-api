import pendulum
from pendulum.parsing.exceptions import ParserError
import collections


class SupplierValidator(object):

    def __init__(self, supplier):
        self.supplier = supplier

    def validate_all(self):
        result = (
            self.validate_basics() +
            # self.validate_documents() +
            self.validate_pricing()
        )
        warnings = [n for n in result if n.get('severity', 'error') == 'warning']
        errors = [n for n in result if n.get('severity', 'error') == 'error']
        validation_result = collections.namedtuple('Notification', 'warnings errors')
        return validation_result(warnings=warnings, errors=errors)

    def validate_basics(self):
        errors = []
        if not self.supplier.name:
            errors.append({
                'message': 'Supplier name is required',
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
                        'message': 'Pricing for {}'.format(supplier_domain.domain.name),
                        'severity': 'error',
                        'step': 'pricing'
                    })

        return errors

    def validate_documents(self):
        documents = self.supplier.data.get('documents')
        if not documents:
            return [{
                'message': 'Documents are required',
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

        if not document:
            errors.append({
                'message': 'Document "{}" is required'.format(name),
                'severity': 'warning',
                'step': 'documents'
            })
            return errors

        filename = document.get('filename', '')
        if not filename and document_required:
            errors.append({
                'message': 'Filename is required for {} document'.format(name),
                'severity': 'error',
                'step': 'documents'
            })

        if has_expiry:
            expiry = document.get('expiry')
            if not expiry and document_required:
                errors.append({
                    'message': 'Expiry is required for {} document'.format(name),
                    'severity': 'error',
                    'step': 'documents'
                })
            elif document_required:
                try:
                    expiry_date = pendulum.parse(expiry)
                    if now > expiry_date.date():
                        errors.append({
                            'message': '{} document has expired'.format(name),
                            'severity': 'error',
                            'step': 'documents'
                        })
                    elif now.add(months=1) > expiry_date.date():
                        errors.append({
                            'message': '{} document is about to expire'.format(name),
                            'severity': 'warning',
                            'step': 'documents'
                        })
                except ParserError:
                    errors.append({
                        'message': '"{}" is an invalid date format'.format(expiry),
                        'severity': 'error',
                        'step': 'documents'
                    })

        return errors
