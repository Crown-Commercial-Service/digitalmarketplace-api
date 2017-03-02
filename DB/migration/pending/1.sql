create sequence "public"."recruiter_info_id_seq";

create table "public"."recruiter_info" (
    "id" integer not null default nextval('recruiter_info_id_seq'::regclass),
    "active_candidates" character varying not null,
    "database_size" character varying not null,
    "placed_candidates" character varying not null,
    "margin" character varying not null,
    "markup" character varying not null
);


alter table "public"."supplier_domain" add column "recruiter_info_id" integer;

CREATE UNIQUE INDEX recruiter_info_pkey ON recruiter_info USING btree (id);

alter table "public"."recruiter_info" add constraint "recruiter_info_pkey" PRIMARY KEY using index "recruiter_info_pkey";

alter table "public"."supplier_domain" add constraint "supplier_domain_recruiter_info_id_fkey" FOREIGN KEY (recruiter_info_id) REFERENCES recruiter_info(id);
