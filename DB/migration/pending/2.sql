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