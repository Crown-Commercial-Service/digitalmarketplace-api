DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'permission_type_enum') THEN
        create type "public"."permission_type_enum" as enum ('create_drafts', 'publish_opportunities', 'answer_seller_questions', 'download_responses', 'create_work_orders');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'team_status_enum') THEN
        create type "public"."team_status_enum" as enum ('created', 'completed', 'deleted');
    END IF;
END$$;

create sequence if not exists "public"."brief_question_id_seq";

create sequence if not exists "public"."brief_response_download_id_seq";

create sequence if not exists "public"."team_id_seq";

create sequence if not exists "public"."team_brief_id_seq";

create sequence if not exists "public"."team_member_id_seq";

create sequence if not exists "public"."team_member_permission_id_seq";

create table if not exists "public"."brief_question" (
    "id" integer not null default nextval('brief_question_id_seq'::regclass),
    "brief_id" integer not null,
    "supplier_code" bigint not null,
    "data" json not null,
    "answered" boolean not null,
    "created_at" timestamp without time zone not null,
    constraint "brief_question_pkey" PRIMARY KEY (id),
    constraint "brief_question_brief_id_fkey" FOREIGN KEY (brief_id) 
        REFERENCES public.brief(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    constraint "brief_question_supplier_code_fkey" FOREIGN KEY (supplier_code)
        REFERENCES public.supplier(code) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


create table if not exists "public"."team" (
    "id" integer not null default nextval('team_id_seq'::regclass),
    "name" character varying not null,
    "email_address" character varying,
    "status" team_status_enum not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null,
    constraint "team_pkey" PRIMARY KEY ("id")
);

create table if not exists "public"."team_member" (
    "id" integer not null default nextval('team_member_id_seq'::regclass),
    "is_team_lead" boolean not null,
    "team_id" integer not null,
    "user_id" integer not null,
    "updated_at" timestamp without time zone not null,
    constraint "team_member_pkey" PRIMARY KEY ("id"),
    constraint "team_member_team_id_fkey" FOREIGN KEY (team_id)
        REFERENCES public.team(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    constraint "team_member_user_id_fkey" FOREIGN KEY (user_id)
        REFERENCES public."user"(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE UNIQUE INDEX if not exists evidence_pkey ON evidence USING btree (id);

create table if not exists "public"."team_member_permission" (
    "id" integer not null default nextval('team_member_permission_id_seq'::regclass),
    "team_member_id" integer not null,
    "permission" permission_type_enum not null,
    constraint "team_member_permission_pkey" PRIMARY KEY ("id"),
    constraint "team_member_permission_team_member_id_fkey" FOREIGN KEY (team_member_id)
        REFERENCES public.team_member(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE INDEX if not exists ix_brief_question_created_at ON public.brief_question USING btree (created_at);

CREATE INDEX if not exists ix_team_member_permission_permission ON public.team_member_permission USING btree (permission);

alter table "public"."brief_clarification_question" add column if not exists "user_id" integer;

update brief_clarification_question bcq
set user_id = bu.user_id
from brief_user bu
where bcq.brief_id = bu.brief_id
and bcq.user_id is null;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'brief_clarification_question_user_id_fkey') THEN
        alter table "public"."brief_clarification_question" add constraint "brief_clarification_question_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id);
    END IF;
END$$;

alter table "public"."brief_clarification_question" alter column "user_id" set not null;


create table if not exists "public"."brief_response_download" (
    "id" integer not null default nextval('brief_response_download_id_seq'::regclass),
    "brief_id" integer not null,
    "user_id" integer not null,
    "created_at" timestamp without time zone not null,
    constraint "brief_response_download_pkey" PRIMARY KEY ("id"),
    constraint "brief_response_download_brief_id_fkey" FOREIGN KEY (brief_id)
        REFERENCES public.brief(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    constraint "brief_response_download_user_id_fkey" FOREIGN KEY (user_id)
        REFERENCES public."user"(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE INDEX if not exists ix_brief_response_download_created_at ON public.brief_response_download USING btree (created_at);


create table if not exists "public"."team_brief" (
    "id" integer not null default nextval('team_brief_id_seq'::regclass),
    "team_id" integer not null,
    "brief_id" integer not null,
    "user_id" integer not null,
    constraint "team_brief_pkey" PRIMARY KEY ("id"),
    constraint "team_brief_brief_id_fkey" FOREIGN KEY (brief_id)
        REFERENCES public.brief(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    constraint "team_brief_user_id_fkey" FOREIGN KEY (user_id)
        REFERENCES public."user"(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    constraint "team_brief_team_id_fkey" FOREIGN KEY (team_id)
        REFERENCES public."team"(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);
