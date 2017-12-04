update brief set closed_at = published_at + interval '1 week' where data->>'requirementsLength' = '1 week';
update brief set closed_at = published_at + interval '2 weeks' where data->>'requirementsLength' = '2 weeks';

update brief set questions_closed_at = published_at + interval '2 days' where data->>'requirementsLength' = '1 week';
update brief set questions_closed_at = published_at + interval '5 days' where data->>'requirementsLength' = '2 weeks';