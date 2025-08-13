"""
Professional Message Log for CAN Analyzer
Advanced message display with filtering and analysis
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
                               QLabel, QComboBox, QCheckBox, QSplitter, QTextEdit,
                               QGroupBox, QFormLayout, QSpinBox, QFrame)
from PySide6.QtCore import Signal, Qt, QTimer, QThread
from PySide6.QtGui import QFont, QColor, QPalette
import time
from datetime import datetime

class MessageData:
    """Data structure for CAN messages"""
    def __init__(self, timestamp, msg_id, dlc, data, direction="RX", flags="", extended=False, channel=""):
        self.timestamp = timestamp
        self.msg_id = msg_id
        self.dlc = dlc
        self.data = data
        self.direction = direction
        self.flags = flags
        self.extended = extended
        self.channel = channel
        self.count = 1

class ProfessionalMessageLog(QWidget):
    """Professional message log with advanced features"""

    def refresh_dbc(self):
        """Refresh DBC decoding for all messages when DBC changes."""
        if not hasattr(self, 'dbc_manager'):
            return
        for msg in self.messages:
            if hasattr(self, 'dbc_manager') and self.dbc_manager:
                try:
                    decoded = self.dbc_manager.decode_can_message(msg.msg_id, msg.data)
                    msg.decoded_signals = decoded
                except Exception:
                    msg.decoded_signals = None
            else:
                msg.decoded_signals = None
        self.apply_filters()
    
    # Signals
    message_selected = Signal(dict)
    filter_changed = Signal(dict)
    export_requested = Signal()
    
    def __init__(self, parent=None, dbc_manager=None):
        super().__init__(parent)
        self.dbc_manager = dbc_manager
        self.messages = []
        self.filtered_messages = []
        self.max_messages = 100
        self.auto_scroll = True
        self.filters = {
            'id_filter': '',
            'data_filter': '',
            'direction_filter': 'All',
            'show_duplicates': True
        }
        
        # Group by ID feature (CANoe-style)
        self.group_by_id_enabled = False
        self.grouped_messages = {}  # Dict to store latest message for each ID
        
        self.setup_ui()
        self.setup_timers()
        self.apply_professional_style()
        
    def setup_ui(self):
        """Setup the message log UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create filter panel
        self.filter_panel = self.create_filter_panel()
        layout.addWidget(self.filter_panel)
        
        # Create main splitter for message view
        splitter = QSplitter(Qt.Vertical)
        
        # Message table
        self.create_message_table()
        splitter.addWidget(self.message_table)
        
        # Message details panel
        self.details_panel = self.create_details_panel()
        splitter.addWidget(self.details_panel)
        
        # Set initial splitter sizes (80% table, 20% details)
        splitter.setSizes([800, 200])
        layout.addWidget(splitter)
        
        # Control panel
        self.control_panel = self.create_control_panel()
        layout.addWidget(self.control_panel)
        
    def create_filter_panel(self):
        """Create message filtering panel"""
        panel = QGroupBox("🔍 Message Filters")
        layout = QHBoxLayout(panel)
        layout.setSpacing(12)
        
        # ID filter
        layout.addWidget(QLabel("ID:"))
        self.id_filter_edit = QLineEdit()
        self.id_filter_edit.setPlaceholderText("0x123, 123-456, *ECU*")
        self.id_filter_edit.textChanged.connect(self.update_filters)
        layout.addWidget(self.id_filter_edit)
        
        # Data filter
        layout.addWidget(QLabel("Data:"))
        self.data_filter_edit = QLineEdit()
        self.data_filter_edit.setPlaceholderText("DE AD BE EF")
        self.data_filter_edit.textChanged.connect(self.update_filters)
        layout.addWidget(self.data_filter_edit)
        
        # Direction filter
        layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["All", "TX", "RX"])
        self.direction_combo.currentTextChanged.connect(self.update_filters)
        layout.addWidget(self.direction_combo)
        
        # Options
        self.show_duplicates_cb = QCheckBox("Show Duplicates")
        self.show_duplicates_cb.setChecked(True)
        self.show_duplicates_cb.toggled.connect(self.update_filters)
        layout.addWidget(self.show_duplicates_cb)
        
        # Group by ID toggle (CANoe-style)
        self.group_by_id_cb = QCheckBox("📊 Group by ID")
        self.group_by_id_cb.setChecked(False)
        self.group_by_id_cb.setToolTip("CANoe-style view: Show only latest data for each ID with real-time signal updates")
        self.group_by_id_cb.toggled.connect(self.toggle_group_by_id)
        layout.addWidget(self.group_by_id_cb)
        
        # Quick filters
        layout.addWidget(self.create_separator())
        
        quick_btn_layout = QHBoxLayout()
        quick_btn_layout.setSpacing(4)
        
        self.clear_filters_btn = QPushButton("Clear")
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        quick_btn_layout.addWidget(self.clear_filters_btn)
        
        self.save_filter_btn = QPushButton("Save")
        self.save_filter_btn.clicked.connect(self.save_current_filter)
        quick_btn_layout.addWidget(self.save_filter_btn)
        
        layout.addLayout(quick_btn_layout)
        layout.addStretch()
        
        return panel
        
    def create_message_table(self):
        """Create the main message table"""
        self.message_table = QTableWidget(0, 8)
        
        # Set headers - add DBC column
        headers = ["#", "Timestamp", "ID", "Name", "DLC", "Data", "Dir", "DBC"]
        self.message_table.setHorizontalHeaderLabels(headers)
        
        # Configure table
        header = self.message_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # #
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Name
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # DLC
        header.setSectionResizeMode(5, QHeaderView.Stretch)          # Data
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Dir
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # DBC
        
        # Configure selection
        self.message_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.message_table.setAlternatingRowColors(True)
        
        # Connect signals
        self.message_table.itemSelectionChanged.connect(self.on_message_selected)
        
        # Set font to monospace for better readability
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.message_table.setFont(font)
        
    def create_details_panel(self):
        """Create message details panel"""
        panel = QGroupBox("📋 Message Details")
        layout = QHBoxLayout(panel)
        
        # Left side - message info
        info_widget = QWidget()
        info_layout = QFormLayout(info_widget)
        
        self.detail_id_label = QLabel("-")
        self.detail_dlc_label = QLabel("-")
        self.detail_direction_label = QLabel("-")
        self.detail_timestamp_label = QLabel("-")
        self.detail_count_label = QLabel("-")
        
        info_layout.addRow("Message ID:", self.detail_id_label)
        info_layout.addRow("DLC:", self.detail_dlc_label)
        info_layout.addRow("Direction:", self.detail_direction_label)
        info_layout.addRow("Timestamp:", self.detail_timestamp_label)
        info_layout.addRow("Count:", self.detail_count_label)
        
        layout.addWidget(info_widget)
        
        # Right side - data breakdown
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        
        data_layout.addWidget(QLabel("Data Bytes:"))
        self.data_text = QTextEdit()
        self.data_text.setMaximumHeight(80)
        self.data_text.setFont(QFont("Consolas", 10))
        data_layout.addWidget(self.data_text)
        
        layout.addWidget(data_widget)
        
        # DBC Signals section (CANoe/TSMaster style)
        dbc_widget = QWidget()
        dbc_layout = QVBoxLayout(dbc_widget)
        
        dbc_layout.addWidget(QLabel("DBC Signals:"))
        self.dbc_signals_text = QTextEdit()
        self.dbc_signals_text.setMaximumHeight(120)
        self.dbc_signals_text.setFont(QFont("Consolas", 9))
        self.dbc_signals_text.setPlaceholderText("Select a message with DBC data to view decoded signals...")
        dbc_layout.addWidget(self.dbc_signals_text)
        
        layout.addWidget(dbc_widget)
        
        return panel
        
    def create_control_panel(self):
        """Create message log controls"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 0)
        
        # Statistics
        self.stats_label = QLabel("Messages: 0 | Filtered: 0 | Rate: 0.0 msg/s")
        self.stats_label.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
        
        # Controls
        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(True)
        self.autoscroll_cb.toggled.connect(self.set_auto_scroll)
        layout.addWidget(self.autoscroll_cb)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_messages)
        layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_btn)
        
        # Max messages spinner
        layout.addWidget(QLabel("Max:"))
        self.max_messages_spin = QSpinBox()
        self.max_messages_spin.setRange(100, 100000)
        self.max_messages_spin.setValue(self.max_messages)
        self.max_messages_spin.setSuffix(" msgs")
        self.max_messages_spin.valueChanged.connect(self.set_max_messages)
        layout.addWidget(self.max_messages_spin)
        
        return panel
        
    def create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        return separator
        
    def setup_timers(self):
        """Setup update timers"""
        # Statistics update timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(1000)  # Update every second
        
        # Filter update timer (batch processing for efficiency)
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.apply_filters)
        self.filter_update_pending = False
        
        # Message rate calculation
        self.last_message_count = 0

    def add_message(self, message_data):
        """Add a new message to the log - accepts both dict and individual parameters. Decodes with DBC if available."""
        print(f"[DEBUG] add_message called with: {message_data}")
        
        # Handle both dictionary input and individual parameters
        if isinstance(message_data, dict):
            # Extract data from dictionary format (from CAN backend)
            msg_id = message_data.get('id', 0)
            # Ensure msg_id is always int for formatting (fix TX bug)
            if isinstance(msg_id, str):
                if msg_id.startswith('0x') or msg_id.startswith('0X'):
                    try:
                        msg_id = int(msg_id, 16)
                    except Exception:
                        msg_id = 0
                else:
                    try:
                        msg_id = int(msg_id)
                    except Exception:
                        msg_id = 0
            dlc = message_data.get('dlc', 0)
            data = message_data.get('data', [])
            direction = message_data.get('direction', 'RX')
            timestamp = message_data.get('timestamp', time.time())
            extended = message_data.get('extended', False)
            channel = message_data.get('channel', '')
            
            # Format timestamp if it's a float
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        else:
            # Legacy individual parameter support
            msg_id = message_data
            # This shouldn't happen with current code but keeping for compatibility
            print("[WARNING] Legacy add_message call format used")
            return
            
        # Ensure data is a list of integers
        if isinstance(data, (list, tuple)):
            data = [int(b) for b in data]
        else:
            data = []
            
        print(f"[DEBUG] Processing message - ID: 0x{msg_id:X}, DLC: {dlc}, Data: {data}, Dir: {direction}")
        
        # DBC decode if available
        decoded_signals = None
        try:
            from ui.dbc_manager import DBCManager
            # Assume a singleton or global instance is available as self.dbc_manager
            if hasattr(self, 'dbc_manager') and self.dbc_manager is not None:
                decoded_signals = self.dbc_manager.decode_can_message(msg_id, data)
        except Exception as e:
            print(f"[DEBUG] DBC decode failed: {e}")
            decoded_signals = None
        
        # Create message data object, attach decoded signals
        message = MessageData(timestamp, msg_id, dlc, data, direction, "", extended, channel)
        message.decoded_signals = decoded_signals
        
        # Check for duplicates if not showing them
        if not self.filters['show_duplicates']:
            for existing_msg in reversed(self.messages[-10:]):  # Check last 10 messages
                if (existing_msg.msg_id == msg_id and 
                    existing_msg.data == data and 
                    existing_msg.direction == direction):
                    existing_msg.count += 1
                    self.update_message_in_table(existing_msg)
                    return
                    
        # Add to message list
        self.messages.append(message)
        print(f"[DEBUG] Total messages now: {len(self.messages)}")
        
        # Handle Group by ID mode - update grouped messages in real-time
        if self.group_by_id_enabled:
            # Update or add to grouped messages
            self.grouped_messages[msg_id] = message
            print(f"[DEBUG] Updated grouped message for ID 0x{msg_id:X} in real-time")
        
        # Trim messages if over limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
            
        # Schedule a filter update (batch processing for efficiency)
        self.schedule_filter_update()

        
    def update_message_in_table(self, message):
        """Update an existing message in the table"""
        # Find the message in the table and update count
        for row in range(self.message_table.rowCount()):
            id_item = self.message_table.item(row, 2)
            if id_item and id_item.data(Qt.UserRole) == message:
                count_item = self.message_table.item(row, 7)
                if count_item:
                    count_item.setText(str(message.count))
                break
                
    def apply_filters(self):
        """Apply current filters to messages"""
        if self.group_by_id_enabled:
            # Use grouped messages (CANoe-style view)
            source_messages = list(self.grouped_messages.values())
            print(f"[DEBUG] Applying filters to {len(source_messages)} grouped messages")
        else:
            # Use all messages (normal view)
            source_messages = self.messages
            print(f"[DEBUG] Applying filters to {len(source_messages)} messages")
            
        self.filtered_messages = []
        
        for message in source_messages:
            if self.message_matches_filters(message):
                self.filtered_messages.append(message)
                
        print(f"[DEBUG] After filtering: {len(self.filtered_messages)} messages")
        self.update_table_display()
        self.filter_update_pending = False
        
    def schedule_filter_update(self):
        """Schedule a filter update with batching for efficiency."""
        if not self.filter_update_pending:
            self.filter_update_pending = True
            self.filter_timer.start(50)  # 50ms delay for batching
        
    def message_matches_filters(self, message):
        """Check if message matches current filters"""
        # ID filter
        if self.filters['id_filter']:
            id_filter = self.filters['id_filter'].lower()
            msg_id_str = f"0x{message.msg_id:X}".lower()
            if id_filter not in msg_id_str:
                return False
                
        # Data filter
        if self.filters['data_filter']:
            data_filter = self.filters['data_filter'].replace(" ", "").lower()
            data_str = "".join(f"{b:02X}" for b in message.data).lower()
            if data_filter not in data_str:
                return False
                
        # Direction filter
        if self.filters['direction_filter'] != "All":
            if message.direction != self.filters['direction_filter']:
                return False
                
        return True
        
    def update_table_display(self):
        """Update the table with filtered messages"""
        print(f"[DEBUG] Updating table display with {len(self.filtered_messages)} messages")
        
        # Clear existing rows
        self.message_table.setRowCount(0)
        
        # Add filtered messages
        for i, message in enumerate(self.filtered_messages):
            self.add_message_to_table(i, message)
            
        # Auto-scroll to bottom if enabled
        if self.auto_scroll:
            self.message_table.scrollToBottom()
            
        print(f"[DEBUG] Table now has {self.message_table.rowCount()} rows")
            
    def add_message_to_table(self, row, message):
        """Add a message to the table with DBC info display (CANoe/TSMaster style)."""
        self.message_table.insertRow(row)
        
        # Row number
        row_num_item = QTableWidgetItem(str(row + 1))
        self.message_table.setItem(row, 0, row_num_item)
        
        # Timestamp
        self.message_table.setItem(row, 1, QTableWidgetItem(str(message.timestamp)))
        
        # Message ID
        id_item = QTableWidgetItem(f"0x{message.msg_id:03X}")
        id_item.setData(Qt.UserRole, message)  # Store message reference
        self.message_table.setItem(row, 2, id_item)
        
        # Message Name (from DBC if available)
        msg_name = self.get_message_name_from_dbc(message.msg_id)
        name_item = QTableWidgetItem(msg_name if msg_name else "-")
        if msg_name:
            name_item.setForeground(QColor("#1565c0"))  # Blue for DBC messages
        self.message_table.setItem(row, 3, name_item)
        
        # DLC
        self.message_table.setItem(row, 4, QTableWidgetItem(str(message.dlc)))
        
        # Data
        data_str = " ".join(f"{b:02X}" for b in message.data)
        self.message_table.setItem(row, 5, QTableWidgetItem(data_str))
        
        # Direction
        dir_item = QTableWidgetItem(message.direction)
        if message.direction == "TX":
            dir_item.setForeground(QColor("#1976d2"))  # Blue for TX
        else:
            dir_item.setForeground(QColor("#2e7d32"))  # Green for RX
        self.message_table.setItem(row, 6, dir_item)
        
        # DBC Status (show if signals decoded)
        dbc_status = "✓" if getattr(message, 'decoded_signals', None) else "-"
        dbc_item = QTableWidgetItem(dbc_status)
        if dbc_status == "✓":
            dbc_item.setForeground(QColor("#2e7d32"))  # Green checkmark
            dbc_item.setToolTip("Message has DBC signals - click to view details")
        self.message_table.setItem(row, 7, dbc_item)

    
    def get_message_name_from_dbc(self, msg_id):
        """Get message name from DBC manager if available."""
        if hasattr(self, 'dbc_manager') and self.dbc_manager:
            try:
                # Debug: check what we have in the active database
                if hasattr(self.dbc_manager, 'active_database') and self.dbc_manager.active_database:
                    db = self.dbc_manager.active_database
                    if hasattr(db, 'messages'):
                        if isinstance(db.messages, list):
                            # cantools database - search by frame_id
                            for message in db.messages:
                                frame_id = getattr(message, 'frame_id', None)
                                if frame_id == msg_id:
                                    return getattr(message, 'name', None)
                        elif isinstance(db.messages, dict):
                            # Custom database - direct lookup
                            message = db.messages.get(msg_id)
                            if message and hasattr(message, 'name'):
                                return message.name
                # Fallback to original method
                message_info = self.dbc_manager.get_message_info(msg_id)
                if message_info and hasattr(message_info, 'name'):
                    return message_info.name
            except Exception as e:
                print(f"[DEBUG] get_message_name_from_dbc failed for ID {msg_id}: {e}")
        return None
        
    def on_message_selected(self):
        """Handle message selection"""
        current_row = self.message_table.currentRow()
        if current_row >= 0:
            id_item = self.message_table.item(current_row, 2)
            if id_item:
                message = id_item.data(Qt.UserRole)
                if message:
                    self.update_details_panel(message)
                    
                    # Emit signal with message data
                    msg_data = {
                        'id': message.msg_id,
                        'dlc': message.dlc,
                        'data': message.data,
                        'direction': message.direction,
                        'timestamp': message.timestamp
                    }
                    self.message_selected.emit(msg_data)
                    
    def update_details_panel(self, message):
        """Update the details panel with message information"""
        self.detail_id_label.setText(f"0x{message.msg_id:03X} ({message.msg_id})")
        self.detail_dlc_label.setText(str(message.dlc))
        self.detail_direction_label.setText(message.direction)
        self.detail_timestamp_label.setText(str(message.timestamp))
        self.detail_count_label.setText(str(message.count))
        
        # Format data bytes in a professional hex editor style
        data_text = f"Data Analysis ({len(message.data)} bytes):\n"
        data_text += "=" * 40 + "\n"
        
        # Hex representation with addresses
        data_text += "HEX: "
        data_text += " ".join(f"{b:02X}" for b in message.data) + "\n"
        
        # Decimal representation
        data_text += "DEC: "
        data_text += " ".join(f"{b:3d}" for b in message.data) + "\n"
        
        # ASCII representation (printable chars only)
        data_text += "ASC: "
        ascii_chars = []
        for b in message.data:
            if 32 <= b <= 126:  # Printable ASCII
                ascii_chars.append(chr(b))
            else:
                ascii_chars.append('.')
        data_text += " ".join(f"{c:>3s}" for c in ascii_chars) + "\n\n"
        
        # Binary representation (compact)
        data_text += "Binary (MSB first):\n"
        for i in range(0, len(message.data), 4):  # Group by 4 bytes
            chunk = message.data[i:i+4]
            data_text += f"Bytes {i}-{i+len(chunk)-1}: "
            data_text += " ".join(f"{b:08b}" for b in chunk) + "\n"
        
        # Set the formatted data to the text widget
        self.data_text.setText(data_text)
        
        # Update DBC signals display (CANoe/TSMaster style)
        self.update_dbc_signals_display(message)
        
    def update_dbc_signals_display(self, message):
        """Update DBC signals display in CANoe/TSMaster style."""
        if not hasattr(message, 'decoded_signals') or not message.decoded_signals:
            self.dbc_signals_text.setText("No DBC signals available for this message.")
            return
            
        # Get message name from DBC
        msg_name = self.get_message_name_from_dbc(message.msg_id)
        
        # Format signals professionally
        signals_text = f"Message: {msg_name or f'0x{message.msg_id:03X}'}\n"
        signals_text += "=" * 50 + "\n\n"
        
        decoded = message.decoded_signals
        if isinstance(decoded, dict) and decoded:
            for signal_name, signal_value in decoded.items():
                # Get signal info from DBC if available
                signal_info = self.get_signal_info_from_dbc(message.msg_id, signal_name)
                
                if isinstance(signal_value, (int, float)):
                    # Format numeric values
                    if isinstance(signal_value, float):
                        value_str = f"{signal_value:.3f}"
                    else:
                        value_str = str(signal_value)
                        
                    # Add unit if available
                    unit = signal_info.get('unit', '') if signal_info else ''
                    if unit and unit != 'None':
                        value_str += f" {unit}"
                        
                    signals_text += f"{signal_name:<20}: {value_str}\n"
                    
                    # Add additional info if available
                    if signal_info:
                        if 'min' in signal_info and 'max' in signal_info:
                            min_val = signal_info['min']
                            max_val = signal_info['max']
                            if min_val is not None and max_val is not None:
                                signals_text += f"{'':<20}  Range: [{min_val}, {max_val}]\n"
                else:
                    signals_text += f"{signal_name:<20}: {signal_value}\n"
                    
                signals_text += "\n"
        else:
            signals_text += "No signals decoded from this message.\n"
            
        self.dbc_signals_text.setText(signals_text)
        
    def get_signal_info_from_dbc(self, msg_id, signal_name):
        """Get detailed signal information from DBC manager."""
        if hasattr(self, 'dbc_manager') and self.dbc_manager:
            try:
                # Try to get signal info from the active database
                if hasattr(self.dbc_manager, 'active_database') and self.dbc_manager.active_database:
                    db = self.dbc_manager.active_database
                    if hasattr(db, 'messages'):
                        if isinstance(db.messages, list):
                            # cantools database
                            for message in db.messages:
                                if getattr(message, 'frame_id', None) == msg_id:
                                    for signal in getattr(message, 'signals', []):
                                        if signal.name == signal_name:
                                            return {
                                                'unit': getattr(signal, 'unit', ''),
                                                'min': getattr(signal, 'minimum', None),
                                                'max': getattr(signal, 'maximum', None),
                                                'factor': getattr(signal, 'scale', 1),
                                                'offset': getattr(signal, 'offset', 0)
                                            }
            except Exception:
                pass
        return None
        
    def toggle_group_by_id(self, enabled):
        """Toggle CANoe-style Group by ID view."""
        self.group_by_id_enabled = enabled
        
        if enabled:
            print("[DEBUG] Enabling Group by ID view (CANoe-style)")
            # Build grouped messages from current messages
            self.rebuild_grouped_messages()
            # Disable show duplicates when grouping (doesn't make sense)
            self.show_duplicates_cb.setChecked(False)
            self.show_duplicates_cb.setEnabled(False)
        else:
            print("[DEBUG] Disabling Group by ID view")
            # Re-enable show duplicates
            self.show_duplicates_cb.setEnabled(True)
            self.grouped_messages.clear()
        
        # Refresh the display
        self.apply_filters()
    
    def rebuild_grouped_messages(self):
        """Rebuild grouped messages from current message list."""
        self.grouped_messages.clear()
        
        # Group messages by ID, keeping only the latest for each ID
        for message in self.messages:
            msg_id = message.msg_id
            if msg_id not in self.grouped_messages or message.timestamp > self.grouped_messages[msg_id].timestamp:
                self.grouped_messages[msg_id] = message
        
        print(f"[DEBUG] Grouped {len(self.messages)} messages into {len(self.grouped_messages)} unique IDs")
    
    def update_filters(self):
        """Update filter settings"""
        self.filters['id_filter'] = self.id_filter_edit.text()
        self.filters['data_filter'] = self.data_filter_edit.text()
        self.filters['direction_filter'] = self.direction_combo.currentText()
        self.filters['show_duplicates'] = self.show_duplicates_cb.isChecked()
        
        self.apply_filters()
        self.filter_changed.emit(self.filters)
        
    def clear_filters(self):
        """Clear all filters"""
        self.id_filter_edit.clear()
        self.data_filter_edit.clear()
        self.direction_combo.setCurrentText("All")
        self.show_duplicates_cb.setChecked(True)
        
    def save_current_filter(self):
        """Save current filter configuration"""
        # Placeholder for filter saving functionality
        pass
        
    def clear_messages(self):
        """Clear all messages"""
        self.messages.clear()
        self.filtered_messages.clear()
        self.message_table.setRowCount(0)
        self.update_statistics()
        
    def set_auto_scroll(self, enabled):
        """Set auto-scroll behavior"""
        self.auto_scroll = enabled
        
    def set_max_messages(self, max_count):
        """Set maximum number of messages to keep"""
        self.max_messages = max_count
        
        # Trim existing messages if needed
        if len(self.messages) > max_count:
            self.messages = self.messages[-max_count:]
            self.apply_filters()
            
    def update_statistics(self):
        """Update statistics display"""
        total_messages = len(self.messages)
        filtered_messages = len(self.filtered_messages)
        
        # Calculate message rate
        current_count = total_messages
        rate = current_count - self.last_message_count
        self.last_message_count = current_count
        
        stats_text = f"Messages: {total_messages:,} | Filtered: {filtered_messages:,} | Rate: {rate:.1f} msg/s"
        self.stats_label.setText(stats_text)
        
    def apply_professional_style(self):
        """Apply professional styling"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin: 4px 0;
                padding-top: 12px;
                background-color: #fafafa;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: white;
            }
            
            QTableWidget {
                gridline-color: #e9ecef;
                background-color: white;
                alternate-background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            
            QTableWidget::item {
                padding: 4px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            
            QHeaderView::section {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                border: 1px solid #dee2e6;
                padding: 6px;
                font-weight: bold;
                color: #495057;
            }
        """)