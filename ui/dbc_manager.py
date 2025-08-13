"""
DBC Manager for Professional CAN Analyzer
Handles DBC file loading, parsing, and signal decoding
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QDialog,
                               QListWidget, QListWidgetItem, QPushButton,
                               QLabel, QFileDialog, QMessageBox, QTextEdit,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QGroupBox, QFormLayout, QLineEdit, QSpinBox,
                               QComboBox, QCheckBox, QSplitter)
from PySide6.QtCore import Signal, Qt, QObject
from PySide6.QtGui import QFont
import os
import json
import cantools

class DBCSignal:
    """Represents a DBC signal"""
    def __init__(self, name, start_bit, length, byte_order='little_endian', 
                 value_type='unsigned', factor=1, offset=0, minimum=0, maximum=0, unit='', comment=''):
        self.name = name
        self.start_bit = start_bit
        self.length = length
        self.byte_order = byte_order  # 'little_endian' or 'big_endian'
        self.value_type = value_type  # 'unsigned', 'signed'
        self.factor = factor
        self.offset = offset
        self.minimum = minimum
        self.maximum = maximum
        self.unit = unit
        self.comment = comment
        
    def decode(self, data):
        """Decode signal value from CAN data"""
        try:
            # Extract bits from data
            if self.byte_order == 'big_endian':
                # Motorola byte order
                byte_pos = self.start_bit // 8
                bit_pos = self.start_bit % 8
            else:
                # Intel byte order
                byte_pos = self.start_bit // 8
                bit_pos = self.start_bit % 8
                
            # Simple extraction for demonstration
            if byte_pos < len(data):
                raw_value = data[byte_pos]
                
                # Apply factor and offset
                value = raw_value * self.factor + self.offset
                
                # Apply limits
                if self.minimum != self.maximum:
                    value = max(self.minimum, min(self.maximum, value))
                    
                return value
            return 0
        except:
            return 0
            
    def encode(self, value):
        """Encode signal value to raw bytes"""
        try:
            # Remove offset and apply factor
            raw_value = (value - self.offset) / self.factor
            
            # Convert to integer
            raw_value = int(raw_value)
            
            # Apply limits
            if self.minimum != self.maximum:
                raw_value = max(int(self.minimum), min(int(self.maximum), raw_value))
                
            # For simple implementation, return as single byte
            return [raw_value & 0xFF]
        except:
            return [0]

class DBCMessage:
    """Represents a DBC message"""
    def __init__(self, msg_id, name, dlc=8, sender='', comment=''):
        self.msg_id = msg_id
        self.name = name
        self.dlc = dlc
        self.sender = sender
        self.comment = comment
        self.signals = {}
        
    def add_signal(self, signal):
        """Add a signal to the message"""
        self.signals[signal.name] = signal
        
    def decode_message(self, data):
        """Decode all signals in the message"""
        decoded = {}
        for signal_name, signal in self.signals.items():
            decoded[signal_name] = {
                'value': signal.decode(data),
                'unit': signal.unit,
                'raw': signal.decode(data) if signal.factor == 1 and signal.offset == 0 else None
            }
        return decoded
        
    def encode_message(self, signal_values):
        """Encode signals into CAN data"""
        data = [0] * self.dlc
        
        for signal_name, value in signal_values.items():
            if signal_name in self.signals:
                signal = self.signals[signal_name]
                encoded_bytes = signal.encode(value)
                
                # Simple placement at byte position
                byte_pos = signal.start_bit // 8
                if byte_pos < len(data) and encoded_bytes:
                    data[byte_pos] = encoded_bytes[0]
                    
        return data

class DBCDatabase:
    """Represents a complete DBC database"""
    def __init__(self, filename=''):
        self.filename = filename
        self.version = '1.0'
        self.messages = {}
        self.ecus = {}
        self.value_tables = {}
        self.comments = {}
        
    def add_message(self, message):
        """Add a message to the database"""
        self.messages[message.msg_id] = message
        
    def get_message(self, msg_id):
        """Get message by ID"""
        return self.messages.get(msg_id)
        
    def decode_message(self, msg_id, data):
        """Decode a CAN message using DBC"""
        message = self.get_message(msg_id)
        if message:
            return message.decode_message(data)
        return {}
        
    def get_message_by_name(self, name):
        """Get message by name"""
        for message in self.messages.values():
            if message.name == name:
                return message
        return None

class DBCManager(QObject):
    """Manages DBC files and signal decoding using cantools"""
    
    # Signals
    dbc_loaded = Signal(str, dict)  # filename, database_info
    dbc_unloaded = Signal(str)      # filename
    message_decoded = Signal(int, dict)  # msg_id, decoded_signals
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.databases = {}  # filename -> cantools.db.Database
        self.active_database = None
        
    def load_dbc_file(self, filename):
        """Load a DBC file using cantools"""
        try:
            db = cantools.database.load_file(filename)
            self.databases[filename] = db
            self.active_database = db
            # Build a full DBC info dict with messages and signals for UI
            db_info = self.get_database_info(filename)
            # Add 'messages' key with all message and signal details
            messages_dict = {}
            # Handle both cantools and custom DBCDatabase
            if hasattr(db, 'messages'):
                if isinstance(db.messages, dict):
                    # Custom DBCDatabase
                    for msg_id, message in db.messages.items():
                        msg_data = {
                            'id': msg_id,
                            'name': getattr(message, 'name', f'Message_{msg_id}'),
                            'dlc': getattr(message, 'dlc', 8),
                            'sender': getattr(message, 'sender', ''),
                            'comment': getattr(message, 'comment', ''),
                            'signals': {}
                        }
                        for signal_name, signal in getattr(message, 'signals', {}).items():
                            msg_data['signals'][signal_name] = {
                                'start_bit': getattr(signal, 'start_bit', 0),
                                'length': getattr(signal, 'length', 1),
                                'byte_order': getattr(signal, 'byte_order', 'little_endian'),
                                'value_type': getattr(signal, 'value_type', 'unsigned'),
                                'factor': getattr(signal, 'factor', 1),
                                'offset': getattr(signal, 'offset', 0),
                                'min': getattr(signal, 'minimum', 0),
                                'max': getattr(signal, 'maximum', 0),
                                'unit': getattr(signal, 'unit', ''),
                                'comment': getattr(signal, 'comment', '')
                            }
                        messages_dict[msg_id] = msg_data
                elif isinstance(db.messages, list):
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
            db_info['messages'] = messages_dict
            # Debug: print the structure of db_info before emitting
            import logging
            logging.debug(f"[DBCManager] Emitting dbc_loaded with db_info keys: {list(db_info.keys())}")
            logging.debug(f"[DBCManager] db_info['messages'] keys: {list(messages_dict.keys())}")
            self.dbc_loaded.emit(filename, db_info)
            return True, f"DBC file '{filename}' loaded successfully"
        except Exception as e:
            return False, f"Failed to load DBC file: {str(e)}"
            
    def create_sample_database(self, filename):
        """Create a sample DBC database for demonstration"""
        db = DBCDatabase(filename)
        db.version = "1.0"
        
        # Add sample ECUs
        db.ecus = {
            'Engine_ECU': {'comment': 'Engine Control Unit'},
            'Body_ECU': {'comment': 'Body Control Module'},
            'Dashboard': {'comment': 'Dashboard Display Unit'}
        }
        
        # Add sample messages
        
        # Engine RPM message
        engine_msg = DBCMessage(0x123, "Engine_Data", 8, "Engine_ECU", "Engine status and RPM data")
        engine_msg.add_signal(DBCSignal("Engine_RPM", 0, 16, factor=0.25, unit="rpm", minimum=0, maximum=8000))
        engine_msg.add_signal(DBCSignal("Engine_Temp", 16, 8, offset=-40, unit="°C", minimum=-40, maximum=150))
        engine_msg.add_signal(DBCSignal("Throttle_Pos", 24, 8, factor=0.4, unit="%", minimum=0, maximum=100))
        db.add_message(engine_msg)
        
        # Vehicle speed message
        speed_msg = DBCMessage(0x456, "Vehicle_Speed", 8, "Body_ECU", "Vehicle speed and distance")
        speed_msg.add_signal(DBCSignal("Vehicle_Speed", 0, 16, factor=0.1, unit="km/h", minimum=0, maximum=250))
        speed_msg.add_signal(DBCSignal("Odometer", 16, 32, factor=0.1, unit="km", minimum=0, maximum=999999))
        db.add_message(speed_msg)
        
        # Dashboard status message
        dash_msg = DBCMessage(0x789, "Dashboard_Status", 8, "Dashboard", "Dashboard indicators and warnings")
        dash_msg.add_signal(DBCSignal("Turn_Signal_Left", 0, 1, unit="bool"))
        dash_msg.add_signal(DBCSignal("Turn_Signal_Right", 1, 1, unit="bool"))
        dash_msg.add_signal(DBCSignal("High_Beam", 2, 1, unit="bool"))
        dash_msg.add_signal(DBCSignal("Engine_Warning", 3, 1, unit="bool"))
        dash_msg.add_signal(DBCSignal("Fuel_Level", 8, 8, factor=0.4, unit="%", minimum=0, maximum=100))
        db.add_message(dash_msg)
        
        # Gear position message
        gear_msg = DBCMessage(0xABC, "Gear_Position", 8, "Engine_ECU", "Current gear and transmission status")
        gear_msg.add_signal(DBCSignal("Current_Gear", 0, 4, unit="gear", minimum=0, maximum=8))
        gear_msg.add_signal(DBCSignal("Gear_Mode", 4, 2, unit="mode"))  # 0=P, 1=R, 2=N, 3=D
        gear_msg.add_signal(DBCSignal("Clutch_Pressed", 6, 1, unit="bool"))
        db.add_message(gear_msg)
        
        return db
        
    def unload_dbc_file(self, filename):
        """Unload a DBC file"""
        if filename in self.databases:
            del self.databases[filename]
            
            if self.active_database and self.active_database.filename == filename:
                self.active_database = None
                
            self.dbc_unloaded.emit(filename)
            return True, f"DBC file '{filename}' unloaded"
        else:
            return False, f"DBC file '{filename}' not loaded"
            
    def get_loaded_files(self):
        """Get list of loaded DBC files"""
        return list(self.databases.keys())
        
    def set_active_database(self, filename):
        """Set the active DBC database"""
        if filename in self.databases:
            self.active_database = self.databases[filename]
            return True
        return False
        
    def decode_can_message(self, msg_id, data):
        """Decode a CAN message using the active DBC (cantools)"""
        if not self.active_database:
            return {}
        try:
            decoded = self.active_database.decode_message(msg_id, bytes(data))
            self.message_decoded.emit(msg_id, decoded)
            return decoded
        except Exception:
            return {}
        
    def get_message_info(self, msg_id):
        """Get message information"""
        if not self.active_database:
            return None
            
        return self.active_database.get_message(msg_id)
        
    def get_all_messages(self):
        """Get all messages from active database"""
        if not self.active_database:
            return {}
            
        return self.active_database.messages
        
    def get_database_info(self, filename=None):
        """Get database information (works for both custom DBCDatabase and cantools.db.Database)."""
        if filename:
            db = self.databases.get(filename)
        else:
            db = self.active_database
        if not db:
            return {}
        info = {}
        # Filename
        if hasattr(db, 'filename'):
            info['filename'] = db.filename
        elif hasattr(db, 'name'):
            info['filename'] = db.name
        else:
            info['filename'] = str(filename) if filename else 'Loaded DBC'
        # Version
        if hasattr(db, 'version'):
            info['version'] = db.version
        elif hasattr(db, 'dbc') and hasattr(db.dbc, 'version'):
            info['version'] = db.dbc.version
        else:
            info['version'] = ''
        # Messages and signals
        if hasattr(db, 'messages') and isinstance(db.messages, dict):
            # Custom DBCDatabase
            info['message_count'] = len(db.messages)
            info['signal_count'] = sum(len(msg.signals) for msg in db.messages.values())
            info['ecus'] = list(getattr(db, 'ecus', {}).keys())
        elif hasattr(db, 'messages') and isinstance(db.messages, list):
            # cantools.db.Database
            info['message_count'] = len(db.messages)
            info['signal_count'] = sum(len(msg.signals) for msg in db.messages)
            info['ecus'] = list(getattr(db, 'nodes', []))
        else:
            info['message_count'] = 0
            info['signal_count'] = 0
            info['ecus'] = []
        return info

        
    def search_messages(self, query):
        """Search messages by name or ID"""
        if not self.active_database:
            return []
            
        results = []
        query_lower = query.lower()
        
        for msg_id, message in self.active_database.messages.items():
            # Search by name
            if query_lower in message.name.lower():
                results.append((msg_id, message))
            # Search by ID (hex)
            elif query_lower in f"0x{msg_id:x}":
                results.append((msg_id, message))
            # Search by ID (decimal)
            elif query in str(msg_id):
                results.append((msg_id, message))
                
        return results
        
    def search_signals(self, query):
        """Search signals by name"""
        if not self.active_database:
            return []
            
        results = []
        query_lower = query.lower()
        
        for msg_id, message in self.active_database.messages.items():
            for signal_name, signal in message.signals.items():
                if query_lower in signal_name.lower():
                    results.append((msg_id, message, signal_name, signal))
                    
        return results
        
    def export_dbc_info(self, filename):
        """Export DBC information to JSON"""
        if not self.active_database:
            return False, "No active database"
            
        try:
            export_data = {
                'database_info': self.get_database_info(),
                'messages': {}
            }
            
            for msg_id, message in self.active_database.messages.items():
                msg_data = {
                    'id': msg_id,
                    'name': message.name,
                    'dlc': message.dlc,
                    'sender': message.sender,
                    'comment': message.comment,
                    'signals': {}
                }
                
                for signal_name, signal in message.signals.items():
                    msg_data['signals'][signal_name] = {
                        'start_bit': signal.start_bit,
                        'length': signal.length,
                        'byte_order': signal.byte_order,
                        'value_type': signal.value_type,
                        'factor': signal.factor,
                        'offset': signal.offset,
                        'minimum': signal.minimum,
                        'maximum': signal.maximum,
                        'unit': signal.unit,
                        'comment': signal.comment
                    }
                    
                export_data['messages'][str(msg_id)] = msg_data
                
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            return True, f"DBC information exported to '{filename}'"
            
        except Exception as e:
            return False, f"Failed to export DBC info: {str(e)}"

class DBCBrowserDialog(QDialog):
    """Dialog for browsing DBC messages and signals"""
    
    message_selected = Signal(int, dict)  # msg_id, message_info
    signal_selected = Signal(str, dict)   # signal_name, signal_info
    
    def __init__(self, parent=None, dbc_manager=None):
        super().__init__(parent)
        self.dbc_manager = dbc_manager
        
        self.setWindowTitle("DBC Browser")
        self.setModal(False)
        self.resize(800, 600)
        
        self.setup_ui()
        self.refresh_data()
        
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Search section
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter message name, ID, or signal name...")
        self.search_edit.textChanged.connect(self.search_items)
        search_layout.addWidget(self.search_edit)
        
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Messages", "Signals"])
        self.search_type_combo.currentTextChanged.connect(self.search_items)
        search_layout.addWidget(self.search_type_combo)
        
        layout.addLayout(search_layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - message list
        left_widget = QGroupBox("Messages")
        left_layout = QVBoxLayout(left_widget)
        
        self.message_table = QTableWidget(0, 4)
        self.message_table.setHorizontalHeaderLabels(["ID", "Name", "DLC", "Sender"])
        self.message_table.horizontalHeader().setStretchLastSection(True)
        self.message_table.itemSelectionChanged.connect(self.on_message_selected)
        left_layout.addWidget(self.message_table)
        
        splitter.addWidget(left_widget)
        
        # Right side - signal details
        right_widget = QGroupBox("Signals")
        right_layout = QVBoxLayout(right_widget)
        
        self.signal_table = QTableWidget(0, 6)
        self.signal_table.setHorizontalHeaderLabels([
            "Name", "Start Bit", "Length", "Factor", "Unit", "Range"
        ])
        self.signal_table.horizontalHeader().setStretchLastSection(True)
        self.signal_table.itemSelectionChanged.connect(self.on_signal_selected)
        right_layout.addWidget(self.signal_table)
        
        # Signal details text
        self.signal_details = QTextEdit()
        self.signal_details.setMaximumHeight(100)
        self.signal_details.setReadOnly(True)
        right_layout.addWidget(self.signal_details)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def refresh_data(self):
        """Refresh the data from DBC manager"""
        if not self.dbc_manager or not self.dbc_manager.active_database:
            return
            
        # Clear tables
        self.message_table.setRowCount(0)
        self.signal_table.setRowCount(0)
        
        # Populate message table
        messages = self.dbc_manager.get_all_messages()
        for msg_id, message in messages.items():
            row = self.message_table.rowCount()
            self.message_table.insertRow(row)
            
            self.message_table.setItem(row, 0, QTableWidgetItem(f"0x{msg_id:03X}"))
            self.message_table.setItem(row, 1, QTableWidgetItem(message.name))
            self.message_table.setItem(row, 2, QTableWidgetItem(str(message.dlc)))
            self.message_table.setItem(row, 3, QTableWidgetItem(message.sender))
            
            # Store message ID in first item
            self.message_table.item(row, 0).setData(Qt.UserRole, msg_id)
            
    def search_items(self):
        """Search for messages or signals"""
        query = self.search_edit.text().strip()
        if not query or not self.dbc_manager:
            self.refresh_data()
            return
            
        search_type = self.search_type_combo.currentText()
        
        if search_type == "Messages":
            results = self.dbc_manager.search_messages(query)
            
            # Clear and populate message table with results
            self.message_table.setRowCount(0)
            for msg_id, message in results:
                row = self.message_table.rowCount()
                self.message_table.insertRow(row)
                
                self.message_table.setItem(row, 0, QTableWidgetItem(f"0x{msg_id:03X}"))
                self.message_table.setItem(row, 1, QTableWidgetItem(message.name))
                self.message_table.setItem(row, 2, QTableWidgetItem(str(message.dlc)))
                self.message_table.setItem(row, 3, QTableWidgetItem(message.sender))
                
                self.message_table.item(row, 0).setData(Qt.UserRole, msg_id)
                
        else:  # Signals
            results = self.dbc_manager.search_signals(query)
            
            # Clear and populate signal table with results
            self.signal_table.setRowCount(0)
            for msg_id, message, signal_name, signal in results:
                row = self.signal_table.rowCount()
                self.signal_table.insertRow(row)
                
                self.signal_table.setItem(row, 0, QTableWidgetItem(signal_name))
                self.signal_table.setItem(row, 1, QTableWidgetItem(str(signal.start_bit)))
                self.signal_table.setItem(row, 2, QTableWidgetItem(str(signal.length)))
                self.signal_table.setItem(row, 3, QTableWidgetItem(str(signal.factor)))
                self.signal_table.setItem(row, 4, QTableWidgetItem(signal.unit))
                self.signal_table.setItem(row, 5, QTableWidgetItem(f"{signal.minimum}-{signal.maximum}"))
                
    def on_message_selected(self):
        """Handle message selection"""
        current_row = self.message_table.currentRow()
        if current_row >= 0:
            msg_id_item = self.message_table.item(current_row, 0)
            if msg_id_item:
                msg_id = msg_id_item.data(Qt.UserRole)
                message = self.dbc_manager.get_message_info(msg_id)
                
                if message:
                    # Update signal table
                    self.signal_table.setRowCount(0)
                    for signal_name, signal in message.signals.items():
                        row = self.signal_table.rowCount()
                        self.signal_table.insertRow(row)
                        
                        self.signal_table.setItem(row, 0, QTableWidgetItem(signal_name))
                        self.signal_table.setItem(row, 1, QTableWidgetItem(str(signal.start_bit)))
                        self.signal_table.setItem(row, 2, QTableWidgetItem(str(signal.length)))
                        self.signal_table.setItem(row, 3, QTableWidgetItem(str(signal.factor)))
                        self.signal_table.setItem(row, 4, QTableWidgetItem(signal.unit))
                        self.signal_table.setItem(row, 5, QTableWidgetItem(f"{signal.minimum}-{signal.maximum}"))
                        
                        # Store signal reference
                        self.signal_table.item(row, 0).setData(Qt.UserRole, signal)
                        
                    # Emit signal
                    msg_info = {
                        'id': msg_id,
                        'name': message.name,
                        'dlc': message.dlc,
                        'sender': message.sender,
                        'comment': message.comment,
                        'signals': message.signals
                    }
                    self.message_selected.emit(msg_id, msg_info)
                    
    def on_signal_selected(self):
        """Handle signal selection"""
        current_row = self.signal_table.currentRow()
        if current_row >= 0:
            signal_item = self.signal_table.item(current_row, 0)
            if signal_item:
                signal = signal_item.data(Qt.UserRole)
                signal_name = signal_item.text()
                
                if signal:
                    # Update signal details
                    details = f"Signal: {signal_name}\n"
                    details += f"Start Bit: {signal.start_bit}\n"
                    details += f"Length: {signal.length} bits\n"
                    details += f"Byte Order: {signal.byte_order}\n"
                    details += f"Value Type: {signal.value_type}\n"
                    details += f"Factor: {signal.factor}\n"
                    details += f"Offset: {signal.offset}\n"
                    details += f"Range: {signal.minimum} to {signal.maximum}\n"
                    details += f"Unit: {signal.unit}\n"
                    details += f"Comment: {signal.comment}"
                    
                    self.signal_details.setPlainText(details)
                    
                    # Emit signal
                    signal_info = {
                        'name': signal_name,
                        'start_bit': signal.start_bit,
                        'length': signal.length,
                        'byte_order': signal.byte_order,
                        'value_type': signal.value_type,
                        'factor': signal.factor,
                        'offset': signal.offset,
                        'minimum': signal.minimum,
                        'maximum': signal.maximum,
                        'unit': signal.unit,
                        'comment': signal.comment
                    }
                    self.signal_selected.emit(signal_name, signal_info)