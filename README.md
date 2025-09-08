# LAN-Share

⚡ Lightning-Fast Cable-Free File Transfer

A simple LAN-based file sharing system built with Python and Flask.
It lets you transfer files between your PC and any device on the same Wi-Fi network — no cables, no third-party apps, no size limits.

Just run the server on your PC, and open the provided link on your phone/tablet/laptop to upload, download, and share files instantly.
--------------------------------------------------------------------------------------------------------------------------------------------

✨ Features:

📂 Share any folder from your PC over LAN.
🌐 Access via browser — no app installation needed.
⬆️ Drag & drop uploads from phone or desktop.
⬇️ One-click downloads with support for large files.
🔐 Optional authentication with a secure token/password.
⚡ High transfer speeds (limited only by your Wi-Fi/router).
💻 Cross-platform — works on Android, iOS, Windows, Linux, macOS.
--------------------------------------------------------------------------------------------------------------------------------------------

🚀 How It Works

1. Run the server on your PC:
python server.py --folder "<Folder-location>" --port <port-number> --user <user-id> --password <user-password>

2. It will show your LAN address, e.g.:
 ---------------------------------------------------------LAN SHARE IS STARTING---------------------------------------------------------
---------------------------------------------------------A PROJECT BY RITIK-TRADEZ---------------------------------------------------------
=== LANShare ===
Shared folder: E:\FTProtocol\Shared
Access URL: http://192.168.1.14:2121/  (login required)

3. Open the link on any device connected to the same Wi-Fi.
4. Enter the token (if enabled).
5. Start uploading, downloading, or sharing files instantly.
--------------------------------------------------------------------------------------------------------------------------------------------

🔒 Security

1. Local network only by default (safe for home/office use).
2. Optional authentication token to restrict access.
3. For internet access, you can use port forwarding or tunneling (e.g., Ngrok, Cloudflare Tunnel), but HTTPS + strong token is strongly recommended.
--------------------------------------------------------------------------------------------------------------------------------------------

📦 Requirements:
Python 3.8+
Install dependencies:
pip install flask werkzeug
--------------------------------------------------------------------------------------------------------------------------------------------

⚠️ Disclaimer
This project is intended for personal use in trusted environments.
If exposing it to the internet, ensure proper authentication and encryption to protect your data.
