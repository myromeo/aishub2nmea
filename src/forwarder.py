import socket
import time
import logging

logger = logging.getLogger("aishub2nmea")

def stream_udp_realtime(nmea_list, host, port):
    """
    Fixed-pace UDP streamer at 200 msg/sec.
    Ensures 7k+ messages finish in ~35s, avoiding API poll overlap.
    """
    # Hard-coded 200 msg/sec (1.0 / 200 = 0.005)
    PACE_DELAY = 0.005 
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 1. Resolve host ONCE to prevent 7,000+ DNS lookups
    try:
        target_ip = socket.gethostbyname(host)
    except socket.gaierror:
        logger.error(f"Network Error: Could not resolve {host}")
        return

    total = len(nmea_list)
    if total == 0:
        return

    logger.info(f"Streaming {total} messages to {target_ip}:{port} at 200 msg/sec")

    start_time = time.time()
    
    for msg in nmea_list:
        # Ensure proper NMEA termination
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        
        try:
            # Send the message
            sock.sendto(msg.encode("ascii"), (target_ip, port))
            
            # Hard-coded pace
            time.sleep(PACE_DELAY)
            
        except Exception as e:
            logger.error(f"UDP Stream Interrupted: {e}")
            break

    duration = time.time() - start_time
    actual_mps = total / max(duration, 0.1)
    logger.info(f"Stream complete: {total} msgs in {duration:.1f}s ({actual_mps:.1f} msg/sec)")
    
    sock.close()
