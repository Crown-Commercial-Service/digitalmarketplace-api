create sequence "public"."service_type_id_seq";

create table "public"."service_type" (
    "id" integer not null default nextval('service_type_id_seq'::regclass),
    "category_id" integer not null,
    "name" character varying not null,
    "framework_id" bigint not null,
    "lot_id" bigint not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null
);


CREATE INDEX ix_service_type_framework_id ON service_type USING btree (framework_id);

CREATE INDEX ix_service_type_lot_id ON service_type USING btree (lot_id);

CREATE UNIQUE INDEX service_type_pkey ON service_type USING btree (id);

alter table "public"."service_type" add constraint "service_type_pkey" PRIMARY KEY using index "service_type_pkey";

alter table "public"."service_type" add constraint "service_type_category_id_fkey" FOREIGN KEY (category_id) REFERENCES service_category(id);

alter table "public"."service_type" add constraint "service_type_framework_id_fkey" FOREIGN KEY (framework_id) REFERENCES framework(id);

alter table "public"."service_type" add constraint "service_type_lot_id_fkey" FOREIGN KEY (lot_id) REFERENCES lot(id);

create sequence "public"."location_id_seq";

create sequence "public"."region_id_seq";

create table "public"."location" (
    "id" integer not null default nextval('location_id_seq'::regclass),
    "region_id" integer not null,
    "name" character varying not null,
    "state" character varying not null,
    "postal_code" integer not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null
);


create table "public"."region" (
    "id" integer not null default nextval('region_id_seq'::regclass),
    "name" character varying not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null
);


CREATE UNIQUE INDEX location_pkey ON location USING btree (id);

CREATE UNIQUE INDEX region_pkey ON region USING btree (id);

alter table "public"."location" add constraint "location_pkey" PRIMARY KEY using index "location_pkey";

alter table "public"."region" add constraint "region_pkey" PRIMARY KEY using index "region_pkey";

alter table "public"."location" add constraint "location_region_id_fkey" FOREIGN KEY (region_id) REFERENCES region(id);

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
