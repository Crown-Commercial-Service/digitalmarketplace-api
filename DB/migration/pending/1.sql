create sequence "public"."brief_assessor_id_seq";

create table "public"."brief_assessor" (
    "id" integer not null default nextval('brief_assessor_id_seq'::regclass),
    "brief_id" integer not null,
    "user_id" integer,
    "email_address" character varying
);

CREATE UNIQUE INDEX brief_assessor_pkey ON brief_assessor USING btree (id);

alter table "public"."brief_assessor" add constraint "brief_assessor_pkey" PRIMARY KEY using index "brief_assessor_pkey";

alter table "public"."brief_assessor" add constraint "brief_assessor_brief_id_fkey" FOREIGN KEY (brief_id) REFERENCES brief(id);

alter table "public"."brief_assessor" add constraint "brief_assessor_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id);
