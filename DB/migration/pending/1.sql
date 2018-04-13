
DO $$                  
    BEGIN 
		IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'brief_response' AND COLUMN_NAME = 'withdrawn_at')
		THEN
			alter table "public"."brief_response" add column "withdrawn_at" timestamp without time zone;

			CREATE INDEX ix_brief_response_withdrawn_at ON brief_response USING btree (withdrawn_at);
		END IF;
		
		IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'domain' AND COLUMN_NAME = 'price_minimum')
		THEN
			alter table "public"."domain" add column "price_minimum" numeric null;
			update domain set price_minimum = 0;
			alter table "public"."domain" alter column "price_minimum" set not null;
		END IF;
		
		IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'domain' AND COLUMN_NAME = 'price_maximum')
		THEN
			alter table "public"."domain" add column "price_maximum" numeric null;
			update domain set price_maximum = 10000;
			alter table "public"."domain" alter column "price_maximum" set not null;
		END IF;
	END;
$$ ;
