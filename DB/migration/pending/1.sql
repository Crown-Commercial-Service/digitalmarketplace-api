alter table "public"."signed_agreement" drop constraint "signed_agreement_agreement_id_fkey";

alter table "public"."signed_agreement" drop constraint "signed_agreement_application_id_fkey";

alter table "public"."signed_agreement" drop constraint "signed_agreement_user_id_fkey";

alter table "public"."signed_agreement" drop constraint "signed_agreement_pkey";

drop index if exists "public"."signed_agreement_pkey";

alter table "public"."signed_agreement" add column "supplier_code" integer;

alter table "public"."signed_agreement" alter column "application_id" drop not null;

CREATE UNIQUE INDEX signed_agreement_pkey ON signed_agreement USING btree (agreement_id, user_id, signed_at);

alter table "public"."signed_agreement" add constraint "signed_agreement_pkey" PRIMARY KEY using index "signed_agreement_pkey";

alter table "public"."signed_agreement" add constraint "signed_agreement_supplier_code_fkey" FOREIGN KEY (supplier_code) REFERENCES supplier(code);

alter table "public"."signed_agreement" add constraint "signed_agreement_agreement_id_fkey" FOREIGN KEY (agreement_id) REFERENCES agreement(id);

alter table "public"."signed_agreement" add constraint "signed_agreement_application_id_fkey" FOREIGN KEY (application_id) REFERENCES application(id);

alter table "public"."signed_agreement" add constraint "signed_agreement_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id);