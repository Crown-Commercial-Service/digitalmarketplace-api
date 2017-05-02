create type "public"."application_type_enum" as enum ('upgrade', 'new', 'edit');

alter table "public"."application" add column "type" application_type_enum;

CREATE INDEX ix_application_type ON application USING btree (type);
