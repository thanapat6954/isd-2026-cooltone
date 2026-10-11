// Availability is derived from the selected SQLite set, never the bundled list.
export function availableOptions(options, health) {
  if (!health || !Array.isArray(health.databases)) return [];
  const databases = health.databases.filter(db => db.queryable && !db.archived);
  return options.map(item => {
    const program = item.value === 'AIT' ? 'AI' : item.value;
    const versions = new Set(databases.filter(db => db.program_id?.split('-')[0] === program)
      .map(db => db.curriculum_version));
    return {...item, versions: item.versions.filter(version => version.value === 'all versions'
      ? versions.size > 1 : version.value === 'old' ? versions.has(2560)
      : versions.has(program === 'AI' ? 2566 : 2565))};
  }).filter(item => item.versions.length > 0);
}
export function scopeNotice(health) {
  const partial = health.build_contract?.partial === true;
  const count = health.queryable_database_count ?? 0;
  const methods = new Set((health.extraction_provenance?.profiles || []).map(p => p.method));
  const reviewed = health.extraction_provenance?.reviewed_input_scope;
  const path = methods.has('pdf-text-tables')
    ? reviewed === 'font-encoding-only; no course corrections'
      ? 'Native PDF + การตรวจ font encoding; ไม่ใช่ vision OCR'
      : 'Native PDF; ไม่ใช่ vision OCR'
    : methods.has('vision-OCR') ? 'Vision OCR (การตรวจ source แยกจากการอ่าน OCR)'
    : 'ฐานข้อมูลที่ส่งให้; ไม่มีผล fresh OCR ที่ประกาศในชุดนี้';
  const labels = (health.databases || []).filter(db => db.queryable && !db.archived)
    .map(db => db.curriculum_name || `${db.program_id} ${db.curriculum_version} ${db.plan}`).join(', ');
  return `Build ${health.build_id} · ${count} profiles (${labels}) · ${path}. ` + (partial
    ? 'ชุดข้อมูลบางส่วน — เฉพาะแผนการศึกษา ไม่ใช่การสร้างทั้งระบบครบ 14 profiles; ไม่รองรับ catalog ทั้งเล่ม ข้อกำหนด วิชาบังคับก่อน หรือการรับรองจบการศึกษา'
    : 'ข้อมูลพร้อมใช้ตามชุดที่เลือก; จำนวนฐานข้อมูลไม่ยืนยันความครบถ้วนของ source ทั้งเล่ม');
}
