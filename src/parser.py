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
            # AISHub attributes are often lowercase in their API output
            # We use .get() with a default or convert to float where needed
            entry = {
                "mmsi": v.attrib.get("mmsi") or v.attrib.get("MMSI"),
                
                # Coordinates MUST be floats for most encoders
                "lat": float(v.attrib.get("latitude") or v.attrib.get("LATITUDE", 0)),
                "lon": float(v.attrib.get("longitude") or v.attrib.get("LONGITUDE", 0)),

                # Movement - converting to float/int helps the encoder
                "sog": float(v.attrib.get("sog") or v.attrib.get("SOG", 0)),
                "cog": float(v.attrib.get("cog") or v.attrib.get("COG", 0)),
                "heading": int(v.attrib.get("heading") or v.attrib.get("HEADING", 511)),
                "navstat": int(v.attrib.get("navstat") or v.attrib.get("NAVSTAT", 15)),
                "rot": int(v.attrib.get("rot") or v.attrib.get("ROT", -128)),
                "accuracy": int(v.attrib.get("pac") or v.attrib.get("PAC", 0)),

                # Static Data
                "imo": v.attrib.get("imo") or v.attrib.get("IMO"),
                "name": v.attrib.get("name") or v.attrib.get("NAME", "UNKNOWN"),
                "callsign": v.attrib.get("callsign") or v.attrib.get("CALLSIGN"),
                "type": v.attrib.get("type") or v.attrib.get("TYPE", 0),
                "A": v.attrib.get("a") or v.attrib.get("A", 0),
                "B": v.attrib.get("b") or v.attrib.get("B", 0),
                "C": v.attrib.get("c") or v.attrib.get("C", 0),
                "D": v.attrib.get("d") or v.attrib.get("D", 0),
                "draught": v.attrib.get("draught") or v.attrib.get("DRAUGHT", 0),
                "dest": v.attrib.get("dest") or v.attrib.get("DEST", ""),
                "eta": v.attrib.get("eta") or v.attrib.get("ETA", ""),
            }

            vessels.append(entry)

        except (TypeError, ValueError) as e:
            # This catches cases where coordinates aren't valid numbers
            logger.debug(f"Skipping vessel due to data error: {e}")
            continue
        except Exception:
            logger.error("Failed to parse vessel entry", exc_info=True)

    return vessels
