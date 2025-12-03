import gradio as gr
import requests
import socket
import time
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Country flag mapping
COUNTRY_FLAGS = {
    'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'DE': '🇩🇪', 'FR': '🇫🇷',
    'NL': '🇳🇱', 'SG': '🇸🇬', 'JP': '🇯🇵', 'IN': '🇮🇳', 'AU': '🇦🇺',
    'BR': '🇧🇷', 'RU': '🇷🇺', 'CN': '🇨🇳', 'KR': '🇰🇷', 'IT': '🇮🇹',
    'ES': '🇪🇸', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮', 'DK': '🇩🇰',
    'PL': '🇵🇱', 'TR': '🇹🇷', 'MX': '🇲🇽', 'AR': '🇦🇷', 'CL': '🇨🇱',
    'ZA': '🇿🇦', 'EG': '🇪🇬', 'IL': '🇮🇱', 'AE': '🇦🇪', 'SA': '🇸🇦',
    'TH': '🇹🇭', 'VN': '🇻🇳', 'ID': '🇮🇩', 'MY': '🇲🇾', 'PH': '🇵🇭',
    'HK': '🇭🇰', 'TW': '🇹🇼', 'UA': '🇺🇦', 'CZ': '🇨🇿', 'AT': '🇦🇹',
    'CH': '🇨🇭', 'BE': '🇧🇪', 'PT': '🇵🇹', 'GR': '🇬🇷', 'HU': '🇭🇺',
    'RO': '🇷🇴', 'BG': '🇧🇬', 'HR': '🇭🇷', 'LT': '🇱🇹', 'LV': '🇱🇻'
}

# Global cache
proxy_cache = {'proxies': [], 'timestamp': None}


def get_country_from_ip(ip):
    """Get country code from IP using ip-api.com"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', 'UN')
    except:
        pass
    return 'UN'


def fetch_proxies():
    """Fetch proxies from the CDN source"""
    try:
        url = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        proxies = [line.strip() for line in response.text.split('\n') if line.strip() and ':' in line]
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


def test_socks5_proxy(proxy, timeout=5):
    """Test SOCKS5 proxy using proper SOCKS5 handshake protocol"""
    try:
        if ':' not in proxy:
            return False, "Invalid", 99999, 'UN'

        server, port = proxy.split(':')
        port = int(port)
        
        start_time = time.time()
        
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Connect to proxy
        sock.connect((server, port))
        
        # Send SOCKS5 greeting (version 5, 1 auth method, no auth)
        greeting = struct.pack('BBB', 0x05, 0x01, 0x00)
        sock.sendall(greeting)
        
        # Receive response (should be 0x05 0x00 for success)
        response = sock.recv(2)
        sock.close()
        
        ping_time = (time.time() - start_time) * 1000
        
        if len(response) == 2:
            version, auth = struct.unpack('BB', response)
            if version == 0x05 and auth == 0x00:
                country = get_country_from_ip(server)
                return True, f"{ping_time:.0f}ms", ping_time, country
        
        return False, "Failed", 99999, 'UN'
        
    except socket.timeout:
        return False, "Timeout", 99999, 'UN'
    except ConnectionRefusedError:
        return False, "Refused", 99999, 'UN'
    except Exception as e:
        return False, "Error", 99999, 'UN'


def test_proxy_full(proxy):
    """Test a single proxy and return full results"""
    is_working, result_text, ping_ms, country = test_socks5_proxy(proxy, timeout=5)
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
        proxy_cache['proxies'] = proxies
        proxy_cache['timestamp'] = datetime.now()
        return f"✅ Loaded {len(proxies)} SOCKS5 proxies ready to test"
    return "❌ Failed to load proxies"


def test_all_proxies(progress=gr.Progress()):
    """Test all proxies and display working ones in a list"""
    progress(0, desc="Fetching proxies...")
    
    # Use cached proxies if available
    if proxy_cache['proxies']:
        proxies = proxy_cache['proxies']
    else:
        proxies = fetch_proxies()
        proxy_cache['proxies'] = proxies
    
    if not proxies:
        return "<div class='error'>❌ Failed to load proxies. Please try again.</div>", "❌ Error"
    
    progress(0.1, desc=f"Testing {len(proxies)} proxies...")
    
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(test_proxy_full, proxy): proxy for proxy in proxies}
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result['is_working']:  # Only keep working proxies
                results.append(result)
            completed += 1
            progress(0.1 + (0.8 * completed / len(proxies)), 
                    desc=f"Tested {completed}/{len(proxies)} | ✅ Found {len(results)} working")
    
    # Sort by ping (lowest first)
    results.sort(key=lambda x: x['ping_ms'])
    
    progress(0.95, desc="Generating list...")
    
    # Generate list HTML
    html = "<div class='proxy-list-container'>"
    
    if not results:
        html += "<div class='error'>🔴 No working SOCKS5 proxies found at this time.<br><br>"
        html += "🔄 Free public proxies can be unstable. Try refreshing in a few minutes.<br>"
        html += "💡 Tip: Public SOCKS5 proxies often have low success rates (5-15%).</div>"
    else:
        # Stats banner
        avg_ping = sum(r['ping_ms'] for r in results) / len(results)
        html += f"<div class='stats-banner'>"
        html += f"<div class='stat-item'><span class='stat-label'>✅ Working</span><span class='stat-value'>{len(results)}</span></div>"
        html += f"<div class='stat-item'><span class='stat-label'>🌍 Total Tested</span><span class='stat-value'>{len(proxies)}</span></div>"
        html += f"<div class='stat-item'><span class='stat-label'>⚡ Avg Ping</span><span class='stat-value'>{avg_ping:.0f}ms</span></div>"
        html += f"<div class='stat-item'><span class='stat-label'>📅 Updated</span><span class='stat-value'>{datetime.now().strftime('%H:%M')}</span></div>"
        html += "</div>"
        
        html += "<div class='proxy-list-header'>"
        html += "<div class='header-item rank-col'>#</div>"
        html += "<div class='header-item country-col'>Country</div>"
        html += "<div class='header-item address-col'>Proxy Address</div>"
        html += "<div class='header-item ping-col'>Ping</div>"
        html += "<div class='header-item action-col'>Action</div>"
        html += "</div>"
        
        for idx, r in enumerate(results, 1):
            tg_link = create_telegram_link(r['proxy'])
            flag = COUNTRY_FLAGS.get(r['country'], '🌍')
            
            # Color code by ping speed
            if r['ping_ms'] < 100:
                ping_class = 'fast'
            elif r['ping_ms'] < 300:
                ping_class = 'medium'
            else:
                ping_class = 'slow'
            
            html += f"""
            <div class='proxy-list-row'>
                <div class='list-cell rank-col'>{idx}</div>
                <div class='list-cell country-col'><span class='flag'>{flag}</span> <span class='country-code'>{r['country']}</span></div>
                <div class='list-cell address-col'><code>{r['proxy']}</code></div>
                <div class='list-cell ping-col'><span class='ping-badge {ping_class}'>{r['ping_text']}</span></div>
                <div class='list-cell action-col'>
                    <a href="{tg_link}" target="_blank" class="add-btn">✈️ Add to Telegram</a>
                </div>
            </div>
            """
    
    html += "</div>"
    
    working_count = len(results)
    success_rate = (working_count / len(proxies) * 100) if proxies else 0
    status = f"✅ Found {working_count} working proxies out of {len(proxies)} tested ({success_rate:.1f}% success rate)"
    
    progress(1.0, desc="Complete!")
    return html, status


def copy_to_clipboard(proxy):
    """Return proxy for copying"""
    return proxy


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

.gradio-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.proxy-list-container {
    max-width: 1300px;
    margin: 20px auto;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(15px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 25px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.stats-banner {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}

.stat-item {
    background: rgba(255, 255, 255, 0.15);
    padding: 15px 20px;
    border-radius: 12px;
    text-align: center;
}

.stat-label {
    display: block;
    color: rgba(255, 255, 255, 0.8);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 5px;
}

.stat-value {
    display: block;
    color: white;
    font-size: 24px;
    font-weight: 800;
}

.proxy-list-header {
    display: grid;
    grid-template-columns: 60px 130px 1fr 110px 200px;
    gap: 15px;
    padding: 15px 20px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    margin-bottom: 10px;
    font-weight: 700;
    color: white;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 0.5px;
}

.proxy-list-row {
    display: grid;
    grid-template-columns: 60px 130px 1fr 110px 200px;
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

.list-cell.rank-col {
    font-weight: 800;
    font-size: 18px;
    color: #a5b4fc;
}

.list-cell.country-col {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
}

.flag {
    font-size: 22px;
}

.country-code {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.9);
}

.list-cell.address-col code {
    font-weight: 500;
    font-family: 'Courier New', monospace;
    color: #e0e7ff;
    background: rgba(0, 0, 0, 0.2);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 13px;
}

.ping-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 13px;
    border: 1px solid;
}

.ping-badge.fast {
    background: rgba(34, 197, 94, 0.3);
    color: #22c55e;
    border-color: rgba(34, 197, 94, 0.5);
}

.ping-badge.medium {
    background: rgba(251, 191, 36, 0.3);
    color: #fbbf24;
    border-color: rgba(251, 191, 36, 0.5);
}

.ping-badge.slow {
    background: rgba(239, 68, 68, 0.3);
    color: #ef4444;
    border-color: rgba(239, 68, 68, 0.5);
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
    color: #fef2f2;
    background: rgba(239, 68, 68, 0.2);
    padding: 40px;
    border-radius: 15px;
    text-align: center;
    font-weight: 600;
    font-size: 16px;
    line-height: 1.8;
    border: 2px solid rgba(239, 68, 68, 0.3);
}

h1 {
    color: white !important;
    text-align: center;
    font-size: 3.5em !important;
    font-weight: 800 !important;
    text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    margin-bottom: 10px !important;
    letter-spacing: -1px;
}

.subtitle {
    color: rgba(255, 255, 255, 0.95);
    text-align: center;
    font-size: 1.3em;
    margin-bottom: 35px;
    font-weight: 500;
}

button.primary {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    padding: 18px 40px !important;
    border-radius: 14px !important;
    font-size: 17px !important;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    transition: all 0.3s !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

button.primary:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.7) !important;
}

@media (max-width: 768px) {
    .proxy-list-header,
    .proxy-list-row {
        grid-template-columns: 1fr;
        gap: 8px;
    }
    
    .header-item {
        display: none;
    }
    
    .list-cell {
        padding: 5px 0;
    }
}
"""


with gr.Blocks(css=custom_css, title="TeleProxyHub - SOCKS5 Proxy Manager") as demo:
    gr.Markdown("# 🚀 TeleProxyHub")
    gr.Markdown("<p class='subtitle'>🔒 Free SOCKS5 Proxies for Telegram | Auto-tested & Sorted by Speed</p>")
    
    status_text = gr.Textbox(label="📊 Status", interactive=False, value="Loading proxies...", show_label=True)
    
    test_btn = gr.Button("⚡ TEST ALL PROXIES & SHOW WORKING LIST", elem_classes="primary", size="lg")
    
    proxy_list = gr.HTML()
    
    gr.Markdown("""<div style='text-align: center; color: rgba(255,255,255,0.8); margin-top: 20px; font-size: 14px;'>
    💡 <b>How it works:</b> We test each proxy using SOCKS5 handshake protocol<br>
    ⚡ <b>Speed:</b> Testing ~20 proxies simultaneously | 🌍 <b>Location:</b> Country detected via IP lookup<br>
    🔄 <b>Refresh:</b> Click test button anytime to get fresh results
    </div>""")
    
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
