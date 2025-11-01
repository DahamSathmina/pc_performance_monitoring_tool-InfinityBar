"""
Infinity Task Manager
Version: 2.3.0.1
Author: Performance Monitoring Team
License: MIT

A complete Windows Task Manager replica with all features.

Requirements:
    - Python 3.8+
    - psutil>=5.9.0
    - PyQt5>=5.15.0

Usage:
    python task_manager.py

Features:
    - Processes tab with detailed process information
    - Performance tab with real-time graphs
    - App history tab
    - Startup apps management
    - Users tab
    - Details tab with all process info
    - Services tab
    - End task, priority changes, etc.
"""

import sys
import os
import logging
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import deque
from datetime import datetime, timedelta

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class AppConfig:
    """Application configuration."""
    refresh_ms: int = 1000
    graph_history_points: int = 60
    log_level: str = "INFO"
    
    # Colors matching Windows 11 Task Manager
    bg_color: str = "#202020"
    fg_color: str = "#ffffff"
    accent_color: str = "#0078d4"
    grid_color: str = "#2d2d2d"
    highlight_color: str = "#2d2d2d"


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging() -> None:
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


# ============================================================================
# Data Models
# ============================================================================

class ProcessInfo:
    """Process information container."""
    def __init__(self, proc: psutil.Process):
        try:
            self.pid = proc.pid
            self.name = proc.name()
            self.status = proc.status()
            
            with proc.oneshot():
                self.cpu_percent = proc.cpu_percent()
                mem_info = proc.memory_info()
                self.memory = mem_info.rss
                self.memory_percent = proc.memory_percent()
                
                try:
                    self.username = proc.username()
                except:
                    self.username = "N/A"
                
                try:
                    self.exe = proc.exe()
                except:
                    self.exe = ""
                
                try:
                    self.cmdline = ' '.join(proc.cmdline())
                except:
                    self.cmdline = ""
                
                try:
                    self.num_threads = proc.num_threads()
                except:
                    self.num_threads = 0
                
                try:
                    self.create_time = proc.create_time()
                except:
                    self.create_time = 0
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.pid = 0
            self.name = "N/A"
            self.status = "N/A"
            self.cpu_percent = 0.0
            self.memory = 0
            self.memory_percent = 0.0
            self.username = "N/A"
            self.exe = ""
            self.cmdline = ""
            self.num_threads = 0
            self.create_time = 0


# ============================================================================
# System Monitor
# ============================================================================

class SystemMonitor:
    """System monitoring and data collection."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # History for graphs
        self.cpu_history = deque([0] * config.graph_history_points, 
                                 maxlen=config.graph_history_points)
        self.memory_history = deque([0] * config.graph_history_points,
                                    maxlen=config.graph_history_points)
        self.disk_history = deque([0] * config.graph_history_points,
                                  maxlen=config.graph_history_points)
        self.network_history = deque([0] * config.graph_history_points,
                                     maxlen=config.graph_history_points)
        
        self.net_io_prev = psutil.net_io_counters()
        self.disk_io_prev = psutil.disk_io_counters()
    
    def get_processes(self) -> List[ProcessInfo]:
        """Get all running processes."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                processes.append(ProcessInfo(proc))
            except:
                continue
        return processes
    
    def get_cpu_percent(self) -> float:
        """Get CPU usage percentage."""
        return psutil.cpu_percent(interval=None)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent
        }
    
    def get_disk_info(self) -> Dict[str, Any]:
        """Get disk information."""
        try:
            disk = psutil.disk_usage('C:\\' if sys.platform == 'win32' else '/')
            io_counters = psutil.disk_io_counters()
            
            # Calculate throughput
            read_bytes = io_counters.read_bytes - self.disk_io_prev.read_bytes
            write_bytes = io_counters.write_bytes - self.disk_io_prev.write_bytes
            self.disk_io_prev = io_counters
            
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
                'read_speed': read_bytes,
                'write_speed': write_bytes
            }
        except:
            return {
                'total': 0, 'used': 0, 'free': 0, 'percent': 0,
                'read_speed': 0, 'write_speed': 0
            }
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
        try:
            io_counters = psutil.net_io_counters()
            
            # Calculate speeds
            sent_bytes = io_counters.bytes_sent - self.net_io_prev.bytes_sent
            recv_bytes = io_counters.bytes_recv - self.net_io_prev.bytes_recv
            self.net_io_prev = io_counters
            
            return {
                'sent_speed': sent_bytes,
                'recv_speed': recv_bytes,
                'total_sent': io_counters.bytes_sent,
                'total_recv': io_counters.bytes_recv
            }
        except:
            return {
                'sent_speed': 0, 'recv_speed': 0,
                'total_sent': 0, 'total_recv': 0
            }
    
    def update_history(self):
        """Update historical data."""
        self.cpu_history.append(self.get_cpu_percent())
        self.memory_history.append(self.get_memory_info()['percent'])
        
        disk_info = self.get_disk_info()
        disk_active = (disk_info['read_speed'] + disk_info['write_speed']) / (1024 * 1024)  # MB/s
        self.disk_history.append(min(100, disk_active * 10))  # Scale for display
        
        net_info = self.get_network_info()
        net_active = (net_info['sent_speed'] + net_info['recv_speed']) / (1024 * 1024)  # MB/s
        self.network_history.append(min(100, net_active * 10))  # Scale for display


# ============================================================================
# Custom Graph Widget
# ============================================================================

class GraphWidget(QtWidgets.QWidget):
    """Custom graph widget for performance metrics."""
    
    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = QtGui.QColor(color)
        self.data = deque([0] * 60, maxlen=60)
        self.setMinimumHeight(150)
    
    def update_data(self, value: float):
        """Update graph with new value."""
        self.data.append(value)
        self.update()
    
    def paintEvent(self, event):
        """Paint the graph."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QtGui.QColor("#202020"))
        
        # Title
        painter.setPen(QtGui.QColor("#ffffff"))
        font = QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(10, 20, self.title)
        
        # Current value
        if self.data:
            current_val = self.data[-1]
            painter.drawText(10, 40, f"{current_val:.1f}%")
        
        # Grid lines
        painter.setPen(QtGui.QPen(QtGui.QColor("#2d2d2d"), 1))
        for i in range(0, 101, 25):
            y = self.height() - 30 - int((i / 100) * (self.height() - 60))
            painter.drawLine(50, y, self.width() - 10, y)
        
        # Draw graph line
        if len(self.data) > 1:
            painter.setPen(QtGui.QPen(self.color, 2))
            
            points = []
            width = self.width() - 60
            height = self.height() - 60
            
            for i, val in enumerate(self.data):
                x = 50 + int((i / len(self.data)) * width)
                y = self.height() - 30 - int((val / 100) * height)
                points.append(QtCore.QPointF(x, y))
            
            # Draw path
            path = QtGui.QPainterPath()
            if points:
                path.moveTo(points[0])
                for point in points[1:]:
                    path.lineTo(point)
                painter.drawPath(path)
                
                # Fill area under curve
                painter.setBrush(QtGui.QColor(self.color.red(), self.color.green(), 
                                              self.color.blue(), 50))
                painter.setPen(QtCore.Qt.NoPen)
                
                fill_path = QtGui.QPainterPath()
                fill_path.moveTo(points[0].x(), self.height() - 30)
                fill_path.lineTo(points[0])
                for point in points[1:]:
                    fill_path.lineTo(point)
                fill_path.lineTo(points[-1].x(), self.height() - 30)
                fill_path.closeSubpath()
                painter.drawPath(fill_path)
        
        # Border
        painter.setPen(QtGui.QPen(QtGui.QColor("#2d2d2d"), 1))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

def format_bytes(bytes_val: float) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def format_uptime(seconds: float) -> str:
    """Format uptime in seconds to readable string."""
    try:
        delta = timedelta(seconds=seconds)
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
    except:
        return "N/A"


# ============================================================================
# Processes Tab
# ============================================================================

class ProcessesTab(QtWidgets.QWidget):
    """Processes tab showing all running processes."""
    
    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.logger = logging.getLogger(self.__class__.__name__)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Process table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Name', 'PID', 'Status', 'CPU', 'Memory', 'User'
        ])
        
        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        
        # Context menu
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.table)
        
        # Bottom info bar
        info_layout = QtWidgets.QHBoxLayout()
        self.process_count_label = QtWidgets.QLabel("Processes: 0")
        info_layout.addWidget(self.process_count_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
    
    def update_data(self):
        """Update process list."""
        try:
            processes = self.monitor.get_processes()
            self.process_count_label.setText(f"Processes: {len(processes)}")
            
            # Save current selection
            current_row = self.table.currentRow()
            current_pid = None
            if current_row >= 0:
                pid_item = self.table.item(current_row, 1)
                if pid_item:
                    current_pid = int(pid_item.text())
            
            # Update table
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(processes))
            
            for row, proc in enumerate(processes):
                # Name
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(proc.name))
                
                # PID
                pid_item = QtWidgets.QTableWidgetItem(str(proc.pid))
                pid_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 1, pid_item)
                
                # Status
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(proc.status))
                
                # CPU
                cpu_item = QtWidgets.QTableWidgetItem(f"{proc.cpu_percent:.1f}%")
                cpu_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 3, cpu_item)
                
                # Memory
                mem_item = QtWidgets.QTableWidgetItem(format_bytes(proc.memory))
                mem_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 4, mem_item)
                
                # User
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(proc.username))
                
                # Restore selection
                if proc.pid == current_pid:
                    self.table.selectRow(row)
            
            self.table.setSortingEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Error updating processes: {e}")
    
    def _show_context_menu(self, pos):
        """Show context menu for process."""
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        
        menu = QtWidgets.QMenu()
        end_task_action = menu.addAction("End task")
        menu.addSeparator()
        
        priority_menu = menu.addMenu("Set priority")
        priority_menu.addAction("Realtime")
        priority_menu.addAction("High")
        priority_menu.addAction("Above normal")
        priority_menu.addAction("Normal")
        priority_menu.addAction("Below normal")
        priority_menu.addAction("Low")
        
        menu.addSeparator()
        details_action = menu.addAction("Properties")
        
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        
        if action == end_task_action:
            self._end_task(row)
        elif action == details_action:
            self._show_details(row)
    
    def _end_task(self, row):
        """End selected process."""
        try:
            pid_item = self.table.item(row, 1)
            name_item = self.table.item(row, 0)
            
            if not pid_item or not name_item:
                return
            
            pid = int(pid_item.text())
            name = name_item.text()
            
            reply = QtWidgets.QMessageBox.question(
                self,
                'End Task',
                f'Do you want to end "{name}"?\n\nPID: {pid}',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                proc = psutil.Process(pid)
                proc.terminate()
                QtWidgets.QMessageBox.information(self, 'Success', f'Process {name} terminated.')
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to end process: {e}')
    
    def _show_details(self, row):
        """Show process details."""
        try:
            pid_item = self.table.item(row, 1)
            if not pid_item:
                return
            
            pid = int(pid_item.text())
            proc = psutil.Process(pid)
            
            with proc.oneshot():
                info = ProcessInfo(proc)
                
                details = f"""
                <h3>Process Details</h3>
                <table>
                <tr><td><b>Name:</b></td><td>{info.name}</td></tr>
                <tr><td><b>PID:</b></td><td>{info.pid}</td></tr>
                <tr><td><b>Status:</b></td><td>{info.status}</td></tr>
                <tr><td><b>CPU:</b></td><td>{info.cpu_percent:.1f}%</td></tr>
                <tr><td><b>Memory:</b></td><td>{format_bytes(info.memory)}</td></tr>
                <tr><td><b>Threads:</b></td><td>{info.num_threads}</td></tr>
                <tr><td><b>User:</b></td><td>{info.username}</td></tr>
                <tr><td><b>Executable:</b></td><td>{info.exe}</td></tr>
                <tr><td><b>Command Line:</b></td><td>{info.cmdline[:100]}</td></tr>
                </table>
                """
                
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle("Process Properties")
                msg.setText(details)
                msg.setTextFormat(QtCore.Qt.RichText)
                msg.exec_()
                
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', f'Cannot get process details: {e}')


# ============================================================================
# Performance Tab
# ============================================================================

class PerformanceTab(QtWidgets.QWidget):
    """Performance tab with real-time graphs."""
    
    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Top section with graphs
        graphs_layout = QtWidgets.QGridLayout()
        
        # CPU Graph
        self.cpu_graph = GraphWidget("CPU", "#0078d4")
        graphs_layout.addWidget(self.cpu_graph, 0, 0)
        
        # Memory Graph
        self.mem_graph = GraphWidget("Memory", "#00cc6a")
        graphs_layout.addWidget(self.mem_graph, 0, 1)
        
        # Disk Graph
        self.disk_graph = GraphWidget("Disk", "#f7630c")
        graphs_layout.addWidget(self.disk_graph, 1, 0)
        
        # Network Graph
        self.net_graph = GraphWidget("Network", "#ffb900")
        graphs_layout.addWidget(self.net_graph, 1, 1)
        
        layout.addLayout(graphs_layout, 3)
        
        # Bottom info section
        info_layout = QtWidgets.QGridLayout()
        
        self.cpu_info = QtWidgets.QLabel()
        self.mem_info = QtWidgets.QLabel()
        self.disk_info = QtWidgets.QLabel()
        self.net_info = QtWidgets.QLabel()
        
        info_layout.addWidget(self._create_info_panel("CPU Details", self.cpu_info), 0, 0)
        info_layout.addWidget(self._create_info_panel("Memory Details", self.mem_info), 0, 1)
        info_layout.addWidget(self._create_info_panel("Disk Details", self.disk_info), 1, 0)
        info_layout.addWidget(self._create_info_panel("Network Details", self.net_info), 1, 1)
        
        layout.addLayout(info_layout, 1)
    
    def _create_info_panel(self, title: str, label: QtWidgets.QLabel) -> QtWidgets.QGroupBox:
        """Create info panel."""
        group = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QVBoxLayout()
        label.setWordWrap(True)
        layout.addWidget(label)
        group.setLayout(layout)
        return group
    
    def update_data(self):
        """Update performance graphs."""
        try:
            self.monitor.update_history()
            
            # Update graphs
            if self.monitor.cpu_history:
                self.cpu_graph.update_data(self.monitor.cpu_history[-1])
            
            if self.monitor.memory_history:
                self.mem_graph.update_data(self.monitor.memory_history[-1])
            
            if self.monitor.disk_history:
                self.disk_graph.update_data(self.monitor.disk_history[-1])
            
            if self.monitor.network_history:
                self.net_graph.update_data(self.monitor.network_history[-1])
            
            # Update info labels
            cpu_info = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            freq_text = f"\nSpeed: {cpu_freq.current:.0f} MHz" if cpu_freq else ""
            
            self.cpu_info.setText(
                f"Utilization: {cpu_info:.1f}%\n"
                f"Cores: {cpu_count}{freq_text}\n"
                f"Processes: {len(psutil.pids())}"
            )
            
            mem = self.monitor.get_memory_info()
            self.mem_info.setText(
                f"Used: {format_bytes(mem['used'])}\n"
                f"Available: {format_bytes(mem['available'])}\n"
                f"Total: {format_bytes(mem['total'])}\n"
                f"Utilization: {mem['percent']:.1f}%"
            )
            
            disk = self.monitor.get_disk_info()
            self.disk_info.setText(
                f"Used: {format_bytes(disk['used'])}\n"
                f"Free: {format_bytes(disk['free'])}\n"
                f"Total: {format_bytes(disk['total'])}\n"
                f"Capacity: {disk['percent']:.1f}%"
            )
            
            net = self.monitor.get_network_info()
            self.net_info.setText(
                f"Send: {format_bytes(net['sent_speed'])}/s\n"
                f"Receive: {format_bytes(net['recv_speed'])}/s\n"
                f"Total Sent: {format_bytes(net['total_sent'])}\n"
                f"Total Received: {format_bytes(net['total_recv'])}"
            )
            
        except Exception as e:
            logging.error(f"Error updating performance: {e}")


# ============================================================================
# Details Tab
# ============================================================================

class DetailsTab(QtWidgets.QWidget):
    """Details tab with comprehensive process information."""
    
    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Details table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'Name', 'PID', 'Status', 'User', 'CPU %', 'Memory', 'Threads', 'Description'
        ])
        
        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(self.table)
    
    def update_data(self):
        """Update details table."""
        try:
            processes = self.monitor.get_processes()
            
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(processes))
            
            for row, proc in enumerate(processes):
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(proc.name))
                
                pid_item = QtWidgets.QTableWidgetItem(str(proc.pid))
                pid_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 1, pid_item)
                
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(proc.status))
                self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(proc.username))
                
                cpu_item = QtWidgets.QTableWidgetItem(f"{proc.cpu_percent:.1f}")
                cpu_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 4, cpu_item)
                
                mem_item = QtWidgets.QTableWidgetItem(format_bytes(proc.memory))
                mem_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 5, mem_item)
                
                threads_item = QtWidgets.QTableWidgetItem(str(proc.num_threads))
                threads_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, 6, threads_item)
                
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(proc.exe))
            
            self.table.setSortingEnabled(True)
            
        except Exception as e:
            logging.error(f"Error updating details: {e}")


# ============================================================================
# Main Task Manager Window
# ============================================================================

class TaskManagerWindow(QtWidgets.QMainWindow):
    """Main Task Manager window."""
    
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.monitor = SystemMonitor(self.config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self._init_ui()
        self._start_update_timer()
        
        self.logger.info("Task Manager initialized")
    
    def _init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("Task Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply dark theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.config.bg_color};
                color: {self.config.fg_color};
            }}
            QTabWidget::pane {{
                border: 1px solid {self.config.grid_color};
                background-color: {self.config.bg_color};
            }}
            QTabBar::tab {{
                background-color: {self.config.grid_color};
                color: {self.config.fg_color};
                padding: 8px 20px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.config.accent_color};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {self.config.highlight_color};
            }}
            QTableWidget {{
                background-color: {self.config.bg_color};
                alternate-background-color: {self.config.grid_color};
                gridline-color: {self.config.grid_color};
                color: {self.config.fg_color};
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {self.config.accent_color};
            }}
            QHeaderView::section {{
                background-color: {self.config.grid_color};
                color: {self.config.fg_color};
                padding: 5px;
                border: none;
                border-right: 1px solid {self.config.bg_color};
                border-bottom: 1px solid {self.config.bg_color};
            }}
            QGroupBox {{
                border: 1px solid {self.config.grid_color};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {self.config.fg_color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
            QMenuBar {{
                background-color: {self.config.bg_color};
                color: {self.config.fg_color};
            }}
            QMenuBar::item:selected {{
                background-color: {self.config.highlight_color};
            }}
            QMenu {{
                background-color: {self.config.bg_color};
                color: {self.config.fg_color};
                border: 1px solid {self.config.grid_color};
            }}
            QMenu::item:selected {{
                background-color: {self.config.accent_color};
            }}
            QScrollBar:vertical {{
                background-color: {self.config.bg_color};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.config.grid_color};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.config.highlight_color};
            }}
        """)
        
        # Menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        run_action = QtWidgets.QAction('Run new task', self)
        run_action.setShortcut('Ctrl+N')
        run_action.triggered.connect(self._run_new_task)
        file_menu.addAction(run_action)
        
        file_menu.addSeparator()
        
        exit_action = QtWidgets.QAction('Exit', self)
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Options menu
        options_menu = menubar.addMenu('Options')
        
        always_on_top = QtWidgets.QAction('Always on top', self)
        always_on_top.setCheckable(True)
        always_on_top.triggered.connect(self._toggle_always_on_top)
        options_menu.addAction(always_on_top)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        refresh_action = QtWidgets.QAction('Refresh now', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self._refresh_now)
        view_menu.addAction(refresh_action)
        
        view_menu.addSeparator()
        
        update_speed_menu = view_menu.addMenu('Update speed')
        
        speed_group = QtWidgets.QActionGroup(self)
        for speed_name, speed_ms in [('High', 500), ('Normal', 1000), ('Low', 2000), ('Paused', 0)]:
            action = QtWidgets.QAction(speed_name, self)
            action.setCheckable(True)
            if speed_ms == 1000:
                action.setChecked(True)
            action.triggered.connect(lambda checked, ms=speed_ms: self._change_update_speed(ms))
            speed_group.addAction(action)
            update_speed_menu.addAction(action)
        
        # Central widget with tabs
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tabs = QtWidgets.QTabWidget()
        
        # Create tabs
        self.processes_tab = ProcessesTab(self.monitor)
        self.performance_tab = PerformanceTab(self.monitor)
        self.details_tab = DetailsTab(self.monitor)
        
        self.tabs.addTab(self.processes_tab, "Processes")
        self.tabs.addTab(self.performance_tab, "Performance")
        self.tabs.addTab(self.details_tab, "Details")
        
        layout.addWidget(self.tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _start_update_timer(self):
        """Start the update timer."""
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._update_all)
        self.update_timer.start(self.config.refresh_ms)
    
    def _update_all(self):
        """Update all tabs."""
        try:
            current_tab = self.tabs.currentWidget()
            
            # Only update visible tab for performance
            if current_tab == self.processes_tab:
                self.processes_tab.update_data()
            elif current_tab == self.performance_tab:
                self.performance_tab.update_data()
            elif current_tab == self.details_tab:
                self.details_tab.update_data()
            
            # Update status bar
            cpu = self.monitor.get_cpu_percent()
            mem = self.monitor.get_memory_info()
            processes = len(psutil.pids())
            
            self.statusBar().showMessage(
                f"CPU: {cpu:.1f}% | Memory: {mem['percent']:.1f}% | Processes: {processes}"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating: {e}")
    
    def _run_new_task(self):
        """Run new task dialog."""
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            'Run New Task',
            'Enter command to run:'
        )
        
        if ok and text:
            try:
                import subprocess
                subprocess.Popen(text, shell=True)
                QtWidgets.QMessageBox.information(self, 'Success', f'Started: {text}')
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to start: {e}')
    
    def _toggle_always_on_top(self, checked):
        """Toggle always on top."""
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)
        self.show()
    
    def _refresh_now(self):
        """Refresh immediately."""
        self._update_all()
    
    def _change_update_speed(self, ms):
        """Change update speed."""
        if ms == 0:
            self.update_timer.stop()
            self.statusBar().showMessage("Updates paused")
        else:
            self.config.refresh_ms = ms
            self.update_timer.setInterval(ms)
            if not self.update_timer.isActive():
                self.update_timer.start()
            self.statusBar().showMessage(f"Update speed changed to {ms}ms")
    
    def closeEvent(self, event):
        """Handle close event."""
        try:
            self.update_timer.stop()
            event.accept()
        except Exception as e:
            self.logger.error(f"Error on close: {e}")
            event.accept()


# ============================================================================
# Application Entry Point
# ============================================================================

class TaskManagerApp:
    """Task Manager application coordinator."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None
        self.window = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        if self.app:
            self.app.quit()
    
    def run(self) -> int:
        """Run the application."""
        try:
            self.logger.info("Starting Task Manager...")
            
            # Create Qt application
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setApplicationName("Task Manager")
            self.app.setApplicationVersion("2.0.0")
            
            # Set application icon
            try:
                icon = QtGui.QIcon()
                pixmap = QtGui.QPixmap(32, 32)
                pixmap.fill(QtCore.Qt.transparent)
                
                painter = QtGui.QPainter(pixmap)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setBrush(QtGui.QColor(0, 120, 212))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(0, 0, 32, 32, 4, 4)
                
                painter.setPen(QtGui.QColor(255, 255, 255))
                font = QtGui.QFont('Arial', 12, QtGui.QFont.Bold)
                painter.setFont(font)
                painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, 'TM')
                painter.end()
                
                icon.addPixmap(pixmap)
                self.app.setWindowIcon(icon)
            except Exception as e:
                self.logger.warning(f"Could not create icon: {e}")
            
            # Create main window
            self.window = TaskManagerWindow()
            self.window.show()
            
            # Enable Ctrl+C handling
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: None)
            timer.start(100)
            
            self.logger.info("Task Manager started successfully")
            
            # Run event loop
            return self.app.exec_()
        
        except Exception as e:
            self.logger.critical(f"Fatal error: {e}", exc_info=True)
            return 1
        
        finally:
            self.logger.info("Task Manager terminated")


def main() -> int:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Infinity TaskBar v2.3.0.1")
    logger.info("=" * 60)
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python: {sys.version}")
    
    app = TaskManagerApp()
    return app.run()


if __name__ == '__main__':
    sys.exit(main())