"""Render original PDF pages without depending on a browser PDF plug-in."""
import hashlib
from functools import lru_cache
from pathlib import Path
import threading
from contextlib import closing

from fastapi import HTTPException
from .database import open_readonly

ALLOWED = frozenset({'AI.pdf','DSBA.pdf','DSBA-60.pdf','IT.pdf','IT-60.pdf','BIT-65.pdf','BIT-60.pdf'})
RENDER_LOCK = threading.Lock()


def source_path(root, filename):
    path = Path(root)/'data/input'/filename
    if filename not in ALLOWED or not path.is_file():
        raise HTTPException(404, 'ไม่พบเอกสารต้นฉบับที่อนุญาต')
    return path


@lru_cache(maxsize=16)
def document_identity(path, size, modified):
    import pymupdf
    try:
        with Path(path).open('rb') as handle:
            digest=hashlib.file_digest(handle,'sha256').hexdigest()
        with pymupdf.open(path) as document:
            return digest,len(document)
    except (OSError,RuntimeError,ValueError) as exc:
        raise HTTPException(422,'เปิดเอกสารต้นฉบับไม่ได้') from exc


def identity(root, filename, page):
    path=source_path(root,filename)
    stat=path.stat()
    digest,count=document_identity(str(path),stat.st_size,stat.st_mtime_ns)
    if not 1 <= page <= count:
        raise HTTPException(416,'หมายเลขหน้าอยู่นอกเอกสารต้นฉบับ')
    return path,digest,count


def printed_pages(registry, filename, page):
    """Only paired locators stored in SQLite; never infer a constant offset."""
    pages=set()
    for database in registry.active_programs:
        with closing(open_readonly(database.path)) as connection:
            for table in ('plan_item','program','course_prerequisite_evidence','program_requirement'):
                if not database.has(table,'source_file','page_number','printed_page_number'):
                    continue
                rows=connection.execute(f'SELECT DISTINCT printed_page_number FROM {table} WHERE source_file=? AND page_number=?',
                                        (filename,page)).fetchall()
                pages.update(row[0] for row in rows if type(row[0]) is int and row[0]>0)
            for table, pdf_column, book_column in (
                    ('plan_source_claim','pdf_page','printed_page'),
                    ('plan_term_source','pdf_page','printed_page'),
                    ('plan_bundle','rule_pdf_page','rule_printed_page')):
                if database.has(table,'source_file',pdf_column,book_column):
                    rows=connection.execute(f'SELECT DISTINCT {book_column} FROM {table} WHERE source_file=? AND {pdf_column}=?',
                                            (filename,page)).fetchall()
                    pages.update(row[0] for row in rows if type(row[0]) is int and row[0]>0)
    return sorted(pages)


def render_page(root, filename, page):
    import pymupdf
    path,digest,_=identity(root,filename,page)
    cache=Path(root)/'work/source_page_cache'/digest/('pymupdf-'+pymupdf.__version__+'-150dpi')
    target=cache/f'{page}.png'
    with RENDER_LOCK:
        if not target.exists():
            cache.mkdir(parents=True,exist_ok=True)
            stage=target.with_suffix('.partial.png')
            try:
                with pymupdf.open(path) as document:
                    document[page-1].get_pixmap(dpi=150,alpha=False).save(stage)
                stage.replace(target)
            except (OSError,RuntimeError,ValueError) as exc:
                raise HTTPException(503,'แสดงภาพหน้าต้นฉบับไม่ได้ โปรดลองอีกครั้ง') from exc
    return target
