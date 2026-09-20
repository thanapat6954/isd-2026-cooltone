# ระบบ OCR และ RAG สำหรับข้อมูลหลักสูตร

## วิธีติดตั้งและใช้งาน

### 1. เตรียม Python และไลบรารี

แนะนำ Python 3.11 จากนั้นเปิด PowerShell ที่โฟลเดอร์โครงการแล้วรัน:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
python -m pip install --upgrade pip
pip install pydantic requests pymupdf pillow pdfplumber pythainlp matplotlib
```

ไม่ต้องคัดลอก `venv/` หรือ `.venv/` จากเครื่องอื่น ให้สร้างใหม่ด้วยคำสั่งข้างต้น

### 2. ติดตั้ง Ollama และโมเดล

ติดตั้ง Ollama แล้วดาวน์โหลดโมเดลที่โครงการใช้:

```powershell
ollama pull scb10x/typhoon-ocr1.5-3b:latest
ollama pull qwen3:4b
ollama serve
```

หาก Ollama ทำงานอยู่แล้ว ไม่ต้องเปิด `ollama serve` ซ้ำ ตรวจสอบความพร้อมได้ด้วย:

```powershell
python .\scr\ocr_system\lab7b_curriculum.py --check
```

### 3. เตรียมไฟล์ PDF

วางไฟล์ต่อไปนี้ใน `data/input/` โดยใช้ชื่อตรงตามนี้:

```text
data/input/AI.pdf
data/input/DSBA.pdf
data/input/IT.pdf
```

ไฟล์ AI และ IT มีขนาดเกินข้อจำกัดการอัปโหลดปกติของ GitHub จึงควรใช้ Git LFS หรือระบุลิงก์ดาวน์โหลดไว้แทน

### 4. รัน pipeline

รันทุกหลักสูตรและทุกแผน:

```powershell
python .\run_lab8b.py --program all
```

หรือรันเฉพาะ profile:

```powershell
python .\run_lab8b.py --program dsba-coop
python .\run_lab8b.py --program dsba-no-coop
python .\run_lab8b.py --program ai
python .\run_lab8b.py --program it-coop
python .\run_lab8b.py --program it-no-coop
```

ผลลัพธ์ของแต่ละ profile จะอยู่ใน `work/lab8b_<profile>/` โดยมีผล OCR, JSON, SQLite, verification และ evaluation แยกกัน

### 5. ถามคำถามจากฐานข้อมูล

ตัวอย่างการถามคำถามจากฐานข้อมูล DSBA แผน coop:

```powershell
python .\scr\ocr_system\lab8b_curriculum_db.py ask -d .\work\lab8b_dsba_coop\curriculum.db -q "หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต"
```

เปลี่ยน path ของฐานข้อมูลเพื่อถาม profile อื่นได้

### 6. รัน robustness evaluation

```powershell
python .\robustness_eval.py --program all --repeats 3
```

คำสั่งนี้จะอัปเดต `work/robustness_summary.json` และรายงานย่อยในโฟลเดอร์ `robustness/` ของแต่ละ profile

### 7. สร้างส่วนผลประเมินใน README ใหม่

ห้ามแก้ข้อความระหว่าง comment `EVAL:START` และ `EVAL:END` ด้วยตนเอง ให้สร้างจาก JSON ด้วยคำสั่ง:

```powershell
python .\scripts\make_eval_summary.py --json .\work\robustness_summary.json --readme .\README.md
```

### 8. รัน tests

```powershell
python -m unittest discover -s tests -v
```

ควรรัน tests และตรวจว่า verification ผ่านก่อน push ขึ้น GitHub

<!-- EVAL:START -->
## สรุปผลการประเมินและการวิเคราะห์ระบบ

### 1. สรุปย่อ

- **ความสามารถของระบบ:** ทุก profile ตอบชุด held-out ได้ครบและให้ผลคงที่เมื่อทดสอบซ้ำ; citation coverage ครบทุก profile
- **จุดที่ต้องปรับปรุง:** `prereq` เป็นปัญหาที่มีผลกระทบสูงสุด ดูรายละเอียดและรายการอื่นในหัวข้อ 8
- **ความน่าเชื่อถือของข้อมูลประเมิน:** ปานกลาง: ผลคงที่ทุก profile ที่มีข้อมูล แต่ชุด held-out ที่เล็กที่สุดมีเพียง n=12 จึงยังมีความไม่แน่นอนแม้คะแนนจะเต็ม
- **ข้อจำกัดของ abstention:** การประเมิน abstention มีคำถามที่ควร abstain เพียง n=2 ต่อ profile ดังนั้นคะแนนเต็มในส่วนนี้ยังเป็นหลักฐานที่อ่อน

### 1.1 profile ที่ใช้ประเมิน

| profile | program | variant | source folder ภายใต้ `work/` | มี OCR ground truth |
| :--- | :--- | :--- | :--- | :--- |
| `dsba-coop` | DSBA | coop | `work/lab8b_dsba_coop` | มี |
| `ai` | AI | แผนเดียว | `work/lab8b_ai` | มี |
| `it-coop` | IT | coop | `work/lab8b_it_coop` | มี |
| `it-no-coop` | IT | no-coop | `work/lab8b_it_no_coop` | มี |
| `dsba-no-coop` | DSBA | no-coop | `work/lab8b_dsba_no_coop` | มี |

JSON key `dsba` ชี้ไปที่ `work/lab8b_dsba_coop` จึงแสดงชื่อเป็น `dsba-coop` ตาม [robustness_eval.py](robustness_eval.py)

### 2. ภาพรวมผลประเมินแยกตาม profile

| profile | OCR F1 | ความแม่นยำ held-out (ถูก/ทั้งหมด) | citation coverage | abstain Precision / Recall | ความคงที่ | latency เฉลี่ย (วินาที) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dsba-coop` | 92.1% (n=44) | 12/12 (100.0%) | 100.0% (n=12) | 100.0% / 100.0% (n=2) | คงที่ | 1.14 (n=12) |
| `ai` | 91.4% (n=41) | 12/12 (100.0%) | 100.0% (n=12) | 100.0% / 100.0% (n=2) | คงที่ | 1.01 (n=12) |
| `it-coop` | 93.2% (n=53) | 12/12 (100.0%) | 100.0% (n=12) | 100.0% / 100.0% (n=2) | คงที่ | 1.06 (n=12) |
| `it-no-coop` | 93.5% (n=54) | 12/12 (100.0%) | 100.0% (n=12) | 100.0% / 100.0% (n=2) | คงที่ | 1.03 (n=12) |
| `dsba-no-coop` | 94.4% (n=45) | 12/12 (100.0%) | 100.0% (n=12) | 100.0% / 100.0% (n=2) | คงที่ | 1.29 (n=12) |

### 3. ผล OCR แยกตาม attribute

#### ผล alignment ระดับรายวิชา

| profile | Precision | Recall | matched | missed | spurious | GT (n) | prediction (n) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dsba-coop` | 91.1% | 93.2% | 41 | 3 | 4 | 44 | 45 |
| `ai` | 92.5% | 90.2% | 37 | 4 | 3 | 41 | 40 |
| `it-coop` | 96.0% | 90.6% | 48 | 5 | 2 | 53 | 50 |
| `it-no-coop` | 94.3% | 92.6% | 50 | 4 | 3 | 54 | 53 |
| `dsba-no-coop` | 95.5% | 93.3% | 42 | 3 | 2 | 45 | 44 |

#### รายละเอียด profile หลัก (`dsba-coop`)

| attribute | จำนวนตัวอย่าง (n) | CER | WER | Exact Match |
| :--- | :--- | :--- | :--- | :--- |
| รหัสวิชา | 41 | 0.0% | n/a | 100.0% |
| ชื่อวิชา (ไทย) ⭐ | 41 | 0.9% | 10.4% | 82.9% |
| ชื่อวิชา (อังกฤษ) ⭐ | 41 | 3.7% | 4.3% | 95.1% |
| หน่วยกิต | 41 | 14.6% | n/a | 87.8% |
| ปี/ภาค | 41 | 0.0% | n/a | 100.0% |
| หมวดวิชา | 41 | 1.7% | n/a | 97.6% |
| บังคับ/เลือก | 41 | 7.5% | n/a | 92.7% |
| วิชาบังคับก่อน | 41 | 18.2% | n/a | 87.8% |
| ปี/ภาคยืดหยุ่น | 41 | 0.0% | n/a | 100.0% |

<details>
<summary>คลิกเพื่อดูผล OCR ของ profile อื่น</summary>

#### `ai`

| attribute | n | CER | WER | Exact Match |
| :--- | :--- | :--- | :--- | :--- |
| รหัสวิชา | 37 | 0.0% | n/a | 100.0% |
| ชื่อวิชา (ไทย) ⭐ | 37 | 4.3% | 2.1% | 97.3% |
| ชื่อวิชา (อังกฤษ) ⭐ | 37 | 1.9% | 4.1% | 91.9% |
| หน่วยกิต | 37 | 0.0% | n/a | 100.0% |
| ปี/ภาค | 37 | 0.0% | n/a | 100.0% |
| หมวดวิชา | 37 | 0.0% | n/a | 100.0% |
| บังคับ/เลือก | 37 | 8.3% | n/a | 91.9% |
| วิชาบังคับก่อน | 37 | 21.2% | n/a | 86.5% |
| ปี/ภาคยืดหยุ่น | 37 | 0.0% | n/a | 100.0% |

#### `it-coop`

| attribute | n | CER | WER | Exact Match |
| :--- | :--- | :--- | :--- | :--- |
| รหัสวิชา | 48 | 0.0% | n/a | 100.0% |
| ชื่อวิชา (ไทย) ⭐ | 48 | 12.2% | 26.8% | 81.2% |
| ชื่อวิชา (อังกฤษ) ⭐ | 48 | 1.5% | 1.8% | 95.8% |
| หน่วยกิต | 48 | 0.7% | n/a | 97.9% |
| ปี/ภาค | 48 | 0.0% | n/a | 100.0% |
| หมวดวิชา | 48 | 0.0% | n/a | 100.0% |
| บังคับ/เลือก | 48 | 29.5% | n/a | 70.8% |
| วิชาบังคับก่อน | 48 | 18.6% | n/a | 87.5% |
| ปี/ภาคยืดหยุ่น | 48 | 0.0% | n/a | 100.0% |

#### `it-no-coop`

| attribute | n | CER | WER | Exact Match |
| :--- | :--- | :--- | :--- | :--- |
| รหัสวิชา | 50 | 0.0% | n/a | 100.0% |
| ชื่อวิชา (ไทย) ⭐ | 50 | 15.5% | 22.0% | 82.0% |
| ชื่อวิชา (อังกฤษ) ⭐ | 50 | 8.5% | 11.0% | 90.0% |
| หน่วยกิต | 50 | 1.3% | n/a | 96.0% |
| ปี/ภาค | 50 | 0.0% | n/a | 100.0% |
| หมวดวิชา | 50 | 0.0% | n/a | 100.0% |
| บังคับ/เลือก | 50 | 30.6% | n/a | 70.0% |
| วิชาบังคับก่อน | 50 | 25.4% | n/a | 80.0% |
| ปี/ภาคยืดหยุ่น | 50 | 0.0% | n/a | 100.0% |

#### `dsba-no-coop`

| attribute | n | CER | WER | Exact Match |
| :--- | :--- | :--- | :--- | :--- |
| รหัสวิชา | 42 | 0.0% | n/a | 100.0% |
| ชื่อวิชา (ไทย) ⭐ | 42 | 10.2% | 27.3% | 81.0% |
| ชื่อวิชา (อังกฤษ) ⭐ | 42 | 14.4% | 16.9% | 83.3% |
| หน่วยกิต | 42 | 13.9% | n/a | 88.1% |
| ปี/ภาค | 42 | 0.0% | n/a | 100.0% |
| หมวดวิชา | 42 | 0.0% | n/a | 100.0% |
| บังคับ/เลือก | 42 | 12.3% | n/a | 88.1% |
| วิชาบังคับก่อน | 42 | 40.5% | n/a | 71.4% |
| ปี/ภาคยืดหยุ่น | 42 | 0.0% | n/a | 100.0% |

</details>

#### ตัวอย่างข้อผิดพลาดจริงจากระบบ

| profile | attribute / คำถาม | เฉลย | ผลลัพธ์จริง | ลักษณะข้อผิดพลาด |
| :--- | :--- | :--- | :--- | :--- |
| dsba-no-coop | วิชาบังคับก่อน / 06026201 | 06026200 | ไม่มี | CER 40.5%; Exact Match 71.4% |
| it-no-coop | บังคับ/เลือก / 06016414 | บังคับ | เลือก | CER 30.6%; Exact Match 70.0% |
| it-coop | บังคับ/เลือก / 06016414 | บังคับ | เลือก | CER 29.5%; Exact Match 70.8% |
| it-no-coop | วิชาบังคับก่อน / 06016419 | 06016413 | ไม่มี | CER 25.4%; Exact Match 80.0% |
| ai | วิชาบังคับก่อน / 06046401 | 06046400 | ไม่มี | CER 21.2%; Exact Match 86.5% |

<details>
<summary>ตัวอย่าง error samples ทั้งหมดของ `dsba-no-coop` สำหรับ `name_th`, `name_en` และ `prereq`</summary>

#### error samples ของ `dsba-no-coop`

##### `name_th`

| key | gt | pred | class |
| :--- | :--- | :--- | :--- |
| 06066303 | การแก้ปัญหาและโปรแกรมคอมพิวเตอร์ | การแก้ปัญหาและการโปรแกรมคอมพิวเตอร์ | spelling |
| 90644xxx | วิชาเลือกภาษาและการสื่อสาร | วิชาเลือกด้านภาษาและการสื่อสาร | spelling |
| 06026xxx | วิชาเลือกกลุ่มวิทยาการข้อมูล 1 / กลุ่มการวิเคราะห์เชิงสถิติ 1 / กลุ่มวิศวกรรมข้อมูล 1 | วิชาเลือกกลุ่มวิทยาการข้อมูล 1<br>วิชาเลือกกลุ่มการวิเคราะห์เชิงสถิติ 1<br>วิชาเลือกกลุ่มวิศวกรรมข้อมูล 1 | truncation |
| 06026xxx | วิชาเลือกกลุ่มวิทยาการข้อมูล 2 / กลุ่มการวิเคราะห์เชิงสถิติ 2 / กลุ่มวิศวกรรมข้อมูล 2 | วิชาเลือกกลุ่มวิทยาการข้อมูล 2<br>วิชาเลือกกลุ่มการวิเคราะห์เชิงสถิติ 2<br>วิชาเลือกกลุ่มวิศวกรรมข้อมูล 2 | truncation |
| 90644042 | การสื่อสารและการนำเสนออย่างมืออาชีพ | การสื่อสารและการนำเสนอดอย่างมืออาชีพ | spelling |

##### `name_en`

| key | gt | pred | class |
| :--- | :--- | :--- | :--- |
| 90642033 | LAW FOR NEW GENERATION | None | other |
| 9064xxxx | ELECTIVE IN GENERAL EDUCATION | ELECTIVE IN GENERAL EDUCATION<br>ELECTIVE IN GENERAL EDUCATION | truncation |
| 06026xxx | ELECTIVE IN DATA SCIENCE 1 / STATISTICAL ANALYSIS 1 / DATA ENGINEERING 1 | ELECTIVE IN DATA SCIENCE<br>ELECTIVE IN STATISTICAL ANALYSIS 1<br>ELECTIVE IN DATA ENGINEERING 1 | truncation |
| 06026xxx | ELECTIVE IN DATA SCIENCE 2 / STATISTICAL ANALYTICS 2 / DATA ENGINEERING 2 | ELECTIVE IN DATA SCIENCE 2<br>ELECTIVE IN STATISTICAL ANALYTICS 2<br>ELECTIVE IN DATA ENGINEERING 2 | truncation |
| 06026xxx | ELECTIVE IN DATA SCIENCE 3 / STATISTICAL ANALYTICS 3 / DATA ENGINEERING 3 | ELECTIVE IN DATA SCIENCE 3<br>ELECTIVE IN STATISTICAL ANALYTICS 3<br>ELECTIVE IN DATA ENGINEERING 3 | truncation |

##### `prereq`

| key | gt | pred | class |
| :--- | :--- | :--- | :--- |
| 06026201 | 06026200 | ไม่มี | other |
| 06066102 | 06066101 | ไม่มี | other |
| 06026212 | 06066300 | ไม่มี | other |
| 9064xxxx | None | ไม่มี | other |
| 06026213 | 06066300 | ไม่มี | other |

</details>

### 4. ผลการประเมิน RAG (RAG Evaluation)

| profile | held-out | count | none | set | value | ผล not found ที่ถูกต้อง | abstain Precision | false abstains | real answer Recall | จำนวนรอบ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dsba-coop` | 12/12 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 6/6 (100.0%) | 100.0% (n=2) | 100.0% | 0/10 | 100.0% (n=10) | 3 |
| `ai` | 12/12 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 6/6 (100.0%) | 100.0% (n=2) | 100.0% | 0/10 | 100.0% (n=10) | 3 |
| `it-coop` | 12/12 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 6/6 (100.0%) | 100.0% (n=2) | 100.0% | 0/10 | 100.0% (n=10) | 3 |
| `it-no-coop` | 12/12 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 6/6 (100.0%) | 100.0% (n=2) | 100.0% | 0/10 | 100.0% (n=10) | 3 |
| `dsba-no-coop` | 12/12 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 6/6 (100.0%) | 100.0% (n=2) | 100.0% | 0/10 | 100.0% (n=10) | 3 |

การตรวจความคงที่เปรียบเทียบ SQL, แถวผลลัพธ์, ข้อความคำตอบ, citation และข้อผิดพลาดจากการรันซ้ำแบบ deterministic ตาม [robustness_eval.py](robustness_eval.py) และ [lab8b_curriculum_db.py](scr/ocr_system/lab8b_curriculum_db.py)

### 5. เปรียบเทียบ baseline v1 กับผลปัจจุบัน

| profile / metric | ความแม่นยำ baseline v1 | ความแม่นยำปัจจุบัน | ผลต่าง (Δ) | baseline F1 | F1 ปัจจุบัน |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dsba-coop` | 10/12 (83.3%) | 12/12 (100.0%) | +16.7 pp | 92.1% (n=44) | 92.1% (n=44) |
| `ai` | 10/12 (83.3%) | 12/12 (100.0%) | +16.7 pp | 91.4% (n=41) | 91.4% (n=41) |
| `it-coop` | 10/12 (83.3%) | 12/12 (100.0%) | +16.7 pp | 93.2% (n=53) | 93.2% (n=53) |
| `it-no-coop` | 10/12 (83.3%) | 12/12 (100.0%) | +16.7 pp | 93.5% (n=54) | 93.5% (n=54) |
| `dsba-no-coop` | n/a | 12/12 (100.0%) | n/a | n/a | 94.4% (n=45) |

profile ที่ไม่มี baseline_v1 report เพราะไม่เคยวัดก่อน current version: `dsba-no-coop` ดังนั้นคอลัมน์ baseline จึงเป็น n/a โดยตั้งใจ ไม่ใช่ข้อมูลสูญหาย

OCR F1 เท่าเดิมจาก baseline v1 ในทุก profile ที่มีข้อมูล ดังนั้นคะแนนความแม่นยำที่เพิ่มขึ้นมาจากฝั่ง RAG เท่านั้น

### 6. แนวทางตีความ metric และผลกระทบ

| metric | ค่าสูงหมายถึง | ค่าต่ำหมายถึง | ผลกระทบต่อระบบ |
| :--- | :--- | :--- | :--- |
| Course-level Recall (alignment) | ดึงข้อมูลได้ครบถ้วน | รายวิชาหรือข้อมูลสูญหายจาก DB | รายวิชาหายและอาจทำให้นักศึกษาจัดแผนเรียนผิด |
| Course-level Precision (alignment) | ข้อมูลที่ดึงมาถูกต้องและไม่มีข้อมูลแต่งขึ้น | มีข้อมูลขยะหรือวิชาที่ไม่มีอยู่จริง | ข้อมูลเท็จอาจถูกบันทึกลงฐานข้อมูล |
| CER / WER | มีข้อผิดพลาดระดับอักขระหรือคำจำนวนมาก | มีข้อผิดพลาดด้านอักขระหรือคำน้อย | ชื่อวิชาและเงื่อนไขอาจเปลี่ยนความหมาย |
| Exact Match | ค่าที่สกัดได้ตรงกับเฉลยเป็นสัดส่วนสูง | ค่าที่สกัดได้ไม่ตรงกับเฉลยหลายรายการ | ค่าที่ผิดอาจถูกนำไปตอบผู้ใช้หรือบันทึกลง DB |
| abstain Precision | การ abstain ส่วนใหญ่เกิดกับคำถามที่ไม่มีคำตอบจริง | ระบบ abstain ทั้งที่ฐานข้อมูลมีคำตอบ | ผู้ใช้ต้องตรวจสอบหรือค้นหาคำตอบเองเพิ่มขึ้น |
| false abstain | ระบบปฏิเสธคำถามจำนวนมากทั้งที่มีคำตอบ | ระบบแทบไม่ปฏิเสธคำถามที่มีคำตอบ | ผู้ใช้อาจไม่ได้รับข้อมูลที่มีอยู่ใน DB |
| abstain Recall | ระบบ abstain ได้ครบเมื่อคำถามไม่มีคำตอบ | ระบบยังพยายามตอบบางคำถามที่ไม่มีคำตอบ | เพิ่มความเสี่ยงที่ระบบจะแต่งคำตอบเมื่อไม่มีข้อมูล |
| citation coverage | คำตอบมีแหล่งอ้างอิงครบถ้วน | คำตอบไม่มีแหล่งอ้างอิง | ตรวจสอบความถูกต้องและความน่าเชื่อถือได้ยาก |

**หมายเหตุ:** ภาษาไทยไม่มีช่องว่างคั่นระหว่างคำ ค่า WER จึงขึ้นกับวิธีตัดคำ และอาจสูงแม้ CER ต่ำเมื่อข้อผิดพลาดกระจายอยู่ในหลายคำ

### 7. การตรวจ overfitting และความน่าเชื่อถือของข้อมูล

- **ขนาดชุดประเมิน:** `dsba-coop`: held-out n=12, OCR GT n=44; `ai`: held-out n=12, OCR GT n=41; `it-coop`: held-out n=12, OCR GT n=53; `it-no-coop`: held-out n=12, OCR GT n=54; `dsba-no-coop`: held-out n=12, OCR GT n=45 ชุด held-out ที่เล็กที่สุดมี n=12 และต้องรายงานขนาดตัวอย่างควบคู่กับคะแนน
- **การตรวจคะแนนเต็ม:** JSON ยืนยันคะแนนและขนาดตัวอย่างได้ แต่ยืนยันไม่ได้ว่าคำถามเคยถูกใช้ระหว่างการพัฒนาหรือไม่
- **ความต่างระหว่าง profile และ shortcut learning:** คะแนน RAG เท่ากันทุก profile ขณะที่ผล OCR แตกต่างกัน แต่ JSON สรุปนี้ยังไม่เพียงพอที่จะตัดความเป็นไปได้ของ shortcut learning จากรูปแบบคำถาม
- **ข้อจำกัดของ abstention:** การประเมิน abstention มีคำถามที่ควร abstain เพียง n=2 ต่อ profile ดังนั้นคะแนนเต็มในส่วนนี้ยังเป็นหลักฐานที่อ่อน

#### เปรียบเทียบ known-gold กับ held-out

| profile | known-gold (ถูก/ทั้งหมด) | held-out (ถูก/ทั้งหมด) | ผลต่าง (Δ) |
| :--- | :--- | :--- | :--- |
| `dsba-coop` | 30/30 (100.0%) | 12/12 (100.0%) | 0.0 pp |
| `ai` | 30/30 (100.0%) | 12/12 (100.0%) | 0.0 pp |
| `it-coop` | 30/30 (100.0%) | 12/12 (100.0%) | 0.0 pp |
| `it-no-coop` | 30/30 (100.0%) | 12/12 (100.0%) | 0.0 pp |
| `dsba-no-coop` | 30/30 (100.0%) | 12/12 (100.0%) | 0.0 pp |

### 8. ปัญหาที่พบและขั้นตอนถัดไป

**กฎการแยก `name_th`:** จัดเป็น truncation / merged row / label bleed-in ก่อน เมื่อ pred เป็น strict subset ของ gt หรือมีข้อความหัวข้อเกินมา เช่น “กลุ่มวิชาด้าน”; รายการที่เหลือจัดเป็น row misalignment เมื่อ char-level similarity ต่ำกว่า 0.50 หรือ pred ตรงกับชื่อรายวิชาอื่นใน GT เต็มของ profile; นอกเหนือจากนั้นจัดเป็นข้อผิดพลาดระดับการสะกด

**หมายเหตุเกี่ยวกับ error samples:** JSON เก็บได้ไม่เกิน 5 รายการต่อ attribute ต่อ profile ดังนั้นจำนวน pattern มาจากตัวอย่างที่บันทึกไว้ ส่วนจำนวนข้อผิดพลาดทั้ง attribute เป็น estimate

1. **วิกฤต:** `prereq` จาก error samples ที่บันทึกไว้ 25 รายการ; pred=“ไม่มี” ทั้งที่ gt ระบุ prerequisite 20/25 รายการ, pred=None ซึ่งหมายถึง extraction ไม่ได้ค่า 4/25 รายการ และ other 1/25 รายการ (`dsba-no-coop/9064xxxx`); รวม 25/25 รายการ; ข้อผิดพลาดทั้ง attribute โดยประมาณ 38/218 รายการ (estimate จาก round(n × (1 - Exact Match))) ผลกระทบคือผู้ใช้อาจได้รับแจ้งว่าไม่มี prerequisite ทั้งที่มีอยู่จริง
2. **วิกฤต:** `name_th` จาก error samples ที่บันทึกไว้ 21 รายการ; พบ row misalignment 3/21 รายการ (`it-coop/06016422`, `it-no-coop/06016422`, `it-no-coop/06016423`); ข้อผิดพลาดทั้ง attribute โดยประมาณ 34/218 รายการ (estimate จาก round(n × (1 - Exact Match))) ซึ่งอาจแสดงชื่อรายวิชาผิดรายการ
3. **สำคัญ:** `name_th` จาก error samples ที่บันทึกไว้ 21 รายการ; พบ truncation / merged row / label bleed-in 4/21 รายการ (`ai/06046443 หรือ 06046444`, `it-coop/06016421`, `dsba-no-coop/06026xxx`, `dsba-no-coop/06026xxx`); ข้อผิดพลาดทั้ง attribute โดยประมาณ 34/218 รายการ (estimate จาก round(n × (1 - Exact Match))) ซึ่งอาจแสดงชื่อรายวิชาไม่ครบหรือปนข้อความหัวข้อ
4. **สำคัญ — Ground-truth review candidates:** `name_th` จำนวน 7 รายการที่ pred ดูเป็นรูปสะกดภาษาไทยมาตรฐานมากกว่า gt: `dsba-coop/90641001` (gt=“โรงเรียนสร้างเสน่าห์”, pred=“โรงเรียนสร้างเสน่ห์”); `dsba-coop/06026205` (gt=“การตลาดเบื้อต้น”, pred=“การตลาดเบื้องต้น”); `dsba-coop/06066304` (gt=“การวิเคราะห์และอออกแบบระบบสารสนเทศ”, pred=“การวิเคราะห์และออกแบบระบบสารสนเทศ”); `it-coop/06066301` (gt=“โครงสร้างข้อมูลและอัลกอรึทึม”, pred=“โครงสร้างข้อมูลและอัลกอริทึม”); `it-coop/06016412` (gt=“โครงสร้างระบบคอมพิวเตอร์และระบบปฎิบัติการ”, pred=“โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ”); `it-no-coop/06066301` (gt=“โครงสร้างข้อมูลและอัลกอรึทึม”, pred=“โครงสร้างข้อมูลและอัลกอริทึม”); `it-no-coop/06016412` (gt=“โครงสร้างระบบคอมพิวเตอร์และระบบปฎิบัติการ”, pred=“โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ”) ต้องตรวจด้วยตนเองกับ source PDF; หาก OCR ถูกต้อง ให้แก้ GT แล้วรัน evaluation ใหม่ โดยยังไม่สรุปว่า GT ผิด
5. **สำคัญ:** `ctype` จาก error samples ที่บันทึกไว้ 21 รายการ; พบทิศทาง gt→pred: บังคับ→เลือก 21/21; ข้อผิดพลาดทั้ง attribute โดยประมาณ 40/218 รายการ (estimate จาก round(n × (1 - Exact Match))) ซึ่งอาจทำให้ผู้ใช้เข้าใจประเภทวิชาผิด
6. **สำคัญ:** `credits` จาก error samples ที่บันทึกไว้ 13 รายการ; ทางเลือกที่มีคำว่า “หรือ” ใน gt ถูกตัดเหลือเพียงรูปแบบเดียว 10/13 รายการ และ wrong pattern 3/13 รายการ; ข้อผิดพลาดทั้ง attribute โดยประมาณ 13/218 รายการ (estimate จาก round(n × (1 - Exact Match))) ซึ่งอาจแสดงรูปแบบหน่วยกิตให้ผู้ใช้ไม่ครบหรือผิดรูปแบบ
7. **เล็กน้อย:** `name_th` จาก error samples ที่บันทึกไว้ 21 รายการ; พบข้อผิดพลาดระดับการสะกด 14/21 รายการ; ข้อผิดพลาดทั้ง attribute โดยประมาณ 34/218 รายการ (estimate จาก round(n × (1 - Exact Match))) ซึ่งมีผลกระทบต่ำกว่า row misalignment

---

*สร้างสรุปนี้ใหม่ด้วยคำสั่ง:* `python scripts/make_eval_summary.py --json work/robustness_summary.json --readme README.md`

#### สิ่งที่ยังยืนยันไม่ได้

- JSON ไม่เก็บตัวหาร n ของ abstain Precision จึงยืนยันได้เฉพาะค่าร้อยละ
- JSON ยืนยันไม่ได้ว่าคำถาม held-out เคยถูกใช้ในขั้นพัฒนาหรือไม่
- การแยก row misalignment เป็น heuristic จาก char-level similarity และการเทียบ GT จึงยังยืนยันสาเหตุเชิงกระบวนการไม่ได้
<!-- EVAL:END -->
