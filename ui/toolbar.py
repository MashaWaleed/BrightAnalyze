"""
Modern Toolbar for Professional CAN Analyzer
Enhanced with custom icons and professional styling
"""

from PySide6.QtWidgets import (QToolBar, QPushButton, QWidget, QHBoxLayout, 
                               QLabel, QComboBox, QSpinBox, QFrame)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor

class ModernToolbar(QWidget):
    # Navigation signals
    show_message_log = Signal()
    show_signal_plotter = Signal()
    show_scripting_console = Signal()
    show_diagnostics_panel = Signal()
    """Professional toolbar with modern styling and enhanced features"""
    
    # Connection signals
    connect_bus = Signal()
    disconnect_bus = Signal()
    
    # Logging signals
    start_logging = Signal()
    stop_logging = Signal()
    pause_logging = Signal()
    clear_log = Signal()
    
    # File operations
    save_log = Signal()
    load_log = Signal()
    export_data = Signal()
    
    # View controls
    toggle_filters = Signal(bool)
    toggle_autoscroll = Signal(bool)
    
    # Quick settings
    interface_changed = Signal(str)
    bitrate_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected = False
        self.logging = False
        self.paused = False
        self.filters_shown = True
        self.autoscroll_enabled = True
        
        # Track active panel for navigation highlighting
        self.active_panel = "message_log"  # Default active panel
        self.nav_buttons = {}  # Will store navigation buttons for easy access
        
        self.setup_ui()
        self.create_icons()
        self.apply_modern_style()
        self.setup_status_animation()
        
    def setup_ui(self):
        """Setup the toolbar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Connection section
        self.create_connection_section(layout)
        layout.addWidget(self.create_separator())
        
        # Logging section
        self.create_logging_section(layout)
        layout.addWidget(self.create_separator())
        
        # File operations section
        self.create_file_section(layout)
        layout.addWidget(self.create_separator())
        
        # View controls section
        self.create_view_section(layout)
        layout.addWidget(self.create_separator())
        
        # Quick settings section
        self.create_quick_settings(layout)
        
        # Navigation section (panel switching)
        self.create_navigation_section(layout)
        layout.addWidget(self.create_separator())

        # Spacer
        layout.addStretch()
        
        # Status indicators
        self.create_status_section(layout)
    def create_navigation_section(self, layout):
        """Create navigation buttons for switching central panels"""
        self.nav_msglog_btn = self.create_modern_button("💬", "Show Message Log", "nav_msglog")
        self.nav_msglog_btn.clicked.connect(lambda: self.set_active_panel("message_log"))
        self.nav_msglog_btn.clicked.connect(self.show_message_log)
        layout.addWidget(self.nav_msglog_btn)

        self.nav_plotter_btn = self.create_modern_button("📊", "Show Signal Plotter", "nav_plotter")
        self.nav_plotter_btn.clicked.connect(lambda: self.set_active_panel("signal_plotter"))
        self.nav_plotter_btn.clicked.connect(self.show_signal_plotter)
        layout.addWidget(self.nav_plotter_btn)

        self.nav_console_btn = self.create_modern_button("🐍", "Show Python Console", "nav_console")
        self.nav_console_btn.clicked.connect(lambda: self.set_active_panel("scripting_console"))
        self.nav_console_btn.clicked.connect(self.show_scripting_console)
        layout.addWidget(self.nav_console_btn)

        self.nav_diag_btn = self.create_modern_button("🔧", "Show Diagnostics Panel", "nav_diag")
        self.nav_diag_btn.clicked.connect(lambda: self.set_active_panel("diagnostics_panel"))
        self.nav_diag_btn.clicked.connect(self.show_diagnostics_panel)
        layout.addWidget(self.nav_diag_btn)
        
        # Store navigation buttons for easy access
        self.nav_buttons = {
            "message_log": self.nav_msglog_btn,
            "signal_plotter": self.nav_plotter_btn,
            "scripting_console": self.nav_console_btn,
            "diagnostics_panel": self.nav_diag_btn
        }
        
        # Set initial active state
        self.update_navigation_highlight()
        
    def create_connection_section(self, layout):
        """Create connection control buttons"""
        self.connect_btn = self.create_modern_button(
            "🔌", "Connect to CAN Bus", "connect"
        )
        self.connect_btn.clicked.connect(self.handle_connect)
        layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = self.create_modern_button(
            "❌", "Disconnect from CAN Bus", "disconnect"
        )
        self.disconnect_btn.clicked.connect(self.handle_disconnect)
        self.disconnect_btn.setEnabled(False)
        layout.addWidget(self.disconnect_btn)
        
    def create_logging_section(self, layout):
        """Create logging control buttons"""
        self.start_log_btn = self.create_modern_button(
            "▶️", "Start Logging", "start"
        )
        self.start_log_btn.clicked.connect(self.handle_start_logging)
        layout.addWidget(self.start_log_btn)
        
        self.pause_log_btn = self.create_modern_button(
            "⏸️", "Pause Logging", "pause"
        )
        self.pause_log_btn.clicked.connect(self.handle_pause_logging)
        self.pause_log_btn.setEnabled(False)
        layout.addWidget(self.pause_log_btn)
        
        self.stop_log_btn = self.create_modern_button(
            "⏹️", "Stop Logging", "stop"
        )
        self.stop_log_btn.clicked.connect(self.handle_stop_logging)
        self.stop_log_btn.setEnabled(False)
        layout.addWidget(self.stop_log_btn)
        
        self.clear_btn = self.create_modern_button(
            "🗑️", "Clear Log", "clear"
        )
        self.clear_btn.clicked.connect(self.clear_log.emit)
        layout.addWidget(self.clear_btn)
        
    def create_file_section(self, layout):
        """Create file operation buttons"""
        self.save_btn = self.create_modern_button(
            "💾", "Save Log", "save"
        )
        self.save_btn.clicked.connect(self.save_log.emit)
        layout.addWidget(self.save_btn)
        
        self.load_btn = self.create_modern_button(
            "📁", "Load Log", "load"
        )
        self.load_btn.clicked.connect(self.load_log.emit)
        layout.addWidget(self.load_btn)
        
        self.export_btn = self.create_modern_button(
            "📤", "Export Data", "export"
        )
        self.export_btn.clicked.connect(self.export_data.emit)
        layout.addWidget(self.export_btn)
        
    def create_view_section(self, layout):
        """Create view control buttons"""
        self.filter_btn = self.create_modern_button(
            "🔍", "Toggle Filters", "filter"
        )
        self.filter_btn.setCheckable(True)
        self.filter_btn.setChecked(True)
        self.filter_btn.clicked.connect(self.handle_toggle_filters)
        layout.addWidget(self.filter_btn)
        
    def create_quick_settings(self, layout):
        """Create quick settings controls (removed interface/bitrate/autoscroll)"""
        # No controls needed
        pass
        
    def create_status_section(self, layout):
        """Create status indicator section"""
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                background-color: #e3f2fd;
                border: 1px solid #2196f3;
                border-radius: 4px;
                color: #1976d2;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Connection status indicator
        self.connection_indicator = self.create_status_indicator("🔴", "Disconnected")
        layout.addWidget(self.connection_indicator)
        
        # Message rate indicator
        self.rate_label = QLabel("0 msg/s")
        self.rate_label.setStyleSheet("QLabel { font-family: monospace; }")
        layout.addWidget(self.rate_label)
        
    def create_modern_button(self, emoji, tooltip, object_name):
        """Create a modern styled button with emoji icon"""
        btn = QPushButton(emoji)
        btn.setToolTip(tooltip)
        btn.setObjectName(object_name)
        btn.setFixedSize(36, 36)
        return btn
        
    def create_status_indicator(self, emoji, tooltip):
        """Create a status indicator"""
        indicator = QLabel(emoji)
        indicator.setToolTip(tooltip)
        indicator.setFixedSize(24, 24)
        indicator.setAlignment(Qt.AlignCenter)
        return indicator
        
    def create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                color: #e0e0e0;
                margin: 4px 0;
            }
        """)
        return separator
        
    def create_icons(self):
        """Create custom icons for buttons"""
        # This would create proper icons instead of using emoji
        pass
        
    def setup_status_animation(self):
        """Setup animation for status indicators"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.start(500)  # Update every 500ms
        self.animation_state = 0
        
    def update_animations(self):
        """Update animated status indicators"""
        if self.logging and not self.paused:
            # Animate logging indicator
            if self.animation_state % 2 == 0:
                self.start_log_btn.setText("🔴")  # Red when logging
            else:
                self.start_log_btn.setText("📝")  # Document when logging
                
        self.animation_state += 1
        
    def handle_connect(self):
        """Handle connect button click"""
        self.set_connection_state(True)
        self.connect_bus.emit()
        
    def handle_disconnect(self):
        """Handle disconnect button click"""
        self.set_connection_state(False)
        self.disconnect_bus.emit()
        
    def handle_start_logging(self):
        """Handle start logging button click"""
        self.set_logging_state(True)
        self.start_logging.emit()
        
    def handle_pause_logging(self):
        """Handle pause logging button click"""
        self.paused = not self.paused
        self.pause_log_btn.setText("▶️" if self.paused else "⏸️")
        self.pause_log_btn.setToolTip("Resume Logging" if self.paused else "Pause Logging")
        self.pause_logging.emit()
        
    def handle_stop_logging(self):
        """Handle stop logging button click"""
        self.set_logging_state(False)
        self.stop_logging.emit()
        
    def handle_toggle_filters(self):
        """Handle filter toggle"""
        self.filters_shown = self.filter_btn.isChecked()
        self.toggle_filters.emit(self.filters_shown)
        
    def handle_toggle_autoscroll(self):
        """Handle autoscroll toggle"""
        self.autoscroll_enabled = self.autoscroll_btn.isChecked()
        self.toggle_autoscroll.emit(self.autoscroll_enabled)
        
    def set_connection_state(self, connected):
        """Update UI for connection state"""
        self.connected = connected
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        
        if connected:
            self.connection_indicator.setText("🟢")
            self.connection_indicator.setToolTip("Connected")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    background-color: #e8f5e8;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                    color: #2e7d32;
                    font-weight: bold;
                }
            """)
        else:
            self.connection_indicator.setText("🔴")
            self.connection_indicator.setToolTip("Disconnected")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    background-color: #ffebee;
                    border: 1px solid #f44336;
                    border-radius: 4px;
                    color: #c62828;
                    font-weight: bold;
                }
            """)
            
    def set_logging_state(self, logging):
        """Update UI for logging state"""
        self.logging = logging
        self.paused = False
        
        self.start_log_btn.setEnabled(not logging)
        self.pause_log_btn.setEnabled(logging)
        self.stop_log_btn.setEnabled(logging)
        
        if logging:
            self.start_log_btn.setText("🔴")
        else:
            self.start_log_btn.setText("▶️")
            
        self.pause_log_btn.setText("⏸️")
        
    def update_message_rate(self, rate):
        """Update message rate display"""
        self.rate_label.setText(f"{rate:.1f} msg/s")
        
    def apply_modern_style(self):
        """Apply modern styling to the toolbar"""
        self.setStyleSheet("""
            ModernToolbar {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border-bottom: 1px solid #e9ecef;
                min-height: 52px;
            }
            
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                padding: 0;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                border-color: #adb5bd;
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #e9ecef, stop: 1 #dee2e6);
            }
            
            QPushButton:checked {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #007bff, stop: 1 #0056b3);
                border-color: #0056b3;
                color: white;
            }
            
            QPushButton:disabled {
                background: #f8f9fa;
                border-color: #e9ecef;
                color: #6c757d;
            }
            
            QComboBox {
                background: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }
            
            QComboBox:hover {
                border-color: #80bdff;
            }
            
            QComboBox:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QLabel {
                color: #495057;
                font-weight: 500;
            }
        """)
        
    def set_active_panel(self, panel_name):
        """Set the active panel and update navigation highlighting"""
        self.active_panel = panel_name
        self.update_navigation_highlight()
        
    def update_navigation_highlight(self):
        """Update the visual highlighting of navigation buttons"""
        for panel_name, button in self.nav_buttons.items():
            if panel_name == self.active_panel:
                # Active button styling - preserve size and emoji display
                button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #007bff, stop:1 #0056b3);
                        color: white;
                        border: 2px solid #0056b3;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 16px;
                        min-width: 36px;
                        min-height: 36px;
                        max-width: 36px;
                        max-height: 36px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #0056b3, stop:1 #003d82);
                        border-color: #003d82;
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #003d82, stop:1 #002952);
                        border-color: #002952;
                    }
                """)
            else:
                # Inactive button styling - preserve size and emoji display
                button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #ffffff, stop:1 #f8f9fa);
                        color: #495057;
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        font-weight: normal;
                        font-size: 16px;
                        min-width: 36px;
                        min-height: 36px;
                        max-width: 36px;
                        max-height: 36px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #e9ecef, stop:1 #dee2e6);
                        border-color: #adb5bd;
                        color: #212529;
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #dee2e6, stop:1 #ced4da);
                        border-color: #6c757d;
                    }
                """)