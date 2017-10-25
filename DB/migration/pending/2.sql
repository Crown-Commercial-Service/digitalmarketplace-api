alter table "public"."service_type_price" add column "service_type_price_ceiling_id" integer;

alter table "public"."service_type_price" add constraint "service_type_price_service_type_price_ceiling_id_fkey" FOREIGN KEY (service_type_price_ceiling_id) REFERENCES service_type_price_ceiling(id);