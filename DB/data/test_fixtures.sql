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
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (17, 'atm', 'Ask the market', true, '{"unitSingular": "service", "unitPlural": "services"}');
INSERT INTO lot (id, slug, name, one_service_limit, data) VALUES (18, 'specialist', 'Specialist', true, '{"unitSingular": "service", "unitPlural": "services"}');


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
INSERT INTO framework_lot (framework_id, lot_id) VALUES (7, 17);
INSERT INTO framework_lot (framework_id, lot_id) VALUES (7, 18);


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
    
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (1, 'Strategy and Policy'                     , 1 , 0, 10000, 2);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (2, 'Change, Training and Transformation'     , 2 , 0, 10000, 3);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (3, 'User research and Design'                , 3 , 0, 10000, 3);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (4, 'Agile delivery and Governance'           , 4 , 0, 10000, 2);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (5, 'Recruitment'                             , 5 , 0, 10000, 1);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (6, 'Software engineering and Development'    , 6 , 0, 10000, 3);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (7, 'Content and Publishing'                  , 7 , 0, 10000, 2);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (8, 'Cyber security'                          , 8 , 0, 10000, 1);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (9, 'Marketing, Communications and Engagement', 9 , 0, 10000, 1);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (10, 'Support and Operations'                 , 10, 0, 10000, 3);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (11, 'Data science'                           , 11, 0, 10000, 1);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (12, 'Digital products'                       , 12, 0, 10000, 1);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (13, 'Emerging technology'                    , 13, 0, 10000, 1);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (14, 'ICT risk management and audit activities', 14, 0, 10000, 2);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (15, 'ICT managed services'                   , 15, 0, 10000, 2);
INSERT INTO domain (id, name, ordering, price_minimum, price_maximum, criteria_needed) VALUES (16, 'Digital sourcing and ICT procurement'   , 16, 0, 10000, 3);

--
-- Data for Name: domain_criteria; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO domain_criteria (name, domain_id) VALUES ('Analysis of new technologies with respect to existing products, practices or processes.', 1);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Developing recommendations based on the quantitative and qualitative evidence gathered via web analytics, applications data, financial data and user feedback.', 1);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Business case development or recommendations on investment alternatives.', 1);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Provide policy interpretation and advice to delivery teams.', 1);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Plan, design, conduct and analyse user research in an agile delivery environment.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Recruit participants from diverse audiences, including people with disability, CALD audiences and other minority groups. Provide facilities for usability testing.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Visually communicate user research through presentations, journey maps, videos etc. to clarify key outcomes and generate empathy for end users.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Map existing user experiences and user needs of government services and analyse existing web and mobile service delivery operations.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Identify failure demand in existing services and opportunities for reducing failure demand, reducing the cost of the service and improving the user experience.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Iterate service designs based on user research.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Create design hypotheses to improve the service and run measurable design experiments.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Develop concepts based on research insights. Iteratively test concepts with end users, from paper sketches to HTML prototypes.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Extensive experience of web and mobile application interface design with a focus on accessibility, designing for different screen sizes and input methods (for example, touch, mouse and keystroke) following style guides and WCAG 2.0 AA guidelines.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Respond in a pragmatic and constructive manner to feedback and constraints that impact the design.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Perform accessibility audits to uncover accessibility issues and get recommended fixes.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Communicate how design decisions impact accessibility to a wide range of digital delivery disciplines both internally and externally.', 3);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Responsible for delivery and ongoing management of high-quality digital product or service.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Lead multi-disciplinary agile teams to deliver or iterate services that meet user needs.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Clarify business priorities, roles and responsibilities and secure individual and team ownership.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Working with data - excellent analytical and problem solving skills, from gathering and analysis through to design and presentation.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Identify a range of relevant and credible information sources and recognise the need to collect new data when necessary from internal and external sources.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Articulate “to be” services via roadmaps, backlogs and user stories.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Prioritise work to be done against user need, team capacity and team capability.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Communicate service performance against key indicators to internal and external stakeholders.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Expertise with data analysis, web analytics and visualisation tools (for example, Google Analytics, Google Refine or Tableau).', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Report progress, budgets, risks and impediments. Propose mitigation solutions.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Define how user / financial benefit can be realised and measured.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Ensure an appropriate level of quality and compliance for a service’s stage (alpha/beta/production).', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Governing delivery and continuous improvement of a digital service, aligned to the Digital Service Standard', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Research and weigh up competing technology choices and make informed decisions based on user needs, with a preference for open source technology.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience using and deploying on cloud-based platforms.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Use and implementation of modern front end web programming techniques, such as HTML5, CSS3, AJAX, REST and JSON.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Good development skills in one or more of .Net, Java, Ruby, Python, JavaScript, PHP or similar with familiarity with one or more open source web frameworks such as Rails, Django, SharePoint, Drupal or similar.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Proven capability in managing technology implementation projects.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Track record of successfully taking an evolutionary architecture approach to software architecture.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience building and scaling high-traffic websites and/or high volume transaction processing and analysis platforms.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience designing and implementing scalable and robust approaches to caching, security and databases (including relational, for example, MySQL and PostgreSQL or similar; and NoSQL, for example, Cassandra and MongoDB or similar).', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Deep and wide experience with infrastructure and platform technologies like AWS, Google Cloud, Cloud Foundry, Deis, Tsuru or similar', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Deep and wide knowledge of the plumbing of the internet (TCP/IP, routing, bridging, HTTP, SSL, DNS, mail).', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with automated configuration management, deployment and testing solutions.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience configuring and managing servers for serving a dynamic website.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience debugging a complex multi-server service. Familiarity with configuration management tools like Puppet and Chef or similar.', 4);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Strong triage skills, creative problem solving and logical decision making on complex support and services issues.', 10);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Evaluate, troubleshoot, and follow-up on customer issues as well as replicate and document for further escalation.', 10);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Communicate progress updates, action plans, and resolution details.', 10);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Develop and interpret operational reports.', 10);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Identifying continuous improvement opportunities for a digital service.', 10);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Provide continual feedback to agile delivery teams for prioritisation and roadmapping.', 10);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Providing content that meets the needs of the user clearly, simply and quickly. Formats include plain language copy, photography, illustration, interactive media and video.', 7);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Creating content for different platforms and devices, following style guides and accessibility and cultural diversity best practice.', 7);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with content platforms (for example Sitecore, GovCMS), content governance frameworks and detailed editorial calendars.', 7);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Defining and maintaining taxonomies, tagging systems and metadata.', 7);
INSERT INTO domain_criteria (name, domain_id) VALUES ('A/B testing to improve and share insights on content performance.', 7);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Creating targeted digital marketing campaigns that have delivered user engagement and significant product or service usage.', 9);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience in quantifying marketing impact and SEO performance and strong understanding of technical SEO - sitemaps, crawl budget, canonicalization, etc.', 9);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Develop press strategies and provide digital communications guidance.', 9);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Create strategies to increase engagement within digital communities.', 9);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Plan, produce, and execute events.', 9);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with public sector account and relationship management.', 9);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Research and development to better detect, deter and respond to emerging cyber security issues.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Discovering, communicating and explaining security vulnerabilities to teams to ensure secure coding in a multi-product, continuous delivery environment.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Automated testing to align with continuous integration.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Carry out assessments (penetration testing, Web Application security testing, vulnerability scanning, threat modelling, etc).', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with security testing tools, (eg Nessus, RKHunter, Fail2Ban, BURP, Cucumber, Netsparker or similar)', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Recommend improvements to fix vulnerabilities in products, infrastructures, and processes.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Security architecture reviews, IRAP assessments, Risk assessments, and writing of security related documentation.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with Data Loss Prevention and Data Protection. Security incident or emergency response.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Provision and monitoring of access to data, IT systems, facilities or infrastructure.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Recovery or secure deletion of information from computers and storage devices.', 8);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Solving difficult, non-routine analysis problems, working with large, complex data sets.', 11);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with statistical methods such as parametric and nonparametric significance testing.', 11);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience with statistical software (for example, R, Julia, MATLAB, pandas or similar) and database languages (e.g. SQL).', 11);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Providing insight or recommendations (for example, cost-benefit, forecasting, experiment analysis) through visual displays of quantitative information.', 11);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Activities that makes an organisation’s enterprise asset (data) discoverable, accessible and useable to stakeholders, while encompassing a good governance framework.', 11);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Artificial intelligence', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Blockchain', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Internet of Things', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Virtual, Augmented, and Mixed Reality', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Robotic devices', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Wearables', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Machine vision technologies', 13);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience in ICT advisory services including saving initiatives, reporting obligations, investment framework, business case development and costing frameworks.', 14);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience in performing periodic review of architectures, patterns and portfolios to ensure that planned investments will successfully achieve business strategies.', 14);
INSERT INTO domain_criteria (name, domain_id) VALUES ('Experience in strategy/framework and architecture development (e.g. models and patterns).', 14);

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

SELECT pg_catalog.setval('domain_id_seq', 16, true);


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
