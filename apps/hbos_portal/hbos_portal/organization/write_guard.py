"""Private per-document write capability, never read from HTTP or Document.flags."""
from contextlib import contextmanager
from contextvars import ContextVar

_permit = ContextVar("hbos_organization_write_permit", default=None)


@contextmanager
def _controlled_write(doctype, name):
    token = _permit.set((doctype, name))
    try:
        yield
    finally:
        _permit.reset(token)


def is_controlled_write(doctype, name):
    return _permit.get() == (doctype, name)
