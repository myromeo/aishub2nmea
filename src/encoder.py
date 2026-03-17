import logging
import datetime

logger = logging.getLogger("aishub2nmea")

def safe_int(v, default=0):
    try:
        if v is None: return default
        return int(float(v))
    except:
        return default

def safe_float(v, default=0.0):
    try:
        if v is None: return default
        return float(v)
    except:
        return default

def to_signed(value, bits):
    if value < 0:
        value = (1 << bits) + value
    value = max(0, min(value, (1 << bits) - 1))
    return format(value, f"0{bits}b")

def sixbit_ascii(text, length):
    if not text: text = ""
    text = str(text).upper()[:length].ljust(length)
    bits = ""
    for c in text:
        code = ord(c)
        if 32 <= code <= 63: val = code - 32
        elif 64 <= code <= 95: val = code - 64
        else: val = 32
        bits += "{:06b}".format(val)
    return bits

def sixbit_encode(bitstring):
    fill = (6 - (len(bitstring) % 6)) % 6
    bitstring += "0" * fill
    payload = ""
    for i in range(0, len(bitstring), 6):
        val = int(bitstring[i:i+6], 2)
        if val < 40: char_code = val + 48
        else: char_code = val + 56
        payload += chr(char_code)
    return payload, fill

def nmea_checksum(body):
    c = 0
    for ch in body:
        c ^= ord(ch)
    return "{:02X}".format(c)

def encode_msg_type1(v):
    # MATCHING XML KEYS: MMSI, LATITUDE, LONGITUDE
    mmsi = safe_int(v.get("MMSI"), None)
    if not mmsi: return None, None

    lat = safe_float(v.get("LATITUDE"))
    lon = safe_float(v.get("LONGITUDE"))
    
    lat_ais = int(lat * 600000)
    lon_ais = int(lon * 600000)

    bits = ""
    bits += "{:06b}".format(1)
    bits += "00"
    bits += "{:030b}".format(mmsi)
    bits += "{:04b}".format(safe_int(v.get("NAVSTAT"), 15))
    bits += to_signed(safe_int(v.get("ROT"), -128), 8)
    
    sog_val = int(safe_float(v.get("SOG"), 102.3) * 10)
    bits += "{:010b}".format(min(sog_val, 1023))
    
    acc = safe_int(v.get("PAC"), 0) # Mapping PAC to Accuracy
    bits += "{:01b}".format(1 if acc else 0)
    
    bits += to_signed(lon_ais, 28)
    bits += to_signed(lat_ais, 27)
    
    cog_val = int(safe_float(v.get("COG"), 360) * 10)
    bits += "{:012b}".format(min(cog_val, 3600))
    
    bits += "{:09b}".format(safe_int(v.get("HEADING"), 511))
    bits += "{:06b}".format(datetime.datetime.utcnow().second)
    bits += "00" # Maneuver
    bits += "0"  # Spare
    bits += "0"  # RAIM
    bits += "0" * 19 # Radio
    
    bits = bits.ljust(168, "0")
    return sixbit_encode(bits)

def encode_msg_type5(v):
    # MATCHING XML KEYS: MMSI, IMO, CALLSIGN, NAME, TYPE, etc.
    mmsi = safe_int(v.get("MMSI"), None)
    if not mmsi: return None

    bits = ""
    bits += "{:06b}".format(5)
    bits += "00"
    bits += "{:030b}".format(mmsi)
    bits += "00"
    bits += "{:030b}".format(safe_int(v.get("IMO"), 0))
    bits += sixbit_ascii(v.get("CALLSIGN", ""), 7)
    bits += sixbit_ascii(v.get("NAME", ""), 20)
    bits += "{:08b}".format(safe_int(v.get("TYPE"), 0))
    bits += "{:09b}".format(safe_int(v.get("A"), 0))
    bits += "{:09b}".format(safe_int(v.get("B"), 0))
    bits += "{:06b}".format(safe_int(v.get("C"), 0))
    bits += "{:06b}".format(safe_int(v.get("D"), 0))
    
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
    bits += "0" # DTE
    bits += "0" # Spare
    
    bits = bits.ljust(424, "0")
    return bits

def vessels_to_nmea(vessels):
    out = []
    seq_counter = 0
    for v in vessels:
        p, f = encode_msg_type1(v)
        if p:
            body = f"AIVDM,1,1,,A,{p},{f}"
            out.append(f"!{body}*{nmea_checksum(body)}\r\n")

        bits5 = encode_msg_type5(v)
        if bits5:
            this_seq_id = seq_counter % 10
            seq_counter += 1
            p1, _ = sixbit_encode(bits5[:342])
            p2, _ = sixbit_encode(bits5[342:])
            b1 = f"AIVDM,2,1,{this_seq_id},A,{p1},0"
            out.append(f"!{b1}*{nmea_checksum(b1)}\r\n")
            b2 = f"AIVDM,2,2,{this_seq_id},A,{p2},2"
            out.append(f"!{b2}*{nmea_checksum(b2)}\r\n")
    return out
