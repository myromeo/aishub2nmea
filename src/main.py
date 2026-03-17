import time
from config import Config
from aishub import fetch_ais_data
from parser import parse_aishub_xml
from encoder import vessels_to_nmea
from forwarder import send_udp

def main():
    print("AIS Streamer starting...")

    while True:
        try:
            xml = fetch_ais_data()
            vessels = parse_aishub_xml(xml)
            nmea = vessels_to_nmea(vessels)

            send_udp(nmea, Config.UDP_HOST, Config.UDP_PORT)
            print(f"Sent {len(nmea)} AIS messages")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(Config.POLL_INTERVAL)

if __name__ == "__main__":
    main()
