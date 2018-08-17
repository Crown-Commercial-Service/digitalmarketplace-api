import pendulum


class ApplicationValidator(object):

    def __init__(self, application):
        self.application = application

    def validate_all(self):
        return (self.validate_basics() +
                self.validate_documents() +
                self.validate_pricing() +
                self.validate_candidates() +
                self.validate_case_studies())

    def validate_basics(self):
        errors = []
        if not self.application.data.get('name'):
            errors.append({
                'message': 'Supplier name is required',
                'severity': 'error'
            })

        return errors

    def validate_pricing(self):
        errors = []
        pricing = self.application.data.get('pricing', {})
        recruiter = self.application.data.get('recruiter')
        services = self.application.data.get('services')

        if recruiter == 'no' or recruiter == 'both':
            if len(services) != len(pricing):
                for service in services.iterkeys():
                    if service not in pricing:
                        errors.append({
                            'message': 'Price is required for {}'.format(service),
                            'severity': 'error'
                        })
        elif recruiter == 'yes':
            # [DOCO] there are no prices for recruiters
            pass

        return errors

    def validate_candidates(self):
        errors = []
        recruiter_info = self.application.data.get('recruiter_info', {})
        recruiter = self.application.data.get('recruiter')
        services = self.application.data.get('services')

        if recruiter == 'yes' or recruiter == 'both':
            if len(services) != len(recruiter_info):
                for service in services.iterkeys():
                    if service not in recruiter_info:
                        errors.append({
                            'message': 'Recruiter info is required for {}'.format(service),
                            'severity': 'error'
                        })
            else:
                for service, value in recruiter_info.iteritems():
                    errors = errors + self.__validate_candidate(value, service)

        else:
            # [DOCO] there is no recruiter info for non-recruiters
            pass
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
                    'message': '{} is required for {}'.format(label, service),
                    'severity': 'error'
                })

        return errors

    def validate_case_studies(self):
        errors = []
        case_studies = self.application.data.get('case_studies', {})
        recruiter = self.application.data.get('recruiter')
        services = self.application.data.get('services')

        if recruiter == 'no' or recruiter == 'both':
            for service in services.iterkeys():
                service_case_studies = [cs for i, cs in case_studies.iteritems() if cs.get('service') == service]
                if len(service_case_studies) == 0:
                    errors.append({
                        'message': 'At least one case study is required for {}'.format(service),
                        'severity': 'error'
                    })
                else:
                    for service_case_study in service_case_studies:
                        errors = errors + self.__validate_case_study(service_case_study)
        elif recruiter == 'yes':
            # [DOCO] there are no case studies for recruiters
            pass

        return errors

    def __validate_case_study(self, case_study):
        errors = []
        required_fields = {
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
        }
        for field, label in required_fields.iteritems():
            if not case_study.get(field):
                errors.append({
                    'message': '{} is required'.format(label),
                    'severity': 'error'
                })

        if len(case_study.get('outcome', [])) == 0:
            errors.append({
                'message': 'Outcome is required',
                'severity': 'error'
            })
        else:
            outcomes = [o for o in case_study.get('outcome') if o]
            if len(outcomes) != len(case_study.get('outcome')):
                errors.append({
                    'message': 'Outcome cannot be empty',
                    'severity': 'error'
                })

        links = [pl for pl in case_study.get('project_links', []) if pl.startswith('http')]
        if len(links) != len(case_study.get('project_links')):
            errors.append({
                'message': 'Project links must begin with http',
                'severity': 'error'
            })

        return errors

    def validate_recruiter(self):
        errors = []
        if self.application.data.get('recruiter') == 'yes':
            # recruiter info required
            # pricing not needed (NULL)
            # case study not needed (NULL)
            pass
        elif self.application.data.get('recruiter') == 'no':
            # recruiter not needed (NULL)
            # pricing required
            # case study required
            pass
        elif self.application.data.get('recruiter') == 'both':
            # recruiter info required
            # pricing required
            # case study required
            pass

    def validate_documents(self):
        documents = self.application.data.get('documents')
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
                'message': 'filename is required for your document',
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
