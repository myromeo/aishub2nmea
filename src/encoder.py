import logging
import datetime

logger = logging.getLogger("aishub2nmea")

AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


###############################################################################
# Utility helpers
###############################################################################

def sixbit_encode(bits):
    """Convert binary to 6-bit AIS payload string."""
    while len(bits) % 6:
        bits += "0"

    out = ""
    for i in range(0, len(bits), 6):
        out += AIS_CHARS[int(bits[i:i+6], 2)]

    fill = (6 - (len(bits) % 6)) % 6
    return out, fill


def to_signed(val, bits):
    """Convert int to 2's complement bitstring."""
    if val < 0:
        val = (1 << bits) + val
    return format(val & ((1 << bits) - 1), f"0{bits}b")


def sixbit_ascii(s, length):
    """Encode text field to AIS sixbit ASCII."""
    if not s:
        s = ""
    s = s.upper()[:length].ljust(length)
    bits = ""
    for ch in s:
        code = ord(ch) - 32
        if not (0 <= code <= 63):
            code = 0
        bits += f"{code:06b}"
    return bits


###############################################################################
# AIS MESSAGE TYPE 1 — DYNAMIC POSITION
###############################################################################

def encode_msg_type1(v):
    """
    Encodes AIS Message Type 1 for AISHub HUMAN FORMAT
    """

    try:
        mmsi = int(v["mmsi"])
    except:
        return None, None

    try:
        lat = float(v["lat"])
        lon = float(v["lon"])
    except:
        return None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None

    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    navstat = int(v["navstat"])
    navstat = max(0, min(15, navstat))

    # COG
    cog_deg = float(v["cog"])
    if cog_deg < 0 or cog_deg >= 360:
        cog = 3600
    else:
        cog = int(cog_deg * 10)

    # SOG
    sog_kts = float(v["sog"])
    if sog_kts < 0.1:
        sog = 0
    elif sog_kts > 102.2:
        sog = 1023
    else:
        sog = int(sog_kts * 10)

    # Heading
    heading = int(float(v["heading"]))
    if not (0 <= heading <= 359):
        heading = 511

    # ROT
    rot_raw = int(float(v["rot"]))
    if rot_raw in (127, 128, -127):
        rot = 128
    else:
        rot = max(-127, min(127, rot_raw))

    accuracy = 1 if int(v["accuracy"]) else 0

    timestamp = datetime.datetime.utcnow().second

    bits = ""
    bits += "000001"                       # msg type 1
    bits += "00"                           # repeat
    bits += f"{mmsi:030b}"                 # MMSI
    bits += f"{navstat:04b}"
    bits += to_signed(rot, 8)
    bits += f"{sog:010b}"
    bits += f"{accuracy:01b}"
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += f"{cog:012b}"
    bits += f"{heading:09b}"
    bits += f"{timestamp:06b}"
    bits += "00"                           # maneuver
    bits += "0"                            # RAIM
    bits += "0" * 19                       # radio

    if len(bits) != 168:
        logger.error(f"Msg1 wrong length {len(bits)}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


###############################################################################
# AIS MESSAGE TYPE 5 — STATIC & VOYAGE DATA
###############################################################################

def encode_msg_type5(v):
    """
    Encode AIS Message Type 5 from AISHub HUMAN XML
    """

    try:
        mmsi = int(v["mmsi"])
    except:
        return None

    imo = int(float(v.get("imo", 0)))
    callsign = v.get("callsign", "")
    name = v.get("name", "")
    shiptype = int(float(v.get("type", 0)))

    # Dimensions A,B,C,D
    dim_a = int(float(v.get("A", 0)))
    dim_b = int(float(v.get("B", 0)))
    dim_c = int(float(v.get("C", 0)))
    dim_d = int(float(v.get("D", 0)))

    # Draught (AIS = 0.1 m)
    draught = int(float(v.get("draught", 0)) * 10)

    # Destination
    dest = v.get("dest", "").upper().strip()

    # ETA: MM-DD HH:MM
    eta = v.get("eta", "")
    try:
        month = int(eta[0:2])
        day = int(eta[3:5])
        hour = int(eta[6:8])
        minute = int(eta[9:11])
    except:
        month = day = hour = minute = 0

    bits = ""
    bits += f"{5:06b}"                     # msg type 5
    bits += "00"                           # repeat
    bits += f"{mmsi:030b}"
    bits += f"{1:02b}"                     # AIS version
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
    bits += "0"                            # DTE
    bits += "0"                            # spare

    if len(bits) != 424:
        logger.error(f"Msg5 wrong length {len(bits)}")
        return None

    # Two fragments
    p1, f1 = sixbit_encode(bits[:360])
    p2, f2 = sixbit_encode(bits[360:])
    return p1, f1, p2, f2


###############################################################################
# Batch assembly
###############################################################################

def nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    return f"!{body}*{nmea_checksum(body)}"


def nmea_checksum(body):
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"{cs:02X}"


def vessels_to_nmea(vessels):
    out = []

    for v in vessels:

        # Msg 1
        p1, f1 = encode_msg_type1(v)
        if p1:
            out.append(nmea_sentence(p1, f1))

        # Msg 5
        msg5 = encode_msg_type5(v)
        if msg5:
            p1, f1, p2, f2 = msg5

            body1 = f"AIVDM,2,1,,A,{p1},{f1}"
            out.append(f"!{body1}*{nmea_checksum(body1)}")

            body2 = f"AIVDM,2,2,,A,{p2},{f2}"
            out.append(f"!{body2}*{nmea_checksum(body2)}")

    return out
