alter table "public"."brief_response" add column "withdrawn_at" timestamp without time zone;

CREATE INDEX ix_brief_response_withdrawn_at ON brief_response USING btree (withdrawn_at);