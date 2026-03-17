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
    # Match the lowercase keys from parser.py
    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi: 
        return None, None

    # AIS coordinates are signed integers: (degrees * 600,000)
    # Range: Lat +/- 90, Lon +/- 180
    lat = safe_float(v.get("lat"))
    lon = safe_float(v.get("lon"))
    
    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    bits = ""
    bits += "{:06b}".format(1)                           # Message ID (Type 1)
    bits += "00"                                         # Repeat Indicator
    bits += "{:030b}".format(mmsi)                       # MMSI
    bits += "{:04b}".format(safe_int(v.get("navstat"), 15)) # Nav Status
    
    # ROT: 0 to +126 (right), 0 to -126 (left). -128 (80h) = not available
    bits += to_signed(safe_int(v.get("rot"), -128), 8)
    
    # SOG: 10 bit, units 0.1 knots. 1023 = not available
    sog_val = int(safe_float(v.get("sog"), 102.3) * 10)
    bits += "{:010b}".format(min(sog_val, 1023))
    
    bits += v.get("accuracy", "0")                       # Position Accuracy
    bits += to_signed(lon_ais, 28)                       # Longitude
    bits += to_signed(lat_ais, 27)                       # Latitude
    
    # COG: 12 bit, units 0.1 degrees. 3600 = not available
    cog_val = int(safe_float(v.get("cog"), 360) * 10)
    bits += "{:012b}".format(min(cog_val, 3600))
    
    # Heading: 0-359. 511 = not available
    bits += "{:09b}".format(safe_int(v.get("heading"), 511))
    
    bits += "{:06b}".format(datetime.datetime.utcnow().second) # Time Stamp
    bits += "00"                                         # Special Maneuver
    bits += "0"                                          # Spare
    bits += "0"                                          # RAIM Flag
    bits += "0" * 19                                     # Radio Status (Default)
    
    # Ensure the bitstring is exactly 168 bits for Type 1
    bits = bits.ljust(168, "0")
    return sixbit_encode(bits)

def encode_msg_type5(v):
    mmsi = safe_int(v.get("mmsi"), None) # Changed to lowercase to match parser
    if not mmsi: return None

    bits = ""
    bits += "{:06b}".format(5)
    bits += "00"
    bits += "{:030b}".format(mmsi)
    bits += "00"
    bits += "{:030b}".format(safe_int(v.get("imo"), 0))
    bits += sixbit_ascii(v.get("callsign", ""), 7)
    bits += sixbit_ascii(v.get("name", ""), 20)
    bits += "{:08b}".format(safe_int(v.get("type"), 0))
    bits += "{:09b}".format(safe_int(v.get("A"), 0))
    bits += "{:09b}".format(safe_int(v.get("B"), 0))
    bits += "{:06b}".format(safe_int(v.get("C"), 0))
    bits += "{:06b}".format(safe_int(v.get("D"), 0))
    
    eta = v.get("eta", "00-00 00:00")
    try:
        month, day, hour, minute = int(eta[0:2]), int(eta[3:5]), int(eta[6:8]), int(eta[9:11])
    except:
        month = day = hour = minute = 0
        
    bits += "{:04b}".format(month)
    bits += "{:05b}".format(day)
    bits += "{:05b}".format(hour)
    bits += "{:06b}".format(minute)
    bits += "{:08b}".format(int(safe_float(v.get("draught"), 0) * 10))
    bits += sixbit_ascii(v.get("dest", ""), 20)
    bits += "0" # DTE
    bits += "0" # Spare
    
    bits = bits.ljust(424, "0")
    return bits # Still returns bits for the multi-part splitter

def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        # MSG 1 - Fix keys to lowercase
        # Use v.get("lat") and v.get("lon") in encode_msg_type1 as well!
        p, f = encode_msg_type1(v) 
        if p:
            body = "AIVDM,1,1,,A,{},{}".format(p, f)
            out.append("!{}*{}\r\n".format(body, nmea_checksum(body))) # Added \r\n

        # MSG 5
        bits5 = encode_msg_type5(v)
        if bits5:
            # 424 bits total. Split at 354 bits (59 characters)
            p1, f1 = sixbit_encode(bits5[:354])
            p2, f2 = sixbit_encode(bits5[354:])
            
            # The '1' in the 4th field is the sequential message ID
            msg_id = random.randint(0, 9) 
            b1 = "AIVDM,2,1,{},A,{},{}".format(msg_id, p1, f1)
            b2 = "AIVDM,2,2,{},A,{},{}".format(msg_id, p2, f2)
            out.append("!{}*{}\r\n".format(b1, nmea_checksum(b1)))
            out.append("!{}*{}\r\n".format(b2, nmea_checksum(b2)))
    return out
