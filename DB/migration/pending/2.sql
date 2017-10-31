alter table "public"."service_type_price" alter column "date_from" set data type date;

alter table "public"."service_type_price" alter column "date_to" set not null;

alter table "public"."service_type_price" alter column "date_to" set data type date;