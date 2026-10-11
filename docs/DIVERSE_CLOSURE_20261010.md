# ผลแก้ diverse development และ BIT OCR

ทำงานบน `week11_thanapat` HEAD `37b3ad5` ไม่ commit/push/merge ไม่เปลี่ยน main, working databases, source PDFs, original OCR หรือ held-out. แก้ทั้ง repository implementation และ LIVE sibling โดยตรวจความต่างก่อน port. ไม่มี factual overlays หรือ evaluation expected answers เข้า production

## สาเหตุและการแก้

1. Generic name grammar จับ “ที่” จากประโยค “วิชาที่มีวิชาบังคับก่อน…” เป็นชื่อวิชา แก้แยก catalog intent และ resolveชื่อกับSQLiteที่เลือก ไม่ส่งfunction wordsเป็นชื่อ และไม่เลือกรายวิชาเองเมื่อมีหลายcandidate
2. Canonical name search เคยถูกliteral substring preferenceตัดcandidateที่ใช้ “การสร้างโปรแกรม/การโปรแกรม” ออก เก็บcandidateทั้งหมดก่อนใช้exact full-name resolution แสดงรหัสให้ผู้ใช้เลือก ไม่ใช้fuzzy factual substitution
3. SQL execution/EXPLAIN ไม่ส่งparameters และJSONparserเก็บrequired fieldsเท่านั้นจนทิ้งoptional parameters แก้ทั้งschema/parser/BoundSQL/validation/execution/provenance replay; positional/named bindingsต้องตรง marker และเป็นfinite scalar. Materialized literalsใช้ตรวจconstraintsเท่านั้น ไม่ใช้execution ไม่อนุญาตwrite SQLหรือunsupported filters
4. Shared/specialization/elective/plan comparison เคยเข้าunknown fallback หรือfilterผิด แก้generic intentsใช้selected SQLite study rows/relationships; รักษาplaceholder/alternative patterns ไม่บวกทุกกลุ่มรวมกัน. ข้อมูลกลุ่ม/แผนที่ขาดต้องdisclose ไม่ยืนยันว่ารายการทุกวิชาเป็นshared
5. Version comparisonเลือกทั้งสองฉบับของprogram/planเดียวกันและตรวจcommon codes แยกprogramก่อนเปรียบเทียบ ไม่มีcommon codesในcourse catalogsที่ตรวจ จึงเป็นspecific data gap ไม่ใช้program totalsแทนคำถามนี้. AI-old/legacy authoritative mappingยังไม่มี ไม่สร้างฉบับใหม่
6. Evidence harnessหมดmemoryตอนserialize/hashทั้งก้อนหลัง237requests แก้streaming JSON/hash; เก็บfailed run/partial evidenceไว้ ไม่resumeเมื่อruntimehashเปลี่ยน

เปลี่ยน `database.py`, `query_planner.py`, `model_service.py`, `frontend_selection.py`, `study_plan.py`, เพิ่ม `sql_parameters.py`; tests `test_sql_parameters.py`, `test_course_name_resolution.py`; scripts `audit_answer_provenance.py`, `probe_profile_development.py`, `probe_ocr_error.py`, `review_diverse_closure.py`. ชื่อไฟล์เหล่านี้อยู่ใต้repository `ocr_final/`; runtime6files portLIVEแล้ว

## การวัดและขอบเขต

ชุดเดิมมี14wordings/14reasoning categories ×14profiles =196profile-question cases /392HTTP requests (ทั้ง `/api/ask` และ `/ask`). ไม่มีquestionใหม่ ไม่มีheld-out exposure. Baselineเป็นhistorical evidenceเท่านั้น ไม่แทนcurrent verification

- Batch-a:6wordings/84scoped/168HTTP:167HTTP200/1HTTP422. พบwildcard regression, legacy misleading list, name-topic mismatch; เก็บfailed result
- Batch-b:6wordings/84scoped/168HTTP. Batch-c:4wordings/56scoped/112HTTP (112HTTP200); rerunเมื่อcanonical candidate/rendering dependenciesเปลี่ยน ไม่ถือว่าHTTP200ผ่านcorrectness
- Full attempt:237savedrequests/217HTTP200/19HTTP422/1HTTP504ก่อนMemoryError; ไม่ใช่complete392run
- Post optional-parser fix:4categories/56scoped/112HTTP:85HTTP200/27HTTP422; source databases unchanged. ยังมีtechnical failuresจากmodelเติมfiltersหรือไม่ส่งbinding—not fixedทั้งหมด
- Final filters2categories:2wordings/28scoped/56HTTP; selected SQLite oracle+requested English checks52/56ผ่าน;legacy4ยังไม่ผ่าน(1technical/3no verified plan schema). นี่ไม่ใช่citation/full-book accuracy. Final conditions2categoriesอีก56requestsเสร็จและDBhashesunchanged
- Final shared regression:254unit/30schema/6frontend/70gold/65old-version QA/14provenance/6version-set cases;7jobs exit0/dependency guard=true. ไม่ใช่held-out/full-answer accuracy

ตารางรายหมวดและper-case criteria: [ผลตรวจปัจจุบัน](results/diverse_closure_20261010/review-current/review.md), [คำตอบจริง/SQL/rows/ข้อจำกัด](results/diverse_closure_20261010/review-current/review.json). ตารางมีhistorical_only flagกรณีที่ยังไม่มีผลใหม่; substantive completeness/citationที่ยังไม่ตรวจครบอยู่unreviewed ไม่เรียกHTTP200หรือabstentionว่าaccuracy pass

Current conservative392case table:34substantive_correct /104justified_partial_gap /28clarification /21incorrect_irrelevant /28technical_failure /177unreviewed. Filters oracle52passเป็นอีกมิติหนึ่ง ไม่ย้ายทุกcaseไปcorrectก่อนตรวจcitationsครบ. Baseline185pendingยังไม่ปิดทั้งหมด: scriptทำDB replay/triageและบันทึกcriteria แต่ไม่ถือว่าreplayสำเร็จคือmanual semantic reviewครบ. Remaining unreviewedต้องตรวจจริง ไม่เติมคะแนนจากunit tests

## ตัวอย่างจริงก่อนและหลัง

### ถามชื่อวิชาแบบกำกวม

คำถามdevelopment: “อยากเรียนเขียนโปรแกรม มีวิชาชื่อใกล้เคียงกันอะไรบ้าง ถ้าหลายตัวให้ช่วยแยกให้เลือก ไม่ต้องเดาว่าหมายถึงตัวไหน”

ก่อนแก้ IT-2565-coop `/api/ask`: “IT-coop: เทคโนโลยีสารสนเทศ (สหกิจศึกษา) (ที่มา: IT.pdf หน้า 44)” เป็นprogram identityที่ไม่ตอบคำถาม ไม่ใช่substantive correct

หลังแก้ IT-2565-coop `/api/ask` (batch-c):

```text
พบหลายรายวิชาที่ตรงกับชื่อที่ค้น โปรดระบุรหัสวิชาที่ต้องการก่อนตอบรายละเอียด:
IT-2565-coop: 06016415 การเขียนโปรแกรมเชิงฟังก์ชัน
IT-2565-coop: 06066302 การเขียนโปรแกรมเว็บพื้นฐาน
IT-2565-coop: 06016408 การสร้างโปรแกรมเชิงวัตถุ
IT-2565-coop: 06016423 การออโตเมชันและโครงสร้างพื้นฐานที่สามารถโปรแกรมได้
IT-2565-coop: 06066303 การแก้ปัญหาและการโปรแกรมคอมพิวเตอร์
IT-2565-coop: 90642118 โปรแกรมคอมพิวเตอร์ประยุกต์ทางธุรกิจ
IT-2565-coop: 90642121 การวิเคราะห์และจัดการข้อมูลด้วยโปรแกรมคอมพิวเตอร์
```

เป็นclarification ไม่ใช่การเดาว่าผู้ใช้หมายถึงรายวิชาใด Raw resultเก็บSQL name normalization/selected rows/timingไว้ครบในbatch-c. Actual UIเปลี่ยนเป็นIT2560แล้วได้เฉพาะ06016315/17/22/23/25/41ในสองแผน พร้อมIT-60.pdf PDF35/36/37และbook30/31/32 ไม่มี2565ปน. [ภาพ](results/diverse_closure_20261010/ui-old-names.png), [DOMจริง](results/diverse_closure_20261010/ui-old-names-dom.txt)

### วิชาร่วมและกลุ่มเฉพาะ

คำถาม: “ปี 3 เทอม 1 วิชาไหนทุกกลุ่มต้องเรียน และวิชาไหนขึ้นกับกลุ่มที่เลือก อย่ารวมทุกกลุ่มเข้าด้วยกัน”

ก่อนแก้ IT-2565-coop: “หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก” — retrieval failure เพราะSQLiteมีgroup relationships

หลังแก้ actual UI IT2565: แสดงรายวิชาร่วม06016404/06066102แยกจาก3specialization groups;06016418อยู่ซอฟต์แวร์และสื่อประสมแต่ไม่ร่วมทุกกลุ่ม;แยกcoop/no-coopและ18creditsตามตารางต่อแผน ไม่รวมทุกทางเลือก. CitationsPDF42/book37และ35/book30, console warning/error=[]; สังเกตloading→success ไม่ใช้API200อย่างเดียว. [ภาพ](results/diverse_closure_20261010/ui-shared.png), [DOMคำตอบเต็ม](results/diverse_closure_20261010/ui-shared-dom.txt)

### วิชาบังคับก่อนหลายตัว

ก่อนแก้ parse “ที่” ทำให้แสดงcandidateชื่อที่มีคำว่า “ที่” ซึ่งไม่เกี่ยวข้อง. หลังแก้ใช้SQLite prerequisite catalogและdisclose AND/OR/registration unknown ไม่อนุมานว่าไม่มีprerequisiteจากmissing edges. การตอบข้อมูลบางส่วนนี้ไม่เท่ากับตรวจprerequisiteทั้งเล่ม;printed foliosของบางdescription citationsยังunknown

## BIT และสิ่งที่ยังเปิด

[การทดลองและภาพ source](results/diverse_closure_20261010/bit-experiments/REVIEW.md):3unique previously failed pagesคืนข้อความใหม่ แต่125DPI257อ่านcredit2แทน6;200DPIแก้fieldนี้ตรงภาพ. Targeted4courses×5fields=19/20matchเมื่อใช้238(DPI125)+257(DPI200), ไม่ใช่full-page accuracy; CER/WER=n/a. Old model500/valid12checkpoints preserved ไม่มีการingestผลนี้เข้าworking DBหรือreuseคนละconfiguration

ยังเปิด:remaining LLM invalid filters/omitted bindings, unknown/future-content answer relevance, project-name typo retrieval, IT year4 imported study relationships/totalsที่ยังไม่มี, baseline/current semantic reviewที่ยังunreviewed, prerequisite/printed-folio coverage, manifest integration/fresh reconstructionทุกprofile, untouched held-out, difficult controlled cold/warm latency, interruption recovery, legacy identity, first-machine/model installation. ไม่อ้างunder5sจากstructured timingsหรือincomplete answers

Checkpoint: [PROGRESS.md](PROGRESS.md). เก็บraw evidenceใน `results/diverse_closure_20261010/`; ห้ามใช้development expected answersเป็นproduction facts
