import requests
import json

url = "http://localhost:5000/run_bot"
headers = {"Content-Type": "application/json"}
data = {
    "device_name": "R58W30MXC7T",  # Thay bằng serial device thực tế
    "package_name": "com.ss.android.ugc.trill",
    "video_url": "https://vt.tiktok.com/ZSBHqRUCM/"
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.json())