DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'body_type_enum') THEN

        create type "public"."body_type_enum" as enum ('ncce', 'cce', 'cc', 'local', 'state', 'other');

    END IF;
END$$;

alter table "public"."agency" add column if not exists "body_type" body_type_enum null;

update agency
set body_type = 'other'
where body_type is null;

alter table "public"."agency" alter column "body_type" set not null;

alter table "public"."agency" add column if not exists "reports" boolean null;

update agency
set reports = true
where reports is null;

alter table "public"."agency" alter column "reports" set not null;