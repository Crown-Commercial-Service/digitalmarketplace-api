create sequence "public"."service_type_price_id_seq";

create table "public"."service_type_price" (
    "id" integer not null default nextval('service_type_price_id_seq'::regclass),
    "supplier_code" integer not null,
    "service_type_id" integer not null,
    "region_id" integer not null,
    "date_from" timestamp without time zone not null,
    "date_to" timestamp without time zone,
    "price" numeric not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null
);


CREATE UNIQUE INDEX service_type_price_pkey ON service_type_price USING btree (id);

alter table "public"."service_type_price" add constraint "service_type_price_pkey" PRIMARY KEY using index "service_type_price_pkey";

alter table "public"."service_type_price" add constraint "service_type_price_region_id_fkey" FOREIGN KEY (region_id) REFERENCES region(id);

alter table "public"."service_type_price" add constraint "service_type_price_service_type_id_fkey" FOREIGN KEY (service_type_id) REFERENCES service_type(id);

alter table "public"."service_type_price" add constraint "service_type_price_supplier_code_fkey" FOREIGN KEY (supplier_code) REFERENCES supplier(code);

create sequence "public"."service_type_price_ceiling_id_seq";

create table "public"."service_type_price_ceiling" (
    "id" integer not null default nextval('service_type_price_ceiling_id_seq'::regclass),
    "supplier_code" integer not null,
    "service_type_id" integer not null,
    "region_id" integer not null,
    "price" numeric not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null
);


CREATE UNIQUE INDEX service_type_price_ceiling_pkey ON service_type_price_ceiling USING btree (id);

alter table "public"."service_type_price_ceiling" add constraint "service_type_price_ceiling_pkey" PRIMARY KEY using index "service_type_price_ceiling_pkey";

alter table "public"."service_type_price_ceiling" add constraint "service_type_price_ceiling_region_id_fkey" FOREIGN KEY (region_id) REFERENCES region(id);

alter table "public"."service_type_price_ceiling" add constraint "service_type_price_ceiling_service_type_id_fkey" FOREIGN KEY (service_type_id) REFERENCES service_type(id);

alter table "public"."service_type_price_ceiling" add constraint "service_type_price_ceiling_supplier_code_fkey" FOREIGN KEY (supplier_code) REFERENCES supplier(code);