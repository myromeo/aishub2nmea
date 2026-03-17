import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("aishub2nmea")


def parse_aishub_xml(xml_string: str):
    try:
        root = ET.fromstring(xml_string)
    except Exception:
        logger.error("Failed to parse AISHub XML", exc_info=True)
        return []

    vessels = []

    for v in root.findall("vessel"):
        try:
            lat_raw = v.attrib.get("LATITUDE")
            lon_raw = v.attrib.get("LONGITUDE")

            lat = float(lat_raw) / 1_000_000 if lat_raw else None
            lon = float(lon_raw) / 1_000_000 if lon_raw else None

            if lat is None or lon is None or lat == 0 or lon == 0:
                logger.warning(f"Skipping vessel with invalid coords: MMSI={v.attrib.get('MMSI')}")
                continue

            vessels.append(
                {
                    "mmsi": v.attrib.get("MMSI"),
                    "lat": lat,
                    "lon": lon,
                    "sog": float(v.attrib.get("SOG")) / 10,
                    "cog": float(v.attrib.get("COG")) / 10,
                    "heading": int(v.attrib.get("HEADING")),
                    "navstat": int(v.attrib.get("NAVSTAT")),
                    "rot": int(v.attrib.get("ROT")),
                    "accuracy": int(v.attrib.get("PAC", "0")),
                }
            )

        except Exception:
            logger.error(f"Failed to parse vessel record: {v.attrib}", exc_info=True)

    logger.info(f"Parsed {len(vessels)} valid vessels")
    return vessels
