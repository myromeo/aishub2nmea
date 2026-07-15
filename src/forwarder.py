import socket
import time
import logging

logger = logging.getLogger("aishub2nmea")

MIN_RATE = 100   # msg/sec floor — no benefit going slower than this for small batches
MAX_RATE = 400   # msg/sec ceiling — protects the UDP receiver from an unnecessary burst


def get_udp_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def compute_pace_delay(total_messages, target_seconds, min_rate=MIN_RATE, max_rate=MAX_RATE):
    """
    Derive a per-message delay so `total_messages` finish in roughly
    `target_seconds`, clamped so we never exceed max_rate (protects the
    receiver) or drop below min_rate (no benefit to going slower).
    """
    if total_messages <= 0 or target_seconds <= 0:
        return 1.0 / max_rate

    required_rate = total_messages / target_seconds
    rate = max(min_rate, min(required_rate, max_rate))
    return 1.0 / rate


def stream_udp_realtime(sock, nmea_list, host, port, target_seconds):
    try:
        target_ip = socket.gethostbyname(host)
    except socket.gaierror:
        logger.error(f"Network Error: Could not resolve {host}")
        return

    total = len(nmea_list)
    if total == 0:
        logger.debug("No changed messages to send this poll")
        return

    pace_delay = compute_pace_delay(total, target_seconds)
    effective_rate = 1.0 / pace_delay
    logger.info(
        f"Streaming {total} messages to {target_ip}:{port} "
        f"at {effective_rate:.1f} msg/sec (target {target_seconds:.0f}s)"
    )

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
            continue

        target_time = start_time + (i + 1) * pace_delay
        delay = target_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    duration = time.monotonic() - start_time
    actual_mps = sent / max(duration, 0.1)
    logger.info(
        f"Stream complete: {sent}/{total} msgs sent ({errors} errors) "
        f"in {duration:.1f}s ({actual_mps:.1f} msg/sec)"
    )