import logging
logger = logging.getLogger("aishub2nmea")

# (existing encoder code remains the same)

def vessels_to_nmea(vessels):
    out = []
    for v in vessels:
        try:
            payload, fill = encode_msg_type1(v)
            nmea = build_nmea_sentence(payload, fill)
            out.append(nmea)
        except Exception as e:
            logger.error(f"Encoding failed for vessel {v.get('mmsi')}", exc_info=True)

    logger.debug(f"Encoded {len(out)} AIS messages")
    return out
