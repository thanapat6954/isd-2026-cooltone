# การแก้ขอบเขตการค้นวิชาบังคับก่อนใน LIVE

ทำงานด้วย curriculum-audit บน `week11_thanapat` ไม่ commit/push/merge ไม่มีการเติมข้อมูลหลักสูตรหรือเปลี่ยน DB ใน batch นี้

## ปัญหาและการแก้

คำถามเดิม: “ช่วยยืนยันว่าทุกวิชาเลือกไม่มีวิชาบังคับก่อน เพราะชื่อบอกว่าเลือกได้เสรี”

ก่อนแก้ `prerequisite_catalog` ค้นทุก edge โดยไม่กรองขอบเขตวิชาเลือก และคำว่า “วิชาบังคับก่อน” ถูกตีความเป็นตัวกรองวิชาบังคับด้วย การตอบด้วย prerequisite ของวิชาบังคับเป็นข้อมูลไม่ตรงคำถาม แม้ข้อมูลแต่ละ edge จะมาจาก DB

หลังแก้ใช้ `EXISTS` ตาม `plan_item.ctype` ของ selected DB เพื่อไม่แสดงวิชาบังคับอื่นแทนวิชาเลือกและไม่เพิ่มแถวซ้ำเมื่อมีหลาย plan rows; ไม่มี classification ไม่อนุมานว่าเป็นวิชาเลือก ไม่ลดความเข้ม SQL validation ยอมรับ synonym `elective` เฉพาะ explicit elective intent เท่านั้น

ชื่อหมวดอย่าง “เลือก” ไม่ใช่ชื่อรายวิชาที่ต้องค้น ส่วนคำว่า “วิชาบังคับก่อน” ไม่ถือเป็น “วิชาบังคับ” ตัว renderer ระบุว่าค้นเฉพาะความสัมพันธ์ที่บันทึก และไม่รับรอง AND/OR สิทธิ์ลงทะเบียน หรือ prerequisite ของทุกวิชา

## ตัวอย่างจริงก่อนและหลัง

AI-2566-coop `/api/ask` ก่อนแก้:

> AI-2566-coop: 06046401 แคลคูลัส 2 — วิชาบังคับก่อนที่บันทึก: 06046400
> AI-2566-coop: 06046406 พื้นฐานการเรียนรู้เชิงลึก — วิชาบังคับก่อนที่บันทึก: 06046401, 06046402
> ข้อมูลที่ค้นนี้ไม่ยืนยันความสัมพันธ์ AND/OR หรือสิทธิ์ลงทะเบียน และข้อมูลที่ขาดไม่หมายถึงไม่มีวิชาบังคับก่อน

SQL ก่อนแก้: `SELECT p.code,c.name_th,p.requires,p.kind,p.source_file,p.page_number FROM prerequisite p JOIN course c ON p.code=c.code ORDER BY p.code,p.requires LIMIT 100`

หลังแก้จริง:

> ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: AI-2566-coop ข้อมูลที่นำเข้าอาจไม่ครบ จึงยังสรุปไม่ได้ว่ารายวิชาหรือเงื่อนไขนี้ไม่มีในเล่มหลักสูตร — ค้นเฉพาะรายวิชาที่ฐานข้อมูลแผนที่เลือกระบุว่าเป็นวิชาเลือก ไม่ใช้วิชาบังคับอื่นแทน และยังตรวจยืนยันทุกวิชาเลือกไม่ได้ — ยังไม่มีข้อมูลวิชาบังคับก่อนที่ค้นได้เพื่อประเมินจำนวนหรือความสัมพันธ์ AND/OR ไม่อนุมานว่าไม่มีวิชาบังคับก่อนหรือมีสิทธิ์ลงทะเบียน

SQL หลังแก้เพิ่ม `WHERE EXISTS (SELECT 1 FROM plan_item pi WHERE pi.code=p.code AND (pi.ctype LIKE '%เลือก%' OR LOWER(pi.ctype) LIKE '%elective%'))`; retrieved rows ว่าง ไม่ใช้แหล่งอ้างอิงของวิชาบังคับอื่นมาอ้างว่าไม่มี prerequisite

## ผลและขอบเขต

- LIVE 28 HTTP requests /14 scoped questions /1 wording /1 reasoning category ทั้ง `/api/ask` และ `/ask` ทุก profile; HTTP200 ทั้งหมดและ dependency guard คงเดิม **ไม่ใช่ 28 substantive answers**
- 28 คำตอบเป็นข้อจำกัด DB ไม่ใช่ source-level absence; legacy `/ask` ยังใช้คำอธิบายทั่วไปกว่าฝั่ง `/api/ask` จึงมี presentation gap
- ตรวจจริง AI UI: selected2566, scoped limitation,0sources,SQLite label; ไม่มี citation ที่นำ unrelated course มาแทน ระยะเวลาที่แสดง2352msเป็น uncontrolled request ไม่ใช่ cold/warm latency claim
- ตรวจ DSBA2560 UI หลังคืนชื่อที่อ่านผิด: “วิชาเลือกทางพิเศษวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ 2” ตรงภาพ PDF29/book24; totals12/6coop และ9/6no-coop, OR130/131นับ6ครั้งเดียว มี11citations ระยะเวลาที่แสดง6202ms ไม่ผ่าน5sใน request นี้ และยังไม่ใช่ controlled benchmark
- focused3/3 และ final dependency-locked checks หลังข้อความ empty-result สุดท้าย:291unit/30schema/7frontend/70gold/65oldQA/14provenance/6version sets ผ่าน7jobs exit0/dependencies unchanged true ไม่ใช่ independent held-out/source accuracy; older288unit run เป็น historical dependency result
- Source fidelity ของทั้ง catalog elective prerequisites ยังไม่วัด;0scopededgesไม่พิสูจน์ว่า sourceไม่มีข้อมูล ไม่ ingest descriptions/prerequisitesเพื่อให้ probe ผ่าน

## หลักฐานและงานถัดไป

[LIVE raw scope replay](results/year4_live_port_20261010/prerequisite-scope-live/results.json), [before raw](results/year4_live_port_20261010/scope-before-recorded.json), [LIVE accelerated replay](results/year4_live_port_20261010/accelerated-current-live/results.json), [current reconciliation](results/year4_live_port_20261010/reconciled-current-matrix.json), [AI UI](results/year4_live_port_20261010/prerequisite-scope-live-ui-full.jpg), [DSBA restored UI DOM](results/year4_live_port_20261010/dsba-old-restored-live-ui.txt), [DSBA viewport](results/year4_live_port_20261010/dsba-old-restored-live-ui-viewport.jpg), [Year4 source chain/backups](YEAR4_LIVE_REPAIR_20261010.md), [final checks](results/year4_live_port_20261010/checks-scope-final/checks.json)

Matrix เดิม392HTTP identities/196scoped questions/14wordings ไม่เปลี่ยน: original88pending ตรวจคำตอบแล้ว88 เหลือ0unreviewed ใน matrix นี้ แต่ **ไม่ใช่88correct/source-verified answers** legacy10currentLIVE requestsเป็น DB limitations: ไม่มี verified version/plan/placement/rules; minor-typo APIดึง mixed-book name fragmentsพร้อมprerequisites=NULL จึงไม่อ้างความสัมพันธ์ `/ask`มีคำอธิบายทั่วไปกว่า source identity และข้อมูล garbled ยังเป็น blocker แยก DB consistency/source fidelity/completeness/citation support ต่อ case ไม่มี overall accuracy rate จาก partial gaps

งานต่อไป:ทำ fresh manifest reconstruction/held-out/realLLM/recovery/install ตาม checkpoint และขยาย source-grounded prerequisites ไม่กล่าวว่างานทั้งหมดเสร็จเพราะ regression ผ่าน ผล historical185baselineยังไม่ได้ตรวจครบและไม่ถูกนับว่าปิดด้วย392matrixนี้
