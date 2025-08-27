#!/usr/bin/env python3
"""
Enhanced Transmit Panel with Threading Integration
Uses worker threads for DBC searches and message composition
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
                               QLabel, QComboBox, QCheckBox, QSplitter, QTextEdit,
                               QGroupBox, QFormLayout, QSpinBox, QFrame, QProgressBar,
                               QCompleter, QListWidget, QDialog, QDialogButtonBox)
from PySide6.QtCore import Signal, Qt, QTimer, Slot, QStringListModel
from PySide6.QtGui import QFont, QColor, QPalette

import time
import uuid
from typing import Dict, List, Any, Optional

from .threading_workers import ThreadingManager, DBCSearchRequest


class DBCSearchDialog(QDialog):
    """Fast DBC search dialog with worker thread integration"""
    
    selection_made = Signal(dict)  # Selected message/signal data
    
    def __init__(self, threading_manager: ThreadingManager, parent=None):
        super().__init__(parent)
        self.threading_manager = threading_manager
        self.current_request_id = None
        
        self.setWindowTitle("🔍 DBC Database Search")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.connect_search_signals()
    
    def setup_ui(self):
        """Setup search dialog UI"""
        layout = QVBoxLayout(self)
        
        # Search input
        search_group = QGroupBox("Search Parameters")
        search_layout = QFormLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term (message name, signal name, ID...)")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addRow("Search Term:", self.search_input)
        
        # Search type
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["All", "Messages", "Signals", "Nodes"])
        search_layout.addRow("Search Type:", self.search_type_combo)
        
        # Case sensitive
        self.case_sensitive_cb = QCheckBox()
        search_layout.addRow("Case Sensitive:", self.case_sensitive_cb)
        
        # Max results
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 1000)
        self.max_results_spin.setValue(100)
        search_layout.addRow("Max Results:", self.max_results_spin)
        
        layout.addWidget(search_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Type", "Name", "ID", "Details", "Parent", "Description"
        ])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.doubleClicked.connect(self.on_result_selected)
        
        results_layout.addWidget(self.results_table)
        layout.addWidget(results_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.clicked.connect(self.execute_search)
        button_layout.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        # Auto-search timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.execute_search)
    
    def connect_search_signals(self):
        """Connect signals from search worker"""
        search_worker = self.threading_manager.dbc_search_worker
        search_worker.search_completed.connect(self.on_search_completed)
        search_worker.search_progress.connect(self.on_search_progress)
        search_worker.search_error.connect(self.on_search_error)
    
    def on_search_text_changed(self, text: str):
        """Auto-search with debouncing"""
        if len(text) >= 2:  # Start searching after 2 characters
            self.search_timer.start(300)  # 300ms debounce
        else:
            self.search_timer.stop()
            self.clear_results()
    
    def execute_search(self):
        """Execute search using worker thread"""
        search_term = self.search_input.text().strip()
        if not search_term:
            return
        
        # Create search request
        self.current_request_id = str(uuid.uuid4())
        
        search_type_map = {
            "All": "all",
            "Messages": "message", 
            "Signals": "signal",
            "Nodes": "node"
        }
        
        search_request = {
            'request_id': self.current_request_id,
            'search_term': search_term,
            'search_type': search_type_map[self.search_type_combo.currentText()],
            'max_results': self.max_results_spin.value(),
            'case_sensitive': self.case_sensitive_cb.isChecked()
        }
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.search_btn.setEnabled(False)
        
        # Execute search in worker thread
        self.threading_manager.dbc_search_worker.execute_search(search_request)
    
    @Slot(str, int, int)
    def on_search_progress(self, request_id: str, current: int, total: int):
        """Update search progress"""
        if request_id == self.current_request_id:
            if total > 0:
                progress = int((current / total) * 100)
                self.progress_bar.setValue(progress)
    
    @Slot(str, list)
    def on_search_completed(self, request_id: str, results: List[Dict[str, Any]]):
        """Handle search completion"""
        if request_id != self.current_request_id:
            return
        
        # Hide progress
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        
        # Clear existing results
        self.results_table.setRowCount(0)
        
        # Populate results
        for i, result in enumerate(results):
            self.results_table.insertRow(i)
            
            # Type
            type_item = QTableWidgetItem(result.get('type', ''))
            self.results_table.setItem(i, 0, type_item)
            
            # Name
            name_item = QTableWidgetItem(result.get('name', ''))
            self.results_table.setItem(i, 1, name_item)
            
            # ID
            id_str = result.get('id', result.get('message_id', ''))
            id_item = QTableWidgetItem(str(id_str))
            self.results_table.setItem(i, 2, id_item)
            
            # Details
            if result.get('type') == 'signal':
                details = f"Bit {result.get('start_bit', 0)}, Len {result.get('length', 0)}"
                if result.get('unit'):
                    details += f", Unit: {result.get('unit')}"
            elif result.get('type') == 'message':
                details = f"DLC {result.get('dlc', 0)}, {result.get('signals_count', 0)} signals"
            else:
                details = ""
            
            details_item = QTableWidgetItem(details)
            self.results_table.setItem(i, 3, details_item)
            
            # Parent (for signals)
            parent = result.get('message_name', '')
            parent_item = QTableWidgetItem(parent)
            self.results_table.setItem(i, 4, parent_item)
            
            # Description
            description = result.get('comment', '')[:100]  # Truncate long descriptions
            desc_item = QTableWidgetItem(description)
            self.results_table.setItem(i, 5, desc_item)
            
            # Store full result data in item
            name_item.setData(Qt.UserRole, result)
        
        # Resize columns to content
        self.results_table.resizeColumnsToContents()
        
        print(f"✅ Search completed: {len(results)} results found")
    
    @Slot(str, str)
    def on_search_error(self, request_id: str, error_message: str):
        """Handle search error"""
        if request_id == self.current_request_id:
            self.progress_bar.setVisible(False)
            self.search_btn.setEnabled(True)
            print(f"❌ Search error: {error_message}")
    
    def clear_results(self):
        """Clear search results"""
        self.results_table.setRowCount(0)
    
    def on_result_selected(self):
        """Handle result double-click"""
        self.accept_selection()
    
    def accept_selection(self):
        """Accept selected result"""
        current_row = self.results_table.currentRow()
        if current_row >= 0:
            name_item = self.results_table.item(current_row, 1)
            if name_item:
                result_data = name_item.data(Qt.UserRole)
                if result_data:
                    self.selection_made.emit(result_data)
                    self.accept()
                    return
        
        self.reject()


class EnhancedTransmitPanel(QWidget):
    """Enhanced transmit panel with threading for DBC operations"""
    
    # Signals
    message_transmission_requested = Signal(dict)
    dbc_search_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize threading manager
        self.threading_manager = ThreadingManager()
        
        # Message composition state
        self.current_message_id = None
        self.current_signals = {}
        self.composition_pending = False
        
        self.setup_ui()
        self.connect_threading_signals()
        self.apply_professional_style()
    
    def setup_ui(self):
        """Setup enhanced transmit panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Message selection with DBC search
        self.create_message_selection_panel(layout)
        
        # Signal composition panel
        self.create_signal_composition_panel(layout)
        
        # Transmission controls
        self.create_transmission_controls(layout)
        
        # Status panel
        self.create_status_panel(layout)
    
    def create_message_selection_panel(self, layout):
        """Create message selection panel with DBC search"""
        selection_group = QGroupBox("📨 Message Selection")
        selection_layout = QVBoxLayout(selection_group)
        
        # Quick selection row
        quick_layout = QHBoxLayout()
        
        # Message ID input
        quick_layout.addWidget(QLabel("Message ID:"))
        self.message_id_edit = QLineEdit()
        self.message_id_edit.setPlaceholderText("0x123")
        self.message_id_edit.textChanged.connect(self.on_message_id_changed)
        quick_layout.addWidget(self.message_id_edit)
        
        # DBC search button
        self.dbc_search_btn = QPushButton("🔍 Search DBC")
        self.dbc_search_btn.clicked.connect(self.open_dbc_search)
        quick_layout.addWidget(self.dbc_search_btn)
        
        # Auto-complete combo
        self.message_combo = QComboBox()
        self.message_combo.setEditable(True)
        self.message_combo.setPlaceholderText("Or select from DBC...")
        self.message_combo.currentTextChanged.connect(self.on_message_combo_changed)
        quick_layout.addWidget(self.message_combo)
        
        selection_layout.addLayout(quick_layout)
        
        # Message info display
        info_layout = QHBoxLayout()
        
        self.message_name_label = QLabel("Message: -")
        self.message_name_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        info_layout.addWidget(self.message_name_label)
        
        self.dlc_label = QLabel("DLC: -")
        info_layout.addWidget(self.dlc_label)
        
        self.signals_count_label = QLabel("Signals: -")
        info_layout.addWidget(self.signals_count_label)
        
        info_layout.addStretch()
        
        # Composition progress
        self.composition_progress = QProgressBar()
        self.composition_progress.setVisible(False)
        self.composition_progress.setMaximumHeight(6)
        info_layout.addWidget(self.composition_progress)
        
        selection_layout.addLayout(info_layout)
        
        layout.addWidget(selection_group)
    
    def create_signal_composition_panel(self, layout):
        """Create signal composition panel"""
        signals_group = QGroupBox("⚙️ Signal Composition")
        signals_layout = QVBoxLayout(signals_group)
        
        # Signals table
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(6)
        self.signals_table.setHorizontalHeaderLabels([
            "Signal Name", "Current Value", "Unit", "Min", "Max", "Description"
        ])
        
        # Optimize table
        self.signals_table.setAlternatingRowColors(True)
        self.signals_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.signals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Signal Name
        header.setSectionResizeMode(1, QHeaderView.Fixed)             # Current Value
        header.setSectionResizeMode(2, QHeaderView.Fixed)             # Unit
        header.setSectionResizeMode(3, QHeaderView.Fixed)             # Min
        header.setSectionResizeMode(4, QHeaderView.Fixed)             # Max
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # Description
        
        self.signals_table.setColumnWidth(1, 100)  # Current Value
        self.signals_table.setColumnWidth(2, 60)   # Unit
        self.signals_table.setColumnWidth(3, 60)   # Min
        self.signals_table.setColumnWidth(4, 60)   # Max
        
        signals_layout.addWidget(self.signals_table)
        
        # Composition controls
        controls_layout = QHBoxLayout()
        
        self.auto_compose_cb = QCheckBox("Auto-compose on change")
        self.auto_compose_cb.setChecked(True)
        controls_layout.addWidget(self.auto_compose_cb)
        
        controls_layout.addStretch()
        
        self.compose_btn = QPushButton("🔧 Compose Message")
        self.compose_btn.clicked.connect(self.compose_message_async)
        controls_layout.addWidget(self.compose_btn)
        
        self.reset_signals_btn = QPushButton("🔄 Reset Signals")
        self.reset_signals_btn.clicked.connect(self.reset_signal_values)
        controls_layout.addWidget(self.reset_signals_btn)
        
        signals_layout.addLayout(controls_layout)
        
        layout.addWidget(signals_group)
    
    def create_transmission_controls(self, layout):
        """Create transmission control panel"""
        tx_group = QGroupBox("📤 Transmission Controls")
        tx_layout = QVBoxLayout(tx_group)
        
        # Raw data display
        raw_layout = QHBoxLayout()
        raw_layout.addWidget(QLabel("Raw Data:"))
        
        self.raw_data_edit = QLineEdit()
        self.raw_data_edit.setPlaceholderText("00 00 00 00 00 00 00 00")
        self.raw_data_edit.setFont(QFont("Consolas", 10))
        raw_layout.addWidget(self.raw_data_edit)
        
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)
        raw_layout.addWidget(QLabel("DLC:"))
        raw_layout.addWidget(self.dlc_spin)
        
        tx_layout.addLayout(raw_layout)
        
        # Transmission controls
        controls_layout = QHBoxLayout()
        
        # Single transmission
        self.send_once_btn = QPushButton("📤 Send Once")
        self.send_once_btn.clicked.connect(self.send_message_once)
        controls_layout.addWidget(self.send_once_btn)
        
        # Periodic transmission
        self.periodic_cb = QCheckBox("Periodic")
        controls_layout.addWidget(self.periodic_cb)
        
        controls_layout.addWidget(QLabel("Interval:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 10000)
        self.interval_spin.setValue(100)
        self.interval_spin.setSuffix(" ms")
        controls_layout.addWidget(self.interval_spin)
        
        self.start_periodic_btn = QPushButton("▶️ Start Periodic")
        self.start_periodic_btn.clicked.connect(self.start_periodic_transmission)
        controls_layout.addWidget(self.start_periodic_btn)
        
        self.stop_periodic_btn = QPushButton("⏹️ Stop Periodic")
        self.stop_periodic_btn.clicked.connect(self.stop_periodic_transmission)
        self.stop_periodic_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_periodic_btn)
        
        controls_layout.addStretch()
        
        tx_layout.addLayout(controls_layout)
        
        layout.addWidget(tx_group)
    
    def create_status_panel(self, layout):
        """Create status and statistics panel"""
        status_group = QGroupBox("📊 Status")
        status_layout = QHBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.sent_count_label = QLabel("Sent: 0")
        status_layout.addWidget(self.sent_count_label)
        
        self.composition_time_label = QLabel("Composition: 0ms")
        status_layout.addWidget(self.composition_time_label)
        
        layout.addWidget(status_group)
    
    def connect_threading_signals(self):
        """Connect signals from worker threads"""
        # Message composition signals
        transmit_worker = self.threading_manager.transmit_worker
        transmit_worker.message_composition_ready.connect(self.on_message_composed)
        transmit_worker.transmission_error.connect(self.on_transmission_error)
    
    def open_dbc_search(self):
        """Open DBC search dialog"""
        search_dialog = DBCSearchDialog(self.threading_manager, self)
        search_dialog.selection_made.connect(self.on_dbc_selection_made)
        search_dialog.show()
    
    @Slot(dict)
    def on_dbc_selection_made(self, selection_data: Dict[str, Any]):
        """Handle DBC search selection"""
        if selection_data.get('type') == 'message':
            # Set message ID
            message_id = selection_data.get('id_decimal', 0)
            self.message_id_edit.setText(f"0x{message_id:X}")
            self.current_message_id = message_id
            
            # Update message info
            self.message_name_label.setText(f"Message: {selection_data.get('name', 'Unknown')}")
            self.dlc_label.setText(f"DLC: {selection_data.get('dlc', 0)}")
            self.signals_count_label.setText(f"Signals: {selection_data.get('signals_count', 0)}")
            
            # Load signals for this message (would need DBC integration)
            self.load_message_signals(message_id)
            
        elif selection_data.get('type') == 'signal':
            # Set message ID from signal's parent message
            message_id = selection_data.get('message_id_decimal', 0)
            self.message_id_edit.setText(f"0x{message_id:X}")
            self.current_message_id = message_id
            
            # Update message info  
            self.message_name_label.setText(f"Message: {selection_data.get('message_name', 'Unknown')}")
            
            # Load signals and highlight the selected one
            self.load_message_signals(message_id, highlight_signal=selection_data.get('name'))
        
        print(f"✅ DBC selection applied: {selection_data.get('name')}")
    
    def on_message_id_changed(self, text: str):
        """Handle message ID input change"""
        try:
            if text.startswith('0x') or text.startswith('0X'):
                message_id = int(text, 16)
            else:
                message_id = int(text) if text else 0
            
            self.current_message_id = message_id
            self.load_message_signals(message_id)
            
        except ValueError:
            self.current_message_id = None
            self.clear_signals_table()
    
    def on_message_combo_changed(self, text: str):
        """Handle message combo selection"""
        # This would be connected to DBC message list
        pass
    
    def load_message_signals(self, message_id: int, highlight_signal: str = None):
        """Load signals for message (placeholder - needs DBC integration)"""
        # This would use the DBC manager to load actual signals
        # For now, we'll create a placeholder implementation
        
        self.signals_table.setRowCount(0)
        
        # Placeholder signals (would come from DBC)
        placeholder_signals = [
            {"name": "Engine_RPM", "value": 800, "unit": "rpm", "min": 0, "max": 8000, "desc": "Engine rotation speed"},
            {"name": "Vehicle_Speed", "value": 0, "unit": "km/h", "min": 0, "max": 255, "desc": "Vehicle velocity"},
            {"name": "Throttle_Pos", "value": 0, "unit": "%", "min": 0, "max": 100, "desc": "Throttle position"},
        ]
        
        for i, signal in enumerate(placeholder_signals):
            self.signals_table.insertRow(i)
            
            # Signal name
            name_item = QTableWidgetItem(signal["name"])
            if highlight_signal and signal["name"] == highlight_signal:
                name_item.setBackground(QColor(255, 255, 0, 100))  # Yellow highlight
            self.signals_table.setItem(i, 0, name_item)
            
            # Current value (editable)
            value_item = QTableWidgetItem(str(signal["value"]))
            value_item.setFlags(value_item.flags() | Qt.ItemIsEditable)
            self.signals_table.setItem(i, 1, value_item)
            
            # Unit
            unit_item = QTableWidgetItem(signal["unit"])
            self.signals_table.setItem(i, 2, unit_item)
            
            # Min value
            min_item = QTableWidgetItem(str(signal["min"]))
            self.signals_table.setItem(i, 3, min_item)
            
            # Max value
            max_item = QTableWidgetItem(str(signal["max"]))
            self.signals_table.setItem(i, 4, max_item)
            
            # Description
            desc_item = QTableWidgetItem(signal["desc"])
            self.signals_table.setItem(i, 5, desc_item)
        
        # Auto-compose if enabled
        if self.auto_compose_cb.isChecked():
            self.compose_message_async()
    
    def clear_signals_table(self):
        """Clear signals table"""
        self.signals_table.setRowCount(0)
        self.message_name_label.setText("Message: -")
        self.dlc_label.setText("DLC: -")
        self.signals_count_label.setText("Signals: -")
    
    def compose_message_async(self):
        """Compose message using worker thread"""
        if not self.current_message_id:
            return
        
        # Collect signal values from table
        signal_values = {}
        for row in range(self.signals_table.rowCount()):
            name_item = self.signals_table.item(row, 0)
            value_item = self.signals_table.item(row, 1)
            
            if name_item and value_item:
                try:
                    signal_values[name_item.text()] = float(value_item.text())
                except ValueError:
                    signal_values[name_item.text()] = 0
        
        # Show composition progress
        self.composition_progress.setVisible(True)
        self.composition_progress.setValue(0)
        self.compose_btn.setEnabled(False)
        self.composition_pending = True
        
        # Request composition in worker thread
        composition_request = {
            'request_id': str(uuid.uuid4()),
            'message_id': self.current_message_id,
            'signal_values': signal_values
        }
        
        self.threading_manager.transmit_worker.compose_message_async(composition_request)
    
    @Slot(str, dict)
    def on_message_composed(self, request_id: str, composed_message: Dict[str, Any]):
        """Handle message composition completion"""
        if not self.composition_pending:
            return
        
        # Hide progress
        self.composition_progress.setVisible(False)
        self.compose_btn.setEnabled(True)
        self.composition_pending = False
        
        # Update raw data display
        data_bytes = composed_message.get('data', b'\\x00' * 8)
        data_hex = ' '.join([f"{b:02X}" for b in data_bytes])
        self.raw_data_edit.setText(data_hex)
        
        # Update DLC
        self.dlc_spin.setValue(composed_message.get('dlc', 8))
        
        # Update status
        self.status_label.setText("Message composed ✅")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        print(f"✅ Message composed: ID=0x{self.current_message_id:X}, Data={data_hex}")
    
    @Slot(str, str)
    def on_transmission_error(self, message_id: str, error_message: str):
        """Handle transmission error"""
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        print(f"❌ Transmission error: {error_message}")
    
    def reset_signal_values(self):
        """Reset all signal values to defaults"""
        for row in range(self.signals_table.rowCount()):
            value_item = self.signals_table.item(row, 1)
            if value_item:
                value_item.setText("0")
        
        if self.auto_compose_cb.isChecked():
            self.compose_message_async()
    
    def send_message_once(self):
        """Send message once"""
        if not self.current_message_id:
            return
        
        # Parse raw data
        try:
            data_text = self.raw_data_edit.text().replace(' ', '')
            data_bytes = bytes.fromhex(data_text)
        except ValueError:
            data_bytes = b'\\x00' * 8
        
        # Create transmission request
        transmission_data = {
            'id': self.current_message_id,
            'data': data_bytes,
            'dlc': self.dlc_spin.value(),
            'is_extended': self.current_message_id > 0x7FF,
            'direction': 'TX'
        }
        
        self.message_transmission_requested.emit(transmission_data)
        self.status_label.setText("Message sent ✅")
        
        # Update sent counter
        current_count = int(self.sent_count_label.text().split(': ')[1])
        self.sent_count_label.setText(f"Sent: {current_count + 1}")
    
    def start_periodic_transmission(self):
        """Start periodic message transmission"""
        if not self.current_message_id:
            return
        
        # Configure periodic transmission
        transmission_config = {
            'message_id': self.current_message_id,
            'interval_ms': self.interval_spin.value(),
            'enabled': True
        }
        
        self.threading_manager.transmit_worker.start_periodic_transmission(
            str(self.current_message_id), transmission_config
        )
        
        # Update UI state
        self.start_periodic_btn.setEnabled(False)
        self.stop_periodic_btn.setEnabled(True)
        self.status_label.setText("Periodic transmission active 🔄")
        self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        
        print(f"▶️ Started periodic transmission: ID=0x{self.current_message_id:X}, Interval={self.interval_spin.value()}ms")
    
    def stop_periodic_transmission(self):
        """Stop periodic message transmission"""
        if self.current_message_id:
            self.threading_manager.transmit_worker.stop_periodic_transmission(str(self.current_message_id))
        
        # Update UI state
        self.start_periodic_btn.setEnabled(True)
        self.stop_periodic_btn.setEnabled(False)
        self.status_label.setText("Periodic transmission stopped ⏹️")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        print("⏹️ Stopped periodic transmission")
    
    def set_dbc_manager(self, dbc_manager):
        """Set DBC manager and update worker threads"""
        self.threading_manager.set_dbc_manager(dbc_manager)
        print("🔄 DBC manager updated in transmit panel")
    
    def apply_professional_style(self):
        """Apply professional styling"""
        style = """
        QGroupBox {
            font-weight: bold;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            margin-top: 1ex;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTableWidget {
            gridline-color: #e0e0e0;
            selection-background-color: #3498db;
            alternate-background-color: #f8f9fa;
        }
        QPushButton {
            padding: 6px 12px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: #ecf0f1;
        }
        QPushButton:hover {
            background-color: #d5dbdb;
        }
        QPushButton:pressed {
            background-color: #bdc3c7;
        }
        QLineEdit {
            padding: 4px;
            border: 1px solid #bdc3c7;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(style)
    
    def closeEvent(self, event):
        """Clean shutdown"""
        print("🔄 Shutting down transmit panel worker threads...")
        self.threading_manager.shutdown()
        event.accept()
