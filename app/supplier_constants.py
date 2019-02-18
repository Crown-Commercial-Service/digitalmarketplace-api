# Here we define a set of hardcoded keys that we use when denormalizing data from Supplier/ContactInformation tables
# into the SupplierFramework.declaration field. These are used only by the API and by the
# `digitalmarketplace-scripts/scripts/generate-framework-agreement-*-pages`, which generates framework agreement
# signature pages for successful suppliers to sign. These agreements are populated with some of the details below.
KEY_DUNS_NUMBER = 'supplierDunsNumber'
KEY_ORGANISATION_SIZE = 'supplierOrganisationSize'
KEY_REGISTERED_NAME = 'supplierRegisteredName'
KEY_REGISTRATION_BUILDING = 'supplierRegisteredBuilding'
KEY_REGISTRATION_COUNTRY = 'supplierRegisteredCountry'
KEY_REGISTRATION_NUMBER = 'supplierCompanyRegistrationNumber'
KEY_REGISTRATION_POSTCODE = 'supplierRegisteredPostcode'
KEY_REGISTRATION_TOWN = 'supplierRegisteredTown'
KEY_TRADING_NAME = 'supplierTradingName'
KEY_TRADING_STATUS = 'supplierTradingStatus'
