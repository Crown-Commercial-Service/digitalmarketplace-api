create sequence "public"."service_sub_type_id_seq";

create table "public"."service_sub_type" (
    "id" integer not null default nextval('service_sub_type_id_seq'::regclass),
    "name" character varying not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null
);


alter table "public"."service_type" add column "fee_type" character varying;

alter table "public"."service_type_price" add column "sub_service_id" integer;

alter table "public"."service_type_price_ceiling" add column "sub_service_id" integer;

CREATE UNIQUE INDEX service_sub_type_pkey ON service_sub_type USING btree (id);

alter table "public"."service_sub_type" add constraint "service_sub_type_pkey" PRIMARY KEY using index "service_sub_type_pkey";

alter table "public"."service_type_price_ceiling" add constraint "service_type_price_ceiling_sub_service_id_fkey" FOREIGN KEY (sub_service_id) REFERENCES service_sub_type(id);

alter table "public"."service_type_price" add constraint "service_type_price_sub_service_id_fkey" FOREIGN KEY (sub_service_id) REFERENCES service_sub_type(id);