alter table "public"."application" alter column "status" set data type varchar;

drop type "public"."application_status_enum";

create type "public"."application_status_enum" as enum ('saved', 'submitted', 'approved', 'complete', 'approval_rejected', 'assessment_rejected', 'deleted');

alter table "public"."application" alter column "status" set data type application_status_enum using "status"::application_status_enum;
