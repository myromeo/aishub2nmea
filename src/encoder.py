import logging

logger = logging.getLogger("aishub2nmea")

AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


def to_signed(value, bits):
    """Convert signed int to 2's complement."""
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), f"0{bits}b")


def sixbit_encode(bitstring):
    """Encode binary to 6‑bit AIS ASCII."""
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    payload = ""
    for i in range(0, len(bitstring), 6):
        chunk = bitstring[i:i+6]
        payload += AIS_CHARS[int(chunk, 2)]

    fill_bits = (6 - (len(bitstring) % 6)) % 6
    return payload, fill_bits


def encode_msg_type1(v):
    """
    Encode AIS Message Type 1 exactly per ITU M.1371‑5.
    Returns (payload, fillbits)
    """

    try:
        mmsi = int(v["mmsi"])
    except:
        logger.error(f"Invalid MMSI: {v.get('mmsi')}")
        return None, None

    # Degrees → AIS units
    lat_deg = float(v["lat"])
    lon_deg = float(v["lon"])

    # Check ranges
    if not (-90 <= lat_deg <= 90 and -180 <= lon_deg <= 180):
        return None, None

    lat = int(lat_deg * 600000)
    lon = int(lon_deg * 600000)

    # Bounds per AIS spec
    if not (-0x4000000 <= lat <= 0x3FFFFF):
        return None, None
    if not (-0x8000000 <= lon <= 0x7FFFFF):
        return None, None

    # Standard AIS fields
    navstat = max(0, min(15, int(v.get("navstat", 15))))

    rot_raw = int(v.get("rot", -128))
    rot = 128 if rot_raw in (127, -127) else max(-127, min(127, rot_raw))

    sog_knots = float(v.get("sog", 102.3))
    sog = 1023 if sog_knots < 0 or sog_knots > 102.2 else int(sog_knots * 10)

    cog_deg = float(v.get("cog", 360.0))
    cog = 3600 if cog_deg < 0 or cog_deg >= 360 else int(cog_deg * 10)

    heading = int(v.get("heading", 511))
    if heading < 0 or heading > 359:
        heading = 511

    accuracy = 1 if int(v.get("accuracy", 0)) else 0

    #
    # BUILD EXACT 168‑BIT MESSAGE
    #
    bits = ""
    bits += format(1, "06b")             # msg type
    bits += format(0, "02b")             # repeat
    bits += format(mmsi, "030b")
    bits += format(navstat, "04b")
    bits += to_signed(rot, 8)
    bits += format(sog, "010b")
    bits += format(accuracy, "01b")
    bits += to_signed(lon, 28)
    bits += to_signed(lat, 27)
    bits += format(cog, "012b")
    bits += format(heading, "09b")
    bits += format(60, "06b")             # timestamp (=60 "unavailable")
    bits += format(0, "02b")              # maneuver
    bits += format(0, "01b")              # RAIM
    bits += format(0, "019b")             # radio status

    if len(bits) != 168:
        logger.error(f"ENCODER ERROR: bitlen={len(bits)} for MMSI={mmsi}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


def nmea_checksum(sentence_body):
    csum = 0
    for ch in sentence_body:
        csum ^= ord(ch)
    return f"{csum:02X}"


def build_nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    return f"!{body}*{nmea_checksum(body)}"


def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        payload, fill = encode_msg_type1(v)
        if payload:
            out.append(build_nmea_sentence(payload, fill))

    logger.debug(f"Encoded {len(out)} AIS sentences")
    return out
