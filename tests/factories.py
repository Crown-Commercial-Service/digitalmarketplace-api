from app import models
import factory
from app import db
from sqlalchemy import orm
import random
from faker import Faker
from faker.providers import BaseProvider
import string
fake = Faker()
from datetime import datetime

# Our custom provider inherits from the BaseProvider
class DMProvider(BaseProvider):

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
        return random.randint(1000000000000000, 9999999999999999)

    def supplier_id(self):
        return random.randint(700000, 800000)

    def user_role(self):
        return random.choice(models.User.ROLES)

    def service_data(self, **kwargs):
        data = {}
        data.update(kwargs)
        return data

    def supplier_framework_declaration(self, **kwargs):
        declaration = {"status": "complete", "organisationSize": DMProvider.supplier_organisation_size}
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
    def _create(cls, *args, **kwargs):
        """
        We don't want to recreate certain objects. For example frameworks and lots should not be recreated.
        Super this method to check first if we have defined _no_recreate_fields on the factory.
        If we have then we do a search for objects with matching fields and skip the creation, returning the object
        we found in our search. This mimics the django_get_or_create meta functionality detailed here:
        http://factoryboy.readthedocs.io/en/latest/orms.html#factory.django.DjangoOptions.django_get_or_create
        """
        if hasattr(cls, '_no_recreate_fields'):
            for attr in getattr(cls, '_no_recreate_fields'):
                obj = cls.Meta.model.query.filter(getattr(cls.Meta.model, attr) ==  kwargs[attr]).first()
                if obj:
                    return obj
        return super(DMBaseFactory, cls)._create(*args, **kwargs)


class DMBaseFactoryCreateUpdate(DMBaseFactory):
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class DMBaseFactoryMeta(object):
    sqlalchemy_session = db.session
    sqlalchemy_session_persistence = 'commit'


class FrameworkLotFactory(DMBaseFactory):
    framework = factory.SubFactory(GcloudFrameworkFactory)
    lot = factory.SubFactory(LotFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.Lot


class LotFactory(DMBaseFactory):

    slug = 'digital-outcomes'
    name = 'Digital Outcomes'
    one_service_limit = True
    data = {"unitSingular": "service", "unitPlural": "services"}

    class Meta(DMBaseFactoryMeta):
        model = models.Lot


class FrameworkFactoryMixin():
    _no_recreate_fields = ('slug', 'name')
    clarification_questions_open = False
    status = 'live'
    class Meta(DMBaseFactoryMeta):
        model = models.Framework
        abstract = True


class DOS2FrameworkFactory(DMBaseFactory, FrameworkFactoryMixin):
    slug = 'digital-outcomes-and-specialists-2'
    name = 'Digital Outcomes and Specialists 2'
    framework = 'digital-outcomes-and-specialists'
    allow_declaration_reuse = True

    class Meta(DMBaseFactoryMeta):
        model = models.Framework


class GcloudFrameworkFactory(DMBaseFactory, FrameworkFactoryMixin):
    slug = 'g-cloud-9'
    name = 'G-Cloud 9'
    framework = 'g-cloud'
    allow_declaration_reuse = False

    class Meta(DMBaseFactoryMeta):
        model = models.Framework


class ContactInformationFactory(DMBaseFactory):
    supplier = factory.SubFactory(SupplierFactory)
    contact_name = factory.Faker('name')
    email = factory.Faker('email')

    class Meta(DMBaseFactoryMeta):
        model = models.ContactInformation


class SupplierFactory(DMBaseFactory):
    class Meta(DMBaseFactoryMeta):
        model = models.Supplier

    supplier_id = factory.lazy_attribute(lambda i: random.randint(700000, 800000))
    name = factory.Faker('company')
    clients = factory.Faker('client_list')


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


### USERS ###

class UserFactory(DMBaseFactoryCreateUpdate):

    name = factory.Faker('name')
    email_address = factory.Faker('buyer_email')
    password = 'Password1234'
    active = True
    password_changed_at = factory.Faker('date_time_this_year', before_now=True)
    role = factory.Faker('user_role')

    class Meta(DMBaseFactoryMeta):
        model = models.User
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'


class BuyerUserFactory(UserFactory):
    """Shortcut class for creating a buyer user."""
    role = 'buyer'
    logged_in_at = factory.LazyFunction(datetime.now)
    class Meta(UserFactory.Meta):
        pass


class SupplierUserFactory(UserFactory):
    """Shortcut class for creating a supplier user."""
    supplier = factory.SubFactory(SupplierFactory)
    role = 'supplier'

    class Meta(UserFactory.Meta):
        pass


class ServiceFactory(DMBaseFactoryCreateUpdate):

    service_id = factory.Faker('service_id')
    data = factory.Faker('service_data')
    status = 'enabled'

    supplier = factory.SubFactory(SupplierFactory)
    framework = factory.SubFactory(GcloudFrameworkFactory)
    lot = factory.SubFactory(LotFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.Service


class ArchiveServiceFactory(ServiceFactory):

    class Meta(DMBaseFactoryMeta):
        model = models.ArchiveService


class DraftServiceFactory(ServiceFactory):

    class Meta(DMBaseFactoryMeta):
        model = models.ArchiveService


class BriefFactory(DMBaseFactoryCreateUpdate):

    framework = factory.SubFactory(DOS2FrameworkFactory)
    lot = factory.SubFactory(LotFactory)
    _lot_id = factory.LazyAttribute(lambda i: i.lot.id)
    is_a_copy = False
    data = factory.Faker('brief_data')
    users_1 = factory.RelatedFactory(BriefUserFactory, 'brief')
    users_2 = factory.RelatedFactory(BriefUserFactory, 'brief')

    class Meta(DMBaseFactoryMeta):
        model = models.Brief


class BriefUserFactory(DMBaseFactory):
    user = factory.SubFactory(BuyerUserFactory)
    brief = factory.SubFactory(BriefFactory)
    class Meta(DMBaseFactoryMeta):
        model = models.BriefUser


class BriefClarificationQuestion(DMBaseFactory):

    _brief_id = factory.LazyAttribute(lambda i: i.brief.id)

    question = 'Test question'
    answer = 'Test answer'

    published_at = factory.LazyFunction(datetime.now)
    brief = factory.SubFactory(BriefFactory)
    class Meta(DMBaseFactoryMeta):
        model = models.BriefClarificationQuestion


class BriefResponse(db.Model):

    data = factory.Faker('brief_response_data')
    award_details = factory.Faker('brief_response_award_details')

    brief = factory.SubFactory(BriefFactory)
    supplier = factory.SubFactory(SupplierFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.BriefResponse


### DIRECT AWARD ###

class DirectAwardProjectFactory(DMBaseFactory):

    name = 'Test project'
    created_at = factory.LazyFunction(datetime.now)
    active = True
    users_1 = factory.RelatedFactory(DirectAwardProjectUserFactory, 'direct_award_project')
    users_2 = factory.RelatedFactory(DirectAwardProjectUserFactory, 'direct_award_project')

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardProject


class DirectAwardProjectUserFactory(DMBaseFactory):
    project = factory.SubFactory(DirectAwardProjectFactory)
    user = factory.SubFactory(BuyerUserFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardProjectUser


class DirectAwardSearchFactory(DMBaseFactory):

    created_by = factory.SubFactory(UserFactory)
    project = factory.SubFactory(DirectAwardProjectFactory)
    created_at = factory.LazyFunction(datetime.now)
    searched_at = factory.LazyFunction(datetime.now)
    search_url = '' # TODO @samwilliams
    active = True

    archived_service_1 = factory.RelatedFactory(DirectAwardSearchResultEntryFactory, 'search')
    archived_service_2 = factory.RelatedFactory(DirectAwardSearchResultEntryFactory, 'search')

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardSearch


class DirectAwardSearchResultEntryFactory(db.Model):
    search = factory.SubFactory(DirectAwardSearchFactory)
    archived_service = factory.SubFactory(ArchiveServiceFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.DirectAwardSearchResultEntry
