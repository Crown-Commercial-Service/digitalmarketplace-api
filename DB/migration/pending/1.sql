alter table "public"."brief_response" add column "submitted_at" timestamp without time zone;

alter table "public"."brief_response" add column "updated_at" timestamp without time zone;

CREATE INDEX ix_brief_response_submitted_at ON brief_response USING btree (submitted_at);

CREATE INDEX ix_brief_response_updated_at ON brief_response USING btree (updated_at);

UPDATE brief_response SET updated_at = created_at WHERE updated_at IS NULL;

UPDATE brief_response SET submitted_at = created_at WHERE submitted_at IS NULL;

alter table "public"."brief_response" alter column "updated_at" set not null;