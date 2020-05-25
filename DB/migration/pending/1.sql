drop view if exists "public"."vuser" cascade;

alter table "public"."user" alter column "role" set data type varchar;

drop type "public"."user_roles_enum";

create type "public"."user_roles_enum" as enum ('buyer', 'supplier', 'admin', 'assessor', 'admin-ccs-category', 'admin-ccs-sourcing', 'applicant');

alter table "public"."user" alter column "role" set data type user_roles_enum using "role"::user_roles_enum;

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