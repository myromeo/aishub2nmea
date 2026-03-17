import xml.etree.ElementTree as ET

def parse_aishub_xml(xml_string: str):
    """
    Returns: list of AIS vessel dicts
    """
    root = ET.fromstring(xml_string)
    vessels = []

    for v in root.findall("vessel"):
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

    return vessels
