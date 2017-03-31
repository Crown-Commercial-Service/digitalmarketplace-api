drop view if exists "public"."users_with_briefs" cascade;

create view "public"."vuser_users_with_briefs" as  SELECT u.id,
    u.name,
    u.email_address,
    u.email_domain,
    array_agg(b.id ORDER BY (b.data ->> 'title'::text)) AS brief_ids,
    array_agg((b.data ->> 'title'::text) ORDER BY (b.data ->> 'title'::text)) AS brief_titles
   FROM ((vuser u
     LEFT JOIN brief_user bu ON ((bu.user_id = u.id)))
     LEFT JOIN brief b ON ((bu.brief_id = b.id)))
  GROUP BY u.id, u.name, u.email_address, u.email_domain
  ORDER BY u.id, u.name;
