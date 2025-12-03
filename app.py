import gradio as gr
import requests
import socket
import time
import concurrent.futures

# =========================
# CONFIGURATION SECTION
# =========================
# Customize these settings according to your needs

# Multiple proxy sources for redundancy
# Replace these with your own proxy sources
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
]

# Performance settings - adjust based on your system
MAX_TEST_PROXIES = 80    # Maximum number of proxies to test at once
CONNECT_TIMEOUT = 4      # Connection timeout in seconds
MAX_WORKERS = 40         # Number of parallel worker threads

# Geolocation API endpoint (change if needed)
# Current: ipwho.is (free, no API key required)
# Alternatives: ip-api.com, ipapi.co, freegeoip.app
GEOLOCATION_API = "https://ipwho.is/{ip}"

# =========================
# END CONFIGURATION
# =========================

COUNTRY_CACHE = {}


def parse_proxy_line(line: str):
    """Parse a line from the proxy list into 'IP:PORT'."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    line = line.split()[0]

    if "@" in line:
        line = line.split("@")[0]

    if ":" not in line:
        return None

    ip, port = line.split(":", 1)
    ip = ip.strip()
    port = port.strip()
    try:
        int(port)
    except ValueError:
        return None

    return f"{ip}:{port}"


def fetch_proxies():
    """Fetch and parse proxies from multiple sources with fallback."""
    all_proxies = []
    errors = []
    
    for idx, url in enumerate(PROXY_SOURCES, 1):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            raw_lines = r.text.splitlines()

            proxies = []
            seen = set()
            for line in raw_lines:
                p = parse_proxy_line(line)
                if p and p not in seen:
                    seen.add(p)
                    proxies.append(p)

            if proxies:
                all_proxies.extend(proxies)
                return list(set(all_proxies)), f"✅ Loaded {len(list(set(all_proxies)))} proxies from source #{idx}"
        except Exception as e:
            errors.append(f"Source #{idx}: {str(e)[:50]}")
            continue
    
    if all_proxies:
        return list(set(all_proxies)), f"✅ Loaded {len(list(set(all_proxies)))} proxies"
    
    error_msg = "\n".join(errors)
    return [], f"❌ Failed to fetch proxies from all sources:\n{error_msg}"


def tcp_ping(proxy: str, timeout: float = CONNECT_TIMEOUT):
    """Measure TCP connect time to IP:PORT."""
    try:
        ip, port_str = proxy.split(":")
        port = int(port_str)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        result = sock.connect_ex((ip, port))
        end = time.time()
        sock.close()

        if result == 0:
            return (end - start) * 1000.0
        else:
            return None
    except Exception:
        return None


def country_code_to_flag(code: str):
    if not code or len(code) != 2:
        return "🌍"
    return "".join(chr(127397 + ord(c.upper())) for c in code)


def get_country(ip: str):
    """Get (flag, country_code) for an IP using geolocation API with caching."""
    if ip in COUNTRY_CACHE:
        return COUNTRY_CACHE[ip]

    try:
        url = GEOLOCATION_API.format(ip=ip)
        resp = requests.get(url, timeout=3)
        data = resp.json()
        
        # Parse response (adjust based on your API)
        if data.get("success"):
            code = data.get("country_code") or "??"
            flag = country_code_to_flag(code)
        else:
            flag, code = "🌍", "??"
    except Exception:
        flag, code = "🌍", "??"

    COUNTRY_CACHE[ip] = (flag, code)
    return flag, code


def build_telegram_link(proxy: str):
    ip, port = proxy.split(":")
    return f"https://t.me/proxy?server={ip}&port={port}"


def build_results_html(working_list):
    """Build HTML table with working proxies."""
    if not working_list:
        return """
        <div class="error">
            🔴 No working proxies found right now.<br><br>
            💡 <b>Possible reasons:</b><br>
            • Hosting platform may block outbound connections to proxy ports<br>
            • Free public proxies are often unstable (5-15% success rate)<br>
            • Try running this app locally: <code>python app.py</code><br><br>
            🔄 Try again in a few minutes or refresh the page.
        </div>
        """

    rows_html = ""
    for idx, (proxy, ping_ms) in enumerate(working_list, 1):
        ip, port = proxy.split(":")
        flag, code = get_country(ip)

        if ping_ms < 120:
            ping_class = "ping-fast"
        elif ping_ms < 350:
            ping_class = "ping-medium"
        else:
            ping_class = "ping-slow"

        tg_link = build_telegram_link(proxy)

        rows_html += f"""
        <tr class="result-row">
            <td class="col-rank">#{idx}</td>
            <td class="col-country">{flag} <span class="cc">{code}</span></td>
            <td class="col-proxy"><code>{proxy}</code></td>
            <td class="col-ping"><span class="ping-badge {ping_class}">{ping_ms:.0f} ms</span></td>
            <td class="col-action">
                <a href="{tg_link}" target="_blank" class="tg-btn">✈️ Add to Telegram</a>
            </td>
        </tr>
        """

    avg_ping = sum(p for _, p in working_list) / len(working_list)
    html = f"""
    <div class="results-wrapper">
        <div class="stats-banner">
            <div class="stat-card">
                <div class="stat-value">{len(working_list)}</div>
                <div class="stat-label">✅ Working</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_ping:.0f}ms</div>
                <div class="stat-label">⚡ Avg Ping</div>
            </div>
        </div>
        <table class="results-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Country</th>
                    <th>Proxy</th>
                    <th>Ping</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    return html


def test_all_and_build_table(proxies, progress=gr.Progress()):
    """Test all proxies and return HTML + summary."""
    if not proxies:
        return (
            "<div class='error'>❌ No proxies loaded. Please refresh the page.</div>",
            "❌ No proxies loaded."
        )

    targets = proxies[:MAX_TEST_PROXIES]
    total = len(targets)
    
    progress(0, desc=f"Starting test of {total} proxies...")

    working = []

    def worker(proxy):
        ping_ms = tcp_ping(proxy)
        return proxy, ping_ms

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(worker, p) for p in targets]
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            proxy, ping_ms = fut.result()
            if ping_ms is not None:
                working.append((proxy, ping_ms))
            completed += 1
            progress(completed / total, desc=f"Tested {completed}/{total} | Found {len(working)}")

    if working:
        working.sort(key=lambda x: x[1])
        html = build_results_html(working)
        avg_ping = sum(p for _, p in working) / len(working)
        success_rate = (len(working) / total) * 100
        summary = f"✅ Found {len(working)}/{total} ({success_rate:.1f}%) | Avg: {avg_ping:.0f}ms"
    else:
        html = build_results_html([])
        summary = f"❌ Tested {total} proxies, none working from this environment."

    return html, summary


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

* { font-family: 'Inter', sans-serif; }

.gradio-container {
    background: radial-gradient(circle at top, #8e9afe 0, #2b1055 45%, #000000 100%);
    min-height: 100vh;
}

h1 {
    color: #ffffff !important;
    text-align: center;
    font-size: 3rem !important;
    font-weight: 800 !important;
    margin-bottom: 0.3rem !important;
    text-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.subtitle {
    color: rgba(255,255,255,0.95);
    text-align: center;
    font-size: 1.1rem;
    margin-bottom: 1.8rem;
    font-weight: 500;
}

.glass-card {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 20px;
    border: 1px solid rgba(148, 163, 184, 0.5);
    backdrop-filter: blur(16px);
    box-shadow: 0 20px 50px rgba(15, 23, 42, 0.9);
    padding: 22px 24px;
}

button.primary {
    background: linear-gradient(135deg, #6366f1, #a855f7) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    padding: 14px 24px !important;
    border-radius: 14px !important;
    font-size: 16px !important;
    box-shadow: 0 12px 28px rgba(129, 140, 248, 0.7) !important;
    transition: all 0.25s ease !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
button.primary:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 16px 36px rgba(129, 140, 248, 0.9) !important;
}

.status-box input {
    background: rgba(15, 23, 42, 0.8) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.5) !important;
    color: #e5e7eb !important;
    font-size: 14px !important;
}

.error {
    margin-top: 20px;
    padding: 24px;
    background: rgba(248, 113, 113, 0.15);
    border-radius: 14px;
    border: 2px solid rgba(248, 113, 113, 0.5);
    color: #fecaca;
    text-align: center;
    font-weight: 500;
    line-height: 1.7;
}

.stats-banner {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.stat-card {
    background: rgba(79, 70, 229, 0.3);
    border: 1px solid rgba(129, 140, 248, 0.5);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    backdrop-filter: blur(10px);
}

.stat-value {
    font-size: 32px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 4px;
}

.stat-label {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.8);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.results-wrapper {
    margin-top: 20px;
    overflow-x: auto;
}
.results-table {
    width: 100%;
    border-collapse: collapse;
    background: rgba(15, 23, 42, 0.8);
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.3);
}
.results-table thead {
    background: rgba(30, 64, 175, 0.95);
}
.results-table th, .results-table td {
    padding: 12px 14px;
    font-size: 0.9rem;
    text-align: left;
    color: #e5e7eb;
}
.results-table th {
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.8rem;
    letter-spacing: 0.5px;
}
.results-table tbody tr:nth-child(even) {
    background: rgba(15, 23, 42, 0.9);
}
.result-row {
    transition: background 0.2s ease, transform 0.2s ease;
}
.result-row:hover {
    background: rgba(79, 70, 229, 0.45);
    transform: translateX(4px);
}

.col-rank { width: 60px; font-weight: 800; font-size: 1rem; color: #a5b4fc; }
.col-country .cc {
    font-size: 0.75rem;
    opacity: 0.9;
    margin-left: 5px;
}
.col-proxy code {
    background: rgba(15, 23, 42, 0.95);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.85rem;
    border: 1px solid rgba(148, 163, 184, 0.3);
}
.col-action {
    text-align: right;
}

.ping-badge {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
}
.ping-fast {
    background: rgba(22, 163, 74, 0.25);
    color: #bbf7d0;
    border: 1px solid rgba(34, 197, 94, 0.7);
}
.ping-medium {
    background: rgba(234, 179, 8, 0.2);
    color: #fef9c3;
    border: 1px solid rgba(234, 179, 8, 0.6);
}
.ping-slow {
    background: rgba(239, 68, 68, 0.2);
    color: #fecaca;
    border: 1px solid rgba(248, 113, 113, 0.7);
}

.tg-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 7px 12px;
    border-radius: 999px;
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
    color: white;
    font-size: 0.8rem;
    font-weight: 700;
    text-decoration: none;
    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.6);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.tg-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(56, 189, 248, 0.9);
}

@media (max-width: 768px) {
    h1 { font-size: 2rem !important; }
    .results-table th, .results-table td { font-size: 0.8rem; padding: 8px 10px; }
}
"""


with gr.Blocks(css=custom_css, title="TeleProxyHub - SOCKS5 Proxy Manager") as demo:
    gr.Markdown("# 🚀 TeleProxyHub")
    gr.Markdown("<p class='subtitle'>🔒 Free SOCKS5 Proxies for Telegram | Auto-tested & Sorted by Speed</p>")

    proxies_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=3):
            with gr.Group(elem_classes="glass-card"):
                status_text = gr.Textbox(
                    label="📊 Status",
                    value="Loading proxies from multiple sources...",
                    interactive=False,
                    elem_classes="status-box",
                    lines=3,
                )
                test_btn = gr.Button("⚡ TEST ALL PROXIES", elem_classes="primary")

        with gr.Column(scale=5):
            results_html = gr.HTML(label="Working proxies")

    gr.Markdown("""
    <div style='text-align: center; color: rgba(255,255,255,0.75); margin-top: 24px; font-size: 13px; line-height: 1.7;'>
    💡 <b>How it works:</b> Tests TCP connection to each proxy port<br>
    🌍 <b>Country Detection:</b> Via IP lookup API with caching<br>
    ⚠️ <b>Note:</b> If no proxies work, try running locally: <code>python app.py</code>
    </div>
    """)

    def init_proxies():
        proxies, msg = fetch_proxies()
        return proxies, msg

    demo.load(
        fn=init_proxies,
        inputs=None,
        outputs=[proxies_state, status_text],
    )

    test_btn.click(
        fn=test_all_and_build_table,
        inputs=[proxies_state],
        outputs=[results_html, status_text],
    )

if __name__ == "__main__":
    demo.launch()
