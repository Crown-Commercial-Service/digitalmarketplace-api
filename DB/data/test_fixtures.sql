--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.1
-- Dumped by pg_dump version 9.6.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET search_path = public, pg_catalog;

--
-- Data for Name: address; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: address_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('address_id_seq', 1, false);


--
-- Data for Name: agreement; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: agreement_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('agreement_id_seq', 1, false);


--
-- Data for Name: supplier; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: application; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: application_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('application_id_seq', 1, false);


--
-- Data for Name: framework; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (1, 'g-cloud-6', 'G-Cloud 6', 'g-cloud', 'live', false, NULL);
INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (2, 'g-cloud-4', 'G-Cloud 4', 'g-cloud', 'expired', false, NULL);
INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (3, 'g-cloud-5', 'G-Cloud 5', 'g-cloud', 'live', false, NULL);
INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (4, 'g-cloud-7', 'G-Cloud 7', 'g-cloud', 'pending', false, NULL);
INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (5, 'digital-outcomes-and-specialists', 'Digital Outcomes and Specialists', 'dos', 'live', false, NULL);
INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (6, 'digital-service-professionals', 'Digital Service Professionals', 'dsp', 'live', false, NULL);
INSERT INTO framework (id, slug, name, framework, status, clarification_questions_open, framework_agreement_details) VALUES (7, 'digital-marketplace', 'Digital Marketplace', 'dm', 'pending', false, NULL);


--
-- Data for Name: lot; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (1, 'saas', 'Software as a Service', false, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (2, 'paas', 'Platform as a Service', false, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (3, 'iaas', 'Infrastructure as a Service', false, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (4, 'scs', 'Specialist Cloud Services', false, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (5, 'digital-outcomes', 'Digital outcomes', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (6, 'digital-specialists', 'Digital specialists', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (7, 'user-research-participants', 'User research participants', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (8, 'user-research-studios', 'User research studios', false, '{"unitSingular": "lab", "unitPlural": "labs"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (9, 'digital-professionals', 'Digital professionals', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (10, 'digital-outcome', 'Digital outcome', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (15, 'training', 'Training', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (16, 'rfx', 'RFX', true, '{"unitSingular": "service", "unitPlural": "services"}');


--
-- Data for Name: framework_lot; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO framework_lot (framework_id, lot_id) VALUES (1, 1);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (1, 2);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (1, 3);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (1, 4);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (2, 1);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (2, 2);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (2, 3);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (2, 4);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (3, 1);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (3, 2);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (3, 3);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (3, 4);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (4, 1);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (4, 2);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (4, 3);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (4, 4);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (5, 5);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (5, 6);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (5, 7);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (5, 8);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (6, 9);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (6, 10);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (7, 9);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (7, 10);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (7, 15);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (7, 16);


--
-- Data for Name: archived_service; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: archived_service_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('archived_service_id_seq', 1, false);


--
-- Data for Name: audit_event; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: audit_event_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('audit_event_id_seq', 1, false);


--
-- Data for Name: domain; Type: TABLE DATA; Schema: public; Owner: -
--
    
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (1, 'Strategy and Policy'                     , 1 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (2, 'Change, Training and Transformation'     , 2 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (3, 'User research and Design'                , 3 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (4, 'Agile delivery and Governance'           , 4 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (5, 'Recruitment'                             , 5 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (6, 'Software engineering and Development'    , 6 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (7, 'Content and Publishing'                  , 7 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (8, 'Cyber security'                          , 8 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (9, 'Marketing, Communications and Engagement', 9 , 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (10, 'Support and Operations'                 , 10, 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (11, 'Data science'                           , 11, 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (12, 'Digital products'                       , 12, 0, 10000);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum) VALUES (13, 'Emerging technology'                    , 13, 0, 10000);


--
-- Data for Name: brief; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: brief_clarification_question; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: brief_clarification_question_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('brief_clarification_question_id_seq', 1, false);


--
-- Name: brief_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('brief_id_seq', 1, false);


--
-- Data for Name: brief_response; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: brief_response_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('brief_response_id_seq', 1, false);


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: brief_user; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: case_study; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: case_study_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('case_study_id_seq', 1, false);


--
-- Data for Name: contact; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: contact_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('contact_id_seq', 1, false);


--
-- Name: domain_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('domain_id_seq', 13, true);


--
-- Data for Name: draft_service; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: draft_service_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('draft_service_id_seq', 1, false);


--
-- Name: framework_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('framework_id_seq', 8, true);


--
-- Name: lot_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('lot_id_seq', 11, true);


--
-- Data for Name: service_category; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO service_category (id, name, abbreviation) VALUES (1, 'Product Management', 'pm');
INSERT INTO service_category (id, name, abbreviation) VALUES (2, 'Business Analysis', 'ba');
INSERT INTO service_category (id, name, abbreviation) VALUES (3, 'Delivery Management and Agile Coaching', 'dm');
INSERT INTO service_category (id, name, abbreviation) VALUES (4, 'User Research', 'ur');
INSERT INTO service_category (id, name, abbreviation) VALUES (5, 'Service Design and Interaction Design', 'sd');
INSERT INTO service_category (id, name, abbreviation) VALUES (6, 'Technical Architecture, Development, Ethical Hacking and Web Operations', 'tech');
INSERT INTO service_category (id, name, abbreviation) VALUES (7, 'Performance and Web Analytics', 'wa');
INSERT INTO service_category (id, name, abbreviation) VALUES (8, 'Inclusive Design and Accessibility', 'acc');
INSERT INTO service_category (id, name, abbreviation) VALUES (9, 'Digital Transformation Advisers', 'dta');
INSERT INTO service_category (id, name, abbreviation) VALUES (10, 'Medical', 'Medical');
INSERT INTO service_category (id, name, abbreviation) VALUES (11, 'Rehabilitation', 'Rehabilitation');


--
-- Data for Name: service_role; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (11, 1, 'Junior Product Manager', 'pm-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (12, 1, 'Senior Product Manager', 'pm-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (21, 2, 'Junior Business Analyst', 'ba-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (22, 2, 'Senior Business Analyst', 'ba-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (31, 3, 'Junior Delivery Manager', 'dm-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (32, 3, 'Senior Delivery Manager', 'dm-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (33, 3, 'Senior Agile Coach', 'ac-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (41, 4, 'Senior User Research', 'ur-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (51, 5, 'Senior Service Designer', 'sd-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (52, 5, 'Junior Interaction Designer', 'id-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (53, 5, 'Senior Interaction Designer', 'id-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (61, 6, 'Senior Technical Lead', 'tl-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (62, 6, 'Junior Developer', 'dev-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (63, 6, 'Senior Developer', 'dev-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (64, 6, 'Junior Ethical Hacker', 'hack-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (65, 6, 'Senior Ethical Hacker', 'hack-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (66, 6, 'Junior Web Devops Engineer', 'devops-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (67, 6, 'Senior Web Devops Engineer', 'devops-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (71, 7, 'Junior Web Performance Analyst', 'wa-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (72, 7, 'Senior Web Performance Analyst', 'wa-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (81, 8, 'Junior Inclusive Designer (accessibility consultant)', 'id-j');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (82, 8, 'Senior Inclusive Designer (accessibility consultant)', 'id-s');
INSERT INTO service_role (id, category_id, name, abbreviation) VALUES (91, 9, 'Senior Digital Transformation Adviser', 'dta-s');


--
-- Data for Name: price_schedule; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: price_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('price_schedule_id_seq', 1, false);


--
-- Data for Name: service; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: service_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('service_category_id_seq', 1, false);


--
-- Name: service_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('service_id_seq', 1, false);


--
-- Name: service_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('service_role_id_seq', 1, false);


--
-- Data for Name: signed_agreement; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: supplier__contact; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: website_link; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: supplier__extra_links; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: supplier_code_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('supplier_code_seq', 311, false);


--
-- Data for Name: supplier_domain; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: supplier_domain_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('supplier_domain_id_seq', 1, false);


--
-- Data for Name: supplier_framework; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: supplier_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('supplier_id_seq', 1, false);


--
-- Data for Name: supplier_reference; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: supplier_reference_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('supplier_reference_id_seq', 1, false);


--
-- Data for Name: supplier_user_invite_log; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('user_id_seq', 1, false);


--
-- Name: website_link_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('website_link_id_seq', 1, false);


--
-- Data for Name: work_order; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: work_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('work_order_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--
