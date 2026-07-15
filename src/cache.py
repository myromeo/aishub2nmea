import time
import logging

logger = logging.getLogger("aishub2nmea")

# How long (seconds) to keep a vessel in the cache after its last sighting
# before dropping it. Bounds memory for vessels that leave the bounding
# box and never come back.
CACHE_TTL = 60 * 60 * 6  # 6 hours


class VesselCache:
    def __init__(self, ttl=CACHE_TTL):
        self.ttl = ttl
        # mmsi -> {"type1": fingerprint, "type5": fingerprint, "last_seen": ts}
        self._store = {}

    @staticmethod
    def _type1_fingerprint(v):
        # Round position to ~1m precision so GPS jitter on a moored/stationary
        # vessel doesn't register as a "change" every single poll.
        return (
            round(v.get("lat") or 0.0, 5),
            round(v.get("lon") or 0.0, 5),
            round(v.get("sog") or 0.0, 1),
            round(v.get("cog") or 0.0, 1),
            v.get("heading"),
            v.get("navstat"),
            v.get("rot"),
        )

    @staticmethod
    def _type5_fingerprint(v):
        return (
            v.get("imo"),
            v.get("callsign"),
            v.get("name"),
            v.get("type"),
            v.get("a"), v.get("b"), v.get("c"), v.get("d"),
            v.get("draught"),
            v.get("dest"),
            v.get("eta"),
        )

    def filter_changed(self, vessels):
        """
        Returns (type1_vessels, type5_vessels): only the vessels whose
        relevant fields changed since we last saw them, or that we've
        never seen before.
        """
        now = time.time()
        type1_out, type5_out = [], []

        for v in vessels:
            mmsi = v.get("mmsi")
            if not mmsi:
                continue

            entry = self._store.setdefault(
                mmsi, {"type1": None, "type5": None, "last_seen": now}
            )
            entry["last_seen"] = now

            fp1 = self._type1_fingerprint(v)
            if fp1 != entry["type1"]:
                entry["type1"] = fp1
                type1_out.append(v)

            fp5 = self._type5_fingerprint(v)
            if fp5 != entry["type5"]:
                entry["type5"] = fp5
                type5_out.append(v)

        return type1_out, type5_out

    def prune(self):
        """Drop vessels not seen recently, to keep memory bounded."""
        cutoff = time.time() - self.ttl
        stale = [m for m, e in self._store.items() if e["last_seen"] < cutoff]
        for m in stale:
            del self._store[m]
        if stale:
            logger.debug(f"Pruned {len(stale)} stale vessels from cache")