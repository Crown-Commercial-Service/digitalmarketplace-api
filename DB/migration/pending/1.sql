INSERT INTO 
	public.domain (id, name, ordering, price_minimum, price_maximum, criteria_needed)
VALUES 
	(21, 'Service Integration and Management', 18, 500, 2400, 6)
ON CONFLICT (id) DO NOTHING;
	
INSERT INTO 
	public.domain_criteria (id, name, domain_id, essential)
VALUES 
	(2101, 'Demonstrated organisational capability to support the delivery of service integration and management services to large, security conscious enterprises, including qualified and security cleared staff and resources.', 21, true),
	(2102, 'Demonstrated experienced in the delivery of SIAM services to medium to large enterprises in accordance with SIAM and ITIL processes or similar principles.', 21, true),
	(2103, 'Demonstrated experience and ability to manage complex relationships between Service Providers including managing conflicts of interest.', 21, true),
	(2104, 'Experience in the development, maintenance and ongoing support of service portfolios and catalogues, including services provided by other suppliers and internal business providers.', 21, true),
	(2105, 'Ability to manage a consortia of suppliers, including suppliers, Service Providers and carriers to deliver seamless end to end services to client stakeholders and users.', 21, true),
	(2106, 'The Service Manager and/or their staff must hold appropriate recognised industry qualifications and/or certifications pertaining to ICT service management, ICT governance and ICT security management.', 21, true),
	(2107, 'The Service Manager should hold recognised industry certifications relevant to quality and risk management, health and safety, project and programme management, environmental systems, etc.', 21, false),
	(2108, 'Ability to support Australian industry, indigenous enterprises and small-to-medium enterprises (including as subcontractors) in the supply chain.', 21, false)
ON CONFLICT (id) DO NOTHING;