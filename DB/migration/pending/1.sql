create sequence if not exists "public"."api_key_id_seq";

create table "public"."api_key" (
    "id" integer not null default nextval('api_key_id_seq'::regclass),
    "user_id" integer not null,
    "key" character varying(64) not null,
    "created_at" timestamp without time zone not null,
    "revoked_at" timestamp without time zone
);


CREATE UNIQUE INDEX api_key_pkey ON api_key USING btree (id);

CREATE UNIQUE INDEX ix_api_key_key ON api_key USING btree (key);

CREATE INDEX ix_api_key_created_at ON api_key USING btree (created_at);

CREATE INDEX ix_api_key_revoked_at ON api_key USING btree (revoked_at);

CREATE INDEX ix_api_key_user_id ON api_key USING btree (user_id);

alter table "public"."api_key" add constraint "api_key_pkey" PRIMARY KEY using index "api_key_pkey";

alter table "public"."api_key" add constraint "api_key_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id);

alter table "public"."api_key" add constraint "key_min_length" CHECK ((char_length((key)::text) > 63));
