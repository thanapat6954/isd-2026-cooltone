# ผู้ช่วยค้นข้อมูลหลักสูตรจาก SQLite และ PDF

โครงงาน P2 · Intelligent System Development · `isd-2026-cooltone`

**ดาวน์โหลดชุด v8 จาก [GitHub Release](https://github.com/thanapat6954/isd-2026-cooltone/releases/tag/instructor-v8)** หรือใช้โค้ดจาก branch `week11_thanapat` คู่กับ runtime bundle รุ่นเดียวกัน แอปอยู่ใน `ocr_final/` ของโครงการที่แตก ZIP ข้อเท็จจริงขณะตอบมาจาก SQLite ที่เลือกเท่านั้น ไม่ใช้เฉลย evaluation หรือ JSON เติมข้อเท็จจริงหลังค้น SQL

| โหมด | สถานะและขอบเขต |
|---|---|
| A — เปิดฐานข้อมูลที่ส่งให้ | ทดสอบจาก ZIP จริงแล้ว: 14 SQLite snapshots และ PDF 7 เล่ม ไม่ต้องรัน OCR |
| B — native เฉพาะแผนการศึกษา | Pipeline ที่ส่งใน v8 มีหลักฐาน v7 fresh source-only 10 profiles: IT2565, DSBA2565/2560, BIT2565/2560 ทั้งสองแผน ใช้ reviewed font decoding + source validation **ไม่ใช่ vision OCR** |
| B — vision OCR / full book | ภาพ single-row ที่เลือกวัดได้ แต่ multi-row ยังมี defect; ยังไม่มี full OCR-to-database reconstruction ที่รับรอง |
| B — แทนระบบครบทุก profile | **ยัง blocked**: catalog descriptions/program rules ยังตรวจไม่ครบ และ legacy ยังไม่มี identity หลักสูตร/ฉบับ/แผน ห้ามใช้ partial build แทนทั้งระบบ |

## สารบัญ

- [รับชุดส่งต่อ](#รับชุดส่งต่อ)
- [ติดตั้งครั้งแรก](#ติดตั้งครั้งแรก)
- [Mode A เปิดใช้งาน](#mode-a-เปิดใช้งาน)
- [Mode B สร้างจากต้นฉบับ](#mode-b-สร้างจากต้นฉบับ)
- [หยุด เริ่มใหม่ และ recovery](#หยุด-เริ่มใหม่-และ-recovery)
- [แก้ปัญหา](#แก้ปัญหา)
- [ขอบเขต ไฟล์ และผลวัด](#ขอบเขต-ไฟล์-และผลวัด)
- [ทีมและหลักฐาน](#ทีมและหลักฐาน)

## รับชุดส่งต่อ

ดาวน์โหลดจาก [Release instructor-v8](https://github.com/thanapat6954/isd-2026-cooltone/releases/tag/instructor-v8):

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| [curriculum-project.zip](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v8/curriculum-project.zip) | โค้ดจาก commit ที่ระบุใน manifest; มี README นี้ |
| [runtime-data.zip](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v8/runtime-data.zip) | SQLite 14 ฐาน + PDF 7 เล่ม; จำเป็นทั้งเปิดแอปและ reconstruct |
| [handoff-manifest.json](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v8/handoff-manifest.json) | Commit, SHA256 และขอบเขตของชุดส่งต่อ |
| [VERIFICATION.md](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v8/VERIFICATION.md) | ผลตรวจและข้อจำกัด; ไม่จำเป็นต่อ runtime |

เปิด **PowerShell 7** ในโฟลเดอร์ที่ดาวน์โหลดไฟล์ ตรวจ SHA256 ให้ตรง manifest แล้วแตก ZIP ลงโฟลเดอร์ใหม่ที่ว่าง:

```powershell
Get-FileHash .\curriculum-project.zip -Algorithm SHA256
Get-FileHash .\runtime-data.zip -Algorithm SHA256
Expand-Archive .\curriculum-project.zip -DestinationPath .\curriculum-handoff
Expand-Archive .\runtime-data.zip -DestinationPath .\curriculum-handoff\supplied-artifacts
Set-Location -LiteralPath .\curriculum-handoff\ocr_final
```

ไม่ต้องใช้โฟลเดอร์ LIVE ของผู้พัฒนา โครงสร้างหลังแตก:

```text
curriculum-handoff/
├── README.md
├── AGENTS.md
├── docs/                              คู่มือ รายงาน และ checkpoint
├── supplied-artifacts/runtime-data/
│   ├── manifest.json                  path/hash/source ของ 14 DB และ 7 PDF
│   ├── build-lineage.json             origin ของแต่ละ snapshot
│   ├── data/input/                    PDF ที่ส่งให้
│   └── work/                          SQLite snapshots แยก profile
└── ocr_final/
    ├── frontend/                      เว็บและ citation viewer
    ├── lab10_fastapi/                  API + SQL retrieval
    ├── scr/ocr_system/                 rendering/OCR/parser/SQLite
    ├── scripts/                       setup/build/activate/recovery
    ├── data/source_reviews/           corrections และ page selection ที่เปิดเผย
    ├── data/ground_truth/              evaluation; ห้ามใช้เป็น build/runtime facts
    └── work/                          สร้างเมื่อ restore/build/start
```

v8 ใช้ runtime bundle ที่ hash ตรงกับ v7/v6 เดิม และ pipeline native ที่ตรวจครบสิบ profiles ใน v7 ไม่ต้องใช้ v7.1 patch เพิ่ม ตรวจ fresh-download/startup ของชุดเผยแพร่ตาม [รายงานส่งต่อสุดท้าย](docs/FINAL_INSTRUCTOR_DELIVERY.md) **เก็บ v6/v7 เดิมไม่เปลี่ยน** Native reconstruction สิบ profiles ไม่ใช่ full14replacement และไม่ใช่ vision OCR

## ติดตั้งครั้งแรก

| โปรแกรม | เวอร์ชันที่ทดสอบ / หน้าที่ | ตรวจใน PowerShell |
|---|---|---|
| Windows 11 + PowerShell 7 | ทดสอบ PowerShell 7.6.5; launcher ตรวจ Windows process ownership | `$PSVersionTable.PSVersion` |
| Python 3.11 | ทดสอบ 3.11.9; ยังไม่รับรองรุ่นอื่น | `py -3.11 --version` |
| Ollama | ทดสอบ 0.19.7; บริการ local สำหรับ answering/OCR | `ollama --version` |
| Node.js | เฉพาะ frontend tests; ไม่ต้องมีเพื่อเปิดเว็บ | `node --version` |

ติดตั้ง Python, [PowerShell](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows) และ [Ollama สำหรับ Windows](https://docs.ollama.com/windows) แล้วเปิด Terminal ใหม่ ยังไม่ได้ซ้อมตัวติดตั้ง OS บน Windows เปล่าหรือเครื่องอาจารย์จริง ไม่รับรอง Linux/macOS ในชุด launcher นี้

### สร้าง environment และติดตั้ง packages

จาก `curriculum-handoff/ocr_final/`:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-web-tested.txt
python -m pip check
```

venv แยก packages ของโครงการ ชุดเว็บ pin FastAPI/Uvicorn/Requests/Pydantic/PyMuPDF เวอร์ชันที่ทดสอบ `requirements-web-lock.txt` เก็บ dependency inventory ถ้า `Activate.ps1` ถูก execution policy ปฏิเสธ ใช้ `.\venv\Scripts\python.exe` แทน `python` ทุกคำสั่ง ไม่ต้องแก้ policy ทั้งเครื่อง

### เตรียมบริการและโมเดลสำหรับตอบ

เปิดแอป Ollama แล้วตรวจและดาวน์โหลด model:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
ollama pull qwen3:4b
ollama list
$env:CURRICULUM_OLLAMA_MODEL = 'qwen3:4b'
$env:CURRICULUM_OLLAMA_URL = 'http://127.0.0.1:11434'
```

ถ้ายังไม่มีบริการ เปิด **อีก Terminal** รัน `ollama serve` และคง Terminal นั้นไว้ ไม่เปิดซ้ำเมื่อ `/api/tags` ตอบอยู่แล้ว `qwen3:4b` ใช้สำหรับ answering fallback; launcher ตรวจ model/service ก่อนเริ่ม แม้บางคำถามใช้ SQL โดยตรง **Mode A และ native PDF extraction ไม่ต้องดาวน์โหลด OCR model**

## Mode A เปิดใช้งาน

### Restore ครั้งแรก

จาก `ocr_final/` ที่สร้าง venv แล้ว:

```powershell
.\venv\Scripts\python.exe scripts/runtime_bundle.py restore --bundle ../supplied-artifacts/runtime-data --app-root .
.\venv\Scripts\python.exe scripts/check_setup.py
```

Restore ตรวจ source/DB hashes และ SQLite integrity ก่อนวาง PDF ใน `data/input/` และ DB ใน `work/lab8b_*/curriculum.db` **ไม่เขียนทับ DB เดิม** ต้อง `ready: true` และ `model_installed_and_service_ready: true` Origin เป็น reviewed runtime snapshots ตาม `build-lineage.json` ไม่ใช่ fresh raw OCR

### เปิดเว็บ

```powershell
.\scripts\start_web.ps1 -Port 8000
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

เปิด **http://127.0.0.1:8000/frontend/** ตาม URL ที่ launcher พิมพ์ ตรวจ health `lab8b_module`, `build_id`, `database_root`, `build_contract`, database paths ว่าเป็นโครงการที่แตก ZIP และ queryable DB 14 ฐานใน Mode A

Port เป็นหมายเลข listener ของ server **ไม่ใช่ขั้นตอน PDF processing** หาก 8000 มีโปรแกรมอื่นใช้ เลือก port ว่าง เช่น:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
.\scripts\start_web.ps1 -Port 8005
Invoke-RestMethod http://127.0.0.1:8005/api/health
```

กรณีนี้เปิด **http://127.0.0.1:8005/frontend/** เว็บส่ง requests/citations แบบ same-origin ตาม port จริง อย่าเปิด frontend ด้วย `file://` หรือ server แยก Normal startup ไม่รัน OCR/rebuild และไม่หยุด server ของโครงการอื่น

เลือกหลักสูตร/ฉบับและระบุแผนในคำถาม ตรวจลิงก์หลักฐาน **PDF page** เทียบ **หน้าพิมพ์ในเล่ม** ต้องคง wildcard/แถว “หรือ” เป็นตัวเลือก ไม่บวก alternatives ที่เลือกอย่างใดอย่างหนึ่ง DB ที่ไม่ระบุ prerequisite หมายถึง **ยังไม่ทราบ** ไม่ใช่ “ไม่มี”

## Mode B สร้างจากต้นฉบับ

ทำใน **สำเนาโครงการแยก** เพื่อเก็บ Mode A ใช้งานได้ระหว่างทดลอง [รายงาน AI native](docs/AI_NATIVE_SCOPE_20261011.md) ระบุ scope/inputs/source defects และ coverage ราย profile

| Build | Inputs / reuse | ผลและขอบเขต |
|---|---|---|
| `raw --extraction native --scope academic-plan-only` | PDF + code/config/page selection; ไม่มี DB/old OCR/master/answers | AI: 8 terms, 40 source rows/41 options, 7 placeholders; ถามแผน/ชื่อ/หน่วยกิตได้เมื่อ source review ผ่าน |
| `raw --extraction ocr` | PDF render/preprocess → Typhoon OCR → Qwen parser | OCR จริง; AI attempt เดิมมี material defects ถูก reject ยังไม่ผ่าน reconstruction |
| `raw --extraction native --source-documents` | PDF ใหม่ทั้งเล่ม + code/config | เพิ่ม literal source-page corpus/catalog/rule candidates ใน staged SQLite; **experimental ยังไม่รับรอง catalog/rules ครบ** |
| `reviewed` | fresh outputs + source-approved corrections ที่ hash ตรง | เปิดเผยทุก correction ใน manifest; reviewed ingestion ไม่ใช่ OCR accuracy improvement |

Native ใช้ข้อความเดิมและ table geometry ใน PDF พร้อม render ภาพเพื่อตรวจ ไม่ได้ใช้ vision OCR หาก native text/association ไม่ชัดต้อง reject ไม่สลับไป bundle/curated master โดยเงียบ ไม่ reuse saved OCR เป็น fresh result

### B1 — IT / DSBA / BIT native ที่ source-validated แล้ว

ติดตั้ง dependencies ขั้นตอนแรกแล้ว ไม่ต้องติดตั้ง Typhoon เพื่อ native rebuild เลือก profile pair หนึ่งแถวจากตาราง แล้วใช้ `rebuild --profiles` ตามตัวอย่าง ไม่เติมข้อมูลจาก bundled DB:

| หลักสูตร | ค่า `--profiles` | Source pages / แถวต่อแผน |
|---|---|---|
| IT2565 | `it-no-coop it-coop` | 31–37/38–44 + rule25; 54/54 |
| DSBA2565 | `dsba-no-coop dsba-coop` | 23–29/30–36; 45/45 |
| DSBA2560 | `dsba-2560-no-coop dsba-2560-coop` | 25–29/30–34; 44/44; no-coopมี9terms |
| BIT2560 | `bit-2560-no-coop bit-2560-coop` | 23–26/27–30; 42/42 |
| BIT2565 | `bit-2565-no-coop bit-2565-coop` | 26–30/31–35; 43/43 |

```powershell
.\venv\Scripts\python.exe scripts/database_build.py rebuild --profiles it-no-coop it-coop --mode reviewed --extraction native --scope academic-plan-only --font-review data/source_reviews/font_encoding/thsarabun-source-glyphs-20261011.json
```

คำสั่งแรก reject เพราะยังไม่มี source review เป็น safety gate ไม่ใช่ extraction failure ตรวจภาพทุกหน้า/ปก/SQLfields และ rule25 แล้วบันทึก receipt+validate ด้วยคำสั่งต่อไปนี้ เปลี่ยนเฉพาะค่าprofilesเมื่อต้องการคู่แผนอื่น ทั้ง10profilesสร้างใน source-onlysandboxจากZIPจริงได้ ใช้reviewedfontencodingเท่านั้น **ไม่มีcoursecorrections** ITเลือกทั้งspecializationbundle/sharedcourseอยู่หลายmembershipและcitationแยก35→36/42→43 ไม่สรุปสิทธิผสมรายวิชาข้ามชุด

IT2560ทั้งสองแผนยังreject: supporting-rule scanไปพบWingdings2ที่ยังไม่review; legacyยังไม่resolved Catalogdescriptions/rules/prereqs/fullbookยังไม่สร้างครบ จึงไม่ใช้partial10แทนfull14gate


แทน `<build-id>` ด้วย ID ที่คำสั่งพิมพ์ ตรวจ `raw/<profile>/identity.png`, ทุก `page-*.png`, `page-*.plan.json`, `selection-rule.png` เมื่อมี และ SQLite ให้ครบ codes/ชื่อไทย-อังกฤษ/credits/hour alternatives/placeholder length/bundle/term/plan identity/source pages หากผิดห้ามยืนยัน receipt:

```powershell
$candidate = '.\work\staging\<build-id>'
.\venv\Scripts\python.exe scripts/certify_plan_source.py --candidate $candidate --reviewer 'ชื่อผู้ตรวจ' --confirm-reviewed-all-fields
.\venv\Scripts\python.exe scripts/database_build.py validate --candidate $candidate --scope declared
```

Receiptบันทึกผู้ตรวจ/source/image/DBhashes ไม่เติมหรือแก้facts ต้องตรวจจริงและได้ `ready: true` ก่อนactivate ExistingDBยังใช้ได้ระหว่างbuild; failedbuildเก็บdiagnosticsและไม่เปลี่ยนactivepointer อ่าน [รายงานแยกsource/native/review/runtime](docs/V7_NATIVE_HANDOFF_20261011.md) ตัวอย่าง AIrawnativeที่ผ่านv6เป็นhistorical ไม่อยู่ในfresh10scopeของv7

### B2 — ทดลอง OCR จริงหรือขยาย source corpus (ยัง blocked)

เฉพาะ OCR ต้องเพิ่ม dependencies/model:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-rebuild.txt
ollama pull scb10x/typhoon-ocr1.5-3b:latest
$env:LAB7_MODEL_OCR = 'scb10x/typhoon-ocr1.5-3b:latest'
```

คำสั่งจริงต่อไปนี้เป็น **experimental ที่ยังไม่ผ่าน full replacement**:

```powershell
.\venv\Scripts\python.exe scripts/database_build.py rebuild --profiles ai --mode raw --extraction ocr --stage-timeout 180
.\venv\Scripts\python.exe scripts/database_build.py rebuild --profiles ai --mode raw --extraction native --source-documents --stage-timeout 180
```

HTTP 200/SQLite integrity ไม่พิสูจน์ source fidelity ไม่ rerun OCR configuration ที่ยังผิดโดยไม่มี hypothesis ใหม่ Catalog candidates เก็บ literal prerequisites/fragments รายหน้า ยังไม่สรุป AND/OR หรือสิทธิลงทะเบียน Rule heading อาจเป็นสารบัญ ต้องตรวจ scope/continuation ก่อนใช้ normative facts

Full gate ต้องครบ 13 curriculum/plan + legacy, source-validated descriptions/rules และ receipt ครบ `activate` reject partial/mismatched/unreviewed build ไม่ใช้ bundled DB เติมข้อที่ขาด ไม่อ้างทุก profile สำเร็จจาก AI profile เดียว

## หยุด เริ่มใหม่ และ recovery

ใช้ port เดียวกับที่เริ่ม:

```powershell
.\scripts\stop_web.ps1 -Port 8000
.\scripts\start_web.ps1 -Port 8000
```

Launcher ตรวจ ownership หยุดเฉพาะ backend ของโครงการนี้ ไม่หยุด shared Ollama/แอปอื่น `deactivate` ปิด venv ใน terminal ไม่ใช่ shutdown server

### Activate scope ที่ตรวจแล้ว

B1 สร้าง academic-plan-only candidate ตามค่า `--profiles` ที่เลือกจริง เช่น `it-no-coop it-coop` มีสองแผน IT2565 ส่วน candidate ที่ทดสอบครบมีสิบ profiles ตามตาราง B1 ไม่ใช่ full14replacement ตรวจรายการ profiles, build ID และ declared scope ในผล `validate --scope declared` ก่อนใช้ `activate-scoped` เพราะคำสั่งจะเปลี่ยน active set ทั้งชุดให้เหลือเฉพาะ profiles ใน candidate; profiles อื่นจะไม่พร้อมใช้งาน UI/health/answers ต้องแสดงขอบเขตจริง และไม่อ้าง catalog descriptions/rules/prerequisites/full-book completeness B2 เป็นงานทดลองที่ยัง blocked จึงห้าม activate จน source review และ validation ของขอบเขตที่ประกาศผ่าน:

```powershell
.\scripts\stop_web.ps1 -Port 8000
.\venv\Scripts\python.exe scripts/database_build.py activate-scoped --candidate $candidate
.\scripts\start_web.ps1 -Port 8000
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Activate backup **active DB ทั้งชุด** ด้วย SQLite backup API ไป `work/backups/build-switch/<backup-id>/backup.json` เก็บ hashes/integrity/build identity และ user-added tables แยก ไม่ discard/migrate edits เงียบ สำเนาใหม่อยู่ `work/builds/<build-id>/` เปลี่ยน `work/active-build.json` ครั้งเดียว Runtime pin build ตอน startup/consumer lock ป้องกัน mixed profiles ต้องหยุด backend ของตนก่อนเปลี่ยน

Build/validation failure ไม่เปลี่ยน pointer/DB เก่า Activation failure หลังเปลี่ยน pointer คืน pointer เก่าและเก็บ diagnostics หลังเริ่มตรวจ build ID/paths/readiness/real answers/citations หาก post-activation ไม่ผ่าน คืน backup จริงจาก output:

```powershell
$backup = '.\work\backups\build-switch\<backup-id>'
.\scripts\stop_web.ps1 -Port 8000
.\venv\Scripts\python.exe scripts/database_build.py rollback --backup $backup
.\scripts\start_web.ps1 -Port 8000
```

ห้ามเดา backup ID Native/source/code/config เปลี่ยนใช้ staging ใหม่ OCR resume ใช้ `--resume <candidate>` เฉพาะ hashes ตรงทุกตัว; เก็บ attempts เดิม ไม่ rerun known-bad configuration โดยอัตโนมัติ

## แก้ปัญหา

| อาการ | วิธีแก้ |
|---|---|
| Python/venv หาย | เปิด PowerShell ใหม่ ตรวจ `py -3.11 --version`; สร้าง venv จาก `ocr_final/` |
| Missing PDF/DB | อ่าน `check_setup.py`; restore ในสำเนาใหม่ ไม่ overwrite DB เดิม |
| PDF ตรง hash อยู่แล้ว | restore เพิ่ม `--reuse-verified-pdfs`; ไม่ overwrite source ที่ hash ต่าง |
| Model/service ไม่พร้อม | เปิด Ollama ตรวจ `/api/tags`, `ollama list`, `ollama pull qwen3:4b`; OCR model เฉพาะ `--extraction ocr` |
| Port occupied/wrong root | เลือก port ว่างและ URL ที่พิมพ์ ไม่หยุด listener อื่น |
| Empty OCR/lost code/invented text | เก็บ staging/log/manifest; reject; ตรวจ source และเปลี่ยน hypothesis ก่อนรอบใหม่ |
| Review หาย/partial set | อย่า activate full; ตรวจ declared scope หรือแก้ extraction |
| ไม่พบ prerequisite/วิชา | ไม่สรุปว่าไม่มี ตรวจฉบับ แผน coverage และ source |
| Consumer lock | หยุด backend ของ root/port ที่เป็นเจ้าของก่อน activate |

## ขอบเขต ไฟล์ และผลวัด

| หลักสูตร/ฉบับ | แผน | PDF |
|---|---|---|
| AI 2566 | coop | `AI.pdf` |
| DSBA 2565 / 2560 | coop + no-coop | `DSBA.pdf`, `DSBA-60.pdf` |
| IT 2565 / 2560 | coop + no-coop | `IT.pdf`, `IT-60.pdf` |
| BIT 2565 / 2560 (นานาชาติ) | coop + no-coop | `BIT-65.pdf`, `BIT-60.pdf` |
| legacy mixed catalog | identity ยังไม่ resolved | raw records จาก AI/DSBA/IT ไม่ใช่ profile ใหม่ที่ยืนยัน |

13 selectable profiles + legacy เป็นขอบเขต Mode A ไม่ได้หมายถึง Mode B 14 catalogs สำเร็จ หนังสือ/recorded mappings เป็น authority ไม่ใช้ OCR เป็น independent ground truth ไม่รับรองสิทธิลงทะเบียน/จบหรือการเปิดวิชาแทนสถาบัน

| ที่เก็บ | หน้าที่ |
|---|---|
| `data/input/` | source PDFs หลัง restore; preserve originals |
| `work/staging/<id>/` | executor/raw/parsed/SQLite/build.json/validation.json/checkpoints |
| `work/builds/`, `work/active-build.json` | versioned builds/atomic pointer |
| `work/backups/build-switch/` | DB backup set, user-added data/recovery manifest |
| `work/web/` | logs/owned process records |
| [docs/PROGRESS.md](docs/PROGRESS.md) | checkpoint เดียว CURRENT authoritative |
| `data/source_reviews/` | approved build inputs; manifest เปิดเผย corrections ที่ใช้ |
| `data/ground_truth/`, `tests/qa_gold.json` | development/evaluation เท่านั้น; held-out แยก ไม่ใช้สร้าง facts |

ผลวัด Windows 11/Python 3.11.9/PowerShell 7.6.5, i7-13620H/RAM 15.7 GiB/RTX 5050 Laptop GPU ไม่ใช่ minimum hardware หรือเวลารับรองเครื่องอื่น:

| งานจริง | เวลา/ผล |
|---|---|
| Mode A actual ZIP v7 candidate: venv/packages uncached/restore | 20.84/33.90/14.91 วินาที |
| Qwen v7 empty store download/start/restart | 84.76/5.50/5.12 วินาที; OS installersไม่ได้rehearse |
| Source-only v7 native10plans รวมrender+normalize+SQLite | 172.033 วินาที;56pages/456rows/81terms; ไม่ใช่OCRtime |
| Final10 scoped activate/start/restart/recover14 | 9.898/4.660/4.121/4.424 วินาที;80HTTPbothroutes/สองcycles |

OCR รอบที่ผิดใช้ 150 DPI/temp 0/retries 0, `scb10x/typhoon-ocr1.5-3b:latest`; parser/answer `qwen3:4b` Native ใช้ PyMuPDF 1.28.2/plan render 200 DPI ไม่ใช้ OCR/LLM ไม่แทน OCR timing ด้วย structured-query latency Difficult-generation latency/เครื่องอาจารย์จริง/independent held-out ยังไม่ได้วัดรอบนี้ Browser policy บล็อกรอบ UI click ใหม่ API/PNG/source inspection **ไม่ใช่ browser-click pass**

## ทีมและหลักฐาน

อ่าน [course PDF จริง](docs/references/P2-course-introduction.pdf): PDF4 ระบุ P2 ทำ OCR; PDF5 ให้ image-reading OCR20คะแนนและกำหนดวัดคุณภาพจากภาพจำลอง/จริง; PDF7 ระบุ bonus multiple versions และ difficult answer <5s รวมretrieval+generation **การตีความ:** ไม่พบ native-extraction waiver ในหน้าที่ตรวจ จึงไม่อ้าง native/font decoding เป็น vision OCR หรือเป็นผลผ่านคะแนน OCR; [รายงานแยก explicit/interpretation](docs/SOURCE_SCOPE_REVIEW_20261011.md#rubric-จริง-explicit-กับการตีความ) แยกnative reconstructionออกจากvisionOCRชัดเจนในv7

ข้อมูลเดิมมี Discord handles ยังไม่มีชื่อจริงที่ยืนยัน:

| รหัสนักศึกษา | Discord |
|---|---|
| 67070068 | pleum |
| 67070257 | plattyr.pus |
| 67070289 | nongingfah |
| 67070306 | Skinny legends |

- [AI reconstruction/source defects/scope boundaries](docs/AI_NATIVE_SCOPE_20261011.md)
- [Mode A/B delivery และ safeguards เดิม](docs/TWO_MODE_HANDOFF_20261011.md)
- [Fresh-machine rehearsals/ข้อจำกัด](docs/FRESH_HANDOFF_20261011.md)
- [Dataset/source-approved ingestion](docs/DATASET_ORGANIZATION.md)
- [Independent evaluation protocol](docs/INDEPENDENT_EVALUATION_PROTOCOL.md)
- [CURRENT checkpoint](docs/PROGRESS.md)

Source PDFs เป็นเอกสารหลักสูตรของมหาวิทยาลัย ส่งประกอบโครงงานตามการอนุญาตของผู้ส่ง ไม่อ้างว่าเป็นเจ้าของหรือมี open redistribution license ของหนังสือ ไม่รวม model weights ใน Release; ใช้ model identifiers/บริการตามเงื่อนไขของผู้ให้บริการ


หลักฐาน v6เดิมและhistoricalAI/BITtimingsอ่านใน [รายงานv6](docs/FONT_TABLE_REBUILD_20261011.md#actual-zip-v6);ไม่ใช้แทนผลfreshv7หรือvisionOCR
