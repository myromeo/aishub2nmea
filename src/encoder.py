import logging
import datetime

logger = logging.getLogger("aishub2nmea")

AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


###############################################################################
# Utility functions
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
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), "0{}b".format(bits))

def sixbit_ascii(text, length):
    if not text:
        text = ""
    text = text.upper()
    text = text[:length].ljust(length)

    bits = ""
    for c in text:
        code = ord(c) - 32
        if code < 0 or code > 63:
            code = 0
        bits += "{:06b}".format(code)

    return bits

def sixbit_encode(bitstring):
    """Binary → 6-bit AIS ASCII."""
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    payload = ""
    for i in range(0, len(bitstring), 6):
        payload += AIS_CHARS[int(bitstring[i:i+6], 2)]

    fill = (6 - (len(bitstring) % 6)) % 6
    return payload, fill

def nmea_checksum(body):
    c = 0
    for ch in body:
        c ^= ord(ch)
    return "{:02X}".format(c)


###############################################################################
# Debug printer
###############################################################################

def debug_bits(label, bits, mmsi):
    logger.error("===== DEBUG {} FOR MMSI {} ({} bits) =====".format(label, mmsi, len(bits)))
    for i in range(0, len(bits), 32):
        segment = bits[i:i+32]
        logger.error("{:03d}-{:03d}: {} (len={})".format(i, i+len(segment), segment, len(segment)))
    logger.error("===============================================")


###############################################################################
# AIS MESSAGE TYPE 1 — dynamic position
###############################################################################

def encode_msg_type1(v):
    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi:
        return None, None

    # Human-readable degrees
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

    rot_in = safe_int(v.get("rot"), 128)
    if rot_in in (127, 128, -127):
        rot = 128
    else:
        rot = max(-127, min(127, rot_in))

    sog_knots = safe_float(v.get("sog"), 0)
    if sog_knots < 0.1:
        sog = 0
    elif sog_knots > 102.2:
        sog = 1023
    else:
        sog = int(sog_knots * 10)

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
    bits += "000001"                          # Msg ID
    bits += "00"                              # Repeat
    bits += "{:030b}".format(mmsi)
    bits += "{:04b}".format(navstat)
    bits += to_signed(rot, 8)
    bits += "{:010b}".format(sog)
    bits += "{:01b}".format(accuracy)
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += "{:012b}".format(cog)
    bits += "{:09b}".format(heading)
    bits += "{:06b}".format(timestamp)
    bits += "00"                              # Maneuver
    bits += "0"                               # RAIM
    bits += "0" * 19                          # Radio

    # DEBUG BEFORE PADDING
    debug_bits("MSG1 PRE-PAD", bits, mmsi)

    # FORCE CORRECT LENGTH (critical fix)
    bits = bits.ljust(168, "0")

    # DEBUG AFTER PADDING
    debug_bits("MSG1 POST-PAD", bits, mmsi)

    payload, fill = sixbit_encode(bits)
    return payload, fill


###############################################################################
# AIS MESSAGE TYPE 5 — static / voyage data
###############################################################################

def encode_msg_type5(v):
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

    draught_m = safe_float(v.get("draught"), 0.0)
    draught = int(draught_m * 10)

    dest = v.get("dest", "")

    # ETA "MM-DD HH:MM"
    eta = v.get("eta", "")
    try:
        month = int(eta[0:2])
        day = int(eta[3:5])
        hour = int(eta[6:8])
        minute = int(eta[9:11])
    except:
        month = day = hour = minute = 0

    bits = ""
    bits += "{:06b}".format(5)               # Msg 5
    bits += "00"                             # Repeat
    bits += "{:030b}".format(mmsi)
    bits += "01"                             # AIS version
    bits += "{:030b}".format(imo)
    bits += sixbit_ascii(callsign, 7)
    bits += sixbit_ascii(name, 20)
    bits += "{:08b}".format(shiptype)
    bits += "{:09b}".format(dim_a)
    bits += "{:09b}".format(dim_b)
    bits += "{:06b}".format(dim_c)
    bits += "{:06b}".format(dim_d)
    bits += "{:04b}".format(month)
    bits += "{:05b}".format(day)
    bits += "{:05b}".format(hour)
    bits += "{:06b}".format(minute)
    bits += "{:08b}".format(draught)
    bits += sixbit_ascii(dest, 20)
    bits += "0"
    bits += "0"

    # DEBUG BEFORE PADDING
    debug_bits("MSG5 PRE-PAD", bits, mmsi)

    # FORCE CORRECT LENGTH
    bits = bits.ljust(424, "0")

    # DEBUG AFTER PADDING
    debug_bits("MSG5 POST-PAD", bits, mmsi)

    p1, f1 = sixbit_encode(bits[:360])
    p2, f2 = sixbit_encode(bits[360:])
    return p1, f1, p2, f2


###############################################################################
# Batch builder
###############################################################################

def nmea_sentence(payload, fill):
    body = "AIVDM,1,1,,A,{},{}".format(payload, fill)
    return "!{}*{}".format(body, nmea_checksum(body))

def vessels_to_nmea(vessels):
    out = []

    for v in vessels:
        # Message 1
        p, f = encode_msg_type1(v)
        if p:
            out.append(nmea_sentence(p, f))

        # Message 5
        result = encode_msg_type5(v)
        if result:
            p1, f1, p2, f2 = result

            body1 = "AIVDM,2,1,,A,{},{}".format(p1, f1)
            out.append("!{}*{}".format(body1, nmea_checksum(body1)))

            body2 = "AIVDM,2,2,,A,{},{}".format(p2, f2)
            out.append("!{}*{}".format(body2, nmea_checksum(body2)))

    return out
