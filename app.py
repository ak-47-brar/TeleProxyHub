import gradio as gr
import requests
import socket
import time
import concurrent.futures

PROXY_SOURCE_URL = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt"
MAX_TEST_PROXIES = 80       # how many proxies to test at once
CONNECT_TIMEOUT = 4         # seconds
MAX_WORKERS = 40            # threads for parallel tests

COUNTRY_CACHE = {}          # ip -> (flag, code)


def parse_proxy_line(line: str):
    """
    Parse a line from the proxy list into 'IP:PORT'.
    Handles possible extra data like user:pass, comments, etc.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # keep only first token
    line = line.split()[0]

    # drop credentials if present (ip:port@user:pass)
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
    """
    Fetch and parse proxies from the remote text file.
    Returns a list of 'IP:PORT' strings.
    """
    try:
        r = requests.get(PROXY_SOURCE_URL, timeout=10)
        r.raise_for_status()
        raw_lines = r.text.splitlines()

        proxies = []
        seen = set()
        for line in raw_lines:
            p = parse_proxy_line(line)
            if p and p not in seen:
                seen.add(p)
                proxies.append(p)

        return proxies, f"✅ Loaded {len(proxies)} proxies from source."
    except Exception as e:
        return [], f"❌ Error fetching proxies: {e}"


def tcp_ping(proxy: str, timeout: float = CONNECT_TIMEOUT):
    """
    Measure TCP connect time to IP:PORT.
    Returns ping in ms if reachable, else None.
    """
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
            return (end - start) * 1000.0  # ms
        else:
            return None
    except Exception:
        return None


def country_code_to_flag(code: str):
    if not code or len(code) != 2:
        return "🌍"
    return "".join(chr(127397 + ord(c.upper())) for c in code)


def get_country(ip: str):
    """
    Get (flag, country_code) for an IP using ipwho.is.
    Cached to avoid repeated lookups.
    """
    if ip in COUNTRY_CACHE:
        return COUNTRY_CACHE[ip]

    try:
        url = f"https://ipwho.is/{ip}"
        resp = requests.get(url, timeout=4)
        data = resp.json()
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
    """
    working_list: list of (proxy 'ip:port', ping_ms)
    Returns pretty HTML table with flags + ping + Telegram link.
    """
    if not working_list:
        return """
        <div class="error">
            No working proxies found right now.<br>
            Free public proxies are often unstable. Try again later.
        </div>
        """

    rows_html = ""
    for idx, (proxy, ping_ms) in enumerate(working_list, 1):
        ip, port = proxy.split(":")
        flag, code = get_country(ip)

        # color for ping
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

    html = f"""
    <div class="results-wrapper">
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


def test_all_and_build_table(proxies):
    """
    Called when user clicks 'Test all proxies & show working list'.
    Tests up to MAX_TEST_PROXIES proxies in parallel and returns HTML + summary.
    """
    if not proxies:
        return (
            "<div class='error'>No proxies loaded. Refresh the page and try again.</div>",
            "❌ No proxies loaded."
        )

    targets = proxies[:MAX_TEST_PROXIES]
    total = len(targets)

    working = []

    def worker(proxy):
        ping_ms = tcp_ping(proxy)
        return proxy, ping_ms

    # Test in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(worker, p) for p in targets]
        for fut in concurrent.futures.as_completed(futures):
            proxy, ping_ms = fut.result()
            if ping_ms is not None:
                working.append((proxy, ping_ms))

    if working:
        # sort by ping ascending
        working.sort(key=lambda x: x[1])
        html = build_results_html(working)
        avg_ping = sum(p for _, p in working) / len(working)
        summary = (
            f"✅ Found {len(working)} working proxies out of {total} tested. "
            f"Average ping: {avg_ping:.0f} ms."
        )
    else:
        html = build_results_html([])
        summary = f"❌ Tested {total} proxies, no open ports detected from this environment."

    return html, summary


# ---------------------- UI ----------------------

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.gradio-container {
    background: radial-gradient(circle at top, #8e9afe 0, #2b1055 45%, #000000 100%);
    min-height: 100vh;
}

/* Header */
h1 {
    color: #ffffff !important;
    text-align: center;
    font-size: 2.8rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.2rem !important;
}
.subtitle {
    color: rgba(255,255,255,0.9);
    text-align: center;
    font-size: 1.05rem;
    margin-bottom: 1.4rem;
}

/* Glass cards */
.glass-card {
    background: rgba(15, 23, 42, 0.65);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.4);
    backdrop-filter: blur(14px);
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.8);
    padding: 18px 20px;
}

/* Buttons */
button.primary {
    background: linear-gradient(135deg, #6366f1, #a855f7) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 12px 20px !important;
    border-radius: 12px !important;
    font-size: 15px !important;
    box-shadow: 0 10px 25px rgba(129, 140, 248, 0.6) !important;
    transition: all 0.2s ease-out !important;
}
button.primary:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 14px 32px rgba(129, 140, 248, 0.85) !important;
}

/* Status box */
.status-box input {
    background: rgba(15, 23, 42, 0.7) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.4) !important;
    color: #e5e7eb !important;
}

/* Error */
.error {
    margin-top: 16px;
    padding: 14px 16px;
    background: rgba(248, 113, 113, 0.12);
    border-radius: 12px;
    border: 1px solid rgba(248, 113, 113, 0.4);
    color: #fecaca;
    text-align: center;
    font-weight: 500;
}

/* Results table */
.results-wrapper {
    margin-top: 18px;
    overflow-x: auto;
}
.results-table {
    width: 100%;
    border-collapse: collapse;
    background: rgba(15, 23, 42, 0.7);
    border-radius: 16px;
    overflow: hidden;
}
.results-table thead {
    background: rgba(30, 64, 175, 0.9);
}
.results-table th, .results-table td {
    padding: 10px 12px;
    font-size: 0.9rem;
    text-align: left;
    color: #e5e7eb;
}
.results-table th {
    font-weight: 600;
}
.results-table tbody tr:nth-child(even) {
    background: rgba(15, 23, 42, 0.85);
}
.result-row {
    transition: background 0.15s ease, transform 0.15s ease;
}
.result-row:hover {
    background: rgba(79, 70, 229, 0.4);
    transform: translateX(3px);
}

/* Columns */
.col-rank { width: 50px; }
.col-country .cc {
    font-size: 0.75rem;
    opacity: 0.9;
    margin-left: 4px;
}
.col-proxy code {
    background: rgba(15, 23, 42, 0.9);
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 0.85rem;
}
.col-action {
    text-align: right;
}

/* Ping badge */
.ping-badge {
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
}
.ping-fast {
    background: rgba(22, 163, 74, 0.2);
    color: #bbf7d0;
    border: 1px solid rgba(34, 197, 94, 0.6);
}
.ping-medium {
    background: rgba(234, 179, 8, 0.15);
    color: #fef9c3;
    border: 1px solid rgba(234, 179, 8, 0.55);
}
.ping-slow {
    background: rgba(239, 68, 68, 0.18);
    color: #fecaca;
    border: 1px solid rgba(248, 113, 113, 0.7);
}

/* Telegram button */
.tg-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 10px;
    border-radius: 999px;
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
    color: white;
    font-size: 0.8rem;
    font-weight: 600;
    text-decoration: none;
    box-shadow: 0 6px 16px rgba(56, 189, 248, 0.5);
    transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.tg-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 9px 22px rgba(56, 189, 248, 0.8);
}
"""


with gr.Blocks(css=custom_css, title="TeleProxyHub - SOCKS5 Proxy Manager") as demo:
    gr.Markdown("# 🚀 TeleProxyHub")
    gr.Markdown("<p class='subtitle'>Auto-loaded SOCKS5 proxies & one-click Telegram links – test and sort by real TCP ping.</p>")

    proxies_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=3):
            with gr.Group(elem_classes="glass-card"):
                status_text = gr.Textbox(
                    label="Status",
                    value="Loading proxies from source...",
                    interactive=False,
                    elem_classes="status-box",
                )
                test_btn = gr.Button("⚡ Test all proxies & show working list", elem_classes="primary")

        with gr.Column(scale=5):
            results_html = gr.HTML(label="Working proxies")

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
