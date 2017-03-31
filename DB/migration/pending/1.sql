create sequence "public"."agency_id_seq";

create sequence "public"."assessment_id_seq";

create sequence "public"."council_id_seq";

alter table "public"."alembic_version" drop constraint "alembic_version_pkc";

drop index if exists "public"."alembic_version_pkc";

drop table "public"."alembic_version";

create table "public"."agency" (
    "id" integer not null default nextval('agency_id_seq'::regclass),
    "name" character varying,
    "domain" character varying not null,
    "category" character varying,
    "state" character varying
);


create table "public"."assessment" (
    "id" integer not null default nextval('assessment_id_seq'::regclass),
    "created_at" timestamp without time zone not null,
    "supplier_domain_id" integer
);


create table "public"."brief_assessment" (
    "brief_id" integer not null,
    "assessment_id" integer not null
);


create table "public"."council" (
    "id" integer not null default nextval('council_id_seq'::regclass),
    "name" character varying,
    "domain" character varying not null,
    "home_page" character varying
);


alter table "public"."application" alter column "status" set data type varchar;

drop type "public"."application_status_enum";

create type "public"."application_status_enum" as enum ('saved', 'submitted', 'approved', 'complete', 'approval_rejected', 'assessment_rejected', 'deleted');

alter table "public"."application" alter column "status" set data type application_status_enum using "status"::application_status_enum;

create view "public"."govdomains" as  SELECT COALESCE(c.domain, a.domain) AS domain,
    COALESCE(c.name, a.name) AS name
   FROM (council c
     FULL JOIN agency a ON (((c.domain)::text = (a.domain)::text)))
  ORDER BY COALESCE(c.domain, a.domain), COALESCE(c.name, a.name);


create view "public"."users_with_briefs" as  SELECT u.id,
    u.name,
    u.email_address,
    u.email_domain,
    array_agg(b.id ORDER BY (b.data ->> 'title'::text)) AS brief_ids,
    array_agg((b.data ->> 'title'::text) ORDER BY (b.data ->> 'title'::text)) AS brief_titles
   FROM ((vuser u
     LEFT JOIN brief_user bu ON ((bu.user_id = u.id)))
     LEFT JOIN brief b ON ((bu.brief_id = b.id)))
  GROUP BY u.id, u.name, u.email_address, u.email_domain
  ORDER BY u.id, u.name;


CREATE UNIQUE INDEX agency_pkey ON agency USING btree (id);

CREATE UNIQUE INDEX assessment_pkey ON assessment USING btree (id);

CREATE UNIQUE INDEX brief_assessment_pkey ON brief_assessment USING btree (brief_id, assessment_id);

CREATE UNIQUE INDEX council_pkey ON council USING btree (id);

CREATE UNIQUE INDEX ix_agency_domain ON agency USING btree (domain);

CREATE INDEX ix_assessment_created_at ON assessment USING btree (created_at);

CREATE UNIQUE INDEX ix_council_domain ON council USING btree (domain);

alter table "public"."agency" add constraint "agency_pkey" PRIMARY KEY using index "agency_pkey";

alter table "public"."assessment" add constraint "assessment_pkey" PRIMARY KEY using index "assessment_pkey";

alter table "public"."brief_assessment" add constraint "brief_assessment_pkey" PRIMARY KEY using index "brief_assessment_pkey";

alter table "public"."council" add constraint "council_pkey" PRIMARY KEY using index "council_pkey";

alter table "public"."assessment" add constraint "assessment_supplier_domain_id_fkey" FOREIGN KEY (supplier_domain_id) REFERENCES supplier_domain(id);

alter table "public"."brief_assessment" add constraint "brief_assessment_assessment_id_fkey" FOREIGN KEY (assessment_id) REFERENCES assessment(id);

alter table "public"."brief_assessment" add constraint "brief_assessment_brief_id_fkey" FOREIGN KEY (brief_id) REFERENCES brief(id);
