import os
import cv2
import time
import re
from threading import Thread
from flask import Flask, request, jsonify

app = Flask(__name__)

class TikTokBot:
    def __init__(self, video_url, device_serial, package_name):
        self.video_url = video_url
        self.device_serial = self.sanitize_serial(device_serial)
        self.package_name = package_name
        self.template_dir = 'templates'
        self.screenshot_count = 0
        
    def sanitize_serial(self, serial):
        """Loại bỏ ký tự đặc biệt khỏi serial device"""
        return re.sub(r'[^a-zA-Z0-9._-]', '_', serial)

    def adb_command(self, command):
        """Thực thi lệnh ADB với device serial cụ thể"""
        return os.system(f'adb -s {self.device_serial} {command}')

    def open_video(self):
        print(f"[{self.device_serial}] Mở video TikTok...")
        self.adb_command(f'shell am start -a android.intent.action.VIEW -d "{self.video_url}"')
        time.sleep(8)

    def take_screenshot(self):
        """Chụp màn hình với tên file duy nhất cho mỗi thiết bị"""
        self.screenshot_count += 1
        filename = f"screen_{self.device_serial}_{self.screenshot_count}.png"
        remote_path = f"/sdcard/{filename}"
        
        print(f"[{self.device_serial}] Chụp màn hình #{self.screenshot_count}")
        self.adb_command(f'shell screencap -p {remote_path}')
        self.adb_command(f'pull {remote_path} {filename}')
        return filename

    def detect_icon(self, screenshot_path, template_path):
        print(f"[{self.device_serial}] 🔍 Đang tìm icon: {os.path.basename(template_path)}")
        
        screenshot = cv2.imread(screenshot_path)
        template = cv2.imread(template_path)
        
        if screenshot is None or template is None:
            print(f"[{self.device_serial}] Lỗi đọc ảnh!")
            return None

        result = cv2.matchTemplate(
            cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY),
            cv2.TM_CCOEFF_NORMED
        )
        
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        print(f'[{self.device_serial}] Độ khớp: {max_val:.3f}')

        if max_val >= 0.8:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
            # Ghi file debug
            debug_file = f"debug_{self.device_serial}.png"
            cv2.rectangle(screenshot, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 255, 0), 2)
            cv2.imwrite(debug_file, screenshot)
            
            print(f"[{self.device_serial}] Tìm thấy icon tại ({center_x}, {center_y})")
            return center_x, center_y
        return None

    def tap(self, x, y):
        print(f"[{self.device_serial}] 👆 Nhấn tại ({x}, {y})")
        self.adb_command(f'shell input tap {x} {y}')
        time.sleep(2)

    def run(self):
        try:
            # Mở ứng dụng gốc (tuỳ chọn)
            if self.package_name:
                self.adb_command(f'shell monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1')
                time.sleep(3)
            
            self.open_video()
            screenshot = self.take_screenshot()

            icons = ["gioHang.png", "moRong.png", "them.png"]
            
            for icon in icons:
                template = os.path.join(self.template_dir, icon)
                if coords := self.detect_icon(screenshot, template):
                    self.tap(*coords)
                    screenshot = self.take_screenshot()
            
            print(f"[{self.device_serial}] Hoàn thành!")
            return True
        except Exception as e:
            print(f"[{self.device_serial}] Lỗi: {str(e)}")
            return False

def run_bot_async(device_serial, package_name, video_url):
    """Chạy bot trong luồng riêng"""
    bot = TikTokBot(video_url, device_serial, package_name)
    bot.run()

@app.route('/run_bot', methods=['POST'])
def api_run_bot():
    data = request.get_json()
    
    # Validate params
    required = ['device_name', 'package_name', 'video_url']
    if not all(key in data for key in required):
        return jsonify({"error": "Thiếu tham số bắt buộc"}), 400

    # Khởi chạy bot trong thread riêng
    Thread(
        target=run_bot_async,
        args=(data['device_name'], data['package_name'], data['video_url'])
    ).start()

    return jsonify({
        "status": "started",
        "device": data['device_name'],
        "package": data['package_name'],
        "video": data['video_url']
    })

if __name__ == '__main__':
    # Tạo thư mục templates nếu chưa có
    if not os.path.exists('templates'):
        os.makedirs('templates')
        
    app.run(host='0.0.0.0', port=5000, threaded=True)