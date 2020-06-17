-- Copy liability details over to indemnity so seller profiles pass validation
UPDATE supplier
SET data = jsonb_set(data::jsonb, '{"documents","indemnity"}', data::jsonb -> 'documents' -> 'liability')::json;

UPDATE application
SET data = jsonb_set(data::jsonb, '{"documents","indemnity"}', data::jsonb -> 'documents' -> 'liability')::json
WHERE 
	status in ('saved', 'submitted') and
	data -> 'documents' is not null and
	data -> 'documents' -> 'liability' is not null;
