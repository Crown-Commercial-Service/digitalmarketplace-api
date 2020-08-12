-- Copy liability details over to indemnity so seller profiles pass validation
UPDATE supplier
SET
    data = jsonb_set(data::jsonb, '{"documents","indemnity"}', data::jsonb -> 'documents' -> 'liability')::json,
    last_update_time = current_timestamp
WHERE 
	status != 'deleted' and
	data -> 'documents' is not null and
	data -> 'documents' -> 'liability' is not null;

UPDATE application
SET
    data = jsonb_set(data::jsonb, '{"documents","indemnity"}', data::jsonb -> 'documents' -> 'liability')::json,
    updated_at = current_timestamp
WHERE 
	status in ('saved', 'submitted') and
	data -> 'documents' is not null and
	data -> 'documents' -> 'liability' is not null;
