"""Hash-chained append-only evidence ledger (stdlib only).

Each entry carries a sequence number, the hash of the previous entry, and a
SHA-256 digest of its canonical payload. Verification recomputes the chain and
reports, deterministically, whether the ledger is intact or has been tampered
with, replayed, or truncated.

No wall-clock timestamps are stored: entries are ordered by sequence number
only, which keeps ledger bytes (and therefore digests) reproducible.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

GENESIS = "0" * 64


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Entry:
    seq: int
    prev_hash: str
    payload: dict
    payload_hash: str = ""
    entry_hash: str = ""

    def __post_init__(self) -> None:
        if not self.payload_hash:
            self.payload_hash = _digest(_canonical(self.payload))
        if not self.entry_hash:
            self.entry_hash = _digest(
                f"{self.seq}|{self.prev_hash}|{self.payload_hash}".encode("utf-8")
            )

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "prev_hash": self.prev_hash,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "entry_hash": self.entry_hash,
        }

    @staticmethod
    def from_dict(d: dict) -> "Entry":
        return Entry(
            seq=d["seq"],
            prev_hash=d["prev_hash"],
            payload=d["payload"],
            payload_hash=d["payload_hash"],
            entry_hash=d["entry_hash"],
        )


@dataclass
class Ledger:
    entries: list = field(default_factory=list)

    @property
    def head_hash(self) -> str:
        return self.entries[-1].entry_hash if self.entries else GENESIS

    def append(self, payload: dict) -> Entry:
        entry = Entry(seq=len(self.entries), prev_hash=self.head_hash, payload=payload)
        self.entries.append(entry)
        return entry

    def to_json(self) -> str:
        return json.dumps([e.to_dict() for e in self.entries], sort_keys=True)

    @staticmethod
    def from_json(text: str) -> "Ledger":
        return Ledger(entries=[Entry.from_dict(d) for d in json.loads(text)])


def verify(ledger: Ledger, expected_head: str | None = None) -> dict:
    """Verify a ledger. Returns {"ok": bool, "problems": [str, ...]}.

    Detects, deterministically:
    - tampering: a payload whose digest no longer matches, or an entry hash
      that no longer matches its (seq, prev_hash, payload_hash);
    - broken links: an entry whose prev_hash is not the previous entry_hash;
    - replay: a duplicated sequence number, a duplicated entry hash, or an
      entry re-appended after the chain moved on (same payload+seq twice);
    - truncation: a gap in sequence numbers, or a head hash that differs from
      an expected head when one is supplied (callers that recorded the head
      at session close detect tail removal even when the remaining chain is
      internally consistent).
    """
    problems: list[str] = []
    seen_seq: set[int] = set()
    seen_hash: set[str] = set()
    prev = GENESIS
    for i, entry in enumerate(ledger.entries):
        if entry.seq in seen_seq:
            problems.append(f"replay: duplicate seq {entry.seq}")
        seen_seq.add(entry.seq)
        if entry.entry_hash in seen_hash:
            problems.append(f"replay: duplicate entry_hash at seq {entry.seq}")
        seen_hash.add(entry.entry_hash)
        if entry.seq != i:
            problems.append(
                f"sequence gap/truncation: entry {i} has seq {entry.seq}, expected {i}"
            )
        if entry.prev_hash != prev:
            problems.append(f"broken link at seq {entry.seq}")
        if entry.payload_hash != _digest(_canonical(entry.payload)):
            problems.append(f"tamper: payload_hash mismatch at seq {entry.seq}")
        recomputed = _digest(
            f"{entry.seq}|{entry.prev_hash}|{entry.payload_hash}".encode("utf-8")
        )
        if entry.entry_hash != recomputed:
            problems.append(f"tamper: entry_hash mismatch at seq {entry.seq}")
        prev = entry.entry_hash
    if expected_head is not None and ledger.head_hash != expected_head:
        problems.append("truncation: head hash differs from expected head")
    return {"ok": not problems, "problems": problems}
