# aishub2nmea 🚢

**aishub2nmea** is a high-performance bridge service designed for maritime data enthusiasts. It fetches live vessel positions from the **AISHub Web Service**, converts the raw data into valid **NMEA !AIVDM** sentences, and streams them via UDP to your local AIS decoder (such as AIS-catcher, PilotLogic, or OpenCPN).

This package is specifically optimized to handle large bursts of data by pacing the delivery at **200 msg/sec**, ensuring your receiver's UDP buffers do not overflow and multi-part messages are reassembled correctly.

## 🚀 Quick Start (Docker Compose)

The example below is pre-configured for **UK Waters**. 

```yaml
services:
  ais-forwarder:
    image: ghcr.io/myromeo/aishub2nmea:latest
    container_name: ais-forwarder
    restart: unless-stopped
    environment:
      - AIS_USERNAME=AH_XXXX_XXXX  # Required: Your AISHub username
      - UDP_HOST=shipfeeder       # The container name of your AIS receiver
      - UDP_PORT=50001
      - LAT_MIN=49.7   # South
      - LAT_MAX=58.8   # North
      - LON_MIN=-8     # West
      - LON_MAX=2.1    # East
    networks:
      - ais_network

networks:
  ais_network:
    external: true
```

> [!CAUTION]
> **RATE LIMIT ADVISORY:** Do not set the `INTERVAL` faster than **60 seconds**. AISHub strictly enforces rate limits based on your account type. Polling too frequently will result in empty data sets or temporary IP bans.

---

## ⚙️ Available Parameters

These variables can be defined in the `environment` section of your `docker-compose.yml`.

| Variable | Default | AISHub Description |
| :--- | :--- | :--- |
| `AIS_USERNAME` | - | **Required:** Your AISHub username. You will receive it after joining AISHub. |
| `AIS_FORMAT` | `1` | Format of data values (0 – AIS encoding, 1 – Human readable format). |
| `AIS_OUTPUT` | `xml` | Output format (xml, json, csv). |
| `AIS_COMPRESS` | `0` | Compression (0 – no compression, 1 – ZIP, 2 – GZIP, 3 – BZIP2). |
| `LAT_MIN` | `48.5` | South (minimum) latitude. |
| `LAT_MAX` | `51.5` | North (maximum) latitude. |
| `LON_MIN` | `-6.5` | West (minimum) longitude. |
| `LON_MAX` | `2.5` | East (maximum) longitude. |
| `MMSI` | - | MMSI number or list of numbers (webservice returns data for requested vessels only). |
| `IMO` | - | IMO number or list of numbers (webservice returns data for requested vessels only). |
| `INTERVAL` | `30` | The maximum age of the returned positions (in minutes). |
| `UDP_HOST` | `shipfeeder` | The hostname/container name of your NMEA receiver. |
| `UDP_PORT` | `50001` | The UDP port of your NMEA receiver. |
| `POLL_INTERVAL` | `60` | Frequency of API requests in seconds. |

---

## 🌐 Docker Networking

To allow `ais-forwarder` to communicate with your AIS receiver, they must share a Docker network.

1. **Service Discovery:** Use the **container_name** of your receiver as the `UDP_HOST`.
2. **External Networks:** If your receiver is in a different Compose file, ensure both services use an externally defined network:
   ```bash
   docker network create ais_network
   ```
   Then set `external: true` in your `networks` section as shown in the Quick Start.

---
