create view vuser as (
  select *, split_part(email_address, '@', 2) as email_domain from "user" u
);

create view govdomains as (
  select
    coalesce(c.domain, a.domain) as domain,
    coalesce(c.name, a.name) as name
  from
    council c
    full outer join agency a
      on c.domain = a.domain
  order by
    1, 2
);

create view users_with_briefs as (
  select
    u.id,
    u.name,
    u.email_address,
    u.email_domain,
    array_agg(b.id  order by b.data->>'title') as brief_ids,
    array_agg(b.data->>'title' order by b.data->>'title') as brief_titles
  from
    vuser u
    left outer join brief_user bu
      on bu.user_id = u.id
    left outer join brief b
      on bu.brief_id = b.id
  group by
    u.id,
    u.name,
    u.email_address,
    u.email_domain
  order by
    1, 2
);
