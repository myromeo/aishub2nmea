import socket

def send_udp(nmea_list, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for msg in nmea_list:
        sock.sendto(msg.encode(), (host, port))

    sock.close()

