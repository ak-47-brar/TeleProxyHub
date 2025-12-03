import gradio as gr
import requests
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_proxies():
    """Fetch proxies from the CDN source"""
    try:
        url = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        proxies = [line.strip() for line in response.text.split('\n') if line.strip()]
        return proxies
    except Exception as e:
        return [f"Error fetching proxies: {str(e)}"]


def create_telegram_link(proxy):
    """Convert proxy to Telegram proxy link"""
    try:
        if ':' in proxy:
            server, port = proxy.split(':')
            return f"https://t.me/proxy?server={server}&port={port}"
        return None
    except:
        return None


def test_proxy_ping(proxy, timeout=3):
    """Test if proxy is responding"""
    try:
        if ':' not in proxy:
            return False, "Invalid format", 99999

        server, port = proxy.split(':')
        start_time = time.time()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server, int(port)))
        sock.close()

        ping_time = (time.time() - start_time) * 1000

        if result == 0:
            return True, f"{ping_time:.0f}ms", ping_time
        else:
            return False, "Unreachable", 99999
    except Exception as e:
        return False, str(e)[:20], 99999


def test_proxy_for_sorting(proxy):
    """Test a single proxy and return results for sorting"""
    is_working, result_text, ping_ms = test_proxy_ping(proxy, timeout=5)
    return {
        'proxy': proxy,
        'is_working': is_working,
        'ping_ms': ping_ms,
        'ping_text': result_text
    }


def format_proxy_html(proxies, show_ping=False, proxy_results=None):
    """Format proxies as beautiful HTML cards"""
    html = """
    <div class="proxy-container">
    """

    for idx, proxy in enumerate(proxies[:50], 1):
        tg_link = create_telegram_link(proxy)
        if tg_link:
            ping_display = ""
            if show_ping and proxy_results:
                result = next((r for r in proxy_results if r['proxy'] == proxy), None)
                if result:
                    status_class = "working" if result['is_working'] else "failed"
                    ping_display = f'<div class="ping-status {status_class}">{result["ping_text"]}</div>'
            
            html += f"""
            <div class="proxy-card" data-proxy="{proxy}">
                <div class="proxy-header">
                    <span class="proxy-number">#{idx}</span>
                    <span class="proxy-address">{proxy}</span>
                </div>
                {ping_display}
                <div class="proxy-actions">
                    <a href="{tg_link}" target="_blank" class="tg-link">
                        <span class="tg-icon">✈️</span> Add to Telegram
                    </a>
                    <button class="test-btn" onclick="testProxy('{proxy}', {idx})">
                        <span id="status-{idx}">🔍 Test</span>
                    </button>
                </div>
            </div>
            """

    html += """
    </div>
    """
    return html


def refresh_proxies():
    """Refresh and display proxies"""
    proxies = fetch_proxies()
    if proxies and not proxies[0].startswith("Error"):
        count = len(proxies)
        html = format_proxy_html(proxies)
        return html, f"✅ Loaded {count} proxies"
    else:
        return "<div class='error'>Failed to load proxies</div>", "❌ Error loading proxies"


def sort_proxies_by_ping(progress=gr.Progress()):
    """Sort proxies by ping speed"""
    progress(0, desc="Fetching proxies...")
    proxies = fetch_proxies()
    
    if not proxies or proxies[0].startswith("Error"):
        return "<div class='error'>Failed to load proxies</div>", "❌ Error loading proxies"
    
    # Limit to 30 proxies for faster testing
    test_proxies = proxies[:30]
    progress(0.2, desc=f"Testing {len(test_proxies)} proxies...")
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_proxy_for_sorting, proxy): proxy for proxy in test_proxies}
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            progress(0.2 + (0.7 * completed / len(test_proxies)), 
                    desc=f"Tested {completed}/{len(test_proxies)} proxies")
    
    # Sort by ping (working proxies first, then by ping time)
    results.sort(key=lambda x: (not x['is_working'], x['ping_ms']))
    
    progress(0.95, desc="Generating display...")
    sorted_proxies = [r['proxy'] for r in results]
    html = format_proxy_html(sorted_proxies, show_ping=True, proxy_results=results)
    
    working_count = sum(1 for r in results if r['is_working'])
    status_msg = f"✅ Sorted {len(results)} proxies | {working_count} working | {len(results) - working_count} failed"
    
    progress(1.0, desc="Done!")
    return html, status_msg


def test_single_proxy(proxy_address):
    """Test a single proxy and return result"""
    is_working, result, _ = test_proxy_ping(proxy_address)
    if is_working:
        return f"✅ {result}"
    else:
        return f"❌ {result}"


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

.gradio-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.proxy-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
}

.proxy-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.proxy-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
    background: rgba(255, 255, 255, 0.15);
}

.proxy-header {
    display: flex;
    align-items: center;
    margin-bottom: 15px;
    gap: 10px;
}

.proxy-number {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 5px 12px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
}

.proxy-address {
    color: white;
    font-weight: 600;
    font-size: 16px;
    word-break: break-all;
}

.ping-status {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 10px;
    text-align: center;
}

.ping-status.working {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.4);
}

.ping-status.failed {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

.proxy-actions {
    display: flex;
    gap: 10px;
    flex-direction: column;
}

.tg-link {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: linear-gradient(135deg, #0088cc, #0066aa);
    color: white;
    padding: 12px 20px;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 600;
    transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(0, 136, 204, 0.3);
}

.tg-link:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 20px rgba(0, 136, 204, 0.5);
}

.tg-icon {
    font-size: 18px;
}

.test-btn {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
    padding: 12px 20px;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.test-btn:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: scale(1.02);
}

.error {
    color: #ff6b6b;
    background: rgba(255, 107, 107, 0.1);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    font-weight: 600;
}

h1 {
    color: white !important;
    text-align: center;
    font-size: 3em !important;
    font-weight: 700 !important;
    text-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    margin-bottom: 10px !important;
}

.subtitle {
    color: rgba(255, 255, 255, 0.9);
    text-align: center;
    font-size: 1.2em;
    margin-bottom: 30px;
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
"""


with gr.Blocks(css=custom_css, title="TeleProxyHub - SOCKS5 Proxy Manager") as demo:
    gr.Markdown("# 🚀 TeleProxyHub")
    gr.Markdown("<p class='subtitle'>Free SOCKS5 Proxies for Telegram - Updated in Real-time</p>")

    with gr.Tabs():
        with gr.Tab("📝 All Proxies"):
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Proxies", elem_classes="primary")
                status_text = gr.Textbox(label="Status", interactive=False, value="Click refresh to load proxies")
            
            proxy_display = gr.HTML()
            
            refresh_btn.click(
                fn=refresh_proxies,
                outputs=[proxy_display, status_text]
            )
            
            demo.load(
                fn=refresh_proxies,
                outputs=[proxy_display, status_text]
            )
        
        with gr.Tab("⚡ Sorted by Ping"):
            gr.Markdown("### 🎯 Proxies sorted from lowest to highest ping (Top 30)")
            gr.Markdown("_This will test each proxy and sort them by response time. Working proxies appear first._")
            
            with gr.Row():
                sort_btn = gr.Button("⚡ Test & Sort Proxies", elem_classes="primary")
                sorted_status = gr.Textbox(label="Status", interactive=False, value="Click to start testing")
            
            sorted_display = gr.HTML()
            
            sort_btn.click(
                fn=sort_proxies_by_ping,
                outputs=[sorted_display, sorted_status]
            )
        
        with gr.Tab("🔍 Test Proxy"):
            gr.Markdown("## 🔍 Test Individual Proxy")
            with gr.Row():
                test_input = gr.Textbox(
                    label="Enter proxy (format: IP:PORT)",
                    placeholder="Example: 14.102.10.152:8443"
                )
                test_btn = gr.Button("Test Proxy", elem_classes="primary")
            test_result = gr.Textbox(label="Test Result", interactive=False)
            
            test_btn.click(
                fn=test_single_proxy,
                inputs=[test_input],
                outputs=[test_result]
            )


if __name__ == "__main__":
    demo.launch()
