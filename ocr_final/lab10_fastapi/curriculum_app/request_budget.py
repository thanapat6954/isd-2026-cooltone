"""One monotonic deadline shared by retrieval, SQL repair and generation."""
from contextvars import ContextVar
import time

REQUEST_DEADLINE = ContextVar('curriculum_request_deadline', default=None)
TIMEOUT_MESSAGE = 'หมดเวลาประมวลผลคำถาม ไม่สามารถยืนยันคำตอบได้ กรุณาลองใหม่'


def expired():
    deadline = REQUEST_DEADLINE.get()
    return deadline is not None and time.perf_counter() >= deadline


def check_deadline():
    if expired():
        raise TimeoutError(TIMEOUT_MESSAGE)


def remaining(default):
    check_deadline()
    deadline = REQUEST_DEADLINE.get()
    return default if deadline is None else min(default, deadline-time.perf_counter())
