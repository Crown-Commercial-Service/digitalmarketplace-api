create sequence if not exists "public"."master_agreement_id_seq";

create table if not exists "public"."master_agreement" (
    "id" integer not null default nextval('master_agreement_id_seq'::regclass),
    "start_date" timestamp without time zone not null,
    "end_date" timestamp without time zone not null,
    data json,
    constraint "master_agreement_pkey" PRIMARY KEY (id)
);

create unique index if not exists master_agreement_pkey ON public.master_agreement using btree (id);

insert into master_agreement (id, start_date, end_date, data)
select *
from json_to_recordset(
	(
		select 
			json_agg(
				json_build_object(
					'id', q.key,
					'start_date', q.value -> 'startDate',
					'end_date', q.value -> 'endDate',
					-- will clean up any keys that are not html or pdf urls manually
					'data', q.value
				)
			) "agreements"
		from (
			select 
				agreements.key as key,
				agreements.value as value
			from 
				key_value kv,
				json_each(kv.data) "agreements"
			where 
				kv.key = 'current_master_agreement'
		) q
	)
) as cols("id" int, "start_date" timestamp without time zone, "end_date" timestamp without time zone, "data" json);

alter table signed_agreement drop constraint if exists signed_agreement_agreement_id_fkey;

alter table signed_agreement add constraint signed_agreement_agreement_id_fkey foreign key (agreement_id) references master_agreement (id);

drop table if exists agreement;

do $$
begin
    if exists (select id from key_value where key = 'old_agreements') then
        delete from key_value where key = 'old_agreements';
    end if;

	if exists (select id from key_value where key = 'current_master_agreement') then
        delete from key_value where key = 'current_master_agreement';
    end if;
end
$$;
