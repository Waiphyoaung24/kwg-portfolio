// The two default pipelines from the spec (§9). Shared early stages, then a divergent tail.
const SHARED = [
  { name: 'Proposal', owner: 'internal', docs: ['signed proposal'] },
  { name: 'Requirement Discussion', owner: 'shared', docs: [] },
  { name: 'BRS', owner: 'client', docs: ['BRS'] },
  { name: 'Quotation', owner: 'internal', docs: ['quotation'] },
  { name: 'Contract', owner: 'shared', docs: ['signed contract'] },
];

const POS_TAIL = [
  { name: 'System/Hardware Requirement Confirmation', owner: 'client', docs: [] },
  { name: 'Wireframe', owner: 'internal', docs: [] },
  { name: 'UI/UX', owner: 'internal', docs: [] },
  { name: 'Development', owner: 'internal', docs: [] },
  { name: 'Client Testing/Feedback', owner: 'client', docs: [] },
  { name: 'Launch/Deployment', owner: 'shared', docs: [] },
  { name: 'Handover & Resource Assignment', owner: 'internal', docs: [] },
];

const WEB_TAIL = [
  { name: 'Content/Brand Assets Collection', owner: 'client', docs: ['brand assets'] },
  { name: 'Wireframe', owner: 'internal', docs: [] },
  { name: 'UI/UX', owner: 'internal', docs: [] },
  { name: 'Development', owner: 'internal', docs: [] },
  { name: 'Client Review/Revisions', owner: 'client', docs: [] },
  { name: 'Launch', owner: 'shared', docs: [] },
  { name: 'Handover', owner: 'internal', docs: [] },
];

export async function seedIfEmpty(sql) {
  const [{ count }] = await sql`SELECT count(*)::int AS count FROM project_types`;
  if (count > 0) return;

  for (const [typeName, tail] of [['POS', POS_TAIL], ['Creative Website', WEB_TAIL]]) {
    const [type] = await sql`INSERT INTO project_types (name) VALUES (${typeName}) RETURNING id`;
    const [tpl] = await sql`
      INSERT INTO pipeline_templates (project_type_id, name)
      VALUES (${type.id}, ${typeName + ' Pipeline'}) RETURNING id`;
    const stages = [...SHARED, ...tail];
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i];
      await sql`
        INSERT INTO stage_templates (pipeline_template_id, ord, name, owner_type, required_documents)
        VALUES (${tpl.id}, ${i + 1}, ${s.name}, ${s.owner}, ${sql.array([...s.docs])})`;
    }
  }
}
