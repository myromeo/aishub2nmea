import logging
import datetime

logger = logging.getLogger("aishub2nmea")

# AIS 6-bit encoding table
AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


def to_signed(value, bits):
    """Signed integer to two's complement."""
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), f"0{bits}b")


def sixbit_encode(bitstring):
    """Pack binary into 6-bit AIS symbols."""
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    payload = ""
    for i in range(0, len(bitstring), 6):
        chunk = bitstring[i:i + 6]
        payload += AIS_CHARS[int(chunk, 2)]

    fill = (6 - (len(bitstring) % 6)) % 6
    return payload, fill


def encode_msg_type1(v):
    """Encode a single AISHub (FORMAT=HUMAN) vessel into AIS Message 1."""

    #
    # MMSI
    #
    try:
        mmsi = int(v["mmsi"])
    except:
        logger.error(f"Invalid MMSI: {v.get('mmsi')}")
        return None, None

    #
    # POSITION (already in DEGREES)
    #
    try:
        lat = float(v["lat"])
        lon = float(v["lon"])
    except:
        logger.error("Invalid lat/lon")
        return None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        logger.warning(f"Dropping invalid coords: MMSI {mmsi} lat={lat} lon={lon}")
        return None, None

    # Convert to AIS units (1/600000 deg)
    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    #
    # Course Over Ground (degrees)
    #
    try:
        cog_deg = float(v.get("cog", 360))
    except:
        cog_deg = 360

    if cog_deg < 0 or cog_deg >= 360:
        cog = 3600  # unavailable
    else:
        cog = int(cog_deg * 10)

    #
    # Speed Over Ground (knots)
    #
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

    #
    # Heading (0–359, 511 = unknown)
    #
    try:
        heading = int(v.get("heading", 511))
    except:
        heading = 511

    if not (0 <= heading <= 359):
        heading = 511

    #
    # Navigation Status
    #
    try:
        navstat = int(v.get("navstat", 15))
    except:
        navstat = 15

    navstat = max(0, min(15, navstat))

    #
    # Rate of Turn
    #
    try:
        rot_raw = int(v.get("rot", 128))
    except:
        rot_raw = 128

    if rot_raw in (127, 128, -127):
        rot = 128  # unavailable
    else:
        rot = max(-127, min(127, rot_raw))

    #
    # Position Accuracy
    #
    try:
        accuracy = 1 if int(v.get("accuracy", 0)) else 0
    except:
        accuracy = 0

    #
    # Timestamp (UTC seconds)
    #
    timestamp = datetime.datetime.utcnow().second

    #
    # Build AIS binary (168 bits)
    #
    bits = ""
    bits += format(1, "06b")          # Message ID
    bits += format(0, "02b")          # Repeat
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
    bits += format(0, "02b")          # Maneuver
    bits += format(0, "01b")          # RAIM
    bits += format(0, "019b")         # Radio status

    if len(bits) != 168:
        logger.error(f"Bad AIS bit length {len(bits)} for MMSI={mmsi}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


def checksum(body):
    c = 0
    for ch in body:
        c ^= ord(ch)
    return f"{c:02X}"


def build_nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    return f"!{body}*{checksum(body)}"


def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        payload, fill = encode_msg_type1(v)
        if payload:
            out.append(build_nmea_sentence(payload, fill))
    return out
