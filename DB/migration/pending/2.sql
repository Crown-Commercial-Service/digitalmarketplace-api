create sequence "public"."assessment_id_seq";

create table "public"."assessment" (
    "id" integer not null default nextval('assessment_id_seq'::regclass),
    "created_at" timestamp without time zone not null,
    "supplier_domain_id" integer
);


create table "public"."brief_assessment" (
    "brief_id" integer not null,
    "assessment_id" integer not null
);


CREATE UNIQUE INDEX assessment_pkey ON assessment USING btree (id);

CREATE UNIQUE INDEX brief_assessment_pkey ON brief_assessment USING btree (brief_id, assessment_id);

CREATE INDEX ix_assessment_created_at ON assessment USING btree (created_at);

alter table "public"."assessment" add constraint "assessment_pkey" PRIMARY KEY using index "assessment_pkey";

alter table "public"."brief_assessment" add constraint "brief_assessment_pkey" PRIMARY KEY using index "brief_assessment_pkey";

alter table "public"."assessment" add constraint "assessment_supplier_domain_id_fkey" FOREIGN KEY (supplier_domain_id) REFERENCES supplier_domain(id);

alter table "public"."brief_assessment" add constraint "brief_assessment_assessment_id_fkey" FOREIGN KEY (assessment_id) REFERENCES assessment(id);

alter table "public"."brief_assessment" add constraint "brief_assessment_brief_id_fkey" FOREIGN KEY (brief_id) REFERENCES brief(id);
