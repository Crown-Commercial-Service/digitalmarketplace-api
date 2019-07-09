import pendulum


class ApplicationValidator(object):

    def __init__(self, application):
        self.application = application

    def validate_all(self):
        return (self.validate_basics() +
                self.validate_details() +
                self.validate_contacts() +
                self.validate_disclosures() +
                self.validate_documents() +
                self.validate_methods() +
                self.validate_recruiter() +
                self.validate_services() +
                self.validate_candidates() +
                self.validate_products())

    def __validate_required(self, data, required_fields, step):
        errors = []
        for field, label in required_fields.iteritems():
            value = data.get(field)
            if not value:
                errors.append({
                    'field': field,
                    'message': '{} is required'.format(label),
                    'severity': 'error',
                    'step': step
                })
        return errors

    def validate_basics(self):
        errors = (
            self.__validate_required(
                self.application.data, {
                    'name': 'Business name',
                    'abn': 'ABN',
                    'summary': 'Summary',
                    'website': 'Website URL'
                },
                'business-details')
        )

        addresses = self.application.data.get('addresses', [])
        if not isinstance(addresses, list):
            addresses = [v for k, v in addresses.iteritems()]

        if not addresses:
            errors.append({
                'message': 'Address is required',
                'severity': 'error',
                'step': 'business-details'
            })

        for address in addresses:
            if address:
                errors = (
                    errors +
                    self.__validate_required(
                        address, {
                            'address_line': 'Primary Address',
                            'suburb': 'Suburb',
                            'state': 'State',
                            'postal_code': 'Postcode'
                        },
                        'business-details')
                )

        links = {
            'website': 'Website',
            'linkedin': 'Linkedin'
        }
        for field, label in links.iteritems():
            value = self.application.data.get(field)
            if value and not value.startswith('http'):
                errors.append({
                    'field': field,
                    'message': '{} link must begin with http'.format(label),
                    'severity': 'error',
                    'step': 'business-details'
                })

        return errors

    def validate_details(self):
        return self.__validate_required(
            self.application.data, {
                'number_of_employees': 'Number of employees'
            },
            'business-info')

    def validate_contacts(self):
        return (
            self.__validate_required(
                self.application.data, {
                    'representative': 'Authorised representative\'s name',
                    'email': 'Authorised representative\'s email',
                    'phone': 'Authorised representative\'s phone number',
                    'contact_name': 'Business contact\'s name',
                    'contact_email': 'Business contact\'s email',
                    'contact_phone': 'Business contact\'s phone'
                },
                'your-info')
        )

    def validate_disclosures(self):
        disclosures = self.application.data.get('disclosures', {})
        fields = {
            'structual_changes': 'Structual changes',
            'investigations': 'Investigations',
            'legal_proceedings': 'Legal proceedings',
            'insurance_claims': 'Insurance claims',
            'conflicts_of_interest': 'Conflicts of interest',
            'other_circumstances': 'Other circumstances'
        }
        required_fields = {}
        for k, v in fields.iteritems():
            required_fields[k] = v
            if disclosures.get(k, 'no') == 'yes':
                required_fields['{}_details'.format(k)] = '{} details'.format(v)

        return (
            self.__validate_required(
                disclosures,
                required_fields,
                'disclosures')
        )

    def validate_documents(self):
        documents = self.application.data.get('documents')
        if not documents:
            return [{
                'message': 'Documents are required',
                'severity': 'error',
                'step': 'documents'
            }]

        now = pendulum.now('Australia/Canberra').date()
        return (self.__validate_document(documents, 'liability', now) +
                self.__validate_document(documents, 'workers', now) +
                self.__validate_document(documents, 'financial', now, False))

    def __validate_document(self, documents, name, now, has_expiry=True):
        errors = []
        document = documents.get(name)
        document_required = (
            (
                name == 'workers' and (
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
                'severity': 'error',
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
                    expiry_date = pendulum.parse(expiry, tz='Australia/Sydney')

                    if now > expiry_date.date():
                        errors.append({
                            'message': '{} document has expired'.format(name),
                            'severity': 'error',
                            'step': 'documents'
                        })
                except ValueError:
                    errors.append({
                        'message': '"{}" is an invalid date format'.format(expiry),
                        'severity': 'error',
                        'step': 'documents'
                    })

        return errors

    def validate_methods(self):
        return (
            self.__validate_required(
                self.application.data, {
                    'tools': 'Tools',
                    'methodologies': 'Methodologies'
                },
                'tools')
        )

    def validate_recruiter(self):
        errors = []
        if not self.application.data.get('recruiter'):
            errors.append({
                'message': 'Recruiter is required',
                'severity': 'error',
                'step': 'recruiter'
            })
        return errors

    def validate_services(self):
        errors = []
        recruiter = self.application.data.get('recruiter')
        if recruiter == 'yes' or recruiter == 'both':
            services = self.application.data.get('services', {})
            if not services:
                errors.append({
                    'message': 'Services is required',
                    'severity': 'error',
                    'step': 'domains'
                })

        return errors

    def validate_pricing(self):
        errors = []
        pricing = self.application.data.get('pricing', {})
        recruiter = self.application.data.get('recruiter')
        services = self.application.data.get('services')

        if recruiter == 'no' or recruiter == 'both':
            for service in services.iterkeys():
                field_id = '{}-maxprice'.format(service.lower().replace(' ', '-'))
                if service not in pricing or not pricing[service].get('maxPrice'):
                    errors.append({
                        'field': field_id,
                        'message': 'Price is required for {}'.format(service),
                        'severity': 'error',
                        'step': 'pricing'
                    })

        return errors

    def __validate_case_study(self, case_study):
        errors = (
            self.__validate_required(
                case_study, {
                    'title': 'Title',
                    'client': 'Client',
                    'timeframe': 'Time frame',
                    'roles': 'Business role',
                    'opportunity': 'Opportunity',
                    'approach': 'Approach',
                    'referee_name': 'Referee name',
                    'referee_position': 'Referee position',
                    'referee_contact': 'Referee contact',
                    'referee_email': 'Referee phone number'
                },
                'case-study')
        )

        if len(case_study.get('outcome', [])) == 0:
            errors.append({
                'message': 'Outcome is required',
                'severity': 'error',
                'step': 'case-study'
            })
        else:
            outcomes = [o for o in case_study.get('outcome') if o]
            if len(outcomes) != len(case_study.get('outcome')):
                errors.append({
                    'message': 'Outcome cannot be empty',
                    'severity': 'error',
                    'step': 'case-study'
                })

        links = [pl for pl in case_study.get('project_links', []) if pl.startswith('http')]
        if len(links) != len(case_study.get('project_links', [])):
            errors.append({
                'field': 'project_links',
                'message': 'Project links must begin with http',
                'severity': 'error',
                'step': 'case-study'
            })

        return errors

    def validate_candidates(self):
        errors = []
        recruiter_info = self.application.data.get('recruiter_info', {})
        recruiter = self.application.data.get('recruiter')
        services = self.application.data.get('services')

        if recruiter == 'yes' or recruiter == 'both':
            for service in services.iterkeys():
                if service not in recruiter_info:
                    errors.append({
                        'message': 'Recruiter info is required for {}'.format(service),
                        'severity': 'error',
                        'step': 'candidates'
                    })
                else:
                    for s, value in recruiter_info.iteritems():
                        errors = errors + self.__validate_candidate(value, s)

        return errors

    def __validate_candidate(self, candidate, service):
        errors = []
        required_fields = {
            'database_size': 'Candidate database size',
            'active_candidates': 'Number of candidates looking',
            'margin': 'Margin',
            'markup': 'Mark-up',
            'placed_candidates': 'Number of candidates successfully placed'
        }
        for field, label in required_fields.iteritems():
            if not candidate.get(field):
                errors.append({
                    'field': field,
                    'message': '{} is required for {}'.format(label, service),
                    'severity': 'error',
                    'step': 'candidates'
                })

        return errors

    def validate_products(self):
        errors = []

        products = self.application.data.get('products', {})
        if isinstance(products, list):
            for index, value in enumerate(products):
                errors = errors + self.__validate_product(index, value)
        else:
            for index, value in products.iteritems():
                errors = errors + self.__validate_product(index, value)

        return errors

    def __validate_product(self, product_number, product):
        # products are identified by an index in the product array
        pns = int(product_number) + int(1)

        url_fields = {
            'website': 'Product {} website link'.format(pns),
            'pricing': 'Product {} pricing link'.format(pns),
            'support': 'Product {} support link'.format(pns)
        }
        required_fields = {
            'name': 'Product {} name'.format(pns),
            'summary': 'Product {} summary'.format(pns)
        }
        required_fields.update(url_fields)

        errors = (
            self.__validate_required(
                product,
                required_fields,
                'products')
        )

        for k, v in url_fields.iteritems():
            value = product.get(k, 'http')
            if value and not value.startswith('http'):
                errors.append({
                    'field': k,
                    'message': '{} must begin with http'.format(v),
                    'severity': 'error',
                    'step': 'products'
                })

        return errors
