# ผลแก้การสร้างฐานข้อมูลจาก PDF

ทดสอบสร้างแผนการเรียนจาก PDF ต้นฉบับครบ 13 profiles แล้ว การทดสอบเริ่มจาก code ZIP v8 ที่แตกใหม่ ใส่ local patch และ PDF ทั้ง 7 ไฟล์ โดยไม่ restore ฐานข้อมูลจาก runtime bundle ตัวสร้างอ่าน PDF text/table ก่อน และใช้ image OCR เมื่ออ่านตรงไม่ได้ ตามขอบเขตที่ผู้ใช้ยอมรับ

คำสั่ง `python scripts/rebuild_from_pdf.py --activate` จบด้วย exit 0; source verification ผ่านครบ 13 profiles; `check_setup.py` รายงาน `missing_profile_databases=[]` การถามผ่าน API จริงผ่าน 105 คำถามเรื่องหน่วยกิตรายภาค และ 26 คำถามชื่อ/หน่วยกิตรายวิชา พร้อมตรวจ PDF page และ printed book page กับหลักฐานที่ตรวจจากหนังสือไว้ก่อนสร้างฐานข้อมูล

ในการทดสอบทั้ง 13 profiles อ่านด้วย native PDF สำเร็จทั้งหมด ส่วน fallback ทดสอบแยกด้วย DSBA.pdf PDF27: เมื่อไม่ให้ font review ตัวอ่าน native ปฏิเสธอักขระที่ยังไม่ตรวจ แล้วทำ image OCR ใหม่ ได้ 6 แถว รวม 18 หน่วยกิต ตรงกับหน้าต้นฉบับ ใช้เวลา 516.277 วินาทีสำหรับ probe หนึ่งหน้า จึงไม่ใช้ผลนี้รับรองความเร็วหรือความถูกต้องของ image OCR ทั้งเล่ม

Actual UI ที่ใช้ฐานข้อมูลใหม่แสดง IT2560 coop ปี4 ภาค1 เป็น 6 หน่วยกิต และแสดงการเลือกหนึ่งแขนงแล้วเลือกหนึ่งวิชาภายในแขนง ตรงกับ PDF39/book34; source viewer เปิดภาพหน้าต้นฉบับได้ ไม่มี console warning/error ในการตรวจครั้งนั้น

ฐานข้อมูลชุดนี้มี contract `academic-plan-only` และยังไม่ใช่ฐานข้อมูลครบทั้งเล่ม: ไม่รองรับคำอธิบายรายวิชา วิชาบังคับก่อน ข้อกำหนดหลักสูตร และ legacy ความหมายของการผ่านคือสร้างและตรวจแผนการเรียนทั้ง 13 profiles ได้ ไม่ใช่รับรองว่าทุกข้อมูลเหมือน SQLite ใน ZIP เดิม หรือรับรอง full OCR accuracy

Local patch รอบแรกที่ตรวจแล้วมี 58 files และตรวจ CRC/hash ครบ การแตกด้วย PowerShell Expand-Archive ผ่านจริง ขณะจัด patch ยังไม่ได้อนุญาตเผยแพร่ ต่อมาผู้ใช้อนุญาตนำขึ้น week11 และส่ง DB ZIP จึงรวมการแก้ใน [ชุด instructor-v9](INSTRUCTOR_V9.md) ไม่ต้องใช้ patch เพิ่ม ส่วน v8 ZIP เดิมยังคงไว้ตามเดิม

Existing regression ผ่าน unit388/schema30/frontend11/gold70/old2560 QA65/provenance14/version sets6; gold เดิมตรวจพฤติกรรมที่มีหลักฐานจำกัด ไม่ใช่การรับรองทุกหน้า หนังสือทุกไฟล์ ฐานข้อมูลเดิม และ evaluation inputs ที่ล็อกไว้ 78 files มี hash เหมือนก่อนแก้ ไม่อ่านหรือแก้ protected held-out inputs Read-only audit เดิมยังมี 1372 findings และ 51 incomplete findings ซึ่งยังต้องแก้แยก

หลักฐานที่ตรวจซ้ำได้อยู่ใน `docs/results/ocr_reconstruction_repair_20261011/`:

- `patch-clean13-rehearsal.json`, `patch-build.json`, `patch-source-validation.json`, `patch-setup.json`: ทดสอบ actual ZIP + patch + PDF-only rebuild
- `source-backed-plan-gold-m.json`, `source-backed-course-gold.json`: source-backed development Q&A; ไม่ใช่ held-out score
- `rebuilt-plan-ui-n.png`, `rebuilt-source-viewer-n.png`: UI ที่ใช้ฐานข้อมูลแผนการเรียนสร้างใหม่
- `hybrid-fallback-j-source-review/`: raw OCR, ภาพ, parsed output และ source comparison ของ fallback หนึ่งหน้า
- `regression-n-complete/`, `final-audit-n/`, `protected-final.json`, `owned-probes-stopped.json`: regression, findings ที่ยังเปิด, input hash และการปิดเฉพาะ test backend

งานถัดไปคือ extraction และการตรวจ association ของ catalog descriptions/prerequisites/program rules จาก PDF จริง รวมถึงหน้าที่มีเนื้อหาเป็นภาพแม้หัวท้ายกระดาษมี native text ก่อนเชื่อมข้อมูลเข้าฐานข้อมูลสำหรับ chatbot ส่วน legacy ต้องรักษาว่าเป็น mixed source catalog จนกว่าจะมีหลักฐาน identity ที่ชัดเจน

## งานต่อส่วน catalog วันที่ 12 ตุลาคม 2026

แก้ตัวอ่าน catalog ให้ใช้ reviewed font encoding และแยกหน่วยกิตออกจากชื่อวิชาที่อยู่บรรทัดเดียวกัน หากอ่าน glyph ไม่ได้จะเก็บ native ต้นฉบับไว้และหยุด association ข้ามหน้านั้น การอ่านใหม่ทั้ง 7 เล่มได้ 469 literal catalog candidates; เทียบกับ prerequisite/name approvals ที่ตรวจจากหนังสือไว้ก่อนแล้วผ่าน 29/29 รายการ ผลนี้ยังไม่รับรองคำอธิบายทั้งหมด 469 รายการหรือ catalog ครบทั้งเล่ม

พบและแก้การนับหน้าที่มี native header/footer แต่ body เป็นภาพว่าอ่านสำเร็จ ตัวตรวจใหม่ระบุ image regions ที่ไม่มี native text ครอบคลุม และไม่นับหน้าดังกล่าวเป็น native corpus ที่ครบ การตรวจนี้เป็น readiness สำหรับ OCR/review รวมถึงภาพประกอบและภาคผนวก จึงไม่ใช่จำนวนหน้าที่มีคำอธิบายรายวิชาโดยตรง

| หนังสือ | PDF pages | Native-readable ยังไม่ certified | OCR/review-required | Literal catalog candidates รอบ O |
|---|---:|---:|---:|---:|
| AI.pdf | 346 | 99 | 247 | 43 |
| DSBA.pdf | 403 | 167 | 236 | 70 |
| IT.pdf | 429 | 175 | 254 | 88 |
| BIT-65.pdf | 317 | 145 | 172 | 48 |
| DSBA-60.pdf | 258 | 139 | 119 | 66 |
| IT-60.pdf | 327 | 199 | 128 | 97 |
| BIT-60.pdf | 242 | 124 | 118 | 57 |

เพิ่ม `scripts/source_document_ocr.py` สำหรับ hybrid transcription ของหน้าที่ระบุ: native first; เมื่อ native ถูกปฏิเสธจึงส่งเฉพาะภาพกับ published Typhoon prompt เข้า model เก็บภาพ ผล native เดิม HTTP response และ raw transcription แยกไว้ ตรวจ model/source/code/config hashes ก่อน resume และปฏิเสธผลว่าง/incomplete/token-truncated โดยไม่ mark หน้าว่าผ่าน เครื่องมือยังไม่ normalize catalog หรืออนุญาต activation

Actual AI PDF240/book236 มีตารางเป็นภาพและไม่มีข้อความตารางใน native text การทดลอง whole-page ได้ผลว่าง; การแบ่ง 4 bands ต่อ block ได้ HTTP500 ซึ่ง log บริการระบุว่า image encoder จอง CPU buffer 1,925,738,496 bytes ไม่สำเร็จ/runtime OOM เก็บทั้งสอง failure ไว้ ไม่ใช้เป็น OCR pass การทดลองแบ่งแถวเล็กลงมี raw/checkpoint แยกต่างหาก ต้องตรวจผลจริงก่อนรับรอง

Full unit suite หลังเพิ่ม catalog/hybrid guards ผ่าน 400 tests; read-only audit ยังคง 14 datasets/FAIL1372/incomplete51/missing=[] รายงาน Summary/HIGH ยังระบุ prerequisite/reference coverage และ legacy identity ที่ไม่ครบ ไม่ใช้ unit pass แทน source accuracy

Actual raster-row probe U อ่านส่วน context แรกได้ แต่ส่วนหัวตารางถัดไปสร้าง empty HTML rows ซ้ำจนถึง 2048 tokens จึงถูกปฏิเสธและยังมี PDF240 pending ไม่อ้างว่าอ่านตารางครบ การสร้าง native catalog อีกครั้งใน minimal PDF-only temporary app หลังจำกัดการ render หน้า rejected สำเร็จ: 99 readable source pages, 43 catalog entries, 53 source fragments, SQLite integrity ok; catalog facts ทั้ง 43 เหมือนรอบ O แต่ยังไม่ใช่ independent source certification สำหรับทุก description Full activation ถูกปฏิเสธตามที่ต้องการ

Final regression W ทั้ง 7 jobs exit0 และ dependencies unchanged: unit400/schema30/frontend11/gold70/old2560 gold65/provenance14/version sets6; focused LIVE tests23 ผ่าน โค้ด/test/guide ที่ port แล้ว 62 files มี hash ตรง repository เก็บ backup ของไฟล์เดิมและตรวจ hash แล้ว Protected source/DB/evaluation 78 files ยังมี hash เดิม ปิดเฉพาะ owned test backend8021; shared application/Ollama server ยังทำงาน

ผลและข้อจำกัดล่าสุดอยู่ใน `catalog-final-summary.json`, `catalog-build-v-proof/`, `catalog-regression-w-complete/`, `catalog-native-coverage-p/`, `catalog-diagnostic-o/`, `catalog-hybrid-{q,r,u}-raw/` และ `catalog-live-port.json` ภายใต้ results directory เดิม งานที่ยังต้องทำคือ context ของ scanned catalog headers/rows โดยให้ใช้ RAM ได้จริง ตรวจคำอธิบายและเงื่อนไขจาก source images แล้ว normalize เข้า runtime รวมทั้ง program rules และ legacy identity ยังไม่ได้รับรองหรือเปิดใช้ full replacement

## ซ้อมชุด v9 จริง

แก้การแพ็กสองจุดจากการซ้อมในโฟลเดอร์ใหม่: เก็บ original bytes ของ source-review JSON ผ่าน `.gitattributes` เพื่อไม่ให้ Git เปลี่ยน CRLF/LF จน receipt SHA ไม่ตรง และใส่ historical `work/robustness_summary.json` ที่ report tests ต้องใช้ โดยไม่ใส่ DB/old OCR เป็น build inputs ไม่เปลี่ยน expected facts หรือ source approvals เดิม

Actual code ZIP 442 files ใช้ environment ใหม่และ dependencies ตาม `requirements-rebuild.txt`; restore 14 snapshots/7 PDF แล้ว startup/restart, development gold70/70, both-route52 checks, citations/source viewer และ missing-model/file/occupied-port guards ผ่าน Unit400/schema30/frontend11 ผ่าน ตรวจ UI จริง AI06046400=3credits/PDF23/book19 และภาพต้นฉบับได้ ผล QA รอบแรกติด atomic file replacement ใน OneDrive จึงเก็บ failure แล้วทดสอบใน TEMP ด้วย code/expectations เดิม

ซ้อม actual ZIP เดียวกันอีกโฟลเดอร์ที่ไม่มี DB เริ่มจาก PDF-only; default `rebuild_from_pdf.py --activate` สร้างและ source-verify ครบ13 profiles ผ่านใน274.940วินาที โดยทั้ง13อ่าน native สำเร็จ Startup/source-backed plan105/105 และ course26/26 ผ่าน เก็บ contract `academic-plan-only` และ backup ก่อน activation ใช้ fresh venv ที่ติดตั้งในรอบนี้และ shared installed models โดยเปิดเผย ไม่ใช่ผล OCR ภาพทั้งเล่ม/การติดตั้ง OS หรือโมเดลบนเครื่องอาจารย์

ผลย่อเผยแพร่ได้ใน [verification-summary.json](public_results/instructor_v9/verification-summary.json) และภาพ [UI](public_results/instructor_v9/v9-ui-full.png), [source viewer](public_results/instructor_v9/v9-source.png) Original DB/PDF/evaluation 77 files ที่อยู่ใน dependency guard W ยังมี SHA เดิม Audit14FAIL1372/incomplete51/missing=[] คงเดิม รายละเอียดรุ่นส่งและ hashes อยู่ใน release manifest/VERIFICATION
