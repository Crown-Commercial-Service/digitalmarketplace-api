create type "public"."project_status_enum" as enum ('draft', 'published');

create sequence "public"."project_id_seq";

create table "public"."project" (
  "id" integer not null default nextval('project_id_seq'::regclass),
  "data" json not null,
  "status" project_status_enum not null,
  "created_at" timestamp without time zone not null
);

CREATE INDEX ix_project_created_at ON project USING btree (created_at);

CREATE UNIQUE INDEX project_pkey ON project USING btree (id);

alter table "public"."project" add constraint "project_pkey" PRIMARY KEY using index "project_pkey";
