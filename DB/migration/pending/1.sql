alter table "public"."domain" add column if not exists "criteria_needed" numeric;

UPDATE "public"."domain" SET "criteria_needed" = 2 WHERE "name" = 'Strategy and Policy';
UPDATE "public"."domain" SET "criteria_needed" = 3 WHERE "name" = 'User research and Design';
UPDATE "public"."domain" SET "criteria_needed" = 2 WHERE "name" = 'Agile delivery and Governance';
UPDATE "public"."domain" SET "criteria_needed" = 3 WHERE "name" = 'Software engineering and Development';
UPDATE "public"."domain" SET "criteria_needed" = 3 WHERE "name" = 'Support and Operations';
UPDATE "public"."domain" SET "criteria_needed" = 2 WHERE "name" = 'Content and Publishing';
UPDATE "public"."domain" SET "criteria_needed" = 3 WHERE "name" = 'Training, Learning and Development';
UPDATE "public"."domain" SET "criteria_needed" = 2 WHERE "name" = 'Change and Transformation';
UPDATE "public"."domain" SET "criteria_needed" = 1 WHERE "name" = 'Marketing, Communications and Engagement';
UPDATE "public"."domain" SET "criteria_needed" = 1 WHERE "name" = 'Cyber security';
UPDATE "public"."domain" SET "criteria_needed" = 1 WHERE "name" = 'Data science';
UPDATE "public"."domain" SET "criteria_needed" = 1 WHERE "name" = 'Emerging technologies';
UPDATE "public"."domain" SET "criteria_needed" = 2 WHERE "name" = 'Change, Training and Transformation';

alter table "public"."domain" alter column "criteria_needed" set not null;

-- domain_criteria

create sequence if not exists "public"."domain_criteria_id_seq";

create table if not exists "public"."domain_criteria" (
    "id" integer not null default nextval('domain_criteria_id_seq'::regclass),
    "name" character varying not null,
    "domain_id" integer not null,
    CONSTRAINT domain_criteria_pkey PRIMARY KEY (id),
    CONSTRAINT domain_criteria_domain_id_fkey FOREIGN KEY (domain_id)
        REFERENCES public.domain (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- evidence

create sequence if not exists "public"."evidence_id_seq";

create table if not exists "public"."evidence" (
    "id" integer not null default nextval('evidence_id_seq'::regclass),
    "domain_id" integer not null,
    "brief_id" integer,
    "user_id" integer not null,
    "supplier_code" bigint not null,
    "data" json,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null,
    "submitted_at" timestamp without time zone,
    "approved_at" timestamp without time zone,
    "rejected_at" timestamp without time zone,
    CONSTRAINT evidence_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_domain_id_fkey FOREIGN KEY (domain_id)
        REFERENCES public.domain (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT evidence_brief_id_fkey FOREIGN KEY (brief_id)
        REFERENCES public.brief (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT evidence_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.user (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT evidence_supplier_code_fkey FOREIGN KEY (supplier_code)
        REFERENCES public.supplier (code) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE UNIQUE INDEX if not exists evidence_pkey ON evidence USING btree (id);

CREATE INDEX if not exists ix_evidence_approved_at ON evidence USING btree (approved_at);

CREATE INDEX if not exists ix_evidence_created_at ON evidence USING btree (created_at);

CREATE INDEX if not exists ix_evidence_submitted_at ON evidence USING btree (submitted_at);

CREATE INDEX if not exists ix_evidence_updated_at ON evidence USING btree (updated_at);

CREATE INDEX if not exists ix_evidence_rejected_at ON evidence USING btree (rejected_at);

-- evidence_assessment

create type "public"."evidence_assessment_status_enum" as enum ('approved', 'rejected');

create sequence "public"."evidence_assessment_id_seq";

create table "public"."evidence_assessment" (
    "id" integer not null default nextval('evidence_assessment_id_seq'::regclass),
    "evidence_id" integer not null,
    "user_id" integer not null,
    "created_at" timestamp without time zone not null,
    "status" evidence_assessment_status_enum not null,
    "data" json,
    CONSTRAINT evidence_assessment_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_assessment_evidence_id_fkey FOREIGN KEY (evidence_id)
        REFERENCES public.evidence (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT evidence_assessment_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.user (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE INDEX ix_evidence_assessment_created_at ON evidence_assessment USING btree (created_at);
