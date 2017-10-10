#!/bin/bash
python import_orams_suppliers.py < ORAMS_Suppliers.csv
python import_orams_services.py < ORAMS_Services_List.csv
python import_orams_sub_services.py < ORAMS_Sub_Service_List.csv
python import_orams_locations.py < ORAMS_Supplier_Locations.csv
python import_orams_prices.py < ORAMS_Pricing.csv
python import_orams_price_ceilings.py < ORAMS_Pricing_Ceilings.csv