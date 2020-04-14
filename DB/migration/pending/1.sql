CREATE SEQUENCE IF NOT EXISTS "public"."brief_history_id_seq";

CREATE TABLE IF NOT EXISTS "public"."brief_history" (
    "id" INTEGER NOT NULL default nextval('brief_history_id_seq'::regclass),
    "brief_id" INTEGER NOT NULL,
    "user_id" INTEGER NOT NULL,
    "edited_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    "data" JSON NOT NULL,
    CONSTRAINT "brief_history_pkey" PRIMARY KEY (id),
    CONSTRAINT "brief_history_brief_id_fkey" FOREIGN KEY (brief_id)
        REFERENCES public.brief(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT "brief_history_user_id_fkey" FOREIGN KEY (user_id)
        REFERENCES public."user"(id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE unique index IF NOT EXISTS brief_history_pkey ON public.brief_history USING btree (id);
CREATE index IF NOT EXISTS ix_brief_history_brief_id ON public.brief_history USING btree (brief_id);
CREATE index IF NOT EXISTS ix_brief_history_user_id ON public.brief_history USING btree (user_id);
CREATE index IF NOT EXISTS ix_brief_history_edited_at ON public.brief_history USING btree (edited_at);
