from app import models
import factory
from app import db
from sqlalchemy import orm
import random
from faker import Faker
from faker.providers import BaseProvider
import string
fake = Faker()

# Our custom provider inherits from the BaseProvider
class DMProvider(BaseProvider):

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

class DMBaseFactoryMeta(object):
    sqlalchemy_session = db.session
    sqlalchemy_session_persistence = 'commit'




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
        abstract=True


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


class SupplierFactory(DMBaseFactory):
    class Meta(DMBaseFactoryMeta):
        model = models.Supplier

    supplier_id = factory.lazy_attribute(lambda i: random.randint(700000, 800000))
    name = factory.Faker('company')
    clients = factory.Faker('client_list')




class SupplierFrameworkFactory(DMBaseFactory):
    supplier = factory.SubFactory(SupplierFactory)
    framework = factory.SubFactory(GcloudFrameworkFactory)

    class Meta(DMBaseFactoryMeta):
        model = models.SupplierFramework


class ContactInformationFactory(DMBaseFactory):
    supplier = factory.SubFactory(SupplierFactory)
    contact_name = factory.Faker('name')
    email = factory.Faker('email')

    class Meta(DMBaseFactoryMeta):
        model = models.ContactInformation

class FrameworkAgreementFactory(DMBaseFactory):
    supplier = factory.SubFactory(SupplierFactory)
    framework = factory.SubFactory(GcloudFrameworkFactory)

    class Meta(DMBaseFactoryMeta):
        model = factory.SubFactory(models.FrameworkAgreement)


class FrameworkAgreementFactory(DMBaseFactory):
    supplier = factory.SubFactory(SupplierFactory)
    framework = factory.SubFactory(GcloudFrameworkFactory)



class BuyerUserFactory(DMBaseFactory):
        class Meta(DMBaseFactoryMeta):
            model = models.User
            sqlalchemy_session = db.session
            sqlalchemy_session_persistence = 'commit'

        name = factory.Faker('name')
        email_address = factory.Faker('buyer_email')
        password = 'Password1234'
        role = 'buyer'
        active = True
        password_changed_at = factory.Faker('date_time_this_year', before_now=True)


class SupplierUserFactory(DMBaseFactory):
    class Meta(DMBaseFactoryMeta):
        model = models.User
    role = 'supplier'
    email = factory.Faker('email')