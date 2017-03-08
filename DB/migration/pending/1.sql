alter table "public"."signed_agreement" drop constraint "signed_agreement_pkey";

drop index if exists "public"."signed_agreement_pkey";

alter table "public"."signed_agreement" alter column "signed_at" set not null;

CREATE UNIQUE INDEX signed_agreement_pkey ON signed_agreement USING btree (agreement_id, user_id, application_id, signed_at);

alter table "public"."signed_agreement" add constraint "signed_agreement_pkey" PRIMARY KEY using index "signed_agreement_pkey";
