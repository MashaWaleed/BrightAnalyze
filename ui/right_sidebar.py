"""
Feature-Rich Right Sidebar for Professional CAN Analyzer
Includes DBC browser, statistics, and documentation panels
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QLabel, QGroupBox,
                               QScrollArea, QTextEdit, QProgressBar, QPushButton,
                               QFormLayout, QLineEdit, QComboBox, QCheckBox,
                               QFrame, QSplitter, QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QIcon

class FeatureRichRightSidebar(QScrollArea):
    """Feature-rich right sidebar with comprehensive functionality"""
    
    # Signals
    dbc_message_selected = Signal(dict)
    signal_selected = Signal(dict)
    export_statistics = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dbc_data = {}
        self.statistics = {}
        self.setup_ui()
        self.setup_timers()
        self.apply_modern_style()
        
    def setup_ui(self):
        """Setup the right sidebar UI"""
        # Create main widget and layout
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create tab widget for different panels
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.East)
        
        # DBC Browser Tab
        self.setup_dbc_browser_tab()
        
        # Statistics Tab
        self.setup_statistics_tab()
        
        # Documentation Tab
        self.setup_documentation_tab()
        
        # System Monitor Tab
        self.setup_system_monitor_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Set the widget for the scroll area
        self.setWidget(main_widget)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
    def setup_dbc_browser_tab(self):
        """Setup DBC browser tab"""
        dbc_widget = QWidget()
        layout = QVBoxLayout(dbc_widget)
        layout.setSpacing(8)
        
        # DBC file info
        info_group = QGroupBox("📁 DBC File Information")
        info_layout = QFormLayout(info_group)
        
        self.dbc_filename_label = QLabel("No file loaded")
        self.dbc_version_label = QLabel("-")
        self.dbc_messages_label = QLabel("0")
        self.dbc_signals_label = QLabel("0")
        
        info_layout.addRow("Filename:", self.dbc_filename_label)
        info_layout.addRow("Version:", self.dbc_version_label)
        info_layout.addRow("Messages:", self.dbc_messages_label)
        info_layout.addRow("Signals:", self.dbc_signals_label)
        
        layout.addWidget(info_group)
        
        # Message browser
        browser_group = QGroupBox("🌲 Message Browser")
        browser_layout = QVBoxLayout(browser_group)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.dbc_search_edit = QLineEdit()
        self.dbc_search_edit.setPlaceholderText("Search messages...")
        self.dbc_search_edit.textChanged.connect(self.filter_dbc_tree)
        search_layout.addWidget(self.dbc_search_edit)
        browser_layout.addLayout(search_layout)
        
        # Tree widget for messages and signals
        self.dbc_tree = QTreeWidget()
        self.dbc_tree.setHeaderLabels(["Name", "ID", "Info"])
        self.dbc_tree.itemClicked.connect(self.on_dbc_item_clicked)
        browser_layout.addWidget(self.dbc_tree)
        
        layout.addWidget(browser_group)
        
        # Message details
        details_group = QGroupBox("📋 Message Details")
        details_layout = QVBoxLayout(details_group)
        
        self.message_details = QTextEdit()
        self.message_details.setMaximumHeight(150)
        self.message_details.setReadOnly(True)
        details_layout.addWidget(self.message_details)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        self.send_msg_btn = QPushButton("📤 Send")
        self.send_msg_btn.setEnabled(False)
        self.copy_msg_btn = QPushButton("📋 Copy")
        self.copy_msg_btn.setEnabled(False)
        
        actions_layout.addWidget(self.send_msg_btn)
        actions_layout.addWidget(self.copy_msg_btn)
        details_layout.addLayout(actions_layout)
        
        layout.addWidget(details_group)
        layout.addStretch()
        
        self.tab_widget.addTab(dbc_widget, "🗃️\nDBC")
        
    def setup_statistics_tab(self):
        """Setup statistics tab"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        layout.setSpacing(8)
        
        # Real-time statistics
        realtime_group = QGroupBox("📊 Real-time Statistics")
        realtime_layout = QFormLayout(realtime_group)
        
        self.total_messages_label = QLabel("0")
        self.messages_per_sec_label = QLabel("0.0")
        self.bus_load_label = QLabel("0%")
        self.error_rate_label = QLabel("0.0%")
        
        realtime_layout.addRow("Total Messages:", self.total_messages_label)
        realtime_layout.addRow("Messages/sec:", self.messages_per_sec_label)
        realtime_layout.addRow("Bus Load:", self.bus_load_label)
        realtime_layout.addRow("Error Rate:", self.error_rate_label)
        
        layout.addWidget(realtime_group)
        
        # Bus load visualization
        load_group = QGroupBox("📈 Bus Load")
        load_layout = QVBoxLayout(load_group)
        
        self.bus_load_bar = QProgressBar()
        self.bus_load_bar.setRange(0, 100)
        self.bus_load_bar.setValue(0)
        self.bus_load_bar.setFormat("%p%")
        load_layout.addWidget(self.bus_load_bar)
        
        # Load history (simplified representation)
        self.load_history_label = QLabel("Load History: ▁▂▃▂▄▅▆▅▄▃▂▁")
        self.load_history_label.setFont(QFont("Consolas", 12))
        load_layout.addWidget(self.load_history_label)
        
        layout.addWidget(load_group)
        
        # Message ID statistics
        id_stats_group = QGroupBox("🏷️ Message ID Statistics")
        id_stats_layout = QVBoxLayout(id_stats_group)
        
        self.id_stats_table = QTableWidget(0, 3)
        self.id_stats_table.setHorizontalHeaderLabels(["ID", "Count", "Rate"])
        self.id_stats_table.horizontalHeader().setStretchLastSection(True)
        self.id_stats_table.setMaximumHeight(200)
        id_stats_layout.addWidget(self.id_stats_table)
        
        layout.addWidget(id_stats_group)
        
        # Export button
        export_layout = QHBoxLayout()
        self.export_stats_btn = QPushButton("📤 Export Statistics")
        self.export_stats_btn.clicked.connect(self.export_statistics.emit)
        export_layout.addWidget(self.export_stats_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)
        
        layout.addStretch()
        
        self.tab_widget.addTab(stats_widget, "📊\nStats")
        
    def setup_documentation_tab(self):
        """Setup documentation tab"""
        docs_widget = QWidget()
        layout = QVBoxLayout(docs_widget)
        layout.setSpacing(8)
        
        # Quick help
        help_group = QGroupBox("❓ Quick Help")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(200)
        help_text.setHtml("""
        <h3>Quick Start Guide</h3>
        <p><b>1. Connect to CAN Bus:</b><br>
        Configure interface in left sidebar, then click Connect.</p>
        
        <p><b>2. Load DBC File:</b><br>
        File → Load DBC File to enable message decoding.</p>
        
        <p><b>3. Send Messages:</b><br>
        Use Transmit tab to send CAN messages.</p>
        
        <p><b>4. Filter Messages:</b><br>
        Use filters in message log to find specific messages.</p>
        """)
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_group)
        
        # Keyboard shortcuts
        shortcuts_group = QGroupBox("⌨️ Keyboard Shortcuts")
        shortcuts_layout = QVBoxLayout(shortcuts_group)
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_text.setMaximumHeight(150)
        shortcuts_text.setPlainText("""
Ctrl+O    - Open DBC File
Ctrl+S    - Save Project
Ctrl+L    - Clear Log
Ctrl+F    - Find Message
Ctrl+G    - Message Generator
F1        - Help
F2        - Toggle Filters
F5        - Refresh
        """)
        shortcuts_text.setFont(QFont("Consolas", 9))
        shortcuts_layout.addWidget(shortcuts_text)
        
        layout.addWidget(shortcuts_group)
        
        # About section
        about_group = QGroupBox("ℹ️ About")
        about_layout = QVBoxLayout(about_group)
        
        about_text = QLabel("""
        <b>Professional CAN Analyzer v2.0</b><br>
        <br>
        A comprehensive CAN bus analysis tool<br>
        with professional features inspired by<br>
        Vector CANoe and TSMaster.<br>
        <br>
        Built with PySide6 and Python-CAN<br>
        """)
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        
        layout.addWidget(about_group)
        layout.addStretch()
        
        self.tab_widget.addTab(docs_widget, "📚\nDocs")
        
    def setup_system_monitor_tab(self):
        """Setup system monitor tab"""
        monitor_widget = QWidget()
        layout = QVBoxLayout(monitor_widget)
        layout.setSpacing(8)
        
        # System performance
        perf_group = QGroupBox("💻 System Performance")
        perf_layout = QFormLayout(perf_group)
        
        # CPU usage
        cpu_layout = QHBoxLayout()
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(25)
        self.cpu_label = QLabel("25%")
        cpu_layout.addWidget(self.cpu_progress, 3)
        cpu_layout.addWidget(self.cpu_label, 1)
        perf_layout.addRow("CPU:", cpu_layout)
        
        # Memory usage
        mem_layout = QHBoxLayout()
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        self.memory_progress.setValue(45)
        self.memory_label = QLabel("45%")
        mem_layout.addWidget(self.memory_progress, 3)
        mem_layout.addWidget(self.memory_label, 1)
        perf_layout.addRow("Memory:", mem_layout)
        
        layout.addWidget(perf_group)
        
        # Interface status
        interface_group = QGroupBox("🔌 Interface Status")
        interface_layout = QFormLayout(interface_group)
        
        self.interface_status_label = QLabel("Disconnected")
        self.interface_driver_label = QLabel("-")
        self.interface_bitrate_label = QLabel("-")
        self.interface_errors_label = QLabel("0")
        
        interface_layout.addRow("Status:", self.interface_status_label)
        interface_layout.addRow("Driver:", self.interface_driver_label)
        interface_layout.addRow("Bitrate:", self.interface_bitrate_label)
        interface_layout.addRow("Errors:", self.interface_errors_label)
        
        layout.addWidget(interface_group)
        
        # Application log
        log_group = QGroupBox("📝 Application Log")
        log_layout = QVBoxLayout(log_group)
        
        self.app_log = QTextEdit()
        self.app_log.setMaximumHeight(150)
        self.app_log.setReadOnly(True)
        self.app_log.setFont(QFont("Consolas", 8))
        log_layout.addWidget(self.app_log)
        
        # Add some sample log entries
        self.app_log.append("[INFO] Application started")
        self.app_log.append("[INFO] UI initialized successfully")
        self.app_log.append("[DEBUG] Style manager loaded")
        
        log_layout.addWidget(self.app_log)
        
        layout.addWidget(log_group)
        layout.addStretch()
        
        self.tab_widget.addTab(monitor_widget, "🖥️\nSystem")
        
    def setup_timers(self):
        """Setup update timers"""
        # Statistics update timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(1000)  # Update every second
        
        # System monitor update timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_system_monitor)
        self.monitor_timer.start(2000)  # Update every 2 seconds
        
    def load_dbc_file(self, filename, dbc_data):
        """Load DBC file data into the browser"""
        print(f"[DEBUG] RightSidebar.load_dbc_file called with filename={filename}")
        print(f"[DEBUG] dbc_data keys: {list(dbc_data.keys())}")
        print(f"[DEBUG] dbc_data: {dbc_data}")
        
        # Store the DBC data
        self.dbc_data = dbc_data
        
        # Update DBC info display using individual labels
        filename = dbc_data.get('filename', 'Unknown')
        # Extract just the filename from full path
        import os
        display_filename = os.path.basename(filename) if filename else 'Unknown'
        version = dbc_data.get('version', 'N/A')
        message_count = dbc_data.get('message_count', 0)
        signal_count = dbc_data.get('signal_count', 0)
        
        # Update individual labels
        self.dbc_filename_label.setText(display_filename)
        self.dbc_version_label.setText(version if version else 'N/A')
        self.dbc_messages_label.setText(str(message_count))
        self.dbc_signals_label.setText(str(signal_count))
        
        # Populate tree
        self.populate_dbc_tree()
        
    def populate_dbc_tree(self):
        """Populate the DBC tree with messages and signals"""
        print("[DEBUG] populate_dbc_tree called")
        self.dbc_tree.clear()
        ecus = self.dbc_data.get('ecus', {})
        if hasattr(self, 'app_log'):
            self.app_log.append(f"[DEBUG] ECUs: {ecus}")
        # Defensive: check for messages key
        messages = self.dbc_data.get('messages', None)
        if messages is None or not isinstance(messages, dict) or not messages:
            print("[WARNING] No 'messages' key or empty messages in dbc_data! Nothing will be shown in browser.")
            if hasattr(self, 'app_log'):
                self.app_log.append("[WARNING] No 'messages' key or empty messages in dbc_data! Nothing will be shown in browser.")
            # Optionally, show a dummy node for debugging
            dummy_item = QTreeWidgetItem(["No messages in DBC", "", ""])
            dummy_item.setIcon(0, self.create_icon("❗"))
            self.dbc_tree.addTopLevelItem(dummy_item)
            return
        # Handle ecus as dict (normal) or list/empty (fallback)
        if isinstance(ecus, dict) and ecus:
            for ecu_name, ecu_data in ecus.items():
                print(f"[DEBUG] Adding ECU node: {ecu_name}")
                if hasattr(self, 'app_log'):
                    self.app_log.append(f"[DEBUG] Adding ECU node: {ecu_name}")
                ecu_item = QTreeWidgetItem([ecu_name, "", "ECU"])
                ecu_item.setIcon(0, self.create_icon("🖥️"))
                self.dbc_tree.addTopLevelItem(ecu_item)
                # Add messages for this ECU
                for msg_id, message in messages.items():
                    if message.get('sender') == ecu_name:
                        print(f"[DEBUG] Adding message {message.get('name')} under ECU {ecu_name}")
                        if hasattr(self, 'app_log'):
                            self.app_log.append(f"[DEBUG] Adding message {message.get('name')} under ECU {ecu_name}")
                        msg_item = QTreeWidgetItem([
                            message.get('name', f'Message_{msg_id}'),
                            f"0x{msg_id:03X}",
                            f"DLC: {message.get('dlc', 8)}"
                        ])
                        msg_item.setIcon(0, self.create_icon("📨"))
                        msg_item.setData(0, Qt.UserRole, {'type': 'message', 'data': message, 'id': msg_id})
                        ecu_item.addChild(msg_item)
                        # Add signals for this message
                        signals = message.get('signals', {})
                        for signal_name, signal in signals.items():
                            print(f"[DEBUG]   Adding signal {signal_name}")
                            if hasattr(self, 'app_log'):
                                self.app_log.append(f"[DEBUG]   Adding signal {signal_name}")
                            signal_item = QTreeWidgetItem([
                                signal_name,
                                f"{signal.get('start_bit', 0)}:{signal.get('length', 1)}",
                                signal.get('unit', '')
                            ])
                            signal_item.setIcon(0, self.create_icon("📊"))
                            signal_item.setData(0, Qt.UserRole, {'type': 'signal', 'data': signal, 'name': signal_name})
                            msg_item.addChild(signal_item)
        else:
            print("[DEBUG] No ECUs found or ECUs not a dict; will add messages without ECUs if present.")
            if hasattr(self, 'app_log'):
                self.app_log.append("[DEBUG] No ECUs found or ECUs not a dict; will add messages without ECUs if present.")
            for msg_id, message in messages.items():
                print(f"[DEBUG] Adding message {message.get('name')} at top level")
                if hasattr(self, 'app_log'):
                    self.app_log.append(f"[DEBUG] Adding message {message.get('name')} at top level")
                msg_item = QTreeWidgetItem([
                    message.get('name', f'Message_{msg_id}'),
                    f"0x{msg_id:03X}",
                    f"DLC: {message.get('dlc', 8)}"
                ])
                msg_item.setIcon(0, self.create_icon("📨"))
                msg_item.setData(0, Qt.UserRole, {'type': 'message', 'data': message, 'id': msg_id})
                self.dbc_tree.addTopLevelItem(msg_item)
                signals = message.get('signals', {})
                for signal_name, signal in signals.items():
                    print(f"[DEBUG]   Adding signal {signal_name}")
                    if hasattr(self, 'app_log'):
                        self.app_log.append(f"[DEBUG]   Adding signal {signal_name}")
                    signal_item = QTreeWidgetItem([
                        signal_name,
                        f"{signal.get('start_bit', 0)}:{signal.get('length', 1)}",
                        signal.get('unit', '')
                    ])
                    signal_item.setIcon(0, self.create_icon("📊"))
                    signal_item.setData(0, Qt.UserRole, {'type': 'signal', 'data': signal, 'name': signal_name})
                    msg_item.addChild(signal_item)



        # If no ECUs, add messages at top level
        if not ecus:
            messages = self.dbc_data.get('messages', {})
            for msg_id, message in messages.items():
                print(f"[DEBUG] Adding message {message.get('name')} at top level")
                if hasattr(self, 'app_log'):
                    self.app_log.append(f"[DEBUG] Adding message {message.get('name')} at top level")
                msg_item = QTreeWidgetItem([
                    message.get('name', f'Message_{msg_id}'),
                    f"0x{msg_id:03X}",
                    f"DLC: {message.get('dlc', 8)}"
                ])
                msg_item.setIcon(0, self.create_icon("📨"))
                msg_item.setData(0, Qt.UserRole, {'type': 'message', 'data': message, 'id': msg_id})
                self.dbc_tree.addTopLevelItem(msg_item)
                signals = message.get('signals', {})
                for signal_name, signal in signals.items():
                    print(f"[DEBUG]   Adding signal {signal_name}")
                    if hasattr(self, 'app_log'):
                        self.app_log.append(f"[DEBUG]   Adding signal {signal_name}")
                    signal_item = QTreeWidgetItem([
                        signal_name,
                        f"{signal.get('start_bit', 0)}:{signal.get('length', 1)}",
                        signal.get('unit', '')
                    ])
                    signal_item.setIcon(0, self.create_icon("📊"))
                    signal_item.setData(0, Qt.UserRole, {'type': 'signal', 'data': signal, 'name': signal_name})
                    msg_item.addChild(signal_item)
        # Expand first level
        for i in range(self.dbc_tree.topLevelItemCount()):
            self.dbc_tree.topLevelItem(i).setExpanded(True)

            
    def create_icon(self, emoji):
        """Create a simple icon from emoji (placeholder)"""
        # In a real implementation, you'd create proper QIcon objects
        return QIcon()
        
    def filter_dbc_tree(self, text):
        """Filter DBC tree based on search text"""
        # Simple filtering implementation
        for i in range(self.dbc_tree.topLevelItemCount()):
            ecu_item = self.dbc_tree.topLevelItem(i)
            ecu_visible = False
            
            for j in range(ecu_item.childCount()):
                msg_item = ecu_item.child(j)
                msg_name = msg_item.text(0).lower()
                msg_visible = text.lower() in msg_name if text else True
                msg_item.setHidden(not msg_visible)
                
                if msg_visible:
                    ecu_visible = True
                    
            ecu_item.setHidden(not ecu_visible)
            
    def on_dbc_item_clicked(self, item, column):
        """Handle DBC tree item selection"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return
            
        if item_data['type'] == 'message':
            message = item_data['data']
            msg_id = item_data['id']
            
            # Update details panel
            details = f"Message: {message.get('name', 'Unknown')}\n"
            details += f"ID: 0x{msg_id:03X} ({msg_id})\n"
            details += f"DLC: {message.get('dlc', 8)}\n"
            details += f"Sender: {message.get('sender', 'Unknown')}\n"
            details += f"Cycle Time: {message.get('cycle_time', 'N/A')} ms\n"
            details += f"Comment: {message.get('comment', 'No comment')}\n"
            
            self.message_details.setPlainText(details)
            self.send_msg_btn.setEnabled(True)
            self.copy_msg_btn.setEnabled(True)
            
            # Emit signal
            self.dbc_message_selected.emit({
                'id': msg_id,
                'name': message.get('name'),
                'dlc': message.get('dlc', 8),
                'signals': message.get('signals', {})
            })
            
        elif item_data['type'] == 'signal':
            signal = item_data['data']
            signal_name = item_data['name']
            
            # Update details panel
            details = f"Signal: {signal_name}\n"
            details += f"Start Bit: {signal.get('start_bit', 0)}\n"
            details += f"Length: {signal.get('length', 1)} bits\n"
            details += f"Byte Order: {signal.get('byte_order', 'Little Endian')}\n"
            details += f"Value Type: {signal.get('value_type', 'Unsigned')}\n"
            details += f"Factor: {signal.get('factor', 1)}\n"
            details += f"Offset: {signal.get('offset', 0)}\n"
            details += f"Min: {signal.get('min', 0)}\n"
            details += f"Max: {signal.get('max', 0)}\n"
            details += f"Unit: {signal.get('unit', '')}\n"
            
            self.message_details.setPlainText(details)
            self.send_msg_btn.setEnabled(False)
            self.copy_msg_btn.setEnabled(True)
            
            # Emit signal
            self.signal_selected.emit({
                'name': signal_name,
                'data': signal
            })
            
    def update_statistics(self):
        """Update statistics displays"""
        # Update real-time stats (placeholder values)
        import random
        
        # Simulate some changing values
        self.messages_per_sec_label.setText(f"{random.uniform(0, 50):.1f}")
        
        bus_load = random.randint(0, 100)
        self.bus_load_label.setText(f"{bus_load}%")
        self.bus_load_bar.setValue(bus_load)
        
        error_rate = random.uniform(0, 5)
        self.error_rate_label.setText(f"{error_rate:.2f}%")
        
        # Update load history visualization
        history_chars = "▁▂▃▄▅▆▇█"
        history = "".join(random.choice(history_chars) for _ in range(12))
        self.load_history_label.setText(f"Load History: {history}")
        
    def update_system_monitor(self):
        """Update system monitor displays"""
        import random
        
        # Update CPU usage
        cpu_value = random.randint(20, 80)
        self.cpu_progress.setValue(cpu_value)
        self.cpu_label.setText(f"{cpu_value}%")
        
        # Update memory usage
        mem_value = random.randint(30, 70)
        self.memory_progress.setValue(mem_value)
        self.memory_label.setText(f"{mem_value}%")
        
    def set_interface_status(self, connected, driver="", bitrate=0, errors=0):
        """Update interface status"""
        if connected:
            self.interface_status_label.setText("✅ Connected")
            self.interface_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.interface_status_label.setText("❌ Disconnected")
            self.interface_status_label.setStyleSheet("color: red; font-weight: bold;")
            
        self.interface_driver_label.setText(driver)
        self.interface_bitrate_label.setText(f"{bitrate} kbps" if bitrate > 0 else "-")
        self.interface_errors_label.setText(str(errors))
        
    def add_log_entry(self, level, message):
        """Add entry to application log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.app_log.append(log_entry)
        
        # Scroll to bottom
        self.app_log.verticalScrollBar().setValue(
            self.app_log.verticalScrollBar().maximum()
        )
        
    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 4px;
            }
            
            QTabBar::tab {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 12px 8px;
                margin-bottom: 2px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                writing-mode: vertical-lr;
                text-orientation: mixed;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                border-left: 1px solid white;
                font-weight: bold;
            }
            
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin: 8px 0;
                padding-top: 12px;
                background-color: #fafafa;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            
            QTreeWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            
            QTreeWidget::item {
                padding: 4px;
                border: none;
            }
            
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
                background-color: #f8f9fa;
            }
            
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)