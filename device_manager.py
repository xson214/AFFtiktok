import sys
import subprocess
from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from tinydb import TinyDB, Query

DB_FILE = "device_data.json"


class DeviceManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Android Device Manager")
        self.resize(1000, 600)

        self.db = TinyDB(DB_FILE)
        self.packages = self.load_packages()
        self.devices = []
        self.data = defaultdict(dict)          # { device_id: {package_name: user_name} }
        self.device_names = {}  # { device_id: device_custom_name }

        self.init_ui()
        self.load_from_db()
        self.load_devices()

    def init_ui(self):
        layout = QVBoxLayout()

        # ==== Title ====
        title = QLabel("Android Device Manager")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # ==== Top bar ====
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        top_layout.setContentsMargins(10, 10, 10, 10)

        device_label = QLabel("Select Device:")
        device_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.device_combo.currentIndexChanged.connect(self.update_table)
        top_layout.addWidget(self.device_combo, 2)

        name_label = QLabel("Device Name:")
        name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(name_label)

        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("Nhập tên thiết bị tuỳ chỉnh...")
        self.device_name_input.setMinimumWidth(180)
        self.device_name_input.editingFinished.connect(self.set_device_name)
        top_layout.addWidget(self.device_name_input, 2)

        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.setMinimumWidth(120)
        refresh_btn.clicked.connect(self.load_devices)
        top_layout.addWidget(refresh_btn, 1)

        layout.addLayout(top_layout)

        # ==== Table in GroupBox ====
        from PyQt5.QtWidgets import QGroupBox
        table_group = QGroupBox()
        table_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; } ")
        table_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Device Name", "Package Name", "User Name", "Set User"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("QTableWidget { font-size: 13px; } QHeaderView::section { font-size: 13px; font-weight: bold; }")
        self.table.setMinimumHeight(350)

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        # Padding bottom
        layout.addSpacing(10)
        self.setLayout(layout)

    def load_packages(self):
        try:
            with open("packages.txt", "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "Không tìm thấy file packages.txt")
            sys.exit(1)

    def load_from_db(self):
        records = self.db.all()
        for entry in records:
            device_id = entry['device_id']
            self.device_names[device_id] = entry.get('device_name', device_id)
            self.data[device_id] = entry.get('packages', {})

    def save_to_db(self):
        self.db.truncate()
        for device_id in self.data:
            self.db.insert({
                "device_id": device_id,
                "device_name": self.device_names.get(device_id, device_id),
                "packages": self.data[device_id]
            })

    def load_devices(self):
        try:
            result = subprocess.check_output(["adb", "devices"], encoding="utf-8")
            lines = result.strip().splitlines()[1:]
            self.devices = [line.split()[0] for line in lines if "device" in line]

            self.device_combo.clear()
            for device_id in self.devices:
                if device_id not in self.data:
                    self.data[device_id] = {}
                if device_id not in self.device_names:
                    self.device_names[device_id] = device_id
                for pkg in self.packages:
                    if pkg not in self.data[device_id]:
                        self.data[device_id][pkg] = ""

                display = f"{self.device_names[device_id]} ({device_id})"
                self.device_combo.addItem(display, device_id)

            self.update_table()

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "ADB Error", str(e))

    def update_table(self):
        current_index = self.device_combo.currentIndex()
        if current_index == -1:
            return

        device_id = self.device_combo.currentData()
        device_name = self.device_names.get(device_id, device_id)
        self.device_name_input.setText(device_name)

        self.table.setRowCount(len(self.packages))

        for row, pkg in enumerate(self.packages):
            user_name = self.data[device_id].get(pkg, "")

            name_item = QTableWidgetItem(device_name if row == 0 else "")
            pkg_item = QTableWidgetItem(pkg)
            user_item = QTableWidgetItem(user_name)

            name_item.setFlags(Qt.ItemIsEnabled)
            pkg_item.setFlags(Qt.ItemIsEnabled)
            user_item.setFlags(Qt.ItemIsEnabled)

            user_input = QLineEdit(user_name)
            user_input.setPlaceholderText("Enter username...")
            user_input.editingFinished.connect(
                lambda row=row, input_box=user_input: self.set_user(row, input_box)
            )

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, pkg_item)
            self.table.setItem(row, 2, user_item)
            self.table.setCellWidget(row, 3, user_input)

    def set_user(self, row, input_box):
        device_id = self.device_combo.currentData()
        pkg = self.packages[row]
        user = input_box.text().strip()
        self.data[device_id][pkg] = user
        self.table.item(row, 2).setText(user)
        self.save_to_db()

    def set_device_name(self):
        current_index = self.device_combo.currentIndex()
        if current_index == -1:
            return

        device_id = self.device_combo.currentData()
        name = self.device_name_input.text().strip() or device_id
        self.device_names[device_id] = name

        self.device_combo.setItemText(current_index, f"{name} ({device_id})")
        self.update_table()
        self.save_to_db()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceManager()
    window.show()
    sys.exit(app.exec_())
