# Here we define a set of hardcoded keys that we use when denormalizing data from Supplier/ContactInformation tables
# into the SupplierFramework.declaration field. These are only used internally by the API - the frontends currently
# do not need knowledge of them, so there is no reason to centralise them e.g. in utils at this time.
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
KEY_VAT_NUMBER = 'supplierVatNumber'
