update briefs set closed_at = published_at + interval '1 week' where data->'requirementsPeriod' = '1 week';
update briefs set closed_at = published_at + interval '2 weeks' where data->'requirementsPeriod' = '2 week';

update briefs set questions_closed_at = published_at + interval '2 days' where data->'requirementsPeriod' = '1 week';
update briefs set questions_closed_at = published_at + interval '5 days' where data->'requirementsPeriod' = '2 week';