DO $$                  
    BEGIN 
		IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'key_value')
		THEN
            create sequence "public"."key_value_id_seq";

            create table "public"."key_value" (
                "id" integer not null default nextval('key_value_id_seq'::regclass),
                "updated_at" timestamp without time zone not null,
                "key" character varying,
                "data" json
            );


            CREATE INDEX ix_key_value_updated_at ON public.key_value USING btree (updated_at);

            CREATE UNIQUE INDEX key_value_key_key ON public.key_value USING btree (key);

            CREATE UNIQUE INDEX key_value_pkey ON public.key_value USING btree (id);

            alter table "public"."key_value" add constraint "key_value_pkey" PRIMARY KEY using index "key_value_pkey";

            alter table "public"."key_value" add constraint "key_value_key_key" UNIQUE using index "key_value_key_key";

		END IF;
	END;
$$ ;

