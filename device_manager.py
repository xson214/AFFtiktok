import sys
import subprocess
from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QSizePolicy, QGroupBox,
)
from PyQt5.QtCore import Qt
from tinydb import TinyDB

DB_FILE = "device_data.json"

class DeviceManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Android Device Manager")
        self.resize(1100, 600)

        self.db = TinyDB(DB_FILE)
        self.packages = self.load_packages()
        self.devices = []
        self.data = defaultdict(dict)        # { device_id: {package_name: user_name} }
        self.device_names = {}               # { device_id: custom_name }

        self.init_ui()
        self.load_from_db()
        self.load_devices()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Android Device Manager")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Refresh button
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.setMinimumWidth(150)
        refresh_btn.clicked.connect(self.load_devices)
        top_layout.addWidget(refresh_btn)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Table
        table_group = QGroupBox()
        table_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; }")
        table_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["STT", "Device ID", "Device Name", "Package Name", "User Name", "Set User"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("QTableWidget { font-size: 13px; } QHeaderView::section { font-size: 13px; font-weight: bold; }")
        self.table.setMinimumHeight(400)

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

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

            for device_id in self.devices:
                if device_id not in self.data:
                    self.data[device_id] = {}
                if device_id not in self.device_names:
                    self.device_names[device_id] = device_id
                for pkg in self.packages:
                    if pkg not in self.data[device_id]:
                        self.data[device_id][pkg] = ""

            self.update_table()

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "ADB Error", str(e))

    def update_table(self):
        total_rows = len(self.devices) * len(self.packages)
        self.table.setRowCount(total_rows)

        row_index = 0
        for device_index, device_id in enumerate(self.devices, start=1):
            device_name = self.device_names.get(device_id, device_id)
            for pkg_index, pkg in enumerate(self.packages):
                user_name = self.data[device_id].get(pkg, "")

                # STT
                if pkg_index == 0:
                    stt_item = QTableWidgetItem(str(device_index))
                    stt_item.setFlags(Qt.ItemIsEnabled)
                    self.table.setItem(row_index, 0, stt_item)
                else:
                    self.table.setItem(row_index, 0, QTableWidgetItem(""))

                # Device ID and Name
                if pkg_index == 0:
                    id_item = QTableWidgetItem(device_id)
                    id_item.setFlags(Qt.ItemIsEnabled)

                    name_input = QLineEdit(device_name)
                    name_input.setPlaceholderText("Custom name...")
                    name_input.editingFinished.connect(
                        lambda dev=device_id, input_box=name_input: self.set_device_name(dev, input_box)
                    )

                    self.table.setItem(row_index, 1, id_item)
                    self.table.setCellWidget(row_index, 2, name_input)
                else:
                    self.table.setItem(row_index, 1, QTableWidgetItem(""))
                    self.table.setCellWidget(row_index, 2, QWidget())

                # Package
                pkg_item = QTableWidgetItem(pkg)
                pkg_item.setFlags(Qt.ItemIsEnabled)

                user_item = QTableWidgetItem(user_name)
                user_item.setFlags(Qt.ItemIsEnabled)

                user_input = QLineEdit(user_name)
                user_input.setPlaceholderText("Enter username...")
                user_input.editingFinished.connect(
                    lambda dev=device_id, p=pkg, input_box=user_input: self.set_user(dev, p, input_box)
                )

                self.table.setItem(row_index, 3, pkg_item)
                self.table.setItem(row_index, 4, user_item)
                self.table.setCellWidget(row_index, 5, user_input)

                row_index += 1

    def set_user(self, device_id, pkg, input_box):
        user = input_box.text().strip()
        self.data[device_id][pkg] = user
        self.save_to_db()
        self.update_table()

    def set_device_name(self, device_id, input_box):
        name = input_box.text().strip() or device_id
        self.device_names[device_id] = name
        self.save_to_db()
        self.update_table()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceManager()
    window.show()
    sys.exit(app.exec_())
