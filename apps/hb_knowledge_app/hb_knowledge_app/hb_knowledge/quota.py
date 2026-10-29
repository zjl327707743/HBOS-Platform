"""One HBOS-owned quota port. This implementation proves only single-process atomics."""
from __future__ import annotations
import threading
import time
from .errors import KnowledgeError

class InMemoryQuota:
    test_only = True
    def __init__(self, clock=time.time):
        self.clock, self.lock = clock, threading.RLock()
        self.requests, self.characters, self.identities = {}, {}, {}

    def reserve_request(self, subject, request_id, fingerprint, *, limit=12):
        with self.lock:
            identity = (subject, request_id)
            prior = self.identities.get(identity)
            if prior is not None:
                if prior != fingerprint:
                    raise KnowledgeError("REPLAY_REJECTED")
                return
            key = (subject, int(self.clock() // 60))
            current = self.requests.get(key, 0)
            if current >= limit:
                raise KnowledgeError("RATE_LIMITED")
            self.requests[key] = current + 1
            self.identities[identity] = fingerprint

    def reserve_output(self, subject, codepoints, *, limit=30000):
        if type(codepoints) is not int or codepoints < 0:
            raise KnowledgeError("INVALID_REQUEST")
        with self.lock:
            key = (subject, int(self.clock() // 60))
            current = self.characters.get(key, 0)
            if current + codepoints > limit:
                raise KnowledgeError("EXTRACTION_LIMITED")
            self.characters[key] = current + codepoints

    def counts(self, subject):
        with self.lock:
            key = (subject, int(self.clock() // 60))
            return self.requests.get(key, 0), self.characters.get(key, 0)
