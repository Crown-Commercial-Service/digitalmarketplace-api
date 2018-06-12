INSERT INTO "domain" VALUES ('14', 'Change and Transformation', '12', '0', '10000') ON CONFLICT (id) DO NOTHING;
INSERT INTO "domain" VALUES ('15', 'Training, Learning and Development', '13', '0', '10000') ON CONFLICT (id) DO NOTHING;

DO $$                  
    BEGIN 
		IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'application' AND COLUMN_NAME = 'updated_at')
		THEN

			ALTER TABLE public.application ADD COLUMN updated_at timestamp without time zone;
			update public.application set updated_at = created_at;
			ALTER TABLE public.application ALTER COLUMN updated_at set not null;
			CREATE INDEX ix_application_updated_at ON public.application USING btree (updated_at);
		END IF;
	END;
$$ ;