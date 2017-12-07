create table "public"."user_framework" (
    "user_id" bigint not null,
    "framework_id" integer not null
);

CREATE UNIQUE INDEX user_framework_pkey ON user_framework USING btree (user_id, framework_id);

alter table "public"."user_framework" add constraint "user_framework_pkey" PRIMARY KEY using index "user_framework_pkey";

alter table "public"."user_framework" add constraint "user_framework_framework_id_fkey" FOREIGN KEY (framework_id) REFERENCES framework(id);

alter table "public"."user_framework" add constraint "user_framework_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id);
