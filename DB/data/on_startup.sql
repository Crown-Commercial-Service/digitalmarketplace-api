delete from domain where name ~* 'Digital products';

insert into domain(id, name, ordering) values
  (1, 'Strategy and Policy',                          1),
  (2, 'Change, Training and Transformation',          7),
  (3, 'User research and Design',                     2),
  (4, 'Agile delivery and Governance',                3),
  (5, 'Recruitment',                                  12),
  (6, 'Software engineering and Development',         4),
  (7, 'Content and Publishing',                       6),
  (8, 'Cyber security',                               9),
  (9, 'Marketing, Communications and Engagement',     8),
  (10, 'Support and Operations',                      5),
  (11, 'Data science',                                10),
  (13, 'Emerging technology',                         11)
on conflict(id) do update set name = excluded.name, ordering = excluded.ordering;
