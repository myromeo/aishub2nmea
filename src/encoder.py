import logging
import datetime

logger = logging.getLogger("aishub2nmea")

# Correct AIS 6-bit binary to ASCII map
AIS_CHARS = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./"

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
    """Binary → 6-bit AIS ASCII with proper fill bit calculation."""
    fill = (6 - (len(bitstring) % 6)) % 6
    bitstring += "0" * fill
    
    payload = ""
    for i in range(0, len(bitstring), 6):
        payload += AIS_CHARS[int(bitstring[i:i+6], 2)]
    return payload, fill

def nmea_checksum(body):
    c = 0
    for ch in body:
        c ^= ord(ch)
    return "{:02X}".format(c)

def encode_msg_type1(v):
    mmsi = safe_int(v.get("MMSI"), None) # AIshub uses uppercase MMSI
    if not mmsi: return None, None

    lat = safe_float(v.get("LATITUDE"))
    lon = safe_float(v.get("LONGITUDE"))
    
    # AIS uses 1/10000 minute precision
    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    bits = ""
    bits += "{:06b}".format(1)                 # Msg ID
    bits += "00"                               # Repeat
    bits += "{:030b}".format(mmsi)
    bits += "{:04b}".format(safe_int(v.get("NAVSTAT"), 15))
    bits += to_signed(safe_int(v.get("ROT"), 128), 8)
    bits += "{:010b}".format(int(safe_float(v.get("SOG")) * 10))
    bits += "0"                                # Accuracy
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += "{:012b}".format(int(safe_float(v.get("COG"), 360) * 10))
    bits += "{:09b}".format(safe_int(v.get("HEADING"), 511))
    bits += "{:06b}".format(datetime.datetime.utcnow().second)
    bits += "00"                               # Maneuver
    bits += "0"                                # RAIM
    bits += "0" * 19                           # Radio
    
    bits = bits.ljust(168, "0")
    return sixbit_encode(bits)

def encode_msg_type5(v):
    mmsi = safe_int(v.get("MMSI"), None)
    if not mmsi: return None

    bits = ""
    bits += "{:06b}".format(5)
    bits += "00"
    bits += "{:030b}".format(mmsi)
    bits += "00"                               # AIS version
    bits += "{:030b}".format(safe_int(v.get("IMO"), 0))
    bits += sixbit_ascii(v.get("CALLSIGN", ""), 7)
    bits += sixbit_ascii(v.get("NAME", ""), 20)
    bits += "{:08b}".format(safe_int(v.get("TYPE"), 0))
    bits += "{:09b}".format(safe_int(v.get("A"), 0))
    bits += "{:09b}".format(safe_int(v.get("B"), 0))
    bits += "{:06b}".format(safe_int(v.get("C"), 0))
    bits += "{:06b}".format(safe_int(v.get("D"), 0))
    
    # Simple ETA parsing
    eta = v.get("ETA", "00-00 00:00")
    try:
        month, day, hour, minute = int(eta[0:2]), int(eta[3:5]), int(eta[6:8]), int(eta[9:11])
    except:
        month = day = hour = minute = 0
        
    bits += "{:04b}".format(month)
    bits += "{:05b}".format(day)
    bits += "{:05b}".format(hour)
    bits += "{:06b}".format(minute)
    bits += "{:08b}".format(int(safe_float(v.get("DRAUGHT"), 0) * 10))
    bits += sixbit_ascii(v.get("DEST", ""), 20)
    bits += "0"                                # DTE
    bits += "0"                                # Spare
    
    bits = bits.ljust(424, "0")
    return bits

def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        # MSG 1
        p, f = encode_msg_type1(v)
        if p:
            body = "AIVDM,1,1,,A,{},{}".format(p, f)
            out.append("!{}*{}".format(body, nmea_checksum(body)))

        # MSG 5 (Multi-sentence)
        bits5 = encode_msg_type5(v)
        if bits5:
            # Type 5 is 424 bits. Part 1 (chars 1-59), Part 2 (rest)
            # Standard split: Part 1 = 354 bits (59 chars), Part 2 = 70 bits
            p1, f1 = sixbit_encode(bits5[:354])
            p2, f2 = sixbit_encode(bits5[354:])
            
            b1 = "AIVDM,2,1,1,A,{},{}".format(p1, f1)
            b2 = "AIVDM,2,2,1,A,{},{}".format(p2, f2)
            out.append("!{}*{}".format(b1, nmea_checksum(b1)))
            out.append("!{}*{}".format(b2, nmea_checksum(b2)))
    return out
