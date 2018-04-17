CREATE TYPE state_enum AS ENUM (
  'ACT',
  'NSW',
  'NT', 
  'QLD',
  'SA',
  'TAS',
  'VIC',
  'WA');

alter table "public"."agency" alter column "whitelisted" set not null;
alter table "public"."agency" alter column "name" set not null;
alter table "public"."agency" alter column state type state_enum using state::state_enum;