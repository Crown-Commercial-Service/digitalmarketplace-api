create view vuser as (
  select *, split_part(email_address, '@', 2) as email_domain from "user" u
);
