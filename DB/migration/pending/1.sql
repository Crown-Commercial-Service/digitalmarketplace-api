alter table "public"."brief" add column "closed_at" timestamp without time zone;

alter table "public"."brief" add column "questions_closed_at" timestamp without time zone;

CREATE INDEX ix_brief_closed_at ON brief USING btree (closed_at);

CREATE INDEX ix_brief_questions_closed_at ON brief USING btree (questions_closed_at);
