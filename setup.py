"""
API for Digital Marketplace.
"""

from setuptools import setup, find_packages

setup(
    name='dto-digitalmarketplace-api',
    version='440',  # TODO: Use semver?
    url='https://github.com/ausdto/dto-digitalmarketplace-api',
    license='MIT',
    author='GDS Developers',
    description='Marketplace API',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'dto-digitalmarketplace-utils',
        'dto-digitalmarketplace-apiclient',
        'Flask',
        'Flask-Bcrypt',
        'Flask-Migrate',
        'Flask-Script',
        'Flask-SQLAlchemy',
        'psycopg2',
        'SQLAlchemy==1.0.5',
        'SQLAlchemy-Utils',
        'streql',
        'newrelic',

        # For schema validation
        'jsonschema',
        'rfc3987',
        'strict-rfc3339',

        # For the import script
        'requests',
        'docopt',
        'six',

        # Elasticsearch 1.0
        'elasticsearch>=1.0.0,<2.0.0',
        'Flask-Elasticsearch',

        'pendulum',
        'jira'
    ]
)
