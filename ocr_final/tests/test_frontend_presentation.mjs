import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { citationHref, sourceFilename, pageLabel, shouldSubmitOnEnter } from '../frontend/presentation.mjs';

test('citations use only recorded allowlisted source identities and integer PDF pages', () => {
  for (const file of ['AI', 'DSBA', 'DSBA-60', 'IT', 'IT-60', 'BIT-65', 'BIT-60']) {
    assert.equal(citationHref('http://localhost:8000', `${file}.pdf`, 41), `http://localhost:8000/api/source/${file}.pdf#page=41`);
  }
  for (const file of ['../../IT.pdf', 'https://example.com/IT.pdf', 'Unknown.pdf', null]) assert.equal(citationHref('', file, 1), null);
  for (const page of [null, '', 0, -1, 1.5, 'NaN', '1&x=2']) assert.equal(citationHref('', 'IT.pdf', page), null);
});
test('source identity is not inferred from program names or free text', () => {
  assert.equal(sourceFilename('IT.pdf · พ.ศ. 2565 · แผนสหกิจศึกษา'), 'IT.pdf');
  assert.equal(citationHref('', sourceFilename('IT — แผนการเรียน'), 1), null);
  assert.equal(citationHref('', sourceFilename('ดู IT.pdf หน้า 3'), 3), null);
});
test('PDF and printed book pages remain separate even when equal or unknown', () => {
  assert.equal(pageLabel(41, 36), 'PDF หน้า 41 / หน้า 36 ในเล่ม');
  assert.equal(pageLabel(10, 10), 'PDF หน้า 10 / หน้า 10 ในเล่ม');
  assert.equal(pageLabel(41, null), 'PDF หน้า 41 / หน้าในเล่มยังไม่ยืนยัน');
});
test('Enter does not submit during Thai composition, Shift+Enter, or an active request', () => {
  assert.equal(shouldSubmitOnEnter({key: 'Enter'}, false), true);
  for (const event of [{key: 'Enter', shiftKey: true}, {key: 'Enter', isComposing: true}, {key: 'Enter', keyCode: 229}, {key: 'a'}]) assert.equal(shouldSubmitOnEnter(event, false), false);
  assert.equal(shouldSubmitOnEnter({key: 'Enter'}, true), false);
});
test('real endpoint, original payload, escaped rendering and option identities are retained', () => {
  const source = readFileSync(new URL('../frontend/app.js', import.meta.url), 'utf8');
  assert.match(source, /const USE_MOCK = false/);
  assert.match(source, /fetch\(`\$\{API_BASE\}\/ask`/);
  for (const value of ['AIT', 'DSBA', 'IT', 'BIT', 'all versions']) assert.ok(source.includes(`value: "${value}"`));
  assert.doesNotMatch(source, /innerHTML|insertAdjacentHTML/);
  assert.match(source, /curriculum: elements\.curriculum\.value/);
  assert.match(source, /version: elements\.version\.value/);
});
test('control labels, error recovery, accessible tables and reduced motion are present', () => {
  const html = readFileSync(new URL('../frontend/index.html', import.meta.url), 'utf8');
  const css = readFileSync(new URL('../frontend/style.css', import.meta.url), 'utf8');
  const source = readFileSync(new URL('../frontend/app.js', import.meta.url), 'utf8');
  for (const id of ['curriculum-select', 'version-select', 'question-input']) assert.ok(html.includes(`for="${id}"`));
  assert.match(html, /id="retry-button"/);
  assert.match(source, /setAttribute\('role', 'table'\)/);
  assert.match(source, /'caption'/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /:focus-visible/);
  assert.doesNotMatch(css, /overflow-x: hidden/);
});
