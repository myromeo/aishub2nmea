import socket
import logging

logger = logging.getLogger("aishub2nmea")

def stream_udp_realtime(nmea_list, host, port, mps=None):
    """
    Renamed back to stream_udp_realtime for compatibility with main.py.
    Ditches delays and shuffling to blast the data immediately.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total = len(nmea_list)

    logger.info(f"Blasting {total} AIS messages to {host}:{port}")

    # No shuffling here. Sequential order is better for Type 5 reassembly.
    for msg in nmea_list:
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        
        try:
            # Blast each sentence as its own UDP packet
            sock.sendto(msg.encode("ascii"), (host, port))
        except Exception as e:
            logger.error(f"UDP send failed: {e}")

    logger.info(f"Blast complete.")
    sock.close()
