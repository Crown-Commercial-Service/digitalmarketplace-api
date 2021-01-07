INSERT INTO 
	public.domain (id, name, ordering, price_minimum, price_maximum, criteria_needed)
VALUES 
	(21, 'Service Integration and Management', 18, 500, 2400, 4)
ON CONFLICT (id) DO NOTHING;
	
INSERT INTO 
	public.domain_criteria (id, name, domain_id, essential)
VALUES 
	(2101, 'Demonstrated organisational experience and capability to conduct and/or support IT service management and coordinated service delivery in large, multi-sourced, multi-service tower, security conscious enterprise environments. Sellers need to demonstrate a sound knowledge and experience managing: end to end IT services; Governance and coordination of multiple service providers; service design and architecture, service portfolios, ITSM tools, and service catalogues; ICT Systems and Security Management including regulatory compliance requirements; ITIL based service management or equivalent ITSM Service management frameworks.', 21, true),
	(2102, 'Service Managers must provide a statement that they hold appropriate recognised industry qualifications and/or certifications pertaining to ICT service management and governance.', 21, true),
	(2103, 'Manage the complex inter-relationships and issues between service tower providers, and conflicts of interest in a multi-sourced, managed service provider enterprise environment.', 21, false),
	(2104, 'Provide a statement that your company holds recognised industry certifications relevant to quality and risk management, health and safety, project and programme management, environmental systems.', 21, false),
	(2105, 'Support of Australian industry, indigenous enterprises and small-to-medium enterprises (including as subcontractors) in the supply chain.', 21, false)
ON CONFLICT (id) DO NOTHING;