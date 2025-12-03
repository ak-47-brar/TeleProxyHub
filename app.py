import gradio as gr
import requests
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Country flag mapping for common proxy locations
COUNTRY_FLAGS = {
    'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'DE': '🇩🇪', 'FR': '🇫🇷',
    'NL': '🇳🇱', 'SG': '🇸🇬', 'JP': '🇯🇵', 'IN': '🇮🇳', 'AU': '🇦🇺',
    'BR': '🇧🇷', 'RU': '🇷🇺', 'CN': '🇨🇳', 'KR': '🇰🇷', 'IT': '🇮🇹',
    'ES': '🇪🇸', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮', 'DK': '🇩🇰',
    'PL': '🇵🇱', 'TR': '🇹🇷', 'MX': '🇲🇽', 'AR': '🇦🇷', 'CL': '🇨🇱',
    'ZA': '🇿🇦', 'EG': '🇪🇬', 'IL': '🇮🇱', 'AE': '🇦🇪', 'SA': '🇸🇦',
    'TH': '🇹🇭', 'VN': '🇻🇳', 'ID': '🇮🇩', 'MY': '🇲🇾', 'PH': '🇵🇭',
    'HK': '🇭🇰', 'TW': '🇹🇼', 'UA': '🇺🇦', 'CZ': '🇨🇿', 'AT': '🇦🇹'
}


def get_country_from_ip(ip):
    """Get country code from IP using ip-api.com"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', 'UN')
        return 'UN'
    except:
        return 'UN'


def fetch_proxies():
    """Fetch proxies from the CDN source"""
    try:
        url = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        proxies = [line.strip() for line in response.text.split('\n') if line.strip()]
        return proxies
    except Exception as e:
        return []


def create_telegram_link(proxy):
    """Convert proxy to Telegram proxy link"""
    try:
        if ':' in proxy:
            server, port = proxy.split(':')
            return f"https://t.me/proxy?server={server}&port={port}"
        return None
    except:
        return None


def test_proxy_ping(proxy, timeout=5):
    """Test if proxy is responding"""
    try:
        if ':' not in proxy:
            return False, "Invalid", 99999, 'UN'

        server, port = proxy.split(':')
        start_time = time.time()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server, int(port)))
        sock.close()

        ping_time = (time.time() - start_time) * 1000

        if result == 0:
            country = get_country_from_ip(server)
            return True, f"{ping_time:.0f}ms", ping_time, country
        else:
            return False, "Unreachable", 99999, 'UN'
    except Exception as e:
        return False, "Failed", 99999, 'UN'


def test_proxy_full(proxy):
    """Test a single proxy and return full results"""
    is_working, result_text, ping_ms, country = test_proxy_ping(proxy, timeout=5)
    return {
        'proxy': proxy,
        'is_working': is_working,
        'ping_ms': ping_ms,
        'ping_text': result_text,
        'country': country
    }


def auto_load_proxies():
    """Auto-load proxies on startup"""
    proxies = fetch_proxies()
    if proxies:
        return f"✅ Loaded {len(proxies)} proxies ready to test"
    return "❌ Failed to load proxies"


def test_all_proxies(progress=gr.Progress()):
    """Test all proxies and display working ones in a list"""
    progress(0, desc="Fetching proxies...")
    proxies = fetch_proxies()
    
    if not proxies:
        return "<div class='error'>Failed to load proxies</div>", "❌ Error"
    
    progress(0.1, desc=f"Testing {len(proxies)} proxies...")
    
    results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(test_proxy_full, proxy): proxy for proxy in proxies}
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result['is_working']:  # Only keep working proxies
                results.append(result)
            completed += 1
            progress(0.1 + (0.8 * completed / len(proxies)), 
                    desc=f"Tested {completed}/{len(proxies)} | Found {len(results)} working")
    
    # Sort by ping (lowest first)
    results.sort(key=lambda x: x['ping_ms'])
    
    progress(0.95, desc="Generating list...")
    
    # Generate list HTML
    html = "<div class='proxy-list-container'>"
    
    if not results:
        html += "<div class='error'>No working proxies found. Try again later.</div>"
    else:
        html += "<div class='proxy-list-header'>"
        html += "<div class='header-item'>#</div>"
        html += "<div class='header-item'>Country</div>"
        html += "<div class='header-item'>Proxy Address</div>"
        html += "<div class='header-item'>Ping</div>"
        html += "<div class='header-item'>Action</div>"
        html += "</div>"
        
        for idx, r in enumerate(results, 1):
            tg_link = create_telegram_link(r['proxy'])
            flag = COUNTRY_FLAGS.get(r['country'], '🌍')
            
            html += f"""
            <div class='proxy-list-row'>
                <div class='list-cell rank'>{idx}</div>
                <div class='list-cell country'><span class='flag'>{flag}</span> {r['country']}</div>
                <div class='list-cell address'>{r['proxy']}</div>
                <div class='list-cell ping'><span class='ping-badge'>{r['ping_text']}</span></div>
                <div class='list-cell action'>
                    <a href="{tg_link}" target="_blank" class="add-btn">✈️ Add to Telegram</a>
                </div>
            </div>
            """
    
    html += "</div>"
    
    working_count = len(results)
    status = f"✅ Found {working_count} working proxies out of {len(proxies)} tested"
    
    progress(1.0, desc="Complete!")
    return html, status


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

.gradio-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.proxy-list-container {
    max-width: 1200px;
    margin: 20px auto;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(15px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.proxy-list-header {
    display: grid;
    grid-template-columns: 60px 120px 1fr 120px 200px;
    gap: 15px;
    padding: 15px 20px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    margin-bottom: 10px;
    font-weight: 700;
    color: white;
    text-transform: uppercase;
    font-size: 13px;
    letter-spacing: 0.5px;
}

.proxy-list-row {
    display: grid;
    grid-template-columns: 60px 120px 1fr 120px 200px;
    gap: 15px;
    padding: 18px 20px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    margin-bottom: 8px;
    transition: all 0.3s ease;
    align-items: center;
    animation: slideIn 0.4s ease;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.proxy-list-row:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: translateX(5px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.list-cell {
    color: white;
    font-size: 14px;
}

.list-cell.rank {
    font-weight: 700;
    font-size: 16px;
    color: #a5b4fc;
}

.list-cell.country {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
}

.flag {
    font-size: 20px;
}

.list-cell.address {
    font-weight: 500;
    font-family: 'Courier New', monospace;
    color: #e0e7ff;
}

.ping-badge {
    display: inline-block;
    padding: 6px 12px;
    background: rgba(34, 197, 94, 0.3);
    color: #22c55e;
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid rgba(34, 197, 94, 0.5);
}

.add-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 18px;
    background: linear-gradient(135deg, #0088cc, #0066aa);
    color: white;
    text-decoration: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 13px;
    transition: all 0.3s;
    box-shadow: 0 4px 12px rgba(0, 136, 204, 0.3);
}

.add-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 18px rgba(0, 136, 204, 0.5);
}

.error {
    color: #ff6b6b;
    background: rgba(255, 107, 107, 0.15);
    padding: 30px;
    border-radius: 15px;
    text-align: center;
    font-weight: 600;
    font-size: 16px;
}

h1 {
    color: white !important;
    text-align: center;
    font-size: 3em !important;
    font-weight: 700 !important;
    text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    margin-bottom: 10px !important;
}

.subtitle {
    color: rgba(255, 255, 255, 0.95);
    text-align: center;
    font-size: 1.2em;
    margin-bottom: 30px;
    font-weight: 500;
}

button.primary {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 15px 30px !important;
    border-radius: 12px !important;
    font-size: 16px !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    transition: all 0.3s !important;
}

button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
}

@media (max-width: 768px) {
    .proxy-list-header,
    .proxy-list-row {
        grid-template-columns: 1fr;
        gap: 10px;
    }
    
    .header-item {
        display: none;
    }
    
    .list-cell::before {
        content: attr(data-label);
        font-weight: 700;
        margin-right: 10px;
    }
}
"""


with gr.Blocks(css=custom_css, title="TeleProxyHub - SOCKS5 Proxy Manager") as demo:
    gr.Markdown("# 🚀 TeleProxyHub")
    gr.Markdown("<p class='subtitle'>Free SOCKS5 Proxies for Telegram - Auto-tested & Sorted by Speed</p>")
    
    status_text = gr.Textbox(label="Status", interactive=False, value="Loading proxies...")
    
    test_btn = gr.Button("⚡ Test All Proxies & Show Working List", elem_classes="primary", size="lg")
    
    proxy_list = gr.HTML()
    
    # Auto-load on startup
    demo.load(
        fn=auto_load_proxies,
        outputs=[status_text]
    )
    
    # Test all on button click
    test_btn.click(
        fn=test_all_proxies,
        outputs=[proxy_list, status_text]
    )


if __name__ == "__main__":
    demo.launch()
