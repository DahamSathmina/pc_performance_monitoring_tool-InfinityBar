"""
Production-Grade PC Performance Monitor - System Tray Application
Version: 2.0.0
Author: Performance Monitoring Team
License: MIT

A professional system monitoring application that runs in the Windows system tray.
Monitors CPU, Memory, Disk, and Network metrics in real-time.

Requirements:
    - Python 3.8+
    - psutil>=5.9.0
    - PyQt5>=5.15.0

Usage:
    python pc_performance_monitor.py [--config config.json] [--debug]

Features:
    - System tray application with context menu
    - Real-time system metrics in tooltip
    - Optional floating widget display
    - Configurable refresh rates and thresholds
    - Comprehensive logging and error handling
    - Runs on startup (optional)
"""

import sys
import logging
import argparse
import json
import signal
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from collections import deque
from datetime import datetime

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets

# Try to import winreg (Windows only)
try:
    import winreg
    WINDOWS_PLATFORM = True
except ImportError:
    WINDOWS_PLATFORM = False


# ============================================================================
# Configuration & Constants
# ============================================================================

@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""
    refresh_ms: int = 1000
    net_history_size: int = 8
    window_height: int = 56
    window_min_width: int = 420
    window_max_width: int = 900
    opacity: float = 0.95
    log_level: str = "INFO"
    log_file: Optional[str] = "pc_monitor.log"
    enable_metrics_logging: bool = False
    show_widget_on_start: bool = False
    start_with_windows: bool = False
    show_startup_notification: bool = False
    show_threshold_notifications: bool = False
    notification_cooldown_minutes: int = 5
    
    # Alert thresholds (percentage)
    cpu_threshold: int = 90
    memory_threshold: int = 85
    disk_threshold: int = 90
    
    # UI Configuration
    background_color: str = "rgba(30,30,30,240)"
    text_color: str = "#e6e6e6"
    accent_color_start: str = "#66ccff"
    accent_color_end: str = "#3399ff"
    border_radius: int = 10
    
    @classmethod
    def from_file(cls, filepath: Path) -> 'AppConfig':
        """Load configuration from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except FileNotFoundError:
            logging.warning(f"Config file {filepath} not found, using defaults")
            return cls()
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in config file: {e}")
            return cls()
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return cls()
    
    def save(self, filepath: Path) -> None:
        """Save configuration to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(asdict(self), f, indent=2)
            logging.info(f"Configuration saved to {filepath}")
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")


# ============================================================================
# System Metrics Collector
# ============================================================================

class MetricsCollector:
    """Handles system metrics collection with error handling."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.net_prev = None
        self.net_deque_down = deque([0] * config.net_history_size, 
                                     maxlen=config.net_history_size)
        self.net_deque_up = deque([0] * config.net_history_size, 
                                   maxlen=config.net_history_size)
        self.last_notification_time = None
        self._initialize_network()
    
    def _initialize_network(self) -> None:
        """Initialize network counters."""
        try:
            self.net_prev = psutil.net_io_counters()
        except Exception as e:
            logging.error(f"Failed to initialize network counters: {e}")
            self.net_prev = None
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=None)
        except Exception as e:
            logging.error(f"Failed to get CPU usage: {e}")
            return 0.0
    
    def get_memory_usage(self) -> Tuple[float, int, int]:
        """Get memory usage: (percentage, used_bytes, total_bytes)."""
        try:
            mem = psutil.virtual_memory()
            return mem.percent, mem.used, mem.total
        except Exception as e:
            logging.error(f"Failed to get memory usage: {e}")
            return 0.0, 0, 0
    
    def get_disk_usage(self, path: str = '/') -> Tuple[float, int, int]:
        """Get disk usage for specified path: (percentage, used_bytes, total_bytes)."""
        try:
            # On Windows, use C: drive
            if sys.platform == 'win32':
                path = 'C:\\'
            disk = psutil.disk_usage(path)
            return disk.percent, disk.used, disk.total
        except Exception as e:
            logging.error(f"Failed to get disk usage for {path}: {e}")
            return 0.0, 0, 0
    
    def get_network_speed(self, interval_sec: float) -> Tuple[float, float]:
        """
        Get network speed: (download_bytes_per_sec, upload_bytes_per_sec).
        Returns smoothed average over history.
        """
        try:
            if self.net_prev is None:
                self._initialize_network()
                return 0.0, 0.0
            
            net_now = psutil.net_io_counters()
            down_speed = (net_now.bytes_recv - self.net_prev.bytes_recv) / interval_sec
            up_speed = (net_now.bytes_sent - self.net_prev.bytes_sent) / interval_sec
            
            self.net_prev = net_now
            self.net_deque_down.append(max(0, down_speed))
            self.net_deque_up.append(max(0, up_speed))
            
            avg_down = sum(self.net_deque_down) / len(self.net_deque_down)
            avg_up = sum(self.net_deque_up) / len(self.net_deque_up)
            
            return avg_down, avg_up
        except Exception as e:
            logging.error(f"Failed to get network speed: {e}")
            return 0.0, 0.0
    
    def get_all_metrics(self, interval_sec: float) -> Dict[str, Any]:
        """Get all metrics at once."""
        cpu = self.get_cpu_usage()
        mem_percent, mem_used, mem_total = self.get_memory_usage()
        disk_percent, disk_used, disk_total = self.get_disk_usage()
        down_speed, up_speed = self.get_network_speed(interval_sec)
        
        return {
            'cpu': cpu,
            'memory': {'percent': mem_percent, 'used': mem_used, 'total': mem_total},
            'disk': {'percent': disk_percent, 'used': disk_used, 'total': disk_total},
            'network': {'download': down_speed, 'upload': up_speed}
        }
    
    def check_thresholds(self, cpu: float, mem: float, disk: float) -> Dict[str, bool]:
        """Check if metrics exceed configured thresholds."""
        return {
            'cpu': cpu >= self.config.cpu_threshold,
            'memory': mem >= self.config.memory_threshold,
            'disk': disk >= self.config.disk_threshold
        }
    
    def should_show_notification(self) -> bool:
        """Check if enough time has passed since last notification."""
        if not self.config.show_threshold_notifications:
            return False
        
        if self.last_notification_time is None:
            return True
        
        elapsed = datetime.now() - self.last_notification_time
        cooldown_seconds = self.config.notification_cooldown_minutes * 60
        return elapsed.total_seconds() >= cooldown_seconds
    
    def mark_notification_shown(self) -> None:
        """Mark that a notification was just shown."""
        self.last_notification_time = datetime.now()


# ============================================================================
# Utility Functions
# ============================================================================

def format_bytes(n: float) -> str:
    """Convert bytes to human-readable format."""
    n = abs(float(n))
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f'{n:.1f}{units[i]}'


def setup_logging(config: AppConfig) -> None:
    """Configure logging with file and console handlers."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = []
    
    # Console handler (only if not frozen as exe)
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)
    
    # File handler
    if config.log_file:
        try:
            file_handler = logging.FileHandler(config.log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")
    
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        handlers=handlers,
        format=log_format
    )


def set_autostart(enable: bool, app_name: str = "PCPerformanceMonitor") -> bool:
    """Set or remove application from Windows startup."""
    if not WINDOWS_PLATFORM:
        logging.warning("Autostart is only supported on Windows")
        return False
    
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        
        if enable:
            app_path = f'"{sys.executable}" "{Path(__file__).absolute()}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            logging.info(f"Added to startup: {app_path}")
        else:
            try:
                winreg.DeleteValue(key, app_name)
                logging.info("Removed from startup")
            except FileNotFoundError:
                pass
        
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logging.error(f"Failed to modify startup: {e}")
        return False


# ============================================================================
# System Tray Icon
# ============================================================================

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """System tray icon with metrics display."""
    
    def __init__(self, config: AppConfig, parent=None):
        # Create icon
        icon = self._create_icon()
        super().__init__(icon, parent)
        
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = MetricsCollector(config)
        self.widget = None
        
        # Setup
        self._create_menu()
        self._start_update_timer()
        
        # Signals
        self.activated.connect(self._on_tray_activated)
        
        self.logger.info("System tray icon initialized")
    
    def _create_icon(self) -> QtGui.QIcon:
        """Create system tray icon."""
        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(QtCore.Qt.transparent)
        
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Draw background circle
        painter.setBrush(QtGui.QColor(30, 30, 30))
        painter.setPen(QtGui.QPen(QtGui.QColor(102, 204, 255), 3))
        painter.drawEllipse(4, 4, 56, 56)
        
        # Draw text
        painter.setPen(QtGui.QColor(102, 204, 255))
        font = QtGui.QFont('Arial', 18, QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, 'PC')
        
        painter.end()
        
        return QtGui.QIcon(pixmap)
    
    def _create_menu(self) -> None:
        """Create context menu."""
        menu = QtWidgets.QMenu()
        
        # Widget toggle
        self.show_widget_action = menu.addAction('Show Widget')
        self.show_widget_action.triggered.connect(self._toggle_widget)
        
        menu.addSeparator()
        
        # Refresh action
        refresh_action = menu.addAction('Refresh Now')
        refresh_action.triggered.connect(self._update_metrics)
        
        menu.addSeparator()
        
        # Settings submenu
        settings_menu = menu.addMenu('Settings')
        
        # Autostart toggle
        if WINDOWS_PLATFORM:
            self.autostart_action = settings_menu.addAction('Run on Startup')
            self.autostart_action.setCheckable(True)
            self.autostart_action.setChecked(self.config.start_with_windows)
            self.autostart_action.triggered.connect(self._toggle_autostart)
        
        # Notifications toggle
        self.notifications_action = settings_menu.addAction('Show Alerts')
        self.notifications_action.setCheckable(True)
        self.notifications_action.setChecked(self.config.show_threshold_notifications)
        self.notifications_action.triggered.connect(self._toggle_notifications)
        
        menu.addSeparator()
        
        # About
        about_action = menu.addAction('About')
        about_action.triggered.connect(self._show_about)
        
        # Exit
        exit_action = menu.addAction('Exit')
        exit_action.triggered.connect(self._exit_application)
        
        self.setContextMenu(menu)
    
    def _start_update_timer(self) -> None:
        """Start metrics update timer."""
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._update_metrics)
        self.update_timer.start(self.config.refresh_ms)
    
    def _update_metrics(self) -> None:
        """Update metrics and tooltip."""
        try:
            interval_sec = self.config.refresh_ms / 1000.0
            metrics = self.metrics.get_all_metrics(interval_sec)
            
            # Update tooltip
            tooltip = (
                f"PC Performance Monitor\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"CPU: {metrics['cpu']:.0f}%\n"
                f"Memory: {metrics['memory']['percent']:.0f}% "
                f"({format_bytes(metrics['memory']['used'])})\n"
                f"Disk: {metrics['disk']['percent']:.0f}%\n"
                f"Network: ↓{format_bytes(metrics['network']['download'])}/s "
                f"↑{format_bytes(metrics['network']['upload'])}/s"
            )
            self.setToolTip(tooltip)
            
            # Update widget if visible
            if self.widget and self.widget.isVisible():
                self.widget._update_with_metrics(metrics)
            
            # Check thresholds (with cooldown)
            if self.config.show_threshold_notifications:
                alerts = self.metrics.check_thresholds(
                    metrics['cpu'],
                    metrics['memory']['percent'],
                    metrics['disk']['percent']
                )
                
                if any(alerts.values()) and self.metrics.should_show_notification():
                    self._show_threshold_notification(alerts, metrics)
                    self.metrics.mark_notification_shown()
        
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}", exc_info=True)
    
    def _show_threshold_notification(self, alerts: Dict[str, bool], 
                                     metrics: Dict[str, Any]) -> None:
        """Show system notification for threshold violations."""
        try:
            messages = []
            if alerts['cpu']:
                messages.append(f"CPU: {metrics['cpu']:.0f}%")
            if alerts['memory']:
                messages.append(f"Memory: {metrics['memory']['percent']:.0f}%")
            if alerts['disk']:
                messages.append(f"Disk: {metrics['disk']['percent']:.0f}%")
            
            if messages:
                self.showMessage(
                    "Performance Alert",
                    "High usage detected:\n" + "\n".join(messages),
                    QtWidgets.QSystemTrayIcon.Warning,
                    3000
                )
                self.logger.warning(f"Threshold alert: {', '.join(messages)}")
        except Exception as e:
            self.logger.error(f"Error showing notification: {e}")
    
    def _toggle_widget(self) -> None:
        """Toggle widget visibility."""
        try:
            if self.widget is None:
                self.widget = FloatingWidget(self.config, self.metrics)
            
            if self.widget.isVisible():
                self.widget.hide()
                self.show_widget_action.setText('Show Widget')
            else:
                self.widget.show()
                self.widget.raise_()
                self.widget.activateWindow()
                self.show_widget_action.setText('Hide Widget')
        
        except Exception as e:
            self.logger.error(f"Error toggling widget: {e}", exc_info=True)
    
    def _toggle_autostart(self) -> None:
        """Toggle autostart setting."""
        try:
            enabled = self.autostart_action.isChecked()
            if set_autostart(enabled):
                self.config.start_with_windows = enabled
                self.logger.info(f"Autostart {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            self.logger.error(f"Error toggling autostart: {e}")
    
    def _toggle_notifications(self) -> None:
        """Toggle notifications setting."""
        try:
            enabled = self.notifications_action.isChecked()
            self.config.show_threshold_notifications = enabled
            self.logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            self.logger.error(f"Error toggling notifications: {e}")
    
    def _on_tray_activated(self, reason) -> None:
        """Handle tray icon activation."""
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self._toggle_widget()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        try:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle("About PC Performance Monitor")
            msg.setText(
                "<h3>PC Performance Monitor v2.0.0</h3>"
                "<p>A production-grade system monitoring tool.</p>"
                "<p><b>Features:</b></p>"
                "<ul>"
                "<li>System tray monitoring</li>"
                "<li>Real-time metrics display</li>"
                "<li>Configurable alerts</li>"
                "<li>Optional floating widget</li>"
                "</ul>"
                "<p><b>Usage:</b></p>"
                "<ul>"
                "<li>Double-click tray icon to show/hide widget</li>"
                "<li>Right-click for options</li>"
                "<li>Hover for current metrics</li>"
                "</ul>"
                "<p>© 2024 Performance Monitoring Team</p>"
            )
            msg.exec_()
        except Exception as e:
            self.logger.error(f"Error showing about dialog: {e}")
    
    def _exit_application(self) -> None:
        """Exit application."""
        self.logger.info("Exiting application...")
        try:
            if self.widget:
                self.widget.close()
            QtWidgets.QApplication.quit()
        except Exception as e:
            self.logger.error(f"Error during exit: {e}")


# ============================================================================
# Floating Widget (Optional Display)
# ============================================================================

class FloatingWidget(QtWidgets.QWidget):
    """Optional floating widget for detailed metrics display."""
    
    def __init__(self, config: AppConfig, metrics: MetricsCollector):
        super().__init__()
        self.config = config
        self.metrics = metrics
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.pinned = True
        self.drag_pos = None
        
        self._setup_window()
        self._init_ui()
        self._position_bottom()
    
    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | 
            QtCore.Qt.WindowStaysOnTopHint | 
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setWindowOpacity(self.config.opacity)
        self.setWindowTitle("PC Performance Widget")
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        self.setFixedHeight(self.config.window_height)
        self.setMinimumWidth(self.config.window_min_width)
        
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(12)
        
        # Create metric widgets
        self.cpu_widget = self._build_metric_block('CPU')
        self.mem_widget = self._build_metric_block('Memory')
        self.disk_widget = self._build_metric_block('Disk')
        self.net_widget = self._build_metric_block('Network')
        
        main_layout.addWidget(self.cpu_widget)
        main_layout.addWidget(self.mem_widget)
        main_layout.addWidget(self.disk_widget)
        main_layout.addWidget(self.net_widget)
        
        # Spacer
        spacer = QtWidgets.QSpacerItem(
            10, 10, 
            QtWidgets.QSizePolicy.Expanding, 
            QtWidgets.QSizePolicy.Minimum
        )
        main_layout.addItem(spacer)
        
        # Pin button
        self.pin_btn = QtWidgets.QPushButton('📌')
        self.pin_btn.setToolTip('Toggle always on top')
        self.pin_btn.setFixedSize(36, 36)
        self.pin_btn.clicked.connect(self._toggle_pinned)
        self.pin_btn.setFlat(True)
        main_layout.addWidget(self.pin_btn)
        
        # Close button
        close_btn = QtWidgets.QPushButton('✕')
        close_btn.setToolTip('Hide widget')
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(self.hide)
        close_btn.setFlat(True)
        main_layout.addWidget(close_btn)
        
        # Container
        container = QtWidgets.QFrame()
        container.setLayout(main_layout)
        container.setStyleSheet(self._get_stylesheet())
        
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.addWidget(container)
    
    def _get_stylesheet(self) -> str:
        """Generate Qt stylesheet."""
        return f"""
            QFrame {{
                background: {self.config.background_color};
                border-radius: {self.config.border_radius}px;
            }}
            QLabel {{
                color: {self.config.text_color};
            }}
            QProgressBar {{
                background: rgba(255,255,255,20);
                border: 0px;
                height: 8px;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.config.accent_color_start},
                    stop:1 {self.config.accent_color_end}
                );
                border-radius: 4px;
            }}
            QPushButton {{
                color: {self.config.text_color};
                background: transparent;
                border: none;
                font-size: 18px;
            }}
            QPushButton:hover {{
                color: #ffffff;
                background: rgba(255,255,255,30);
                border-radius: 4px;
            }}
        """
    
    def _build_metric_block(self, title: str) -> QtWidgets.QWidget:
        """Build a metric display widget."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(4, 0, 4, 0)
        
        title_label = QtWidgets.QLabel(title)
        title_label.setFont(QtGui.QFont('Segoe UI', 8, QtGui.QFont.Bold))
        
        val_label = QtWidgets.QLabel('--')
        val_label.setFont(QtGui.QFont('Segoe UI', 10))
        
        progress = QtWidgets.QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedWidth(160)
        
        layout.addWidget(title_label)
        layout.addWidget(val_label)
        layout.addWidget(progress)
        widget.setLayout(layout)
        
        widget.val_label = val_label
        widget.prog = progress
        
        return widget
    
    def _position_bottom(self) -> None:
        """Position widget at bottom center."""
        try:
            screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
            width = min(screen.width() - 40, self.config.window_max_width)
            self.setFixedWidth(width)
            
            x = (screen.width() - width) // 2
            y = screen.height() - self.height() - 12
            
            self.setGeometry(x, y, width, self.height())
        except Exception as e:
            self.logger.error(f"Failed to position window: {e}")
    
    def _update_with_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update display with metrics data."""
        try:
            # CPU
            cpu = metrics['cpu']
            self.cpu_widget.val_label.setText(f'{cpu:.0f}%')
            self.cpu_widget.prog.setValue(int(cpu))
            
            # Memory
            mem = metrics['memory']
            self.mem_widget.val_label.setText(
                f'{mem["percent"]:.0f}% ({format_bytes(mem["used"])})'
            )
            self.mem_widget.prog.setValue(int(mem['percent']))
            
            # Disk
            disk = metrics['disk']
            self.disk_widget.val_label.setText(f'{disk["percent"]:.0f}%')
            self.disk_widget.prog.setValue(int(disk['percent']))
            
            # Network
            net = metrics['network']
            self.net_widget.val_label.setText(
                f'↓ {format_bytes(net["download"])}/s • ↑ {format_bytes(net["upload"])}/s'
            )
            combined_kb = (net['download'] + net['upload']) / 1024.0
            net_progress = min(100, int(combined_kb / 10))
            self.net_widget.prog.setValue(net_progress)
        
        except Exception as e:
            self.logger.error(f"Error updating widget: {e}")
    
    def _toggle_pinned(self) -> None:
        """Toggle always-on-top state."""
        try:
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
        except Exception as e:
            self.logger.error(f"Error toggling pin: {e}")
    
    # Mouse events for dragging
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.drag_pos and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self._toggle_pinned()
    
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self.drag_pos = None


# ============================================================================
# Application Entry Point
# ============================================================================

class PerformanceMonitorApp:
    """Main application coordinator."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None
        self.tray_icon = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        if self.app:
            self.app.quit()
    
    def run(self) -> int:
        """Run the application."""
        try:
            self.logger.info("Starting PC Performance Monitor (System Tray)...")
            
            # Create Qt application
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setApplicationName("PC Performance Monitor")
            self.app.setApplicationVersion("2.0.0")
            self.app.setQuitOnLastWindowClosed(False)  # Keep running in tray
            
            # Check system tray availability
            if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
                self.logger.error("System tray not available!")
                QtWidgets.QMessageBox.critical(
                    None,
                    "System Tray Error",
                    "System tray is not available on this system.\n"
                    "The application requires system tray support to run."
                )
                return 1
            
            # Create tray icon
            self.tray_icon = SystemTrayIcon(self.config)
            self.tray_icon.show()
            
            # Show welcome message only if configured
            if self.config.show_startup_notification:
                self.tray_icon.showMessage(
                    "PC Performance Monitor",
                    "Running in system tray. Double-click icon to show widget.",
                    QtWidgets.QSystemTrayIcon.Information,
                    2000
                )
            
            # Show widget if configured
            if self.config.show_widget_on_start:
                QtCore.QTimer.singleShot(500, self.tray_icon._toggle_widget)
            
            # Enable Ctrl+C handling
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: None)
            timer.start(100)
            
            self.logger.info("Application started successfully")
            
            # Run event loop
            return self.app.exec_()
        
        except Exception as e:
            self.logger.critical(f"Fatal error: {e}", exc_info=True)
            return 1
        
        finally:
            self.logger.info("Application terminated")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="PC Performance Monitor - System tray monitoring application"
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config.json'),
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='Generate default configuration file and exit'
    )
    parser.add_argument(
        '--show-widget',
        action='store_true',
        help='Show widget on startup'
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()
    
    # Generate config if requested
    if args.generate_config:
        config = AppConfig()
        config.save(args.config)
        print(f"Configuration file generated: {args.config}")
        print(f"\nEdit {args.config} to customize settings:")
        print("  - show_widget_on_start: Show widget immediately")
        print("  - show_startup_notification: Show startup notification")
        print("  - show_threshold_notifications: Enable performance alerts")
        print("  - start_with_windows: Auto-start with Windows")
        print("  - cpu_threshold, memory_threshold, disk_threshold: Alert thresholds")
        return 0
    
    # Load configuration
    config = AppConfig.from_file(args.config)
    
    # Override settings from command line
    if args.debug:
        config.log_level = "DEBUG"
    
    if args.show_widget:
        config.show_widget_on_start = True
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("PC Performance Monitor v2.0.0 - System Tray Edition")
    logger.info("=" * 60)
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Config loaded from: {args.config}")
    
    # Run application
    app = PerformanceMonitorApp(config)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())