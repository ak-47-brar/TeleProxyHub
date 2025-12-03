---
title: TeleProxyHub
emoji: 🚀
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# 🚀 TeleProxyHub

> **⚠️ PROJECT DISCONTINUED**  
> This project has been discontinued as of December 3, 2025.

## What Happened

This application was designed to test free SOCKS5 proxies and generate Telegram proxy links for educational purposes. However, the Hugging Face Space hosting this project was removed due to platform policy violations.

### Why It Was Removed

**Hugging Face Content Policy Violation:**
- The platform explicitly prohibits tools that facilitate proxy usage, VPNs, or similar networking tools under their "Platform Abuse, Security Violations and Spam" policy
- The app's functionality (testing 80+ concurrent TCP connections to proxy servers) triggered automated abuse detection systems
- Resource-intensive network testing is incompatible with Hugging Face Spaces' intended use case (ML/AI applications)

### What This Project Did

TeleProxyHub was a web application that:
- ✅ Fetched free SOCKS5 proxy lists from multiple public sources
- ✅ Tested proxy availability using TCP connection ping
- ✅ Displayed working proxies sorted by response time
- ✅ Generated one-click Telegram proxy links with country flags
- ✅ Provided a beautiful glassmorphism UI with real-time progress tracking

## Technical Details

### Features Implemented
- **Multiple proxy sources** with automatic fallback (4 different APIs)
- **Parallel TCP connection testing** (up to 80 proxies, 40 workers)
- **Country detection** via IP geolocation API with caching
- **Real-time progress** indicator during testing
- **Responsive design** with gradient backgrounds and smooth animations
- **Statistics dashboard** showing working count and average ping

### Technology Stack
- **Frontend/Backend:** Gradio 4.x
- **Language:** Python 3.x
- **Libraries:** `requests`, `socket`, `concurrent.futures`
- **Deployment:** ~~Hugging Face Spaces~~ (discontinued)

## Configuration

### 🔧 Customizing the App

All configurable settings are at the top of `app.py`:

```python
# Proxy data sources - add your own or modify existing
PROXY_SOURCES = [
    "https://example.com/your-proxy-source-1.txt",
    "https://example.com/your-proxy-source-2.txt",
    # Add more sources here
]

# Performance settings
MAX_TEST_PROXIES = 80    # How many proxies to test at once
CONNECT_TIMEOUT = 4      # Seconds to wait for connection
MAX_WORKERS = 40         # Parallel testing threads
```

### 🌐 Adding Your Own Proxy Sources

1. Find free proxy list APIs or GitHub repositories with proxy lists
2. Add URLs to the `PROXY_SOURCES` list in `app.py`
3. Supported formats:
   - Plain text files with `IP:PORT` per line
   - APIs returning proxy lists
   - GitHub raw file URLs

**Example sources you can use:**
```python
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/[USERNAME]/[REPO]/main/proxies.txt",
    "https://api.yourservice.com/proxies?type=socks5",
    "https://cdn.jsdelivr.net/gh/[USERNAME]/[REPO]@main/list.txt",
]
```

### ⚙️ Performance Tuning

**For slower systems:**
```python
MAX_TEST_PROXIES = 30   # Test fewer proxies
MAX_WORKERS = 15        # Use fewer threads
CONNECT_TIMEOUT = 3     # Shorter timeout
```

**For faster systems/servers:**
```python
MAX_TEST_PROXIES = 150  # Test more proxies
MAX_WORKERS = 60        # Use more threads
CONNECT_TIMEOUT = 5     # Longer timeout for distant servers
```

### 🌍 Changing Geolocation Service

The app uses `ipwho.is` for country detection. To use a different service:

1. Find the `get_country()` function in `app.py`
2. Replace the API URL and response parsing:

```python
def get_country(ip: str):
    if ip in COUNTRY_CACHE:
        return COUNTRY_CACHE[ip]
    
    try:
        # Replace with your preferred geolocation API
        url = f"https://your-geo-api.com/{ip}"
        resp = requests.get(url, timeout=3)
        data = resp.json()
        
        # Parse according to your API's response format
        code = data.get("countryCode") or "??"
        flag = country_code_to_flag(code)
    except Exception:
        flag, code = "🌍", "??"
    
    COUNTRY_CACHE[ip] = (flag, code)
    return flag, code
```

**Free alternatives:**
- `ip-api.com` - 45 requests/min free
- `ipapi.co` - 1000 requests/day free
- `freegeoip.app` - Free tier available

## Running Locally

If you want to use this tool for educational purposes, you can still run it locally:

```bash
# Clone the repository (replace with your fork)
git clone https://github.com/YOUR-USERNAME/TeleProxyHub.git
cd TeleProxyHub

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The app will launch at `http://localhost:7860`

## Alternative Deployment Options

If you want to deploy this elsewhere (at your own risk):

### Platforms That May Allow This
- **Railway.app** - More lenient networking policies ($5 free credit)
- **Render.com** - Free tier, check their terms first
- **Self-hosted VPS** - DigitalOcean, Linode, Hetzner (full control)
- **Replit** - May work for educational projects

### ⚠️ Important Notes
- Always check platform Terms of Service before deploying
- Proxy testing tools may be restricted on many platforms
- Use for educational/research purposes only
- Ensure compliance with local laws and regulations

## Why This Project Was Educational

This project demonstrated:
- 🔹 **Network programming** - TCP socket connections and timeout handling
- 🔹 **Concurrent programming** - Parallel testing with ThreadPoolExecutor
- 🔹 **API integration** - Multiple data sources with fallback mechanisms
- 🔹 **UI/UX design** - Modern web interfaces with Gradio
- 🔹 **Error handling** - Robust exception management and retry logic
- 🔹 **Caching strategies** - IP geolocation result caching

## Lessons Learned

1. **Platform policies matter** - Always read and understand ToS before deploying
2. **Resource usage has limits** - Mass network testing triggers abuse detection
3. **Choose appropriate hosting** - ML platforms aren't for networking tools
4. **Educational intent doesn't exempt violations** - Policies apply regardless of purpose

## Project Status

- ✅ Code is complete and functional
- ❌ No longer hosted on Hugging Face Spaces
- ℹ️ Available for local use only
- 🔒 Repository archived for reference

---

## Disclaimer

This tool was created for educational purposes to demonstrate network programming concepts. The author is not responsible for any misuse of this code. Users must:
- Comply with all applicable laws and regulations
- Respect platform Terms of Service
- Use proxies ethically and legally
- Understand privacy and security implications

## License

MIT License - See LICENSE file for details

---

## Contributing

While the original project is discontinued, you're welcome to:
- Fork this repository and create your own version
- Submit issues for bugs or improvements
- Share alternative deployment methods
- Suggest better proxy sources or APIs

---

**Project Timeline:**
- Created: December 3, 2025
- Deployed: December 3, 2025
- Discontinued: December 3, 2025

*This README serves as documentation of what was learned during this project's brief existence.*
