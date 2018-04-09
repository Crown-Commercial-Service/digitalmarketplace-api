alter table "public"."brief_response" add column "withdrawn_at" timestamp without time zone;

CREATE INDEX ix_brief_response_withdrawn_at ON brief_response USING btree (withdrawn_at);

alter table "public"."domain" add column "price_minimum" numeric null;

alter table "public"."domain" add column "price_maximum" numeric null;

update domain set price_minimum = 0, price_maximum = 10000;

alter table "public"."domain" alter column "price_maximum" set not null;

alter table "public"."domain" alter column "price_minimum" set not null;
