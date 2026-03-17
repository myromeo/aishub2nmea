import logging

logger = logging.getLogger("aishub2nmea")

# AIS 6-bit character map per ITU-R M.1371
AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


#
# Utility Functions
#

def to_signed(value, bit_len):
    """
    Convert signed integer into 2's complement bitstring of length bit_len.
    """
    if value < 0:
        value = (1 << bit_len) + value
    return format(value & ((1 << bit_len) - 1), f"0{bit_len}b")


def sixbit_encode(bitstring):
    """
    Convert a bitstring into AIS 6-bit ASCII payload.
    Pads to nearest 6 bits.
    """
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    payload = ""
    for i in range(0, len(bitstring), 6):
        val = int(bitstring[i:i + 6], 2)
        payload += AIS_CHARS[val]

    fill_bits = (6 - len(bitstring) % 6) % 6
    return payload, fill_bits


#
# AIS Message Type 1 Encoder
#

def encode_msg_type1(v):
    """
    Encode a single vessel dict into AIS Message Type 1 (Position Report Class A).
    v contains:
       mmsi, lat, lon, sog, cog, heading, navstat, rot, accuracy
    """

    try:
        mmsi = int(v["mmsi"])
    except Exception:
        logger.error(f"Invalid MMSI: {v.get('mmsi')}")
        return None, None

    # Navigation status (4 bits)
    navstat = int(v.get("navstat", 15))

    # Rate of Turn (ROT)
    rot_raw = int(v.get("rot", -128))
    if rot_raw in (127, -127):
        rot = 128  # "not available"
    else:
        rot = max(-127, min(127, rot_raw))

    # Speed Over Ground (0.1 knots)
    sog_knots = float(v.get("sog", 102.3))
    sog = 1023 if sog_knots < 0 else min(1022, int(sog_knots * 10))

    # Course Over Ground (0.1 degrees)
    cog_deg = float(v.get("cog", 360.0))
    cog = 3600 if cog_deg < 0 else min(3599, int(cog_deg * 10))

    # Heading (0–359, 511 unavailable)
    heading = int(v.get("heading", 511))

    # Position accuracy
    accuracy = int(v.get("accuracy", 0))

    #
    # Coordinate conversion:
    # AISHub gives lat/lon in degrees.
    # AIS expects lat/lon * 600000 in 2’s complement.
    #
    lat = int(float(v["lat"]) * 600000)
    lon = int(float(v["lon"]) * 600000)

    #
    # Assemble 168-bit AIS type 1 message
    #
    bits = ""
    bits += format(1, "06b")                   # Message ID = 1
    bits += format(0, "02b")                   # Repeat indicator = 0
    bits += format(mmsi, "030b")               # MMSI (30 bits)
    bits += format(navstat, "04b")             # Navigational status
    bits += to_signed(rot, 8)                  # Rate of Turn
    bits += format(sog, "010b")                # Speed over ground
    bits += format(accuracy, "01b")            # Position accuracy
    bits += to_signed(lon, 28)                 # Longitude
    bits += to_signed(lat, 27)                 # Latitude
    bits += format(cog, "012b")                # Course over ground
    bits += format(heading, "09b")             # True heading
    bits += format(60, "06b")                  # Timestamp (60 = unavailable)
    bits += format(0, "02b")                   # Maneuver indicator
    bits += format(0, "01b")                   # RAIM
    bits += format(0, "019b")                  # Radio status

    payload, fill = sixbit_encode(bits)
    return payload, fill


#
# NMEA Wrapping
#

def nmea_checksum(sentence_body: str) -> str:
    """
    XOR checksum for NMEA sentences.
    """
    csum = 0
    for ch in sentence_body:
        csum ^= ord(ch)
    return f"{csum:02X}"


def build_nmea_sentence(payload: str, fill_bits: int) -> str:
    """
    Pack AIS payload + fill bits into a full !AIVDM sentence.
    """
    body = f"AIVDM,1,1,,A,{payload},{fill_bits}"
    checksum = nmea_checksum(body)
    return f"!{body}*{checksum}"


#
# Batch Encoding
#

def vessels_to_nmea(vessels):
    """
    Convert list of vessel dicts into list of NMEA AIS sentences.
    """
    out = []

    for v in vessels:
        try:
            payload, fill = encode_msg_type1(v)
            if payload is None:
                continue

            msg = build_nmea_sentence(payload, fill)
            out.append(msg)

        except Exception as e:
            logger.error(f"Error encoding vessel {v.get('mmsi')}: {e}", exc_info=True)

    logger.debug(f"Encoded {len(out)} AIS messages")
    return out
