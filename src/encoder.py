import logging
import datetime

logger = logging.getLogger("aishub2nmea")

def safe_int(v, default=0):
    try:
        return int(float(v)) if v is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def to_signed(value, bits):
    """Converts a signed integer to a 2's complement bit string."""
    if value < 0:
        value = (1 << bits) + value
    value = max(0, min(value, (1 << bits) - 1))
    return format(value, f"0{bits}b")

def sixbit_ascii(text, length):
    """Standard AIS 6-bit ASCII encoding (@=0, A=1...Z=26)."""
    if not text:
        text = ""
    # Clean and pad to exactly 'length' characters
    text = str(text).upper()[:length].ljust(length, " ")
    
    bits = ""
    for c in text:
        code = ord(c)
        if 32 <= code <= 63:
            val = code - 32
        elif 64 <= code <= 95:
            val = code - 64
        else:
            val = 0  # Default to Space (@)
        bits += format(val & 0x3F, "06b")
    return bits

def sixbit_encode(bitstring):
    """NMEA armoring logic (The 48/56 ASCII jump)."""
    fill = (6 - (len(bitstring) % 6)) % 6
    bitstring += "0" * fill
    payload = ""
    for i in range(0, len(bitstring), 6):
        val = int(bitstring[i:i+6], 2)
        char_code = val + 48 if val < 40 else val + 56
        payload += chr(char_code)
    return payload, fill

def nmea_checksum(body):
    """Standard NMEA 0183 XOR checksum."""
    c = 0
    for ch in body:
        c ^= ord(ch)
    return "{:02X}".format(c)

def encode_msg_type1(v):
    """Encodes Position Report Class A (Type 1)."""
    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi:
        return None, None

    # AIS resolution is 1/10000th of a minute
    lat_ais = int(safe_float(v.get("lat")) * 600000)
    lon_ais = int(safe_float(v.get("lon")) * 600000)

    bits =  format(1, "06b")                           # Msg ID
    bits += "00"                                       # Repeat
    bits += format(mmsi, "030b")                       # MMSI
    bits += format(safe_int(v.get("navstat"), 15), "04b")
    bits += to_signed(safe_int(v.get("rot"), -128), 8)
    bits += format(min(int(safe_float(v.get("sog")) * 10), 1023), "010b")
    bits += format(1 if safe_int(v.get("pac")) else 0, "01b") # Accuracy
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    bits += format(min(int(safe_float(v.get("cog")) * 10), 3600), "012b")
    bits += format(safe_int(v.get("heading"), 511), "09b")
    bits += format(datetime.datetime.utcnow().second, "06b")
    bits += "0000"                                     # Maneuver(2) + Spare(1) + RAIM(1)
    bits += "0" * 19                                   # Radio Status
    
    return sixbit_encode(bits)

def encode_msg_type5(v):
    """Encodes Static and Voyage Related Data (Type 5)."""
    mmsi = safe_int(v.get("mmsi"), None)
    if not mmsi:
        return None

    # --- Dimension Handling ---
    # Map A, B, C, D directly from XML; fallback to length/beam if missing.
    a = safe_int(v.get("a"))
    b = safe_int(v.get("b"))
    c = safe_int(v.get("c"))
    d = safe_int(v.get("d"))

    if not (a or b):
        length = safe_int(v.get("length"), 0)
        a = length // 2
        b = length - a

    if not (c or d):
        beam = safe_int(v.get("beam"), 0)
        c = beam // 2
        d = beam - c

    # BUILDING BITS - TOTAL MUST BE 424
    bits =  format(5, "06b")                           # 0-5
    bits += "00"                                       # 6-7
    bits += format(mmsi, "030b")                       # 8-37
    bits += "00"                                       # 38-39 (AIS Version)
    bits += format(safe_int(v.get("imo"), 0), "030b")  # 40-69
    bits += sixbit_ascii(v.get("callsign"), 7)         # 70-111
    bits += sixbit_ascii(v.get("name"), 20)            # 112-231
    bits += format(safe_int(v.get("type"), 0), "08b")  # 232-239
    
    # Antenna Offsets (20 bits total)
    bits += format(min(a, 511), "09b")                 # 240-248 (A)
    bits += format(min(b, 511), "09b")                 # 249-257 (B)
    bits += format(min(c, 63), "06b")                  # 258-263 (C)
    bits += format(min(d, 63), "06b")                  # 264-269 (D)
    
    bits += "0000"                                     # 270-273 (Fix Type/Spare)
    
    # ETA Handling (20 bits)
    eta = v.get("eta", "00-00 00:00")
    try:
        month = int(eta[0:2])
        day   = int(eta[3:5])
        hour  = int(eta[6:8])
        minute = int(eta[9:11])
    except (ValueError, TypeError, IndexError):
        month = day = hour = minute = 0
    
    bits += format(month, "04b") + format(day, "05b") + format(hour, "05b") + format(minute, "06b")
    
    # Draught (8 bits) - 0.1m resolution
    bits += format(min(int(safe_float(v.get("draught")) * 10), 255), "08b")
    
    # Destination (120 bits)
    bits += sixbit_ascii(v.get("dest"), 20)
    
    bits += "00"                                       # DTE(1) + Spare(1)

    return bits.ljust(424, "0")

def vessels_to_nmea(vessels):
    """Converts vessel list to !AIVDM UDP-ready strings."""
    out = []
    seq_counter = 0
    for v in vessels:
        # Generate Type 1 (Position)
        p, f = encode_msg_type1(v)
        if p:
            body = f"AIVDM,1,1,,A,{p},{f}"
            out.append(f"!{body}*{nmea_checksum(body)}\r\n")

        # Generate Type 5 (Static/Voyage)
        raw5 = encode_msg_type5(v)
        if raw5:
            sid = seq_counter % 10
            seq_counter += 1
            
            # Split 424-bit Type 5 into two NMEA sentences
            p1, _ = sixbit_encode(raw5[:342])
            p2, _ = sixbit_encode(raw5[342:])
            
            b1 = f"AIVDM,2,1,{sid},A,{p1},0"
            b2 = f"AIVDM,2,2,{sid},A,{p2},2"
            
            out.append(f"!{b1}*{nmea_checksum(b1)}\r\n")
            out.append(f"!{b2}*{nmea_checksum(b2)}\r\n")
            
    return out
