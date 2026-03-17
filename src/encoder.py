import logging
import datetime

logger = logging.getLogger("aishub2nmea")

AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


###############################################################################
# Utility helpers
###############################################################################

def sixbit_encode(bits):
    while len(bits) % 6:
        bits += "0"

    out = ""
    for i in range(0, len(bits), 6):
        out += AIS_CHARS[int(bits[i:i+6], 2)]

    fill = (6 - (len(bits) % 6)) % 6
    return out, fill


def to_signed(value, bits):
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), f"0{bits}b")


def safe_float(v, default=0.0):
    try:
        return float(v)
    except:
        return default


def safe_int(v, default=0):
    try:
        return int(float(v))
    except:
        return default


def sixbit_ascii(text, length):
    if not text:
        text = ""
    text = text.upper()[:length].ljust(length)
    bits = ""
    for c in text:
        code = ord(c) - 32
        if code < 0 or code > 63:
            code = 0
        bits += f"{code:06b}"
    return bits


###############################################################################
# DEBUG PRINTER
###############################################################################

def debug_bits(label, bits):
    logger.error(f"===== DEBUG {label} (TOTAL {len(bits)} BITS) =====")
    for i in range(0, len(bits), 32):
        segment = bits[i:i+32]
        logger.error(f"{i:03d}-{i+len(segment):03d}: {segment} (len={len(segment)})")
    logger.error("=======================================")


###############################################################################
# MESSAGE TYPE 1 — dynamic
###############################################################################

def encode_msg_type1(v):
    """Debug version with bit printing"""

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
    if rot_raw in (127, 128, -127):
        rot = 128
    else:
        rot = max(-127, min(127, rot_raw))

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
    if not (0 <= heading <= 359):
        heading = 511

    accuracy = 1 if safe_int(v.get("accuracy"), 0) else 0

    timestamp = datetime.datetime.utcnow().second

    bits = ""
    bits += "000001"                      # msg ID
    bits += "00"                          # repeat
    bits += f"{mmsi:030b}"
    bits += f"{navstat:04b}"
    bits += to_signed(rot, 8)
    bits += f"{sog:010b}"
    bits += f"{accuracy:01b}"
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += f"{cog:012b}"
    bits += f"{heading:09b}"
    bits += f"{timestamp:06b}"
    bits += "00"                          # maneuver
    bits += "0"                           # raim
    bits += "0" * 19                      # radio status

    # PRINT DEBUG
    debug_bits(f"MSG1 FOR MMSI {mmsi}", bits)

    if len(bits) != 168:
        logger.error(f"BAD MSG1 LENGTH {len(bits)} INBOUND DATA={v}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


###############################################################################
# MESSAGE TYPE 5 — static & voyage
###############################################################################

def encode_msg_type5(v):
    """Debug version with bit printing"""

    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi:
        return None

    imo = safe_int(v.get("imo"), 0)
    callsign = v.get("callsign", "")
    name = v.get("name", "")
    shiptype = safe_int(v.get("type"), 0)

    dim_a = safe_int(v.get("A"), 0)
    dim_b = safe_int(v.get("B"), 0)
    dim_c = safe_int(v.get("C"), 0)
    dim_d = safe_int(v.get("D"), 0)

    draught = int(safe_float(v.get("draught"), 0) * 10)

    dest = v.get("dest", "")

    eta = v.get("eta", "")
    try:
        month = int(eta[0:2])
        day = int(eta[3:5])
        hour = int(eta[6:8])
        minute = int(eta[9:11])
    except:
        month = day = hour = minute = 0

    bits = ""
    bits += f"{5:06b}"
    bits += "00"
    bits += f"{mmsi:030b}"
    bits += f"{1:02b}"
    bits += f"{imo:030b}"
    bits += sixbit_ascii(callsign, 7)
    bits += sixbit_ascii(name, 20)
    bits += f"{shiptype:08b}"
    bits += f"{dim_a:09b}"
    bits += f"{dim_b:09b}"
    bits += f"{dim_c:06b}"
    bits += f"{dim_d:06b}"
    bits += f"{month:04b}"
    bits += f"{day:05b}"
    bits += f"{hour:05b}"
    bits += f"{minute:06b}"
    bits += f"{draught:08b}"
    bits += sixbit_ascii(dest, 20)
    bits += "0"
    bits += "0"

    # PRINT DEBUG
    debug_bits(f"MSG5 FOR MMSI {mmsi}", bits)

    if len(bits) != 424:
        logger.error(f"BAD MSG5 LENGTH {len(bits)} INPUT={v}")
        return None

    p1, f1 = sixbit_encode(bits[:360])
    p2, f2 = sixbit_encode(bits[360:])
    return p1, f1, p2, f2


###############################################################################
# Batch builder
###############################################################################

def nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    return f"!{body}*{nmea_checksum(body)}"


def nmea_checksum(body):
    c = 0
    for ch in body:
        c ^= ord(ch)
    return f"{c:02X}"


def vessels_to_nmea(vessels):
    out = []
    for v in vessels:

        p1, f1 = encode_msg_type1(v)
        if p1:
            out.append(nmea_sentence(p1, f1))

        msg5 = encode_msg_type5(v)
        if msg5:
            pa, fa, pb, fb = msg5

            body1 = f"AIVDM,2,1,,A,{pa},{fa}"
            out.append(f"!{body1}*{nmea_checksum(body1)}")

            body2 = f"AIVDM,2,2,,A,{pb},{fb}"
            out.append(f"!{body2}*{nmea_checksum(body2)}")

    return out
``
