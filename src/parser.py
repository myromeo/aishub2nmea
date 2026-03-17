import xml.etree.ElementTree as ET
import logging
logger = logging.getLogger("aishub2nmea")

def parse_aishub_xml(xml_string: str):
    try:
        root = ET.fromstring(xml_string)
    except Exception as e:
        logger.error("Failed to parse AISHub XML", exc_info=True)
        return []

    vessels = []
    for v in root.findall("vessel"):
        try:
            vessels.append({
                "mmsi": v.attrib.get("MMSI"),
                "lat": int(v.attrib.get("LATITUDE")) / 1_000_000,
                "lon": int(v.attrib.get("LONGITUDE")) / 1_000_000,
                "sog": float(v.attrib.get("SOG")) / 10,
                "cog": float(v.attrib.get("COG")) / 10,
                "heading": int(v.attrib.get("HEADING")),
                "navstat": int(v.attrib.get("NAVSTAT")),
                "rot": int(v.attrib.get("ROT")),
                "accuracy": int(v.attrib.get("PAC", "0")),
            })
        except Exception as e:
            logger.warning(f"Failed to parse vessel entry: {v.attrib}", exc_info=True)

    logger.debug(f"XML parsed into {len(vessels)} vessel objects")
    return vessels
