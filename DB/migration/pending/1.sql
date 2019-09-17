alter table "public"."team_member_permission" alter column "permission" set data type varchar;

drop type "public"."permission_type_enum";

create type "public"."permission_type_enum" as enum ('create_drafts', 'publish_opportunities', 'answer_seller_questions', 'download_responses', 'download_reports', 'create_work_orders');

alter table "public"."team_member_permission" alter column "permission" set data type permission_type_enum using "permission"::permission_type_enum;

