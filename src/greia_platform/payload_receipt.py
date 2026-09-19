"""Shared payload-receipt schema owner (R4-G3-RECEIPT-HARDENING).

Single neutral owner for ``PAYLOAD_RECEIPT_SCHEMA_VERSION`` importable by
both ``tools/build_release.py`` (producer) and ``tools/greia_update.py``
(consumer). Lives in ``greia_platform`` because both tools already depend
on that package, carries no update-service composition dependency, no new
heavy dependency, and no import cycle (standalone, stdlib only).

Field names (schema_version, payload_sha256, payload_compressed_bytes,
payload_uncompressed_bytes, minimum_slot_bytes, profile_id, release_id)
are stable for Session 03 release CLI work.
"""

from __future__ import annotations

PAYLOAD_RECEIPT_SCHEMA_VERSION = 1
