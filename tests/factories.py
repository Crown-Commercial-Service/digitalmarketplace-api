from datetime import datetime, timedelta
import random

import factory
from app import db, models


class DMProvider(object):
    """Custom Faker provider to supply Digial Marketplace specific test data."""

    def __init__(self, generator):
        self.generator = generator

    @property
    def supplier_organisation_size(self):
        return random.choice(['micro', 'small', 'medium', 'large'])

    @property
    def _BUYER_EMAIL_DOMAINS(self):
        with open('./data/buyer-email-domains.txt') as f:
            return f.read().splitlines()

    def buyer_email(self):
        return factory.Faker('user_name').generate({}) + '@' + random.choice(self._BUYER_EMAIL_DOMAINS)

    def client_list(self, length=1):
        return [factory.Faker('company').generate({}) for i in range(length)]

    def service_id(self):
        return str(random.randint(1000000000000000, 9999999999999999))

    def supplier_id(self):
        return random.randint(700000, 800000)

    def user_role(self):
        return random.choice(models.User.ROLES)

    def service_data(self, **kwargs):
        data = {}
        data.update(kwargs)
        return data

    def supplier_framework_declaration(self, **kwargs):
        declaration = {'status': 'complete', 'organisationSize': DMProvider.supplier_organisation_size}
        declaration.update(**kwargs)
        return declaration

    def brief_data(self, **kwargs):
        data = {}
        data.update(**kwargs)
        return data

    def brief_response_data(self, **kwargs):
        data = {}
        data.update(**kwargs)
        return data

    def brief_response_award_details(self, **kwargs):
        award_details = {}
        award_details.update(**kwargs)
        return award_details


factory.Faker.add_provider(DMProvider)


class DMBaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base class for Digital Marketplace factories"""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        We don't want to recreate certain objects. For example frameworks and lots should not be recreated.
        Super this method to check first if we have defined _no_recreate_fields on the factory.
        If we have then we do a search for objects with matching fields and skip the creation, returning the object
        we found in our search. This mimics the django_get_or_create meta functionality detailed here:
        http://factoryboy.readthedocs.io/en/latest/orms.html#factory.django.DjangoOptions.django_get_or_create
        """
        if hasattr(cls, '_no_recreate_fields'):
            no_recreate_fields = getattr(cls, '_no_recreate_fields')
            for attr in no_recreate_fields:
                if type(attr) == str:
                    obj = model_class.query.filter(getattr(model_class, attr) == kwargs[attr]).first()
                else:
                    attr_iter = attr
                    obj = model_class.query.filter(
                        *[getattr(model_class, attr) == kwargs[attr] for attr in attr_iter]
                    ).first()
                if obj:
                    no_recreate_fields_flat = [item for sublist in no_recreate_fields for item in sublist]
                    values = {k: v for k, v in kwargs.items() if k not in no_recreate_fields_flat}
                    if values:
                        obj.query.update(values=values)
                    return obj
        return super(DMBaseFactory, cls)._create(model_class, *args, **kwargs)


class DMBaseFactoryCreateUpdate(DMBaseFactory):

    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class DMBaseFactoryMeta(object):

    sqlalchemy_session = db.session
    sqlalchemy_session_persistence = 'commit'


class FrameworkLotFactory(DMBaseFactory):

    _no_recreate_fields = (('framework_id', 'lot_id'),)

    framework_id = 0
    lot_id = 0

    class Meta(DMBaseFactoryMeta):
        model = models.FrameworkLot


class LotFactory(DMBaseFactory):

    _no_recreate_fields = (('slug',), ('name',))

    slug = 'some-lot'
    name = 'Some Lot'
    data = {'unitSingular': 'service', 'unitPlural': 'services'}
    one_service_limit = True

    class Meta(DMBaseFactoryMeta):
        model = models.Lot


class FrameworkFactoryMixin(DMBaseFactory):

    _no_recreate_fields = (('slug',), ('name',))

    status = 'live'
    clarification_questions_open = True

    class Meta(DMBaseFactoryMeta):
        model = models.Framework
        abstract = True


class DOS2FrameworkFactory(FrameworkFactoryMixin):

    slug = 'digital-outcomes-and-specialists-2'
    name = 'Digital Outcomes and Specialists 2'
    framework = 'digital-outcomes-and-specialists'
    allow_declaration_reuse = True

    @factory.post_generation
    def post_generation_tasks(self, *args, **kwargs):
        lots = (
            LotFactory(slug='digital-outcomes', name='Digital outcomes'),
            LotFactory(slug='digital-specialists', name='Digital specialists'),
            LotFactory(slug='user-research-participants', name='User research participants'),
            LotFactory(
                slug='user-research-studios',
                name='User research studios',
                one_service_limit=False,
                data={"unitSingular": "lab", "unitPlural": "labs"}
            )
        )
        for lot in lots:
            FrameworkLotFactory(lot_id=lot.id, framework_id=self.id)

    class Meta(DMBaseFactoryMeta):
        model = models.Framework


class GcloudFrameworkFactory(FrameworkFactoryMixin):

    slug = 'g-cloud-9'
    name = 'G-Cloud 9'
    framework = 'g-cloud'
    allow_declaration_reuse = False

    @factory.post_generation
    def post_generation_tasks(self, *args, **kwargs):
        lots = (
            LotFactory(slug='cloud-support', name='Cloud support', one_service_limit=False),
            LotFactory(slug='cloud-hosting', name='Cloud hosting', one_service_limit=False),
            LotFactory(slug='cloud-software', name='Cloud software', one_service_limit=False)
        )
        for lot in lots:
            FrameworkLotFactory(lot_id=lot.id, framework_id=self.id)

    class Meta(DMBaseFactoryMeta):
        model = models.Framework


class ContactInformationFactory(DMBaseFactory):

    supplier = factory.SubFactory('tests.factories.SupplierFactory')
    contact_name = factory.Faker('name')
    email = factory.Faker('email')

    class Meta(DMBaseFactoryMeta):
        model = models.ContactInformation


class SupplierFactory(DMBaseFactory):

    supplier_id = factory.lazy_attribute(lambda i: random.randint(700000, 800000))
    name = factory.Faker('company')
    clients = factory.Faker('client_list')

    class Meta(DMBaseFactoryMeta):
        model = models.Supplier


class SupplierFrameworkFactory(DMBaseFactory):

    supplier = factory.SubFactory(SupplierFactory)
    framework = factory.SubFactory(GcloudFrameworkFactory)
    declaration = factory.Faker('supplier_framework_declaration')
    on_framework = True

    class Meta(DMBaseFactoryMeta):
        model = models.SupplierFramework


class FrameworkAgreementFactory(DMBaseFactory):

    supplier = factory.SubFactory(SupplierFactory)
    framework = factory.SubFactory(GcloudFrameworkFactory)

    class Meta(DMBaseFactoryMeta):
        model = factory.SubFactory(models.FrameworkAgreement)


class UserFactory(DMBaseFactoryCreateUpdate):

    name = factory.Faker('name')
    role = factory.Faker('user_role')
    email_address = factory.Faker('buyer_email')
    password_changed_at = factory.Faker('date_time_this_year', before_now=True)
    password = 'Password1234'
    active = True

    class Meta(DMBaseFactoryMeta):
        model = models.User


class BuyerUserFactory(UserFactory):
    """Shortcut class for creating a buyer user."""

    role = 'buyer'

    logged_in_at = factory.LazyFunction(datetime.now)

    class Meta(DMBaseFactoryMeta):
        model = models.User


class SupplierUserFactory(UserFactory):
    """Shortcut class for creating a supplier user."""

    role = 'supplier'

    supplier = factory.SubFactory(SupplierFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.User


class ServiceFactory(DMBaseFactoryCreateUpdate):

    service_id = factory.Faker('service_id')
    data = factory.Faker('service_data')
    status = 'enabled'

    framework = factory.SubFactory(GcloudFrameworkFactory, status='open')
    supplier = factory.LazyAttribute(lambda i: SupplierUserFactory().supplier)
    lot_id = factory.LazyAttribute(lambda i: random.choice(i.framework.lots).id)
    framework_id = factory.LazyAttribute(lambda i: i.framework.id)

    class Meta(DMBaseFactoryMeta):
        model = models.Service


class ArchivedServiceFactory(ServiceFactory):

    class Meta(DMBaseFactoryMeta):
        model = models.ArchivedService


class DraftServiceFactory(ServiceFactory):

    class Meta(DMBaseFactoryMeta):
        model = models.DraftService


class BriefFactory(DMBaseFactoryCreateUpdate):

    is_a_copy = False
    data = factory.Faker('brief_data')

    lot = factory.SubFactory(LotFactory)
    framework = factory.SubFactory(DOS2FrameworkFactory, status='open')

    _lot_id = factory.LazyAttribute(lambda i: i.lot.id)
    users = factory.PostGeneration(lambda br, *args, **kwargs: BriefUserFactory(brief_id=br.id))

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class LiveBriefFactory(BriefFactory):

    created_at = datetime.now() - timedelta(days=1)
    published_at = datetime.now() - timedelta(weeks=2, days=1)

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class ClosedBriefFactory(BriefFactory):

    created_at = datetime.now() - timedelta(weeks=3)
    published_at = datetime.now() - timedelta(weeks=2, days=1)

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class WithdrawnBriefFactory(BriefFactory):

    created_at = datetime.now() - timedelta(days=2)
    published_at = datetime.now() - timedelta(days=1)
    withrawn_at = datetime.now()

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class CancelledBriefFactory(BriefFactory):

    created_at = datetime.now() - timedelta(weeks=3)
    published_at = datetime.now() - timedelta(weeks=2, days=1)
    cancelled_at = datetime.now()

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class UnsuccessfuldBriefFactory(BriefFactory):
    created_at = datetime.now() - timedelta(weeks=3)
    published_at = datetime.now() - timedelta(weeks=2, days=1)
    unsuccessful_at = datetime.now()

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class BriefUserFactory(DMBaseFactory):

    user_id = factory.LazyAttribute(lambda a: BuyerUserFactory().id)
    brief_id = factory.LazyAttribute(lambda a: BriefFactory().id)

    class Meta(DMBaseFactoryMeta):
        model = models.BriefUser


class BriefClarificationQuestionFactory(DMBaseFactory):

    question = 'Test question'
    answer = 'Test answer'

    brief = factory.SubFactory(LiveBriefFactory)
    _brief_id = factory.LazyAttribute(lambda i: i.brief.id)
    published_at = factory.LazyFunction(datetime.now)

    class Meta(DMBaseFactoryMeta):
        model = models.BriefClarificationQuestion


class BriefResponseFactory(DMBaseFactory):

    data = factory.Faker('brief_response_data')
    award_details = factory.Faker('brief_response_award_details')

    brief = factory.SubFactory(LiveBriefFactory)
    supplier = factory.SubFactory(SupplierFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.BriefResponse


class PendingAwardBriefResponseFactory(BriefResponseFactory):

    award_details = {'pending': True}

    class Meta(DMBaseFactoryMeta):
        model = models.BriefResponse


class AwardedBriefResponseFactory(PendingAwardBriefResponseFactory):

    @factory.post_generation
    def post_generation_tasks(self, *args, **kwargs):
        self.awarded_at = datetime.now()
        self.award_details = {
            "awardedContractStartDate": (self.awarded_at + timedelta(weeks=8)).strftime("%Y-%-m-%-d"),
            "awardedContractValue": "100"
        }

    class Meta(DMBaseFactoryMeta):
        model = models.BriefResponse


class DirectAwardProjectFactory(DMBaseFactory):

    name = 'Test project'
    active = True

    users_1 = factory.RelatedFactory('tests.factories.DirectAwardProjectUserFactory', 'direct_award_project')
    users_2 = factory.RelatedFactory('tests.factories.DirectAwardProjectUserFactory', 'direct_award_project')
    created_at = factory.LazyFunction(datetime.now)

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardProject


class DirectAwardProjectUserFactory(DMBaseFactory):

    project = factory.SubFactory(DirectAwardProjectFactory)
    user = factory.SubFactory(BuyerUserFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardProjectUser


class DirectAwardSearchFactory(DMBaseFactory):

    search_url = ''  # TODO @samwilliams
    active = True

    created_by = factory.SubFactory(UserFactory)
    project = factory.SubFactory(DirectAwardProjectFactory)
    archived_service_1 = factory.RelatedFactory('tests.factories.DirectAwardSearchResultEntryFactory', 'search')
    archived_service_2 = factory.RelatedFactory('tests.factories.DirectAwardSearchResultEntryFactory', 'search')
    created_at = factory.LazyFunction(datetime.now)
    searched_at = factory.LazyFunction(datetime.now)

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardSearch


class DirectAwardSearchResultEntryFactory(DMBaseFactory):

    search = factory.SubFactory(DirectAwardSearchFactory)
    archived_service = factory.SubFactory(ArchivedServiceFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardSearchResultEntry
