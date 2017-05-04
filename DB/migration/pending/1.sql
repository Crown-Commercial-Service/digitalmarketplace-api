CREATE TYPE "public"."project_status_enum" AS ENUM ('draft', 'published');
CREATE SEQUENCE project_id_seq START 4;
CREATE TABLE project
(
  id         INTEGER DEFAULT nextval('project_id_seq' :: REGCLASS) NOT NULL
    CONSTRAINT project_pkey
    PRIMARY KEY,

  data       JSON                                                  NOT NULL,
  status     project_status_enum                                   NOT NULL,
  created_at TIMESTAMP                                             NOT NULL
);

CREATE INDEX ix_project_created_at
  ON project (created_at);

CREATE INDEX ix_project_status
  ON project USING BTREE (status);

