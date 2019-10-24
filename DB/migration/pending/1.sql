create sequence if not exists "public"."insight_id_seq";

create table if not exists "public"."insight" (
    "id" integer not null default nextval('insight_id_seq'::regclass),
    "data" json,
    "published_at" timestamp without time zone not null,
    "active" boolean not null,
    constraint "insight_pkey" PRIMARY KEY (id)
);

alter table "public"."insight" drop constraint "insight_pkey";
CREATE UNIQUE INDEX if not exists insight_pkey ON public.insight USING btree (id);
alter table "public"."insight" add constraint "insight_pkey" PRIMARY KEY using index "insight_pkey";