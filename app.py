"""
PC Performance Taskbar-like Widget
File: pc_taskbar.py
Requirements:
  - Python 3.8+
  - pip install psutil PyQt5

What it does:
  - Creates a slim, always-on-top taskbar-style window docked to the bottom of the primary screen.
  - Shows realtime CPU, Memory, Disk, and Network usage (download/upload speeds).
  - Click-and-drag to move; double-click to toggle "pinned" state (stay on top).
  - Right-click to exit.

Usage:
  python pc_taskbar.py

Note: On Linux/Wayland, window docking/moving behavior may vary. Tested on Windows 10/11 and many Linux X11 setups.
"""

import sys
import psutil
import time
from collections import deque
from PyQt5 import QtCore, QtGui, QtWidgets

REFRESH_MS = 800
NET_HISTORY = 8

class TaskbarWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self.pinned = True
        self.drag_pos = None

        self.net_prev = psutil.net_io_counters()
        self.net_deque_down = deque([0]*NET_HISTORY, maxlen=NET_HISTORY)
        self.net_deque_up = deque([0]*NET_HISTORY, maxlen=NET_HISTORY)

        self.init_ui()
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(REFRESH_MS)

        self.position_bottom()

    def init_ui(self):
        self.setFixedHeight(56)
        self.setMinimumWidth(420)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(12)

        # Create four metric widgets
        self.cpu_widget = self.build_metric_block('CPU')
        self.mem_widget = self.build_metric_block('Memory')
        self.disk_widget = self.build_metric_block('Disk')
        self.net_widget = self.build_metric_block('Network')

        main_layout.addWidget(self.cpu_widget)
        main_layout.addWidget(self.mem_widget)
        main_layout.addWidget(self.disk_widget)
        main_layout.addWidget(self.net_widget)

        # Add spacer and mini-controls
        spacer = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        main_layout.addItem(spacer)

        self.pin_btn = QtWidgets.QPushButton('📌')
        self.pin_btn.setToolTip('Double-click the bar or use this to toggle pinned')
        self.pin_btn.setFixedSize(36,36)
        self.pin_btn.clicked.connect(self.toggle_pinned)
        self.pin_btn.setFlat(True)

        main_layout.addWidget(self.pin_btn)

        container = QtWidgets.QFrame()
        container.setLayout(main_layout)
        container.setStyleSheet(self.frame_style())

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(6,6,6,6)
        outer_layout.addWidget(container)

        # Context menu for right click
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def frame_style(self):
        return (
            """QFrame{background: rgba(30,30,30,230); border-radius:10px;}
            QLabel{color: #e6e6e6;}
            QProgressBar{background: rgba(255,255,255,20); border: 0px; height:8px; border-radius:4px;}
            QProgressBar::chunk{background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66ccff, stop:1 #3399ff); border-radius:4px;}
            QPushButton{color:#e6e6e6; background:transparent; border:none; font-size:18px;}
            QPushButton:hover{color:#ffffff;}"""
        )

    def build_metric_block(self, title):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(4,0,4,0)

        title_label = QtWidgets.QLabel(title)
        title_label.setFont(QtGui.QFont('Segoe UI', 8, QtGui.QFont.Bold))

        val_label = QtWidgets.QLabel('0%')
        val_label.setFont(QtGui.QFont('Segoe UI', 10))

        prog = QtWidgets.QProgressBar()
        prog.setRange(0, 100)
        prog.setValue(0)
        prog.setTextVisible(False)
        prog.setFixedWidth(160)

        layout.addWidget(title_label)
        layout.addWidget(val_label)
        layout.addWidget(prog)
        w.setLayout(layout)

        # attach for updates
        w.val_label = val_label
        w.prog = prog
        return w

    def position_bottom(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        width = min(screen.width() - 40, 900)
        self.setFixedWidth(width)
        x = (screen.width() - width)//2
        y = screen.height() - self.height() - 12
        self.setGeometry(x, y, width, self.height())

    def update_stats(self):
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        self.cpu_widget.val_label.setText(f'{cpu:.0f}%')
        self.cpu_widget.prog.setValue(int(cpu))

        # Memory
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        self.mem_widget.val_label.setText(f'{mem_percent:.0f}% ({self.format_bytes(mem.used)} used)')
        self.mem_widget.prog.setValue(int(mem_percent))

        # Disk
        disk = psutil.disk_usage('/')
        self.disk_widget.val_label.setText(f'{disk.percent:.0f}%')
        self.disk_widget.prog.setValue(int(disk.percent))

        # Network speed (bytes/sec)
        net_now = psutil.net_io_counters()
        down_speed = (net_now.bytes_recv - self.net_prev.bytes_recv) / (REFRESH_MS/1000.0)
        up_speed = (net_now.bytes_sent - self.net_prev.bytes_sent) / (REFRESH_MS/1000.0)
        self.net_prev = net_now
        self.net_deque_down.append(down_speed)
        self.net_deque_up.append(up_speed)
        avg_down = sum(self.net_deque_down)/len(self.net_deque_down)
        avg_up = sum(self.net_deque_up)/len(self.net_deque_up)

        self.net_widget.val_label.setText(f'Down {self.format_bytes(avg_down)}/s • Up {self.format_bytes(avg_up)}/s')
        # map combined speed to 0-100 for progress bar (arbitrary scaling)
        combined = min(100, (avg_down + avg_up) / 1024.0)  # KB/s mapping
        self.net_widget.prog.setValue(int(combined))

    def format_bytes(self, n):
        # human readable
        n = float(n)
        units = ['B','KB','MB','GB','TB']
        i = 0
        while n >= 1024 and i < len(units)-1:
            n /= 1024.0
            i += 1
        return f'{n:.1f}{units[i]}'

    # mouse events for moving the bar
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        # toggle pinned (stay on top)
        self.toggle_pinned()
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        super().mouseReleaseEvent(event)

    def toggle_pinned(self):
        self.pinned = not self.pinned
        flags = self.windowFlags()
        if self.pinned:
            flags |= QtCore.Qt.WindowStaysOnTopHint
            self.pin_btn.setText('📌')
        else:
            flags &= ~QtCore.Qt.WindowStaysOnTopHint
            self.pin_btn.setText('📍')
        self.setWindowFlags(flags)
        self.show()

    def show_context_menu(self, pos):
        menu = QtWidgets.QMenu()
        quit_action = menu.addAction('Exit')
        action = menu.exec_(self.mapToGlobal(pos))
        if action == quit_action:
            QtWidgets.QApplication.quit()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    w = TaskbarWindow()
    w.show()
    sys.exit(app.exec_())
