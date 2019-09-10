create sequence if not exists "public"."agency_domain_id_seq";

create table if not exists "public"."agency_domain" (
    "id" integer not null default nextval('agency_domain_id_seq'::regclass),
    "agency_id" integer not null,
    "domain" character varying not null,
    "active" boolean not null,
    constraint "agency_domain_pkey" PRIMARY KEY (id),
    constraint "agency_domain_agency_id_fkey" FOREIGN KEY (agency_id) 
        REFERENCES public.agency(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE UNIQUE INDEX if not exists agency_domain_pkey ON public.agency_domain USING btree (id);

CREATE UNIQUE INDEX if not exists ix_agency_domain_domain ON public.agency_domain USING btree (domain);

insert into agency_domain (agency_id, domain, active)
select a.id "agency_id", a.domain, true
from agency a
left join agency_domain ad on ad.agency_id != a.id
where ad.domain is null;


drop view if exists "public"."vuser" cascade;

alter table "public"."user" add column if not exists "agency_id" bigint;

create view "public"."vuser" as  SELECT u.id,
    u.name,
    u.email_address,
    u.phone_number,
    u.password,
    u.active,
    u.created_at,
    u.updated_at,
    u.password_changed_at,
    u.logged_in_at,
    u.terms_accepted_at,
    u.failed_login_count,
    u.role,
    u.supplier_code,
    u.application_id,
    u.agency_id,
    split_part((u.email_address)::text, '@'::text, 2) AS email_domain
   FROM "user" u;


CREATE INDEX if not exists ix_user_agency_id ON public."user" USING btree (agency_id);

ALTER TABLE "public"."user" DROP CONSTRAINT IF EXISTS "user_agency_id_fkey";
alter table "public"."user" add constraint "user_agency_id_fkey" FOREIGN KEY (agency_id) REFERENCES agency(id);

update "user" u
set agency_id = a.id
from (
    select u.id "user_id", split_part((u.email_address)::text, '@'::text, 2) "domain"
    from "user" u
    where u.role = 'buyer'
) r
inner join agency a on a.domain = r.domain
where r.user_id = u.id
and u.agency_id is null;

drop view if exists govdomains;

drop view if exists vuser_users_with_briefs;
