DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'supplier_domain_price_status_enum') THEN

        create type "public"."supplier_domain_price_status_enum" as enum ('approved', 'rejected', 'unassessed');

        alter table "public"."supplier_domain" add column "price_status" supplier_domain_price_status_enum null;

        update "public"."supplier_domain" set price_status = 'unassessed';

        ALTER TABLE "public"."supplier_domain" ALTER COLUMN price_status SET NOT NULL;
    END IF;
END$$;
