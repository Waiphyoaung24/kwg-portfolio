CREATE TABLE IF NOT EXISTS project_types (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pipeline_templates (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_type_id integer NOT NULL REFERENCES project_types(id),
  name text NOT NULL,
  version integer NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS stage_templates (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pipeline_template_id integer NOT NULL REFERENCES pipeline_templates(id),
  ord integer NOT NULL,
  name text NOT NULL,
  owner_type text NOT NULL CHECK (owner_type IN ('internal','client','shared')),
  description text NOT NULL DEFAULT '',
  required_documents text[] NOT NULL DEFAULT '{}',
  checklist_items text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS projects (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  client_name text NOT NULL,
  project_type_id integer NOT NULL REFERENCES project_types(id),
  pipeline_template_id integer NOT NULL REFERENCES pipeline_templates(id),
  created_date timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','on_hold','done','cancelled'))
);

CREATE TABLE IF NOT EXISTS project_stages (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage_template_id integer REFERENCES stage_templates(id),
  ord integer NOT NULL,
  name text NOT NULL,
  owner_type text NOT NULL CHECK (owner_type IN ('internal','client','shared')),
  status text NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started','in_progress','waiting_on_client','blocked_internal','done','skipped')),
  notes text NOT NULL DEFAULT '',
  blocked_reason text,
  blocked_since timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  required_documents text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_stage_id integer NOT NULL REFERENCES project_stages(id) ON DELETE CASCADE,
  filename text NOT NULL,
  doc_type text NOT NULL CHECK (doc_type IN ('proposal','brs','quotation','contract','wireframe','other')),
  version_number integer,
  uploaded_by text NOT NULL DEFAULT '',
  uploaded_at timestamptz NOT NULL DEFAULT now(),
  note text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS team_members (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  role text NOT NULL DEFAULT '',
  contact text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS project_assignments (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  team_member_id integer NOT NULL REFERENCES team_members(id) ON DELETE CASCADE,
  role_on_project text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS activity_log (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  actor text NOT NULL DEFAULT '',
  action text NOT NULL,
  timestamp timestamptz NOT NULL DEFAULT now(),
  note text NOT NULL DEFAULT ''
);
