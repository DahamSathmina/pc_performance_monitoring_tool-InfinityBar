"""
Production-Grade PC Performance Monitor
Version: 2.0.0
Author: Performance Monitoring Team
License: MIT

A professional system monitoring application with taskbar widget display.
Monitors CPU, Memory, Disk, and Network metrics in real-time.

Requirements:
    - Python 3.8+
    - psutil>=5.9.0
    - PyQt5>=5.15.0

Usage:
    python pc_performance_monitor.py [--config config.json] [--debug]

Features:
    - Real-time system metrics monitoring
    - Configurable refresh rates and thresholds
    - Comprehensive logging and error handling
    - Cross-platform support (Windows, Linux, macOS)
    - Graceful degradation and resource cleanup
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


# ============================================================================
# Configuration & Constants
# ============================================================================

@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""
    refresh_ms: int = 800
    net_history_size: int = 8
    window_height: int = 56
    window_min_width: int = 420
    window_max_width: int = 900
    opacity: float = 0.9
    log_level: str = "INFO"
    log_file: Optional[str] = "pc_monitor.log"
    enable_metrics_logging: bool = False
    
    # Alert thresholds (percentage)
    cpu_threshold: int = 90
    memory_threshold: int = 85
    disk_threshold: int = 90
    
    # UI Configuration
    background_color: str = "rgba(30,30,30,230)"
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
    
    def check_thresholds(self, cpu: float, mem: float, disk: float) -> Dict[str, bool]:
        """Check if metrics exceed configured thresholds."""
        return {
            'cpu': cpu >= self.config.cpu_threshold,
            'memory': mem >= self.config.memory_threshold,
            'disk': disk >= self.config.disk_threshold
        }


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
    
    # Console handler
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


# ============================================================================
# Main Application Window
# ============================================================================

class TaskbarWindow(QtWidgets.QWidget):
    """Main application window for system monitoring."""
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = MetricsCollector(config)
        
        # Window state
        self.pinned = True
        self.drag_pos = None
        self.is_closing = False
        
        # UI components (will be set in init_ui)
        self.cpu_widget = None
        self.mem_widget = None
        self.disk_widget = None
        self.net_widget = None
        self.pin_btn = None
        
        self._setup_window()
        self._init_ui()
        self._start_update_timer()
        self._position_bottom()
        
        self.logger.info("TaskbarWindow initialized successfully")
    
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
        self.setWindowTitle("PC Performance Monitor")
    
    def _init_ui(self) -> None:
        """Initialize user interface components."""
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
        
        # Container frame
        container = QtWidgets.QFrame()
        container.setLayout(main_layout)
        container.setStyleSheet(self._get_stylesheet())
        
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.addWidget(container)
        
        # Context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _get_stylesheet(self) -> str:
        """Generate Qt stylesheet from configuration."""
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
        
        # Attach labels for easy access
        widget.val_label = val_label
        widget.prog = progress
        
        return widget
    
    def _start_update_timer(self) -> None:
        """Start the metrics update timer."""
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._update_stats)
        self.update_timer.start(self.config.refresh_ms)
        self.logger.debug(f"Update timer started with interval {self.config.refresh_ms}ms")
    
    def _position_bottom(self) -> None:
        """Position window at bottom center of screen."""
        try:
            screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
            width = min(screen.width() - 40, self.config.window_max_width)
            self.setFixedWidth(width)
            
            x = (screen.width() - width) // 2
            y = screen.height() - self.height() - 12
            
            self.setGeometry(x, y, width, self.height())
            self.logger.debug(f"Window positioned at ({x}, {y})")
        except Exception as e:
            self.logger.error(f"Failed to position window: {e}")
    
    def _update_stats(self) -> None:
        """Update all system metrics displays."""
        try:
            # CPU
            cpu = self.metrics.get_cpu_usage()
            self.cpu_widget.val_label.setText(f'{cpu:.0f}%')
            self.cpu_widget.prog.setValue(int(cpu))
            
            # Memory
            mem_percent, mem_used, mem_total = self.metrics.get_memory_usage()
            self.mem_widget.val_label.setText(
                f'{mem_percent:.0f}% ({format_bytes(mem_used)})'
            )
            self.mem_widget.prog.setValue(int(mem_percent))
            
            # Disk
            disk_percent, disk_used, disk_total = self.metrics.get_disk_usage('/')
            self.disk_widget.val_label.setText(f'{disk_percent:.0f}%')
            self.disk_widget.prog.setValue(int(disk_percent))
            
            # Network
            interval_sec = self.config.refresh_ms / 1000.0
            down_speed, up_speed = self.metrics.get_network_speed(interval_sec)
            self.net_widget.val_label.setText(
                f'↓ {format_bytes(down_speed)}/s • ↑ {format_bytes(up_speed)}/s'
            )
            
            # Progress bar for network (scaled arbitrarily)
            combined_kb = (down_speed + up_speed) / 1024.0
            net_progress = min(100, int(combined_kb / 10))
            self.net_widget.prog.setValue(net_progress)
            
            # Check thresholds
            alerts = self.metrics.check_thresholds(cpu, mem_percent, disk_percent)
            if any(alerts.values()):
                self._handle_threshold_alerts(alerts, cpu, mem_percent, disk_percent)
            
            # Log metrics if enabled
            if self.config.enable_metrics_logging:
                self.logger.info(
                    f"Metrics - CPU: {cpu:.1f}%, "
                    f"Memory: {mem_percent:.1f}%, "
                    f"Disk: {disk_percent:.1f}%, "
                    f"Net: ↓{format_bytes(down_speed)}/s ↑{format_bytes(up_speed)}/s"
                )
        
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}", exc_info=True)
    
    def _handle_threshold_alerts(self, alerts: Dict[str, bool], 
                                 cpu: float, mem: float, disk: float) -> None:
        """Handle metric threshold violations."""
        messages = []
        if alerts['cpu']:
            messages.append(f"CPU usage high: {cpu:.0f}%")
        if alerts['memory']:
            messages.append(f"Memory usage high: {mem:.0f}%")
        if alerts['disk']:
            messages.append(f"Disk usage high: {disk:.0f}%")
        
        if messages:
            self.logger.warning("Threshold alerts: " + ", ".join(messages))
    
    def _toggle_pinned(self) -> None:
        """Toggle window always-on-top state."""
        try:
            self.pinned = not self.pinned
            flags = self.windowFlags()
            
            if self.pinned:
                flags |= QtCore.Qt.WindowStaysOnTopHint
                self.pin_btn.setText('📌')
                self.logger.info("Window pinned (always on top)")
            else:
                flags &= ~QtCore.Qt.WindowStaysOnTopHint
                self.pin_btn.setText('📍')
                self.logger.info("Window unpinned")
            
            self.setWindowFlags(flags)
            self.show()
        except Exception as e:
            self.logger.error(f"Failed to toggle pinned state: {e}")
    
    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        """Display context menu."""
        try:
            menu = QtWidgets.QMenu()
            
            # Add menu actions
            refresh_action = menu.addAction('Refresh Now')
            menu.addSeparator()
            about_action = menu.addAction('About')
            quit_action = menu.addAction('Exit')
            
            # Execute menu
            action = menu.exec_(self.mapToGlobal(pos))
            
            if action == quit_action:
                self.close()
            elif action == refresh_action:
                self._update_stats()
            elif action == about_action:
                self._show_about_dialog()
        
        except Exception as e:
            self.logger.error(f"Error showing context menu: {e}")
    
    def _show_about_dialog(self) -> None:
        """Display about dialog."""
        QtWidgets.QMessageBox.about(
            self,
            "About PC Performance Monitor",
            "<h3>PC Performance Monitor v2.0.0</h3>"
            "<p>A production-grade system monitoring tool.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Real-time CPU, Memory, Disk, Network monitoring</li>"
            "<li>Configurable thresholds and alerts</li>"
            "<li>Comprehensive logging</li>"
            "</ul>"
            "<p>© 2024 Performance Monitoring Team</p>"
        )
    
    # Mouse event handlers for drag functionality
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle mouse press event."""
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle mouse move event."""
        if self.drag_pos and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        super().mouseMoveEvent(event)
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle double-click event."""
        self._toggle_pinned()
        super().mouseDoubleClickEvent(event)
    
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle mouse release event."""
        self.drag_pos = None
        super().mouseReleaseEvent(event)
    
    def closeEvent(self, event: QtCore.QCloseEvent) -> None:
        """Handle window close event with cleanup."""
        if not self.is_closing:
            self.is_closing = True
            self.logger.info("Application closing, cleaning up...")
            
            # Stop timer
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            
            self.logger.info("Cleanup complete")
        
        event.accept()


# ============================================================================
# Application Entry Point
# ============================================================================

class PerformanceMonitorApp:
    """Main application coordinator."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None
        self.window = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals for graceful shutdown."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        if self.app:
            self.app.quit()
    
    def run(self) -> int:
        """Run the application."""
        try:
            self.logger.info("Starting PC Performance Monitor...")
            
            # Create Qt application
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setApplicationName("PC Performance Monitor")
            self.app.setApplicationVersion("2.0.0")
            self.app.setQuitOnLastWindowClosed(True)
            
            # Enable Ctrl+C handling
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: None)
            timer.start(100)
            
            # Create and show main window
            self.window = TaskbarWindow(self.config)
            self.window.show()
            
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
        description="PC Performance Monitor - Real-time system metrics display"
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
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()
    
    # Load or generate configuration
    if args.generate_config:
        config = AppConfig()
        config.save(args.config)
        print(f"Configuration file generated: {args.config}")
        return 0
    
    config = AppConfig.from_file(args.config)
    
    # Override log level if debug flag is set
    if args.debug:
        config.log_level = "DEBUG"
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("PC Performance Monitor v2.0.0")
    logger.info("=" * 60)
    
    # Run application
    app = PerformanceMonitorApp(config)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())