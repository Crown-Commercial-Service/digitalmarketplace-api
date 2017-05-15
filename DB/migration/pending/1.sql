alter table "public"."assessment" add column "active" boolean;
update "assessment" set "active" = true;
alter table "public"."assessment" alter column "active" set not null;

alter table "public"."supplier_domain" drop constraint "supplier_domain_pkey";
drop index if exists "public"."supplier_domain_pkey";
alter table "public"."supplier_domain" alter column "domain_id" drop not null;
alter table "public"."supplier_domain" alter column "id" set not null;
alter table "public"."supplier_domain" alter column "supplier_id" drop not null;
CREATE UNIQUE INDEX supplier_domain_pkey ON supplier_domain USING btree (id);
alter table "public"."supplier_domain" add constraint "supplier_domain_pkey" PRIMARY KEY using index "supplier_domain_pkey";
