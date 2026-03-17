import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("aishub2nmea")

def parse_aishub_xml(xml_string):
    try:
        root = ET.fromstring(xml_string)
    except Exception as e:
        logger.error("Failed to parse XML", exc_info=True)
        return []

    vessels = []

    for v in root.findall("vessel"):

        try:
            entry = {
                "mmsi": v.attrib.get("MMSI"),

                # Human-readable degrees
                "lat": v.attrib.get("LATITUDE"),
                "lon": v.attrib.get("LONGITUDE"),

                # Movement
                "sog": v.attrib.get("SOG"),
                "cog": v.attrib.get("COG"),
                "heading": v.attrib.get("HEADING"),
                "navstat": v.attrib.get("NAVSTAT"),
                "rot": v.attrib.get("ROT"),
                "accuracy": v.attrib.get("PAC"),  # 0/1

                # Static / voyage — Msg 5 fields
                "imo": v.attrib.get("IMO"),
                "name": v.attrib.get("NAME"),
                "callsign": v.attrib.get("CALLSIGN"),
                "type": v.attrib.get("TYPE"),
                "A": v.attrib.get("A"),
                "B": v.attrib.get("B"),
                "C": v.attrib.get("C"),
                "D": v.attrib.get("D"),
                "draught": v.attrib.get("DRAUGHT"),
                "dest": v.attrib.get("DEST"),
                "eta": v.attrib.get("ETA"),
            }

            vessels.append(entry)

        except Exception:
            logger.error("Failed to parse vessel entry", exc_info=True)

    return vessels
