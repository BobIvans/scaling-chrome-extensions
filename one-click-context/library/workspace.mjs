const MAX_NAME = 180;
const MAX_QUERY = 4096;
const STATUS = new Set(['ORIGINAL','EXTRACTED','EMPTY','UNSUPPORTED','SELECTION','RAW_TEXT','PARTIAL','BEST_EFFORT']);

export function text(value, fallback = '', max = MAX_NAME) {
  const out = typeof value === 'string' ? value.trim() : '';
  return (out || fallback).slice(0, max);
}

export function normalizedRecord(record, {defaultProject='Inbox', defaultSession=''}={}) {
  if (!record || typeof record !== 'object') throw Error('INVALID_RECORD');
  if (typeof record.id !== 'string' || !record.id) throw Error('INVALID_RECORD_ID');
  if (typeof record.name !== 'string' || typeof record.text !== 'string' || typeof record.source !== 'string') throw Error('INVALID_RECORD_TEXT');
  if (!STATUS.has(record.status)) throw Error('INVALID_RECORD_STATUS');
  if (!Array.isArray(record.warnings) || record.warnings.some(w => typeof w !== 'string')) throw Error('INVALID_RECORD_WARNINGS');
  const savedAt = record.savedAt || record.createdAt;
  if (typeof savedAt !== 'string' || Number.isNaN(Date.parse(savedAt))) throw Error('INVALID_SAVED_AT');
  const capturedAt = record.capturedAt == null ? null : record.capturedAt;
  if (capturedAt !== null && (typeof capturedAt !== 'string' || Number.isNaN(Date.parse(capturedAt)))) throw Error('INVALID_CAPTURED_AT');
  return {
    ...record,
    project: text(record.project, defaultProject),
    session: text(record.session, defaultSession),
    savedAt: new Date(savedAt).toISOString(),
    createdAt: new Date(savedAt).toISOString(),
    capturedAt: capturedAt === null ? null : new Date(capturedAt).toISOString()
  };
}

export function filterRecords(records, options={}) {
  const project = text(options.project, '', MAX_NAME);
  const session = text(options.session, '', MAX_NAME);
  const query = text(options.query, '', MAX_QUERY).toLocaleLowerCase();
  const from = options.from || '';
  const to = options.to || '';
  if (from && !/^\d{4}-\d{2}-\d{2}$/.test(from)) throw Error('INVALID_FROM');
  if (to && !/^\d{4}-\d{2}-\d{2}$/.test(to)) throw Error('INVALID_TO');
  if (from && to && from > to) throw Error('REVERSED_DATE_RANGE');
  const field = ['savedAt','capturedAt'].includes(options.dateField) ? options.dateField : 'savedAt';
  return records.filter(r => {
    const when = r[field] || r.savedAt || r.createdAt;
    const day = when ? when.slice(0,10) : null;
    return (!project || r.project === project) && (!session || r.session === session) &&
      (!from || (day && day >= from)) && (!to || (day && day <= to)) &&
      (!query || [r.name,r.source,r.project,r.session,r.text].some(v => String(v || '').toLocaleLowerCase().includes(query)));
  }).sort((a,b)=>(a.savedAt||a.createdAt).localeCompare(b.savedAt||b.createdAt)||a.id.localeCompare(b.id));
}

export function facets(records) {
  return {
    projects: [...new Set(records.map(r=>r.project).filter(Boolean))].sort(),
    sessions: [...new Set(records.map(r=>r.session).filter(Boolean))].sort()
  };
}

export function restorePlan(existing, incoming) {
  const current = new Map(existing.map(r => [r.id, r]));
  const adds = [], duplicates = [], conflicts = [];
  for (const r of incoming) {
    const prior = current.get(r.id);
    if (!prior) { adds.push(r); continue; }
    const same = prior.sha256 && r.sha256 ? prior.sha256 === r.sha256 : JSON.stringify(prior) === JSON.stringify(r);
    if (same) duplicates.push(r.id);
    else conflicts.push({id:r.id, existingSha256:prior.sha256 || null, incomingSha256:r.sha256 || null});
  }
  return {adds, duplicates, conflicts};
}

export function applyRestorePlan(existing, plan) {
  if (!plan || plan.conflicts?.length) throw Error('RESTORE_CONFLICT');
  return [...existing, ...(plan.adds || [])];
}
