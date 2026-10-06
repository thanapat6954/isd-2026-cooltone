# การสร้าง branch 2026-10-07

ผู้ใช้ขอสร้าง branch บน GitHub จึงเผยแพร่เฉพาะ commit ที่มีอยู่ ไม่สร้าง commit จากงานแก้ local ไม่ push main ไม่สร้าง PR หรือ merge

`git fetch origin` สำเร็จ exit 0 (ไม่มี output)

ก่อนสร้าง branch `git ls-remote --heads origin week11_thanapat main`:

```text
9b8c20c7611da50f9de0de4855266b96d42992ed refs/heads/main
```

`git push --set-upstream origin HEAD:refs/heads/week11_thanapat` สำเร็จ exit 0:

```text
remote:
remote: Create a pull request for 'week11_thanapat' on GitHub by visiting:
remote:      https://github.com/thanapat6954/isd-2026-cooltone/pull/new/week11_thanapat
remote:
branch 'week11_thanapat' set up to track 'origin/week11_thanapat'.
To https://github.com/thanapat6954/isd-2026-cooltone.git
 * [new branch]      HEAD -> week11_thanapat
```

ข้อความแนะนำ PR เป็น output ของ Git เท่านั้น ไม่ได้เปิด PR

หลังสร้าง `git ls-remote --heads origin week11_thanapat main`:

```text
9b8c20c7611da50f9de0de4855266b96d42992ed refs/heads/main
d051d7c3d3e961fa6b55b1e5299acc71ab9c2ba2 refs/heads/week11_thanapat
```

งานแก้ code/README/scripts/tests/reports ล่าสุดยัง uncommitted จึงยังไม่อยู่บน remote branch
