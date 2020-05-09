-- adding the must_join_team flag for agencies

alter table "public"."agency" add column "must_join_team" boolean;

update agency set must_join_team = false;

alter table "public"."agency" alter column "must_join_team" set not null;

-- adding the join_team claim type

alter table "public"."user_claim" alter column "type" set data type varchar;

drop type "public"."user_claim_type_enum";

create type "public"."user_claim_type_enum" as enum ('signup', 'password_reset', 'join_team');

alter table "public"."user_claim" alter column "type" set data type user_claim_type_enum using "type"::user_claim_type_enum;
