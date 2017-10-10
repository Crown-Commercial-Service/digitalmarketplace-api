insert into service_category (name, abbreviation, id) values ('Rehabilitation', 'Rehabilitation', 10);
insert into service_category (name, abbreviation, id) values ('Medical', 'Medical', 11);
insert into lot (slug, name, one_service_limit, id) values ('orams', 'orams', 'f', 11);
insert into framework (slug, name, framework, status, clarification_questions_open, id) values ('orams', 'orams', 'orams', 'open', 'f', 8);
insert into framework_lot (framework_id, lot_id) values (8,11);