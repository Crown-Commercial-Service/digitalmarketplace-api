alter table "public"."location" drop column "state";

alter table "public"."region" add column "state" character varying not null;