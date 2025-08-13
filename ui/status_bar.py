"""
Intelligent Status Bar for Professional CAN Analyzer
Shows connection status, message rates, and system information
"""

from PySide6.QtWidgets import (QStatusBar, QLabel, QWidget, QHBoxLayout, 
                               QProgressBar, QPushButton, QFrame, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter

class IntelligentStatusBar(QStatusBar):
    """Professional status bar with comprehensive system information"""
    
    # Signals
    connection_clicked = Signal()
    settings_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected = False
        self.message_count = 0
        self.error_count = 0
        self.current_interface = ""
        self.current_bitrate = 0
        
        self.setup_ui()
        self.setup_timers()
        self.apply_modern_style()
        
    def setup_ui(self):
        """Setup status bar widgets"""
        # Connection status section
        self.connection_widget = self.create_connection_widget()
        self.addWidget(self.connection_widget)
        
        # Add separator
        self.addWidget(self.create_separator())
        
        # Message statistics section  
        self.stats_widget = self.create_stats_widget()
        self.addWidget(self.stats_widget)
        
        # Add separator
        self.addWidget(self.create_separator())
        
        # Interface information
        self.interface_widget = self.create_interface_widget()
        self.addWidget(self.interface_widget)
        
        # Add separator
        self.addWidget(self.create_separator())
        
        # System performance
        self.performance_widget = self.create_performance_widget()
        self.addWidget(self.performance_widget)
        
        # Spacer to push right-aligned items
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
        
        # Right-aligned widgets
        self.time_label = QLabel()
        self.time_label.setStyleSheet("QLabel { font-family: monospace; color: #666; }")
        self.addPermanentWidget(self.time_label)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        self.addPermanentWidget(self.settings_btn)
        
    def create_connection_widget(self):
        """Create connection status widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        
        # Connection indicator
        self.connection_indicator = QLabel("🔴")
        self.connection_indicator.setFixedSize(20, 20)
        layout.addWidget(self.connection_indicator)
        
        # Connection text
        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("""
            QLabel {
                color: #c62828;
                font-weight: bold;
                padding: 2px 6px;
                background-color: #ffebee;
                border: 1px solid #ef5350;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.connection_label)
        
        # Make clickable
        widget.mousePressEvent = lambda e: self.connection_clicked.emit()
        widget.setCursor(Qt.PointingHandCursor)
        widget.setToolTip("Click to toggle connection")
        
        return widget
        
    def create_stats_widget(self):
        """Create message statistics widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)
        
        # Message count
        msg_layout = QHBoxLayout()
        msg_layout.addWidget(QLabel("📝"))
        self.msg_count_label = QLabel("0")
        self.msg_count_label.setStyleSheet("QLabel { font-family: monospace; font-weight: bold; }")
        msg_layout.addWidget(self.msg_count_label)
        msg_layout.addWidget(QLabel("msgs"))
        
        msg_widget = QWidget()
        msg_widget.setLayout(msg_layout)
        layout.addWidget(msg_widget)
        
        # Message rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("📊"))
        self.msg_rate_label = QLabel("0.0")
        self.msg_rate_label.setStyleSheet("QLabel { font-family: monospace; font-weight: bold; }")
        rate_layout.addWidget(self.msg_rate_label)
        rate_layout.addWidget(QLabel("msg/s"))
        
        rate_widget = QWidget()
        rate_widget.setLayout(rate_layout)
        layout.addWidget(rate_widget)
        
        # Error count
        error_layout = QHBoxLayout()
        error_layout.addWidget(QLabel("⚠️"))
        self.error_count_label = QLabel("0")
        self.error_count_label.setStyleSheet("QLabel { font-family: monospace; font-weight: bold; color: #d32f2f; }")
        error_layout.addWidget(self.error_count_label)
        error_layout.addWidget(QLabel("errors"))
        
        error_widget = QWidget()
        error_widget.setLayout(error_layout)
        layout.addWidget(error_widget)
        
        return widget
        
    def create_interface_widget(self):
        """Create interface information widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        
        # Interface name
        layout.addWidget(QLabel("🔌"))
        self.interface_label = QLabel("none")
        self.interface_label.setStyleSheet("QLabel { font-family: monospace; }")
        layout.addWidget(self.interface_label)
        
        # Bitrate
        layout.addWidget(QLabel("@"))
        self.bitrate_label = QLabel("0")
        self.bitrate_label.setStyleSheet("QLabel { font-family: monospace; }")
        layout.addWidget(self.bitrate_label)
        layout.addWidget(QLabel("kbps"))
        
        return widget
        
    def create_performance_widget(self):
        """Create system performance widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        
        # CPU usage (placeholder)
        layout.addWidget(QLabel("💻"))
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setFixedSize(60, 16)
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(25)
        self.cpu_progress.setTextVisible(False)
        layout.addWidget(self.cpu_progress)
        
        # Memory usage (placeholder)
        layout.addWidget(QLabel("🧠"))
        self.memory_progress = QProgressBar()
        self.memory_progress.setFixedSize(60, 16)
        self.memory_progress.setRange(0, 100)
        self.memory_progress.setValue(45)
        self.memory_progress.setTextVisible(False)
        layout.addWidget(self.memory_progress)
        
        return widget
        
    def create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #e0e0e0; }")
        return separator
        
    def setup_timers(self):
        """Setup update timers"""
        # Update time display
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # Update every second
        
        # Update statistics
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(100)  # Update every 100ms
        
        # Initial update
        self.update_time()
        
    def update_time(self):
        """Update time display"""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(current_time)
        
    def update_stats(self):
        """Update statistics display"""
        # This would be connected to real data in a full implementation
        pass
        
    def set_connection_state(self, connected, interface="", bitrate=0):
        """Update connection state display"""
        self.connected = connected
        self.current_interface = interface
        self.current_bitrate = bitrate
        
        if connected:
            self.connection_indicator.setText("🟢")
            self.connection_label.setText("Connected")
            self.connection_label.setStyleSheet("""
                QLabel {
                    color: #2e7d32;
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: #e8f5e8;
                    border: 1px solid #4caf50;
                    border-radius: 3px;
                }
            """)
            self.interface_label.setText(interface)
            self.bitrate_label.setText(str(bitrate))
        else:
            self.connection_indicator.setText("🔴")
            self.connection_label.setText("Disconnected")
            self.connection_label.setStyleSheet("""
                QLabel {
                    color: #c62828;
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: #ffebee;
                    border: 1px solid #ef5350;
                    border-radius: 3px;
                }
            """)
            self.interface_label.setText("none")
            self.bitrate_label.setText("0")
            
    def update_message_count(self, count):
        """Update message count display"""
        self.message_count = count
        self.msg_count_label.setText(f"{count:,}")
        
    def update_message_rate(self, rate):
        """Update message rate display"""
        self.msg_rate_label.setText(f"{rate:.1f}")
        
    def update_error_count(self, count):
        """Update error count display"""
        self.error_count = count
        self.error_count_label.setText(f"{count}")
        
        # Change color based on error count
        if count > 0:
            self.error_count_label.setStyleSheet("""
                QLabel { 
                    font-family: monospace; 
                    font-weight: bold; 
                    color: #d32f2f; 
                    background-color: #ffebee;
                    padding: 1px 4px;
                    border-radius: 2px;
                }
            """)
        else:
            self.error_count_label.setStyleSheet("""
                QLabel { 
                    font-family: monospace; 
                    font-weight: bold; 
                    color: #2e7d32; 
                }
            """)
            
    def show_message(self, message, timeout=3000):
        """Show a temporary message"""
        self.showMessage(message, timeout)
        
    def apply_modern_style(self):
        """Apply modern styling to the status bar"""
        self.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                border-top: 1px solid #dee2e6;
                color: #495057;
                padding: 4px;
            }
            
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #dee2e6;
            }
            
            QPushButton:pressed {
                background-color: #dee2e6;
            }
            
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 7px;
            }
        """)