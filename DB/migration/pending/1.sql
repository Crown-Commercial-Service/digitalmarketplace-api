DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'case_study_status_enum') THEN

        create type "public"."case_study_status_enum" as enum ('unassessed', 'approved', 'rejected');

        alter table "public"."case_study" add column "status" case_study_status_enum null;

        update "public"."case_study" set status = 'unassessed';

        ALTER TABLE "public"."case_study" ALTER COLUMN status SET NOT NULL;
    END IF;
END$$;
