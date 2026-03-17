import logging
import datetime

logger = logging.getLogger("aishub2nmea")

AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


###############################################################################
# UTILITIES — SAFE PARSING
###############################################################################

def safe_int(v, default=0):
    try:
        return int(float(v))
    except:
        return default

def safe_float(v, default=0.0):
    try:
        return float(v)
    except:
        return default


def to_signed(value, bits):
    """Convert int to two's complement binary."""
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), f"0{bits}b")


def sixbit_ascii(text, length):
    """Convert string to AIS 6-bit ASCII padded to length."""
    if text is None:
        text = ""
    text = text.upper()[:length].ljust(length)
    bits = ""
    for c in text:
        code = ord(c) - 32
        if not (0 <= code <= 63):
            code = 0
        bits += format(code, "06b")
    return bits


def sixbit_encode(bits):
    """Binary → 6-bit AIS payload."""
    while len(bits) % 6 != 0:
        bits += "0"
    payload = ""
    for i in range(0, len(bits), 6):
        payload += AIS_CHARS[int(bits[i:i+6], 2)]
    fill = (6 - len(bits) % 6) % 6
    return payload, fill


def nmea_checksum(body):
    c = 0
    for ch in body:
        c ^= ord(ch)
    return f"{c:02X}"


###############################################################################
# MESSAGE TYPE 1 — DYNAMIC POSITION
###############################################################################

def encode_msg_type1(v):

    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi:
        return None, None

    lat = safe_float(v.get("lat"), None)
    lon = safe_float(v.get("lon"), None)
    if lat is None or lon is None:
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None

    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    navstat = safe_int(v.get("navstat"), 15)
    navstat = max(0, min(15, navstat))

    rot_raw = safe_int(v.get("rot"), 128)
    rot = 128 if rot_raw in (127, 128, -127) else max(-127, min(127, rot_raw))

    sog_kts = safe_float(v.get("sog"), 0)
    if sog_kts < 0.1:
        sog = 0
    elif sog_kts > 102.2:
        sog = 1023
    else:
        sog = int(sog_kts * 10)

    cog_deg = safe_float(v.get("cog"), 360)
    if cog_deg < 0 or cog_deg >= 360:
        cog = 3600
    else:
        cog = int(cog_deg * 10)

    heading = safe_int(v.get("heading"), 511)
    if heading < 0 or heading > 359:
        heading = 511

    accuracy = 1 if safe_int(v.get("accuracy"), 0) else 0

    timestamp = datetime.datetime.utcnow().second

    bits = ""
    bits += format(1, "06b")
    bits += format(0, "02b")
    bits += format(mmsi, "030b")
    bits += format(navstat, "04b")
    bits += to_signed(rot, 8)
    bits += format(sog, "010b")
    bits += format(accuracy, "01b")
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += format(cog, "012b")
    bits += format(heading, "09b")
    bits += format(timestamp, "06b")
    bits += format(0, "02b")
    bits += format(0, "01b")
    bits += format(0, "019b")

    if len(bits) != 168:
        logger.error(f"MSG1 BAD LENGTH {len(bits)} for MMSI={mmsi}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


###############################################################################
# MESSAGE TYPE 5 — STATIC / VOYAGE DATA
###############################################################################

def encode_msg_type5(v):

    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi:
        return None

    imo = safe_int(v.get("imo") or v.get("IMO") or "0", 0)
    callsign = v.get("callsign") or v.get("CALLSIGN") or ""
    name     = v.get("name") or v.get("NAME") or ""
    shiptype = safe_int(v.get("type") or v.get("TYPE"), 0)

    dim_a = safe_int(v.get("A"), 0)
    dim_b = safe_int(v.get("B"), 0)
    dim_c = safe_int(v.get("C"), 0)
    dim_d = safe_int(v.get("D"), 0)

    draught_m = safe_float(v.get("draught") or v.get("DRAUGHT"), 0.0)
    draught = min(255, max(0, int(draught_m * 10)))

    dest = (v.get("dest") or v.get("DEST") or "").upper()

    eta_raw = v.get("eta") or v.get("ETA") or ""
    try:
        month  = int(eta_raw[0:2])
        day    = int(eta_raw[3:5])
        hour   = int(eta_raw[6:8])
        minute = int(eta_raw[9:11])
    except:
        month = day = hour = minute = 0

    bits = ""
    bits += format(5, "06b")
    bits += format(0, "02b")
    bits += format(mmsi, "030b")
    bits += format(1, "02b")              # AIS version
    bits += format(imo, "030b")

    bits += sixbit_ascii(callsign, 7)
    bits += sixbit_ascii(name, 20)

    bits += format(shiptype, "08b")
    bits += format(dim_a, "09b")
    bits += format(dim_b, "09b")
    bits += format(dim_c, "06b")
    bits += format(dim_d, "06b")

    bits += format(month,  "04b")
    bits += format(day,    "05b")
    bits += format(hour,   "05b")
    bits += format(minute, "06b")

    bits += format(draught, "08b")
    bits += sixbit_ascii(dest, 20)

    bits += format(0, "01b")  # DTE
    bits += format(0, "01b")  # spare

    if len(bits) != 424:
        logger.error(f"MSG5 BAD LENGTH {len(bits)} for MMSI={mmsi}")
        return None

    # Fragment into two sentences (2-fragment AIS)
    p1, f1 = sixbit_encode(bits[:360])
    p2, f2 = sixbit_encode(bits[360:])

    return p1, f1, p2, f2


###############################################################################
# BATCH MODE — generate Msg1 + Msg5 per vessel
###############################################################################

def build_nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    return f"!{body}*{nmea_checksum(body)}"


def vessels_to_nmea(vessels):
    out = []

    for v in vessels:

        # MSG 1
        p, f = encode_msg_type1(v)
        if p:
            out.append(build_nmea_sentence(p, f))

        # MSG 5
        m5 = encode_msg_type5(v)
        if m5:
            p1, f1, p2, f2 = m5

            body1 = f"AIVDM,2,1,,A,{p1},{f1}"
            out.append(f"!{body1}*{nmea_checksum(body1)}")

            body2 = f"AIVDM,2,2,,A,{p2},{f2}"
            out.append(f"!{body2}*{nmea_checksum(body2)}")

    logger.info(f"Encoded {len(out)} AIS messages total")
    return out
