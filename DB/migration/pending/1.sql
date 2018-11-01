DO $$
BEGIN
    DROP TABLE IF EXISTS "public"."region" CASCADE;
    DROP TABLE IF EXISTS "public"."location" CASCADE;
    DROP TABLE IF EXISTS "public"."service_sub_type" CASCADE;
    DROP TABLE IF EXISTS "public"."service_type" CASCADE;
    DROP TABLE IF EXISTS "public"."service_type_price" CASCADE;
    DROP TABLE IF EXISTS "public"."service_type_price_ceiling" CASCADE;

    DROP SEQUENCE IF EXISTS "public"."location_id_seq";
    DROP SEQUENCE IF EXISTS "public"."region_id_seq";
    DROP SEQUENCE IF EXISTS "public"."service_sub_type_id_seq";
    DROP SEQUENCE IF EXISTS "public"."service_type_id_seq";
    DROP SEQUENCE IF EXISTS "public"."service_type_price_ceiling_id_seq";
    DROP SEQUENCE IF EXISTS "public"."service_type_price_id_seq";
END$$;
