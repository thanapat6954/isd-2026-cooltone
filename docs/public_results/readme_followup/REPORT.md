# ตรวจคู่มือ startup เพิ่มเติม — 2026-10-07

## ขอบเขต

ต่อจาก README verification เดิม หลัง recreate branch locally ไม่ทำ audit หนังสือหรือ baseline ที่ผ่านแล้วซ้ำ ใช้ current application source เดิมใน isolated runtime snapshot 14 DB/7 PDF และ model service ที่มีอยู่ ไม่แก้ DB production หรือ facts

## ผลตรวจ

| การตรวจ | ผลสังเกต | หลักฐาน |
|---|---|---|
| manual Uvicorn ใน isolated folder ที่มีช่องว่าง | พร้อมพอร์ต8001; frontend แสดง IT2560-no-coop4ปี/PDF6/หน้า1ในเล่ม; console=[] | [UI raw](manual_ui.json), [ภาพ](manual_ui.png) |
| Ctrl+C ใน foreground terminal | Shutting down → Application shutdown complete → Finished server process35272; พอร์ต8001ว่าง | [raw](manual_shutdown.json) |
| launcher guard เมื่อพอร์ต8000เป็นคนละโฟลเดอร์ | exit1ตามที่คาด; ไม่หยุด process เดิม | [ผล](retry/launcher.json) |
| alternate start / start ซ้ำ / stop | exit0ทั้ง3; ไม่สร้างอีกserverเมื่อพร้อมแล้ว; พอร์ต8001ว่างหลังstop | [ผล](retry/launcher.json) |
| snapshot DB | 14/14 SHA256เหมือนเดิม | [ผล](retry/launcher.json) |
| focused tests | 14ผ่าน/15กรณี; 1 skipped เพราะ Git checkout ไม่มี generated DB | [raw](focused_tests.log) |
| focused tests พร้อม isolated DB | 15/15ผ่าน ไม่มี skipped; ตั้ง CURRICULUM_TEST_ROOT ไปsnapshotแล้วตรวจแบบread-only | [raw](focused_tests_with_db.log) |
| README links / PDF transport | 26/26local links และ7/7PDF routesผ่าน | [raw](links.json) |

manual sessionคืนexit1เมื่อส่งCtrl+C ไม่ใช่exit0; ยืนยันการหยุดจาก shutdown logและพอร์ตว่าง ไม่ถือว่าexit1ทุกแบบคือสำเร็จ ใช้ existing venv/model files และ snapshot เดิม ไม่หยุด model service ของผู้ใช้ ไม่ทำ database migration

## สิ่งที่แก้

root README เพิ่ม tested PowerShell7.6.5, ขั้นตอนเลือกพอร์ตอื่นพร้อมstopที่ใช้เลขเดียวกัน, health summary และหลักฐานmanual fallback เพิ่ม `scripts/verify_launcher_commands.py` เพื่อตรวจcommandจริงในisolatedapp พร้อม `tests/test_launcher_verification.py`

ครั้งแรก verifier อ่านข้อความPowerShellที่ตัดบรรทัดไม่ครบ จึงรายงานfailทั้งที่ guardทำงาน เก็บ [ผลแรก](launcher.json) แล้วแก้เฉพาะ CLI text normalization เพิ่มregression3กรณีและrerunสำเร็จ ไม่แก้production launcher/API/answersเพื่อให้ผ่าน

## รันซ้ำ

จาก `ocr_final/` โดยเปลี่ยน isolated app path เป็นsnapshotของตนเอง พอร์ต8001ต้องว่างและ8000ต้องเป็นbackendจากอีกโฟลเดอร์สำหรับguardcase:

```powershell
.\venv\Scripts\python.exe scripts/verify_launcher_commands.py --app-root '<isolated-app-folder>' --output ../docs/results/readme_followup/retry/launcher.json
.\venv\Scripts\python.exe -m unittest tests.test_launcher_verification tests.test_web_routing tests.test_week11_handoff -v
```

หากต้องการรัน DB integration ด้วย ให้ตั้ง `$env:CURRICULUM_TEST_ROOT='<isolated-app-folder>'` ก่อน unittest แล้วอ่าน skipped counts เสมอ บริการ live8000 PID28104/Ollama11434 PID19364คงอยู่หลังทดสอบ พอร์ต8001หยุดแล้ว ไม่มีjobค้าง

## ยังไม่ยืนยัน

ไม่ rerun full OCR/model download/OSอื่น หรือ independent book-wide evaluation; reuseผลพื้นฐานเดิมที่dependenciesไม่เปลี่ยน Windows PowerShell5.1และGitHub rendererยังไม่ทดสอบ ไม่มีcommit/push/merge
