import pendulum


class SupplierValidator(object):

    def __init__(self, supplier):
        self.supplier = supplier

    def validate_all(self):
        return (self.validate_basics() +
                self.validate_documents() +
                self.validate_pricing())

    def validate_basics(self):
        errors = []
        if not self.supplier.name:
            errors.append({
                'message': 'Supplier name is required',
                'severity': 'error'
            })

        return errors

    def validate_pricing(self):
        errors = []
        pricing = self.supplier.data.get('pricing', {})
        recruiter = self.supplier.data.get('recruiter')
        supplier_domains = self.supplier.domains

        if recruiter == 'no' or recruiter == 'both':
            if len(supplier_domains) != len(pricing):
                for supplier_domain in supplier_domains:
                    if supplier_domain.domain.name not in pricing:
                        errors.append({
                            'message': 'Pricing for {}'.format(supplier_domain.domain.name),
                            'severity': 'error'
                        })
        elif recruiter == 'yes':
            # [DOCO] there are no prices for recruiters
            pass

        return errors

    def validate_documents(self):
        documents = self.supplier.data.get('documents')
        if not documents:
            return [{
                'message': 'Documents are required',
                'severity': 'error'
            }]

        now = pendulum.now().date()
        return (self.__validate_document(documents, 'liability', now) +
                self.__validate_document(documents, 'workers', now) +
                self.__validate_document(documents, 'financial', now, False))

    def __validate_document(self, documents, name, now, has_expiry=True):
        errors = []
        document = documents.get(name)

        if not document:
            errors.append({
                'message': 'Document "{}" is required'.format(name),
                'severity': 'error'
            })
            return errors

        filename = document.get('filename', '')
        if not filename:
            errors.append({
                'message': 'Filename is required for your document',
                'severity': 'error'
            })
            return errors

        if has_expiry:
            expiry = document.get('expiry')
            if now > pendulum.parse(expiry).date():
                errors.append({
                    'message': 'Up-to-date {} document'.format(name),
                    'severity': 'error'
                })

        return errors
