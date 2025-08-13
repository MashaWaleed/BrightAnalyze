#!/usr/bin/env python3
"""
Professional CAN Bus Analyzer - Main Application
Enhanced version with modern UI and advanced features
"""

import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                               QHBoxLayout, QWidget, QSplitter, QPushButton,
                               QMenuBar, QStatusBar, QTabWidget, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QSettings, Signal, QThread
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QAction, QKeySequence

# Import all our custom widgets
from ui.menu_bar import EnhancedMenuBar
from ui.toolbar import ModernToolbar
from ui.left_sidebar import AdvancedLeftSidebar
from ui.message_log import ProfessionalMessageLog
from ui.status_bar import IntelligentStatusBar
from ui.right_sidebar import FeatureRichRightSidebar
from ui.workspace_manager import WorkspaceManager
from ui.dbc_manager import DBCManager
from ui.diagnostics_panel import DiagnosticsPanel
from ui.scripting_console import ScriptingConsole
from ui.signal_plotter import SignalPlotter
from ui.style_manager import ModernStyleManager
from can_backend import CANBusManager
from uds_backend import SimpleUDSBackend 
import time

class CANAnalyzerMainWindow(QMainWindow):
    """Main application window with advanced features and modern styling"""
    
    # Signals
    theme_changed = Signal(str)  # 'light' or 'dark'
    workspace_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional CAN Bus Analyzer v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Application state
        self.settings = QSettings("CANAnalyzer", "Professional")
        self.current_theme = self.settings.value("theme", "light")
        self.current_workspace = "Default"
        
        # Managers
        self.style_manager = ModernStyleManager()
        self.workspace_manager = WorkspaceManager()
        self.dbc_manager = DBCManager()
        self.can_manager = CANBusManager(self)
        
        # Create UDS backend with default CAN IDs
        self.uds_backend = SimpleUDSBackend(self.can_manager, tx_id=0x7E0, rx_id=0x7E8, parent=self)
        
        # Initialize UI
        self.setup_ui()
        self.setup_connections()
        self.apply_theme(self.current_theme)
        self.restore_settings()
        
        # Set application icon
        self.setWindowIcon(self.create_app_icon())
        
    def setup_ui(self):
        """Initialize the user interface with modern layout"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create menu bar
        self.menu_bar = EnhancedMenuBar(self)
        self.setMenuBar(self.menu_bar)
        
        # Create toolbar
        self.toolbar = ModernToolbar(self)
        main_layout.addWidget(self.toolbar)
        
        # Create workspace tabs
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setTabsClosable(True)
        self.workspace_tabs.tabCloseRequested.connect(self.close_workspace)
        
        main_layout.addWidget(self.workspace_tabs)
        
        # Create default workspace
        self.create_workspace("Default")
        
        # Create status bar
        self.status_bar = IntelligentStatusBar(self)
        self.setStatusBar(self.status_bar)
        
    def create_workspace(self, name):
        """Create a new workspace with all panels, using a stacked widget for central navigation"""
        from PySide6.QtWidgets import QStackedWidget
        workspace_widget = QWidget()
        # Main horizontal splitter for the workspace
        main_splitter = QSplitter(Qt.Horizontal)
        workspace_layout = QVBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(2, 2, 2, 2)
        workspace_layout.addWidget(main_splitter)

        # Left sidebar
        left_sidebar = AdvancedLeftSidebar(self)
        left_sidebar.set_dbc_manager(self.dbc_manager)
        left_sidebar.setMinimumWidth(350)
        left_sidebar.setMaximumWidth(600)
        main_splitter.addWidget(left_sidebar)

        # Central area: QStackedWidget for navigation
        central_stack = QStackedWidget()
        message_log = ProfessionalMessageLog(self, dbc_manager=self.dbc_manager)
        signal_plotter = SignalPlotter(self, dbc_manager=self.dbc_manager)
        scripting_console = ScriptingConsole(self)
        scripting_console.set_dbc_manager(self.dbc_manager)
        diagnostics_panel = DiagnosticsPanel(self)

        # Connect UDS backend to diagnostics panel  
        diagnostics_panel.set_uds_backend(self.uds_backend)
        
        # Add widgets to stack
        central_stack.addWidget(message_log)         # index 0
        central_stack.addWidget(signal_plotter)      # index 1
        central_stack.addWidget(scripting_console)   # index 2
        central_stack.addWidget(diagnostics_panel)   # index 3
        main_splitter.addWidget(central_stack)

        # Right sidebar
        right_sidebar = FeatureRichRightSidebar(self)
        right_sidebar.setMinimumWidth(350)
        right_sidebar.setMaximumWidth(600)
        main_splitter.addWidget(right_sidebar)

        # Set initial splitter sizes
        main_splitter.setSizes([350, 900, 350])

        # Store references
        workspace_data = {
            'widget': workspace_widget,
            'left_sidebar': left_sidebar,
            'message_log': message_log,
            'right_sidebar': right_sidebar,
            'signal_plotter': signal_plotter,
            'scripting_console': scripting_console,
            'diagnostics_panel': diagnostics_panel,
            'central_stack': central_stack,
            'splitter': main_splitter
        }

        # Add to tabs
        index = self.workspace_tabs.addTab(workspace_widget, name)
        self.workspace_tabs.tabBar().setTabData(index, workspace_data)
        self.workspace_tabs.setCurrentIndex(index)

        # Connect left sidebar signals to CAN manager
        left_sidebar.connect_requested.connect(self.handle_can_connect)
        left_sidebar.disconnect_requested.connect(self.handle_can_disconnect)
        left_sidebar.send_message.connect(self.handle_can_send_message)

        # Connect CAN manager signals to UI components
        self.can_manager.message_received.connect(lambda msg: self.handle_can_message(msg, message_log))
        self.can_manager.bus_state_changed.connect(self.handle_can_state)
        self.can_manager.error_occurred.connect(self.handle_can_error)

        # Connect diagnostics panel UDS signals to main window (for logging/status updates)
        diagnostics_panel.uds_connect_requested.connect(self.handle_uds_connect_request)
        diagnostics_panel.uds_disconnect_requested.connect(self.handle_uds_disconnect_request)

        return workspace_data
        
    def show_workspace_panel(self, panel_name):
        """Switch the central stack to the requested panel by name."""
        idx = self.workspace_tabs.currentIndex()
        workspace_data = self.workspace_tabs.tabBar().tabData(idx)
        if not workspace_data or 'central_stack' not in workspace_data:
            return
        stack = workspace_data['central_stack']
        panel_indices = {
            'message_log': 0,
            'signal_plotter': 1,
            'scripting_console': 2,
            'diagnostics_panel': 3
        }
        if panel_name in panel_indices:
            stack.setCurrentIndex(panel_indices[panel_name])
        
    def setup_connections(self):
        """Setup signal connections"""
        # Menu bar connections
        self.menu_bar.new_workspace.connect(self.new_workspace)
        self.menu_bar.toggle_theme.connect(self.toggle_theme)
        self.menu_bar.load_dbc.connect(self.load_dbc_file)
        self.menu_bar.show_about.connect(self.show_about)

        # DBC Manager live update: connect dbc_loaded to all message logs/plotters
        def on_dbc_loaded(filename, dbinfo):
            for i in range(self.workspace_tabs.count()):
                data = self.workspace_tabs.tabBar().tabData(i)
                if data:
                    if hasattr(data['message_log'], 'refresh_dbc'):
                        data['message_log'].refresh_dbc()
                    if hasattr(data['signal_plotter'], 'refresh_dbc'):
                        data['signal_plotter'].refresh_dbc()
        self.dbc_manager.dbc_loaded.connect(on_dbc_loaded)

        # Toolbar connections
        self.toolbar.connect_bus.connect(self.handle_can_connect_from_toolbar)
        self.toolbar.disconnect_bus.connect(self.handle_can_disconnect)
        self.toolbar.start_logging.connect(self.start_logging)
        self.toolbar.stop_logging.connect(self.stop_logging)
        self.toolbar.toggle_filters.connect(self.handle_toolbar_toggle_filters)

        # Toolbar navigation buttons (assume these signals exist in ModernToolbar)
        if hasattr(self.toolbar, 'show_message_log'):
            self.toolbar.show_message_log.connect(lambda: self.show_workspace_panel('message_log'))
        if hasattr(self.toolbar, 'show_signal_plotter'):
            self.toolbar.show_signal_plotter.connect(lambda: self.show_workspace_panel('signal_plotter'))
        if hasattr(self.toolbar, 'show_scripting_console'):
            self.toolbar.show_scripting_console.connect(lambda: self.show_workspace_panel('scripting_console'))
        if hasattr(self.toolbar, 'show_diagnostics_panel'):
            self.toolbar.show_diagnostics_panel.connect(lambda: self.show_workspace_panel('diagnostics_panel'))
        
        # UDS Backend global connections
        self.uds_backend.uds_response_received.connect(self.handle_uds_response)
        self.uds_backend.uds_error_occurred.connect(self.handle_uds_error)
        
    def new_workspace(self):
        """Create a new workspace"""
        name = f"Workspace {self.workspace_tabs.count() + 1}"
        self.create_workspace(name)
        
    def close_workspace(self, index):
        """Close a workspace tab"""
        if self.workspace_tabs.count() > 1:
            self.workspace_tabs.removeTab(index)
        
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new_theme)
        
    def apply_theme(self, theme):
        """Apply the selected theme with Windows compatibility"""
        import platform
        self.current_theme = theme
        
        # Apply base theme
        self.style_manager.apply_theme(self, theme)
        
        # Apply Windows-specific enhancements if needed
        if platform.system() == "Windows":
            # Force font for better Windows visibility
            app_font = QFont("Segoe UI", 9)
            QApplication.instance().setFont(app_font)
            
            # Additional Windows-specific styling if needed
            if theme == "light":
                # Ensure maximum contrast on Windows
                additional_style = """
                QWidget {
                    color: #000000;
                }
                QLabel {
                    color: #000000;
                }
                QGroupBox {
                    color: #000000;
                }
                """
                current_style = self.styleSheet()
                self.setStyleSheet(current_style + additional_style)
        
        self.theme_changed.emit(theme)
        self.settings.setValue("theme", theme)
        
    def connect_to_bus(self):
        """Connect to CAN bus"""
        # Implementation would go here
        self.status_bar.set_connection_state(True, "can0", 500)
        
    def disconnect_from_bus(self):
        """Disconnect from CAN bus"""
        # Implementation would go here
        self.status_bar.set_connection_state(False)
        
    def start_logging(self):
        """Start message logging"""
        # Implementation would go here
        self.toolbar.set_logging_state(True)
        
    def stop_logging(self):
        """Stop message logging"""
        # Implementation would go here
        self.toolbar.set_logging_state(False)
        
    def load_dbc_file(self):
        """Load a DBC file and update all relevant UI components"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        filename, _ = QFileDialog.getOpenFileName(self, "Load DBC File", "", "DBC Files (*.dbc)")
        if filename:
            ok, msg = self.dbc_manager.load_dbc_file(filename)
            if ok:
                self.status_bar.show_message(f"DBC loaded: {filename}")
                # Update all message logs and plotters in all workspaces
                for i in range(self.workspace_tabs.count()):
                    data = self.workspace_tabs.tabBar().tabData(i)
                    if data:
                        if hasattr(data['message_log'], 'refresh_dbc'):
                            data['message_log'].refresh_dbc()
                        if hasattr(data['signal_plotter'], 'refresh_dbc'):
                            data['signal_plotter'].refresh_dbc()
                        # Update right sidebar DBC browser with full info including messages
                        if hasattr(data['right_sidebar'], 'load_dbc_file'):
                            # Get full DBC info with messages
                            full_dbc_info = self.dbc_manager.get_database_info(filename)
                            # Add messages manually since get_database_info doesn't include them
                            messages_dict = {}
                            if self.dbc_manager.active_database and hasattr(self.dbc_manager.active_database, 'messages'):
                                db = self.dbc_manager.active_database
                                if isinstance(db.messages, list):
                                    # cantools.db.Database
                                    for message in db.messages:
                                        msg_id = getattr(message, 'frame_id', getattr(message, 'message_id', None))
                                        if msg_id is None:
                                            continue
                                        msg_data = {
                                            'id': msg_id,
                                            'name': getattr(message, 'name', f'Message_{msg_id}'),
                                            'dlc': getattr(message, 'length', 8),
                                            'sender': (message.senders[0] if hasattr(message, 'senders') and message.senders else ''),
                                            'comment': getattr(message, 'comment', ''),
                                            'signals': {}
                                        }
                                        for signal in getattr(message, 'signals', []):
                                            msg_data['signals'][signal.name] = {
                                                'start_bit': getattr(signal, 'start', 0),
                                                'length': getattr(signal, 'length', 1),
                                                'byte_order': 'big_endian' if getattr(signal, 'byte_order', 1) == 0 else 'little_endian',
                                                'value_type': 'signed' if getattr(signal, 'is_signed', False) else 'unsigned',
                                                'factor': getattr(signal, 'scale', 1),
                                                'offset': getattr(signal, 'offset', 0),
                                                'min': getattr(signal, 'minimum', 0),
                                                'max': getattr(signal, 'maximum', 0),
                                                'unit': getattr(signal, 'unit', ''),
                                                'comment': getattr(signal, 'comment', '')
                                            }
                                        messages_dict[msg_id] = msg_data
                            full_dbc_info['messages'] = messages_dict
                            data['right_sidebar'].load_dbc_file(filename, full_dbc_info)
            else:
                QMessageBox.warning(self, "DBC Load Error", msg)

    def show_about(self):
        """Show about dialog"""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(self, "About CAN Analyzer", 
                         "Professional CAN Bus Analyzer v2.0\n\n"
                         "Advanced CAN/CAN FD analysis tool\n"
                         "with DBC integration, diagnostics,\n"
                         "and real-time signal plotting.")
        
    def create_app_icon(self):
        """Create application icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a simple CAN icon
        painter.setBrush(Qt.blue)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(Qt.white)
        painter.drawEllipse(8, 8, 16, 16)
        painter.setBrush(Qt.blue)
        painter.drawEllipse(12, 12, 8, 8)
        
        painter.end()
        return QIcon(pixmap)
        
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
    def restore_settings(self):
        """Restore application settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
            
    def closeEvent(self, event):
        """Handle application close"""
        self.save_settings()
        # Stop all periodic timers in left sidebars before closing
        for i in range(self.workspace_tabs.count()):
            data = self.workspace_tabs.tabBar().tabData(i)
            if data and 'left_sidebar' in data:
                left_sidebar = data['left_sidebar']
                # Stop any periodic transmission
                if hasattr(left_sidebar, 'start_stop_action') and left_sidebar.start_stop_action.isChecked():
                    left_sidebar.toggle_all_periodic(False)
        
        # Disconnect CAN bus and UDS
        self.uds_backend.disconnect()
        self.can_manager.disconnect()
        event.accept()

    # === CAN Backend Event Handlers ===
    
    def handle_can_connect(self, config):
        """Handle CAN connection request from left sidebar"""
        print(f"[DEBUG] handle_can_connect called with: {config}")
        iface = config.get('interface')
        bitrate = config.get('bitrate', 500000)
        driver = config.get('driver', 'socketcan')
        print(f"[DEBUG] Connecting to CAN: {iface} at {bitrate} bps using driver {driver}")
        
        # Pass the driver and other configuration to the CAN manager
        self.can_manager.connect(
            interface=iface, 
            bitrate=bitrate, 
            driver=driver,
            channel=config.get('channel'),
            is_canfd=config.get('is_canfd', False),
            listen_only=config.get('listen_only', False),
            fd_non_iso=config.get('fd_non_iso', False)
        )

    def handle_can_disconnect(self):
        """Handle CAN disconnection request"""
        print("[DEBUG] handle_can_disconnect called")
        # Disconnect UDS first
        if self.uds_backend.is_connected:
            print("[DEBUG] Disconnecting UDS before CAN disconnect")
            self.uds_backend.disconnect()
        # Then disconnect CAN
        print("[DEBUG] Disconnecting CAN bus")
        self.can_manager.disconnect()

    def handle_can_connect_from_toolbar(self):
        """Handle connection request from toolbar - use current workspace's left sidebar config"""
        idx = self.workspace_tabs.currentIndex()
        workspace_data = self.workspace_tabs.tabBar().tabData(idx)
        if workspace_data and 'left_sidebar' in workspace_data:
            left_sidebar = workspace_data['left_sidebar']
            config = left_sidebar.get_current_connection_config()
            if config:
                print(f"[DEBUG] Toolbar connect request: {config}")
                self.handle_can_connect(config)
            else:
                print("[WARNING] No connection config available from left sidebar.")

    def handle_can_send_message(self, msg):
        """Handle message send request from left sidebar"""
        print(f"[DEBUG] handle_can_send_message called with: {msg}")
        try:
            msg_id = msg['id']
            data = msg['data']
            extended = msg.get('extended', False)
            print(f"[DEBUG] Sending CAN message: ID=0x{msg_id:X}, Data={data}, Extended={extended}")
            
            success = self.can_manager.send_message(msg_id, data, extended_id=extended)
            print(f"[DEBUG] CAN send result: {success}")
            
            # Add TX message to current workspace's message log
            tx_msg = {
                'timestamp': time.time(),
                'id': msg_id,
                'dlc': msg['dlc'],
                'data': data,
                'extended': extended,
                'direction': 'TX',
                'channel': self.can_manager.interface or 'unknown'
            }
            print(f"[DEBUG] Logging TX message: {tx_msg}")
            
            # Find the current workspace's message log
            idx = self.workspace_tabs.currentIndex()
            workspace_data = self.workspace_tabs.tabBar().tabData(idx)
            if workspace_data and 'message_log' in workspace_data:
                workspace_data['message_log'].add_message(tx_msg)
                print(f"[DEBUG] TX message added to message log")
            else:
                print("[WARNING] No message log found for current workspace")
                
        except Exception as e:
            print(f"[ERROR] handle_can_send_message: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.show_message(f"Send Error: {e}", 5000)

    def handle_can_message(self, msg, message_log):
        """Handle received CAN message"""
        print(f"[DEBUG] Received CAN message: ID=0x{msg['id']:X}, Data={msg['data']}, DLC={msg['dlc']}")
        # Add RX message to the specific message log
        message_log.add_message(msg)
        print(f"[DEBUG] RX message added to message log")

    def handle_can_state(self, state):
        """Handle CAN bus state change"""
        print(f"[DEBUG] CAN bus state changed: {state}")
        # Update status bar
        connected = state == 'connected'
        if connected:
            self.status_bar.set_connection_state(True, self.can_manager.interface, self.can_manager.bitrate)
            print(f"[DEBUG] CAN bus connected: {self.can_manager.interface} at {self.can_manager.bitrate} bps")
        else:
            self.status_bar.set_connection_state(False)
            print(f"[DEBUG] CAN bus disconnected")
            
        # Update all workspace left sidebars
        for i in range(self.workspace_tabs.count()):
            workspace_data = self.workspace_tabs.tabBar().tabData(i)
            if workspace_data and 'left_sidebar' in workspace_data:
                left_sidebar = workspace_data['left_sidebar']
                left_sidebar.set_connection_state(connected)
                print(f"[DEBUG] Updated left sidebar {i} connection state: {connected}")
                
        # Update toolbar connection state
        self.toolbar.set_connection_state(connected)
        print(f"[DEBUG] Updated toolbar connection state: {connected}")

    def handle_can_error(self, error):
        """Handle CAN backend error"""
        print(f"[ERROR] CAN backend: {error}")
        self.status_bar.show_message(f"CAN Error: {error}", 5000)

    def handle_toolbar_toggle_filters(self, shown):
        """Handle filter panel toggle from toolbar"""
        print(f"[DEBUG] Toggle filters: {shown}")
        # Show/hide the filter panel in the current workspace's message log
        idx = self.workspace_tabs.currentIndex()
        workspace_data = self.workspace_tabs.tabBar().tabData(idx)
        if workspace_data and 'message_log' in workspace_data:
            message_log = workspace_data['message_log']
            if hasattr(message_log, 'filter_panel'):
                message_log.filter_panel.setVisible(shown)
                print(f"[DEBUG] Filter panel visibility set to: {shown}")
    
    # === UDS Backend Event Handlers ===
    
    def handle_uds_connect_request(self, config):
        """Handle UDS connection request from diagnostics panel"""
        print(f"[DEBUG] UDS connect request: {config}")
        try:
            # Extract CAN IDs from config
            tx_id = int(config.get('tx_id', '7E0'), 16)
            rx_id = int(config.get('rx_id', '7E8'), 16)
            print(f"[DEBUG] UDS CAN IDs: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
            
            # Update UDS backend CAN IDs
            self.uds_backend.set_can_ids(tx_id, rx_id)
            
            # Ensure CAN bus is connected
            if not self.can_manager.is_connected:
                print("[DEBUG] CAN bus not connected, cannot connect UDS")
                self.status_bar.show_message("CAN bus must be connected first", 3000)
                return
            
            print(f"[DEBUG] CAN bus is connected, proceeding with UDS connection")
            
            # Connect UDS
            if self.uds_backend.connect():
                print(f"[DEBUG] UDS connection successful")
                self.status_bar.show_message(f"UDS connected: TX=0x{tx_id:X}, RX=0x{rx_id:X}", 3000)
            else:
                print(f"[DEBUG] UDS connection failed")
                self.status_bar.show_message("UDS connection failed", 3000)
                
        except Exception as e:
            print(f"[ERROR] UDS connect error: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.show_message(f"UDS Error: {e}", 5000)
    
    def handle_uds_disconnect_request(self):
        """Handle UDS disconnection request from diagnostics panel"""
        print("[DEBUG] UDS disconnect request")
        try:
            self.uds_backend.disconnect()
            print("[DEBUG] UDS disconnect completed")
            self.status_bar.show_message("UDS disconnected", 3000)
        except Exception as e:
            print(f"[ERROR] UDS disconnect error: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.show_message(f"UDS Disconnect Error: {e}", 5000)
    
    def handle_uds_response(self, response):
        """Handle UDS response for logging in main window"""
        service = response.get('service', 'unknown')
        success = response.get('success', False)
        
        print(f"[DEBUG] UDS Response: {service} - Success={success}")
        if success:
            data = response.get('data', b'')
            print(f"[DEBUG] UDS Response data: {data.hex().upper() if data else 'None'}")
        else:
            error = response.get('error', 'Unknown error')
            print(f"[DEBUG] UDS Response error: {error}")
    
    def handle_uds_error(self, error):
        """Handle UDS error for logging in main window"""
        print(f"[ERROR] UDS Error: {error}")
        self.status_bar.show_message(f"UDS Error: {error}", 5000)

def main():
    """Main application entry point"""
    import platform
    
    # Enable high DPI support on Windows
    if platform.system() == "Windows":
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        # Set DPI awareness for Windows
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_PER_MONITOR_DPI_AWARE
        except:
            pass  # Ignore if not available
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("CAN Bus Analyzer Professional")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Professional Automotive Tools")
    app.setOrganizationDomain("cananalyzer.pro")
    
    # Set Windows-optimized font
    if platform.system() == "Windows":
        font = QFont("Segoe UI", 9)
        app.setFont(font)
    else:
        font = QFont("Segoe UI", 9)
        app.setFont(font)
    
    # Create and show main window
    window = CANAnalyzerMainWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())