import logging
import datetime

logger = logging.getLogger("aishub2nmea")

# AIS 6-bit ASCII Table (ITU-R M.1371)
AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


################################################################################
# Utility Functions
################################################################################

def to_signed(value, bits):
    """Convert a signed integer into two's complement bitstring."""
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), f"0{bits}b")


def sixbit_ascii(text, length):
    """
    Convert text to AIS 6-bit ASCII padded to fixed length.
    AIS uses 6-bit characters: ASCII 32 -> 63.
    """
    if text is None:
        text = ""

    text = text.upper()
    text = "".join(c if 32 <= ord(c) <= 126 else " " for c in text)
    text = text[:length].ljust(length)

    bits = ""
    for char in text:
        code = ord(char) - 32
        if code < 0 or code > 63:
            code = 0
        bits += format(code, "06b")

    return bits


def sixbit_encode(bitstring):
    """
    Convert binary string into AIS 6-bit payload.
    """
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    payload = ""
    for i in range(0, len(bitstring), 6):
        chunk = bitstring[i:i+6]
        payload += AIS_CHARS[int(chunk, 2)]

    fill = (6 - (len(bitstring) % 6)) % 6
    return payload, fill


def nmea_checksum(body):
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"{cs:02X}"


################################################################################
# AIS Message Type 1 (Dynamic Position)
################################################################################

def encode_msg_type1(v):
    """Encode AIS Message Type 1 from AISHub HUMAN FORMAT."""

    try:
        mmsi = int(v["mmsi"])
    except:
        return None, None

    # Human readable lat/lon
    try:
        lat = float(v["lat"])
        lon = float(v["lon"])
    except:
        return None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None

    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    # Navigation status (0–15)
    try:
        navstat = int(v.get("navstat", 15))
    except:
        navstat = 15
    navstat = max(0, min(15, navstat))

    # ROT
    try:
        rot_raw = int(v.get("rot", 128))
    except:
        rot_raw = 128
    if rot_raw in (127, 128, -127):
        rot = 128
    else:
        rot = max(-127, min(127, rot_raw))

    # SOG
    try:
        sog_knots = float(v.get("sog", 0))
    except:
        sog_knots = 0
    if sog_knots < 0.1:
        sog = 0
    elif sog_knots > 102.2:
        sog = 1023
    else:
        sog = int(sog_knots * 10)

    # COG
    try:
        cog_deg = float(v.get("cog", 360))
    except:
        cog_deg = 360
    if cog_deg < 0 or cog_deg >= 360:
        cog = 3600
    else:
        cog = int(cog_deg * 10)

    # Heading
    try:
        heading = int(v.get("heading", 511))
    except:
        heading = 511
    if not (0 <= heading <= 359):
        heading = 511

    # PAC
    accuracy = 1 if int(v.get("accuracy", 0)) else 0

    timestamp = datetime.datetime.utcnow().second  # 0–59

    bits = ""
    bits += format(1, "06b")            # Msg ID
    bits += format(0, "02b")            # Repeat
    bits += format(mmsi, "030b")        # MMSI
    bits += format(navstat, "04b")
    bits += to_signed(rot, 8)
    bits += format(sog, "010b")
    bits += format(accuracy, "01b")
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += format(cog, "012b")
    bits += format(heading, "09b")
    bits += format(timestamp, "06b")
    bits += format(0, "02b")            # Maneuver
    bits += format(0, "01b")            # RAIM
    bits += format(0, "019b")           # Radio status

    if len(bits) != 168:
        logger.error(f"BAD MSG1 LENGTH {len(bits)} for MMSI={mmsi}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


################################################################################
# AIS Message Type 5 (Static & Voyage Data)
################################################################################

def encode_msg_type5(v):
    """
    Encode AIS Message Type 5 using AISHub HUMAN FORMAT.
    Includes:
    Name, Callsign, IMO, Type, Dimensions, Draught, Destination, ETA.
    """

    try:
        mmsi = int(v["mmsi"])
    except:
        return None

    # IMO
    try:
        imo = int(v.get("imo", v.get("IMO", 0)))
    except:
        imo = 0

    callsign = v.get("callsign", v.get("CALLSIGN", "")).upper().strip()
    name = v.get("name", v.get("NAME", "")).upper().strip()
    shiptype = int(v.get("type", v.get("TYPE", 0)))

    # Dimensions
    try:
        dim_a = int(v.get("A", 0))
        dim_b = int(v.get("B", 0))
        dim_c = int(v.get("C", 0))
        dim_d = int(v.get("D", 0))
    except:
        dim_a = dim_b = dim_c = dim_d = 0

    # Draught (metres → AIS units: 0.1 m)
    try:
        draught_m = float(v.get("draught", v.get("DRAUGHT", 0)))
        draught = int(draught_m * 10)
    except:
        draught = 0

    # Destination
    dest = v.get("dest", v.get("DEST", "")).upper().strip()

    # ETA "MM-DD HH:MM"
    eta_raw = v.get("eta", v.get("ETA", ""))
    try:
        month = int(eta_raw[0:2])
        day = int(eta_raw[3:5])
        hour = int(eta_raw[6:8])
        minute = int(eta_raw[9:11])
    except:
        month = day = hour = minute = 0

    # Assemble 424-bit Msg 5
    bits = ""
    bits += format(5, "06b")
    bits += format(0, "02b")
    bits += format(mmsi, "030b")
    bits += format(1, "02b")              # AIS version
    bits += format(imo, "030b")           # IMO

    bits += sixbit_ascii(callsign, 7)
    bits += sixbit_ascii(name, 20)

    bits += format(shiptype, "08b")
    bits += format(dim_a, "09b")
    bits += format(dim_b, "09b")
    bits += format(dim_c, "06b")
    bits += format(dim_d, "06b")

    bits += format(month, "04b")
    bits += format(day, "05b")
    bits += format(hour, "05b")
    bits += format(minute, "06b")

    bits += format(draught, "08b")
    bits += sixbit_ascii(dest, 20)

    bits += format(0, "01b")  # DTE
    bits += format(0, "01b")  # Spare

    if len(bits) != 424:
        logger.error(f"BAD MSG5 LENGTH {len(bits)} for MMSI={mmsi}")
        return None

    # Break into 2 sentences
    # First 360 bits, then remainder
    p1, f1 = sixbit_encode(bits[:360])
    p2, f2 = sixbit_encode(bits[360:])

    return p1, f1, p2, f2


################################################################################
# Batch Encode: Msg 1 + Msg 5 (once per cycle)
################################################################################

def build_nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    return f"!{body}*{nmea_checksum(body)}"


def vessels_to_nmea(vessels):
    out = []

    for v in vessels:
        #
        # Msg 1 (dynamic)
        #
        p, f = encode_msg_type1(v)
        if p:
            out.append(build_nmea_sentence(p, f))

        #
        # Msg 5 (static) — Option A: send once each cycle
        #
        m5 = encode_msg_type5(v)
        if m5:
            p1, f1, p2, f2 = m5

            body1 = f"AIVDM,2,1,,A,{p1},{f1}"
            out.append(f"!{body1}*{nmea_checksum(body1)}")

            body2 = f"AIVDM,2,2,,A,{p2},{f2}"
            out.append(f"!{body2}*{nmea_checksum(body2)}")

    logger.debug(f"Encoded {len(out)} AIS sentences total")
    return out
