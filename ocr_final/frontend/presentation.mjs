// Presentation-only helpers: never infer a source identity or curriculum fact.
export function citationHref(base, filename, page) {
  if (!/^(AI|DSBA|DSBA-60|IT|IT-60|BIT-65|BIT-60)\.pdf$/.test(filename || '')) return null;
  const number = Number(page);
  if (!Number.isInteger(number) || number < 1) return null;
  return `${base}/api/source/${encodeURIComponent(filename)}#page=${number}`;
}

export function sourceFilename(section) {
  // The API supplies the recorded source file as the first section component.
  return typeof section === 'string' ? section.split(' · ')[0] : null;
}

export function pageLabel(page, bookPage) {
  return `PDF หน้า ${page ?? 'ยังไม่ยืนยัน'} / ${bookPage != null && bookPage !== '' ? `หน้า ${bookPage} ในเล่ม` : 'หน้าในเล่มยังไม่ยืนยัน'}`;
}

export function shouldSubmitOnEnter(event, busy) {
  return !busy && event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229;
}
