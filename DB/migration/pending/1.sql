CREATE INDEX ix_evidence_brief_id ON evidence USING btree (brief_id);

CREATE INDEX ix_evidence_domain_id ON evidence USING btree (domain_id);

CREATE INDEX ix_evidence_supplier_code ON evidence USING btree (supplier_code);

CREATE INDEX ix_evidence_user_id ON evidence USING btree (user_id);

CREATE INDEX ix_evidence_assessment_evidence_id ON evidence_assessment USING btree (evidence_id);