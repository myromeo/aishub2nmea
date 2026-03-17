This is the final, comprehensive `README.md` that perfectly balances your minimalist requirements with the technical documentation provided by AISHub.

---

# aishub2nmea 🚢

**aishub2nmea** is a high-performance bridge service designed for maritime data enthusiasts. It fetches live vessel positions from the **AISHub Web Service**, converts the raw data into valid **NMEA !AIVDM** sentences, and streams them via UDP to your local AIS decoder (such as AIS-catcher, PilotLogic, or OpenCPN).

This package is specifically optimized to handle large bursts of data (7,000+ messages) by pacing the delivery at **200 msg/sec**, ensuring your receiver's UDP buffers do not overflow and multi-part messages are reassembled correctly.

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
      - LAT_MIN=48.2               # UK South
      - LAT_MAX=63.9               # UK North
      - LON_MIN=-14.9              # UK West
      - LON_MAX=3.4                # UK East
      - INTERVAL=60                # API Polling Interval
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
| `INTERVAL` | `60` | The maximum age of the returned positions (in minutes). |
| `UDP_HOST` | `shipfeeder` | The hostname/container name of your NMEA receiver. |
| `UDP_PORT` | `50001` | The UDP port of your NMEA receiver. |

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

## 🛠 Technical Details
* **Fixed Pacing:** Regardless of the volume of data, the streamer is locked at **200 messages per second**.
* **Order Preservation:** Messages are sent in the exact sequence they are received from the API to ensure Type 5 Static Data parts 1 and 2 remain linked.
* **Auto-Padding:** The encoder automatically handles 6-bit alignment and padding for NMEA sentences.

---

**Everything looks solid! Would you like me to generate a simple `.dockerignore` file to ensure your `.git` and `.env` folders aren't accidentally bundled into the public image?**
