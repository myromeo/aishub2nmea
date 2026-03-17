AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"


def to_signed(value, bit_len):
    """Convert signed integer to 2's complement bitstring."""
    if value < 0:
        value = (1 << bit_len) + value
    return format(value, f"0{bit_len}b")


def sixbit_encode(bitstring):
    """Convert bitstring into 6-bit AIS payload characters."""
    payload = ""

    # pad to multiple of 6
    while len(bitstring) % 6 != 0:
        bitstring += "0"

    for i in range(0, len(bitstring), 6):
        val = int(bitstring[i:i+6], 2)
        payload += AIS_CHARS[val]

    fill_bits = (6 - (len(bitstring) % 6)) % 6
    return payload, fill_bits


def encode_msg_type1(v):
    """
    Encode AIS Message Type 1 from vessel data.
    """

    # Extract fields
    mmsi = int(v["mmsi"])
    navstat = int(v.get("navstat", 15))
    rot_raw = int(v.get("rot", -128))
    sog_knots = float(v.get("sog", 102.3))
    cog_deg = float(v.get("cog", 360.0))
    heading = int(v.get("heading", 511))
    accuracy = int(v.get("accuracy", 0))

    lon = int(v["lon"] * 600000)
    lat = int(v["lat"] * 600000)

    # ROT handling
    if rot_raw in (127, -127):
        rot = 128
    else:
        rot = max(-127, min(127, rot_raw))

    # SOG
    sog = 1023 if sog_knots < 0 else min(1022, int(sog_knots * 10))

    # COG
    cog = 3600 if cog_deg < 0 else min(3599, int(cog_deg * 10))

    bits = ""
    bits += format(1, "06b")                   # Msg type
    bits += format(0, "02b")                   # Repeat
    bits += format(mmsi, "030b")
    bits += format(navstat, "04b")
    bits += to_signed(rot, 8)
    bits += format(sog, "010b")
    bits += format(accuracy, "01b")
    bits += to_signed(lon, 28)
    bits += to_signed(lat, 27)
    bits += format(cog, "012b")
    bits += format(heading, "09b")
    bits += format(60, "06b")                   # timestamp
    bits += format(0, "02b")                    # maneuver
    bits += format(0, "01b")                    # RAIM
    bits += format(0, "019b")                   # radio

    payload, fill = sixbit_encode(bits)
    return payload, fill


def nmea_checksum(sentence_body: str) -> str:
    csum = 0
    for ch in sentence_body:
        csum ^= ord(ch)
    return f"{csum:02X}"


def build_nmea_sentence(payload: str, fill_bits: int) -> str:
    body = f"AIVDM,1,1,,A,{payload},{fill_bits}"
    checksum = nmea_checksum(body)
    return f"!{body}*{checksum}"


def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        payload, fill = encode_msg_type1(v)
        nmea = build_nmea_sentence(payload, fill)
        out.append(nmea)
    return out
