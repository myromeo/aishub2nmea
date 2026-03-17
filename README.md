# AISHub-to-UDP Forwarder 🛰️

A high-performance Python service that bridges the **AISHub API** to local AIS decoders (like **AIS-catcher**). It fetches XML vessel data, encodes it into bit-perfect AIVDM NMEA sentences, and forwards them via UDP.

## 🛠 Features
* **Sequential Payload Delivery:** Sends multi-part Type 5 messages (Static Data) in a tight sequence to ensure decoders link them correctly.
* **Auto-Alignment:** Handles the complex 424-bit padding required for AIS Type 5 to prevent text corruption in destination fields.
* **Dockerized:** Ready for `ghcr.io` deployment with zero local dependencies.

---

## 🚀 Deployment (Docker Compose)

The most reliable way to run this is alongside your AIS-catcher container:

```yaml
services:
  ais-forwarder:
    image: ghcr.io/myromeo/aishub2nmea:latest
    container_name: ais-forwarder
    restart: unless-stopped
    environment:
      - AIS_USER=AH_XXXX_XXXX   # Your AISHub Username
      - TARGET_HOST=shipfeeder # Container name or IP
      - TARGET_PORT=50001   # Your container port
      - LAT_MIN=48.2
      - LAT_MAX=63.9
      - LON_MIN=-14.9
      - LON_MAX=3.4
      - INTERVAL=60            # Pull every 60 seconds
    networks:
      - shipfeeder_net

networks:
  shipfeeder_net:
    external: true
```

---

## ⚙️ Configuration Variables

### 🔴 Fixed Parameters (Do Not Change)
These are required for the internal parser to function. Changing these in your script will cause decoding errors.
* **`format`**: `1` (Human-readable XML structure)
* **`compress`**: `0` (Uncompressed for direct parsing)
* **`output`**: `xml`

### 🟢 Customization Variables
| Variable | Description | Default |
| :--- | :--- | :--- |
| `AIS_USER` | Your AISHub Username | **REQUIRED** |
| `TARGET_HOST` | UDP Destination (IP or Hostname) | `localhost` |
| `TARGET_PORT` | UDP Destination Port | `50001` |
| `INTERVAL` | Seconds between API pulls | `60` |

### 🌐 Bounding Box (Default: UK Waters)
Adjust these to change your coverage area.
* **`LAT_MIN` / `LAT_MAX`**: `48.2` to `63.9`
* **`LON_MIN` / `LON_MAX`**: `-14.9` to `3.4`

---

## 📡 Network Tips

* **Internal Networking:** If running in Docker, ensure this container is on the **same network** as your AIS receiver. Use the receiver's **container name** as the `TARGET_HOST`.
* **UDP Traffic:** Unlike TCP, UDP doesn't "handshake." Use `tcpdump -i any udp port 50001 -A` on your host to verify data is actually flowing if you don't see ships on your map.
* **API Limits:** Ensure your `INTERVAL` doesn't exceed your AISHub subscription limits (usually 60 seconds for basic users).

---

## 📦 How to Build (Local)
If you want to modify the code and build your own image:
```bash
docker build -t ais-forwarder .
```

---

### Final Polish for your Repository:
1.  **License:** Consider adding an `MIT License` file so people know they can use it.
2.  **Secrets:** Remind users in the README **never** to commit their `AIS_USER` to their own public forks.
