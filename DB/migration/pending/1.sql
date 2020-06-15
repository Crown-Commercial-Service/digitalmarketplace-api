-- Copy liability details over to indemnity so seller profiles pass validation
UPDATE supplier
SET data = jsonb_set(data::jsonb, '{"documents","indemnity"}', data::jsonb -> 'documents' -> 'liability')::json;
