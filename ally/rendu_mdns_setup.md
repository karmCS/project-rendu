# Rendu - mDNS Setup Guide

Allows the Pi to always find the Ally by hostname (`rendu-ally.local`) instead of IP address. Do this once at deployment time.

---

## 1. Ally (Windows) - Set Hostname

1. **Settings → System → About → Rename this PC**
2. Set name to: `rendu-ally`
3. Reboot when prompted

That's all Windows needs. mDNS (via the built-in Bonjour service) is enabled by default on Windows 10/11.

> **Verify:** Open a command prompt and run `hostname` - it should return `rendu-ally`.

---

## 2. Pi - Install and Enable Avahi

SSH into the Pi and run:

```bash
sudo apt update
sudo apt install avahi-daemon -y
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

Verify it's running:

```bash
sudo systemctl status avahi-daemon
```

You should see `active (running)`.

---

## 3. Pi - Test Resolution

From the Pi, confirm it can resolve the Ally's hostname:

```bash
ping rendu-ally.local
```

You should see replies from the Ally's current IP. If this works, mDNS is good.

> **If ping fails:** Make sure both devices are on the same network and that the Ally's firewall isn't blocking mDNS (UDP port 5353). See troubleshooting section below.

---

## 4. Pi - Update Sync Script

Wherever your Pi sync script has the Ally's IP hardcoded, replace it:

```python
# Before
ALLY_URL = "http://192.168.1.100:8000"

# After
ALLY_URL = "http://rendu-ally.local:8000"
```

---

## 5. Frontend - Update .env

On the Ally, in your Rendu project `.env`:

```
VITE_API_BASE_URL=http://rendu-ally.local:8000
```

Rebuild the React app after changing this:

```bash
npm run build
```

Then copy the build output into `app/static/` as usual.

---

## Troubleshooting

### Ping fails from Pi to Ally

**Check avahi is running:**
```bash
sudo systemctl status avahi-daemon
```

**Check Windows Firewall isn't blocking mDNS:**
- Open Windows Defender Firewall → Advanced Settings
- Inbound Rules → look for any rule blocking UDP port 5353
- Or temporarily disable the firewall to test

**Check client isolation:**
Some public WiFi (hotels, airports, many coffee shops) blocks device-to-device traffic even on the same network. If ping fails on public WiFi but works at home, this is why. Use a travel router to create your own private LAN.

### Ally hostname not resolving

Make sure the Ally was rebooted after renaming. Windows doesn't broadcast the new mDNS hostname until after a restart.

### Works at home, fails elsewhere

See client isolation note above. A GL.iNet travel router (~$25) solves this - both devices connect to it and form an isolated LAN that works anywhere.

---

## How It Works (for reference)

mDNS (multicast DNS) lets devices on the same LAN find each other by hostname without a central DNS server. When the Pi looks up `rendu-ally.local`, it sends a multicast query on the network. The Ally hears it and replies with its current IP - whatever that IP happens to be. This means the sync always works even if the Ally gets a new DHCP address on a different network.

- **Windows side:** Built-in Bonjour service handles mDNS automatically
- **Pi side:** `avahi-daemon` is the Linux equivalent of Bonjour
- **No code changes required** beyond updating the hostname string in the sync script and `.env`
