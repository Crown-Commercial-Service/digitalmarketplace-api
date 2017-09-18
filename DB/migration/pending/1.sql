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