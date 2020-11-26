DO $$                  
    BEGIN 
		IF NOT EXISTS (
			SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'domain_criteria' AND COLUMN_NAME = 'essential'
		)
		THEN
			ALTER TABLE public.domain_criteria ADD COLUMN essential boolean;
			UPDATE public.domain_criteria SET essential = false;
			ALTER TABLE public.domain_criteria ALTER COLUMN essential SET NOT NULL;
		END IF;
	END;
$$;

INSERT INTO 
	public.domain (id, name, ordering, price_minimum, price_maximum, criteria_needed)
VALUES 
	(20, 'Platforms integration', 17, 500, 2500, 4)
ON CONFLICT (id) DO NOTHING;
	
INSERT INTO 
	public.domain_criteria (id, name, domain_id, essential)
VALUES 
	(2001, 'Experience with the Information Security Manual (ISM) and other Government security frameworks in relation to large transformation programs and experience in managing a consortia within these government security frameworks.', 20, true),
	(2002, 'Experience in leading large transformational programs that deliver strategic digital platforms and experience in providing ongoing management and support of these platforms.', 20, true),
	(2003, 'Demonstrated ability to work with providers to enable a scalable, reusable platform that can support multiple, distinct use cases.', 20, false),
	(2004, 'Experience in providing ongoing management, support and continual improvement of these platforms with clear transparency of services and associated SLAs.', 20, false),
	(2005, 'Experience in establishing a strategic vendor partnership with the client (for example, by delivering strategic insight and aligning product development roadmaps with client needs).', 20, false),
	(2006, 'Ability to participate in development of transformational strategy, implementation planning / execution and operating model changes required to optimise outcomes.', 20, false),
	(2007, 'Ability to manage a consortia of vendors and integrators to deliver a holistic solution / service.', 20, false),
	(2008, 'Demonstrated ability to support Australian Industry and Indigenous participation.', 20, false)
ON CONFLICT (id) DO NOTHING;