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

A beautiful web application to fetch and manage free SOCKS5 proxies for Telegram with real-time testing capabilities.

## ✨ Features

- 🔄 Auto-fetch proxies from ProxiFly's free proxy list
- 🎨 Liquid glass morphism UI with smooth animations
- 📱 One-click Telegram integration with clickable proxy links
- 🔍 Proxy ping testing to verify connectivity
- 🌐 Responsive design that works on all devices
- 🔄 Auto-sync to Hugging Face via GitHub Actions

## 🚀 Live Demo

Visit the app on Hugging Face Spaces: https://huggingface.co/spaces/fgjfj/TeleProxyHub

## 🛠️ Tech Stack

- Gradio - Web interface framework
- Python - Backend logic
- GitHub Actions - Auto-sync to Hugging Face
- ProxiFly API - Proxy data source

## 📦 Installation

```bash
git clone https://github.com/ak-47-brar/TeleProxyHub.git
cd TeleProxyHub
pip install -r requirements.txt
python app.py
```

## 🔧 Usage

1. Click **Refresh Proxies** to load the latest proxy list
2. Click on **Add to Telegram** to add proxy directly to Telegram
3. Use **Test Proxy** button to check if a proxy is working
4. Enter custom proxy address in the test section to verify connectivity

## 🌟 Features Explained

### Telegram Proxy Links
Each proxy is converted to a Telegram-compatible link format:

https://t.me/proxy?server=IP&port=PORT

### Proxy Testing
Built-in ping test functionality that checks:
- Connection availability
- Response time in milliseconds
- Socket connectivity

### Auto-Sync
Automatically syncs to Hugging Face Spaces on every push to main branch.

## 📄 License

MIT License - Feel free to use and modify!

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

Made with ❤️ for the Telegram community
