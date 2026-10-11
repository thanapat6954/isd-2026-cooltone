# Vision OCR: การทดลองภาพจริงและภาพจำลอง — 11 ตุลาคม 2026

## Rubric จริงและขอบเขตการวัด

[Course PDF](references/P2-course-introduction.pdf) หน้าPDF4ระบุ P2ทำOCR; PDF5ระบุ image-reading OCR20คะแนนและquantitative evaluationภาพจำลอง/จริง; PDF7bonus difficult retrieval+generation<5s การตีความ: native PDF extraction/font decoding ไม่ใช่หลักฐานผ่านOCR ไม่มีการเปลี่ยน rubric ให้เข้ากับระบบ

Typhoon `scb10x/typhoon-ocr1.5-3b:latest`, digest `483bac0b367b529f874880767af8b183c8d99e64c37105fbe3c5756cf0529b49`; Windows11/i7-13620H/RTX5050Laptop/RAM15.7GiB PDF DSBA27 freshly rendered200DPI temp0/retries0 image-only prompt ไม่มี native text/coursefacts/referenceanswersในmodelinputs

Development transcriptions เขียนจากภาพต้นฉบับเพื่อmeasurementเท่านั้น แยกจากproduction/held-out ไม่ส่งให้model ภาพ synthetic สร้างจากsource-grounded development transcriptionด้วยTahoma31px เป็นsynthetictestdata ไม่ใช้ทำproductionfacts

## ผลจริงแยก real/synthetic

| Configuration / case | Exact code | Exact bilingual names | Exact hour patterns | Row association | เวลา model |
|---|---|---|---|---|---|
| JSON multi-name placeholder / real | 1/1 | literal presence6/6 | 2/2 | manual cell1/1; parser contract0 | 37.471s |
| JSON two rows / real | 1/2 | literal presence2/4 | 2/3 | manual row1/2; parser contract0 | 27.756s |
| JSON two rows / synthetic | 1/2 | literal presence2/4 | 2/3 | manual row1/2; parser contract0 | 19.355s |
| Single-row Markdown / real general | 1/1 | paired2/2 | 2/2 | 1/1 | 34.947s |
| Single-row Markdown / real faculty | 1/1 | paired2/2 | 1/1 | 1/1 | 19.921s |
| Single-row Markdown / synthetic faculty | 1/1 | paired2/2 | 1/1 | 1/1 | 32.626s |

Multi-rowtrialยังผิด: responseไม่ตรงJSONschemaและละแถวสุดท้าย แม้HTTP200 จึงrejectก่อนproductionDB แยกformatcontractออกจาก OCRrecognition การเปลี่ยนรอบถัดไปมีhypothesis: segmentหนึ่งphysicalrowและใช้Markdowntranscriptionที่ตรงtask ไม่มี unchanged failed retry ผลreal2single rows code2/2 names4/4 hours3/3 association2/2; synthetic1row1/1,2/2,1/1,1/1 เป็นtiny selected development cases ไม่ใช่wholepage/fullbook/held-outaccuracy และยังไม่visionOCR→productionSQLiteสำเร็จ

## CER/WER ที่วัดได้

วัดเฉพาะEnglish labels: NFC, whitespaceหนึ่งช่อง, casepreserving CERใช้LevenshteinบนUnicodecodepointsรวมspace; WERtokenregex `[A-Z0-9]+(?:-[A-Z0-9]+)*` ไม่วัดThaiWERเพราะไม่มีwordsegmentationreference Single-rowทุกcaseCER/WER0; multi-nameplaceholder0/90charsและ0/14tokens; two-rowrealและsynthetic CER44/73=60.274%, WER4/8=50% เนื่องจากแถวfacultyหาย ExactThai labelsใช้NFC/whitespacenormalization ไม่รายงานThaiCER/WER หรือfull-pageCER

Source review/native decoding ไม่ถูกนับในOCRmetrics ไม่ใช้จำนวน regressiontestsเป็นOCRaccuracy ชื่อหลายชื่อในsharedcellไม่มีsourceassociationname↔hourรายคู่ จึงไม่สร้างpairที่ไม่มีหลักฐาน

## หลักฐานและข้อจำกัด

`docs/results/source_scope_20261011/ocr-layout-development/` และ `ocr-single-row/` เก็บactualimages/imagehash/modelrequestconfiguration/rawresponse/checkpoint/developmenttranscriptions/metrics ภาพและrawตรวจจริง ไม่ใช่คำตอบmodelตรวจตัวเอง การทดลองก่อนหน้าทั้งtableที่ผิดplaceholderlength/hours/rowspanเก็บใน `dsba27-vision-rejected/` ทุกfailureรักษาไว้ ไม่มีผลOCRถูกactivate ไม่มีIndependentheld-outscoreหรือP2คะแนนที่รับรอง
