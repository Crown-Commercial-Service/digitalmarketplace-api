DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_claim_type_enum') THEN
        create type "public"."user_claim_type_enum" as enum ('signup', 'password_reset');
END IF;
END$$;

create sequence "public"."user_claim_id_seq";

create table "public"."user_claim" (
    "id" integer not null default nextval('user_claim_id_seq'::regclass),
    "email_address" character varying not null,
    "token" character varying not null,
    "data" json,
    "claimed" boolean not null,
    "created_at" timestamp without time zone not null,
    "updated_at" timestamp without time zone not null,
    "type" user_claim_type_enum not null
);


CREATE INDEX ix_user_claim_email_address ON user_claim USING btree (email_address);

CREATE INDEX ix_user_claim_token ON user_claim USING btree (token);

CREATE INDEX ix_user_claim_type ON user_claim USING btree (type);

CREATE UNIQUE INDEX user_claim_pkey ON user_claim USING btree (id);

alter table "public"."user_claim" add constraint "user_claim_pkey" PRIMARY KEY using index "user_claim_pkey";