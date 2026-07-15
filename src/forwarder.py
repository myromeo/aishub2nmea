import socket
import time
import logging

logger = logging.getLogger("aishub2nmea")

PACE_DELAY = 0.005  # 200 msg/sec


def get_udp_socket():
    """Create the UDP socket once; the caller keeps it for the process's lifetime."""
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def stream_udp_realtime(sock, nmea_list, host, port):
    """
    Fixed-pace UDP streamer at 200 msg/sec, using a drift-corrected
    schedule so per-message overhead doesn't slow the batch down over time.
    """
    try:
        target_ip = socket.gethostbyname(host)
    except socket.gaierror:
        logger.error(f"Network Error: Could not resolve {host}")
        return

    total = len(nmea_list)
    if total == 0:
        logger.debug("No changed messages to send this poll")
        return

    logger.info(f"Streaming {total} messages to {target_ip}:{port} at 200 msg/sec")

    start_time = time.monotonic()
    sent = 0
    errors = 0

    for i, msg in enumerate(nmea_list):
        if not msg.endswith("\r\n"):
            msg += "\r\n"

        try:
            sock.sendto(msg.encode("ascii"), (target_ip, port))
            sent += 1
        except OSError as e:
            errors += 1
            logger.warning(f"Failed to send message {i}: {e}")
            continue  # one bad send shouldn't drop the rest of the batch

        target_time = start_time + (i + 1) * PACE_DELAY
        delay = target_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    duration = time.monotonic() - start_time
    actual_mps = sent / max(duration, 0.1)
    logger.info(
        f"Stream complete: {sent}/{total} msgs sent ({errors} errors) "
        f"in {duration:.1f}s ({actual_mps:.1f} msg/sec)"
    )