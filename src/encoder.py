import logging

logger = logging.getLogger("aishub2nmea")

# AIS 6-bit encoding table per ITU-R M.1371
AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


#
# Utility Functions
#

def to_signed(value, bits):
    """
    Convert integer to signed 2's-complement with given bit width.
    """
    limit = 1 << bits
    if value < 0:
        value = limit + value
    return format(value & (limit - 1), f"0{bits}b")


def sixbit_encode(bitstring):
    """
    Encode a bitstring into AIS 6-bit ASCII payload.
    """
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    payload = ""
    for i in range(0, len(bitstring), 6):
        payload += AIS_CHARS[int(bitstring[i:i+6], 2)]

    fill_bits = (6 - (len(bitstring) % 6)) % 6
    return payload, fill_bits


#
# AIS Message Type 1 Encoder (with AIS‑Catcher validation)
#

def encode_msg_type1(v):
    """
    Encode a vessel dict into AIS Message Type 1.
    Performs strict validation of lat/lon and all AIS fields.
    """

    #
    # MMSI
    #
    try:
        mmsi = int(v["mmsi"])
    except Exception:
        logger.error(f"Invalid MMSI: {v.get('mmsi')}")
        return None, None

    #
    # LAT / LON (degrees)
    #
    lat_deg = float(v.get("lat"))
    lon_deg = float(v.get("lon"))

    # Drop impossible coordinates (AIS-Catcher requirement)
    if not (-90.0 <= lat_deg <= 90.0 and -180.0 <= lon_deg <= 180.0):
        logger.warning(f"Dropping invalid coords: MMSI={mmsi} lat={lat_deg} lon={lon_deg}")
        return None, None

    # Convert to AIS units (1/10000 minute = degrees * 600000)
    lat_ais = int(lat_deg * 600000)
    lon_ais = int(lon_deg * 600000)

    # Validate AIS 2's complement coordinate bounds
    if not (-0x08000000 <= lon_ais <= 0x07FFFFFF) or not (-0x04000000 <= lat_ais <= 0x03FFFFFF):
        logger.warning(f"AIS-Catcher invalid AIS coords: LAT={lat_ais} LON={lon_ais}")
        return None, None

    #
    # Navigation status
    #
    navstat = int(v.get("navstat", 15))  # 15 = undefined
    navstat = max(0, min(15, navstat))

    #
    # Rate of Turn (ROT)
    #
    rot_raw = int(v.get("rot", -128))
    if rot_raw in (127, -127):
        rot = 128  # "not available"
    else:
        rot = max(-127, min(127, rot_raw))

    #
    # Speed Over Ground (SOG) — knots * 10 → 10-bit
    #
    sog_knots = float(v.get("sog", 0.0))
    if sog_knots < 0 or sog_knots > 102.2:
        sog = 1023  # unavailable
    else:
        sog = min(1022, int(sog_knots * 10))

    #
    # Course Over Ground (COG) — degrees * 10 → 12-bit
    #
    cog_deg = float(v.get("cog", 0.0))
    if cog_deg < 0 or cog_deg >= 360:
        cog = 3600
    else:
        cog = int(cog_deg * 10)

    #
    # Heading
    #
    heading = int(v.get("heading", 511))
    if heading < 0 or heading > 359:
        heading = 511  # unavailable

    #
    # Position Accuracy (PAC)
    #
    accuracy = int(v.get("accuracy", 0))
    accuracy = 1 if accuracy else 0

    #
    # Assemble AIS 168-bit message
    #
    bits = ""
    bits += format(1, "06b")             # message ID = 1
    bits += format(0, "02b")             # repeat indicator
    bits += format(mmsi, "030b")         # MMSI
    bits += format(navstat, "04b")
    bits += to_signed(rot, 8)
    bits += format(sog, "010b")
    bits += format(accuracy, "01b")
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += format(cog, "012b")
    bits += format(heading, "09b")
    bits += format(60, "06b")            # timestamp = 60 ("not available")
    bits += format(0, "02b")             # maneuver indicator
    bits += format(0, "01b")             # RAIM
    bits += format(0, "019b")            # radio status

    if len(bits) != 168:
        logger.error(f"INVALID BIT LENGTH {len(bits)} for MMSI={mmsi}")
        return None, None

    payload, fill = sixbit_encode(bits)
    return payload, fill


#
# NMEA Wrapping
#

def nmea_checksum(sentence_body):
    csum = 0
    for ch in sentence_body:
        csum ^= ord(ch)
    return f"{csum:02X}"


def build_nmea_sentence(payload, fill):
    body = f"AIVDM,1,1,,A,{payload},{fill}"
    checksum = nmea_checksum(body)
    return f"!{body}*{checksum}"


#
# Batch encode
#

def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        try:
            payload, fill = encode_msg_type1(v)
            if payload is None:
                continue

            msg = build_nmea_sentence(payload, fill)
            out.append(msg)

        except Exception:
            logger.error("Error encoding vessel", exc_info=True)

    logger.debug(f"Encoded {len(out)} AIS messages (post-validation)")
    return out
