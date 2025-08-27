#!/usr/bin/env python3
"""
Enhanced Security Access UI Panel
Comprehensive security management with DLL integration
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json
import os
from pathlib import Path

class SecurityAccessWidget(QWidget):
    """Enhanced security access widget with DLL management"""
    
    # Signals
    dll_load_requested = Signal(str, str, dict)  # dll_path, ecu_name, config
    dll_unload_requested = Signal(str)  # ecu_name
    seed_requested = Signal(str, int)  # ecu_name, level
    key_send_requested = Signal(str, int, bytes)  # ecu_name, level, key
    
    def __init__(self, uds_backend=None):
        super().__init__()
        self.uds_backend = uds_backend
        self.dll_interface = None
        self.current_ecu = None
        self.security_status = {}
        
        self.setup_ui()
        self.setup_connections()
    
    def set_dll_interface(self, dll_interface):
        """Set the DLL interface"""
        self.dll_interface = dll_interface
        if dll_interface:
            dll_interface.dll_loaded.connect(self.on_dll_loaded)
            dll_interface.dll_unloaded.connect(self.on_dll_unloaded)
            dll_interface.dll_error.connect(self.on_dll_error)
            dll_interface.key_calculated.connect(self.on_key_calculated)
    
    def setup_ui(self):
        """Setup the enhanced security UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header with status
        header_layout = QHBoxLayout()
        self.security_title = QLabel("🔐 Security Access Management")
        self.security_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.security_status_label = QLabel("🔒 Not Connected")
        self.security_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        header_layout.addWidget(self.security_title)
        header_layout.addStretch()
        header_layout.addWidget(self.security_status_label)
        layout.addLayout(header_layout)
        
        # ECU Selection and Configuration
        ecu_group = self.create_ecu_selection_group()
        layout.addWidget(ecu_group)
        
        # DLL Management
        dll_group = self.create_dll_management_group()
        layout.addWidget(dll_group)
        
        # Security Operations
        security_group = self.create_security_operations_group()
        layout.addWidget(security_group)
        
        # Advanced Options
        advanced_group = self.create_advanced_options_group()
        layout.addWidget(advanced_group)
        
        # Status and Logging
        status_group = self.create_status_logging_group()
        layout.addWidget(status_group)
        
        layout.addStretch()
    
    def create_ecu_selection_group(self) -> QGroupBox:
        """Create ECU selection and configuration group"""
        group = QGroupBox("🚗 ECU Configuration")
        layout = QFormLayout(group)
        
        # ECU Selection
        self.ecu_combo = QComboBox()
        self.ecu_combo.setEditable(True)
        self.ecu_combo.addItems([
            "Engine_ECU_0x7E0",
            "Transmission_ECU_0x7E1", 
            "Body_ECU_0x7E2",
            "Gateway_ECU_0x7E3",
            "Custom_ECU"
        ])
        self.ecu_combo.currentTextChanged.connect(self.on_ecu_changed)
        layout.addRow("ECU Name:", self.ecu_combo)
        
        # CAN IDs
        can_id_layout = QHBoxLayout()
        self.tx_id_edit = QLineEdit("0x7E0")
        self.tx_id_edit.setPlaceholderText("TX ID (to ECU)")
        self.rx_id_edit = QLineEdit("0x7E8") 
        self.rx_id_edit.setPlaceholderText("RX ID (from ECU)")
        
        can_id_layout.addWidget(QLabel("TX ID:"))
        can_id_layout.addWidget(self.tx_id_edit)
        can_id_layout.addWidget(QLabel("RX ID:"))
        can_id_layout.addWidget(self.rx_id_edit)
        layout.addRow("CAN IDs:", can_id_layout)
        
        # Session Requirements
        self.session_combo = QComboBox()
        self.session_combo.addItems([
            "0x01 - Default Session",
            "0x02 - Programming Session", 
            "0x03 - Extended Session",
            "0x10 - Custom Session"
        ])
        layout.addRow("Required Session:", self.session_combo)
        
        return group
    
    def create_dll_management_group(self) -> QGroupBox:
        """Create DLL management group"""
        group = QGroupBox("📚 DLL Management")
        layout = QVBoxLayout(group)
        
        # DLL Selection
        dll_select_layout = QHBoxLayout()
        self.dll_path_edit = QLineEdit()
        self.dll_path_edit.setPlaceholderText("Select security access DLL...")
        
        browse_dll_btn = QPushButton("📁 Browse")
        browse_dll_btn.clicked.connect(self.browse_dll_file)
        
        load_dll_btn = QPushButton("⬇️ Load DLL")
        load_dll_btn.clicked.connect(self.load_dll)
        
        dll_select_layout.addWidget(self.dll_path_edit)
        dll_select_layout.addWidget(browse_dll_btn)
        dll_select_layout.addWidget(load_dll_btn)
        layout.addLayout(dll_select_layout)
        
        # Loaded DLLs Table
        self.dll_table = QTableWidget(0, 5)
        self.dll_table.setHorizontalHeaderLabels([
            "ECU Name", "DLL Status", "Info", "Levels", "Actions"
        ])
        self.dll_table.horizontalHeader().setStretchLastSection(True)
        self.dll_table.setMaximumHeight(120)
        layout.addWidget(self.dll_table)
        
        # DLL Configuration
        dll_config_layout = QHBoxLayout()
        
        save_config_btn = QPushButton("💾 Save Config")
        save_config_btn.clicked.connect(self.save_dll_config)
        
        load_config_btn = QPushButton("📂 Load Config")
        load_config_btn.clicked.connect(self.load_dll_config)
        
        test_dll_btn = QPushButton("🧪 Test DLL")
        test_dll_btn.clicked.connect(self.test_current_dll)
        
        dll_config_layout.addWidget(save_config_btn)
        dll_config_layout.addWidget(load_config_btn)
        dll_config_layout.addWidget(test_dll_btn)
        dll_config_layout.addStretch()
        layout.addLayout(dll_config_layout)
        
        return group
    
    def create_security_operations_group(self) -> QGroupBox:
        """Create security operations group"""
        group = QGroupBox("🔑 Security Operations")
        layout = QFormLayout(group)
        
        # Algorithm Provider Selection
        provider_layout = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "🤖 Built-in Algorithms",
            "📚 DLL (if loaded)",
            "🔄 Auto (DLL first, fallback to built-in)"
        ])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        self.provider_status = QLabel("✅ Ready")
        self.provider_status.setStyleSheet("color: green;")
        provider_layout.addWidget(self.provider_status)
        
        layout.addRow("Algorithm Provider:", provider_layout)
        
        # Security Level Selection
        level_layout = QHBoxLayout()
        self.security_level_combo = QComboBox()
        self.update_security_levels()
        
        self.level_description = QLabel("Service mode access")
        self.level_description.setStyleSheet("color: #666; font-style: italic;")
        
        level_layout.addWidget(self.security_level_combo)
        level_layout.addWidget(self.level_description)
        layout.addRow("Security Level:", level_layout)
        
        # Seed Display
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("Seed will appear here after request...")
        self.seed_edit.setReadOnly(True)
        layout.addRow("Received Seed:", self.seed_edit)
        
        # Key Input/Display
        key_layout = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Key will be calculated or enter manually...")
        
        self.manual_key_checkbox = QCheckBox("Manual")
        self.manual_key_checkbox.toggled.connect(self.on_manual_key_toggled)
        
        key_layout.addWidget(self.key_edit)
        key_layout.addWidget(self.manual_key_checkbox)
        layout.addRow("Security Key:", key_layout)
        
        # Operation Buttons
        buttons_layout = QHBoxLayout()
        
        self.request_seed_btn = QPushButton("🌱 Request Seed")
        self.request_seed_btn.clicked.connect(self.request_seed)
        
        self.calculate_key_btn = QPushButton("🧮 Calculate Key")
        self.calculate_key_btn.clicked.connect(self.calculate_key)
        self.calculate_key_btn.setEnabled(False)
        
        self.send_key_btn = QPushButton("🔓 Send Key")
        self.send_key_btn.clicked.connect(self.send_key)
        self.send_key_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.request_seed_btn)
        buttons_layout.addWidget(self.calculate_key_btn)
        buttons_layout.addWidget(self.send_key_btn)
        layout.addRow("Operations:", buttons_layout)
        
        return group
    
    def create_advanced_options_group(self) -> QGroupBox:
        """Create advanced options group"""
        group = QGroupBox("⚙️ Advanced Options")
        group.setCheckable(True)
        group.setChecked(False)
        layout = QFormLayout(group)
        
        # Timeouts
        timeout_layout = QHBoxLayout()
        self.seed_timeout_spin = QSpinBox()
        self.seed_timeout_spin.setRange(1000, 30000)
        self.seed_timeout_spin.setValue(5000)
        self.seed_timeout_spin.setSuffix(" ms")
        
        self.key_timeout_spin = QSpinBox()
        self.key_timeout_spin.setRange(1000, 30000)
        self.key_timeout_spin.setValue(3000)
        self.key_timeout_spin.setSuffix(" ms")
        
        timeout_layout.addWidget(QLabel("Seed:"))
        timeout_layout.addWidget(self.seed_timeout_spin)
        timeout_layout.addWidget(QLabel("Key:"))
        timeout_layout.addWidget(self.key_timeout_spin)
        layout.addRow("Timeouts:", timeout_layout)
        
        # Retry Options
        retry_layout = QHBoxLayout()
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 5)
        self.retry_count_spin.setValue(1)
        
        self.auto_retry_checkbox = QCheckBox("Auto retry on failure")
        self.auto_retry_checkbox.setChecked(True)
        
        retry_layout.addWidget(self.retry_count_spin)
        retry_layout.addWidget(self.auto_retry_checkbox)
        layout.addRow("Retry Attempts:", retry_layout)
        
        # Security Level Tracking
        self.multi_level_checkbox = QCheckBox("Track multiple security levels")
        layout.addRow("Multi-Level:", self.multi_level_checkbox)
        
        # Session Integration
        self.auto_session_checkbox = QCheckBox("Auto change to required session")
        self.auto_session_checkbox.setChecked(True)
        layout.addRow("Session Control:", self.auto_session_checkbox)
        
        return group
    
    def create_status_logging_group(self) -> QGroupBox:
        """Create status and logging group"""
        group = QGroupBox("📊 Status & Logging")
        layout = QVBoxLayout(group)
        
        # Status Overview
        status_layout = QGridLayout()
        
        # Current Security Status
        self.current_level_label = QLabel("Level: None")
        self.unlock_status_label = QLabel("Status: 🔒 Locked")
        self.last_operation_label = QLabel("Last: None")
        self.dll_status_label = QLabel("DLL: Not loaded")
        
        status_layout.addWidget(QLabel("Current Level:"), 0, 0)
        status_layout.addWidget(self.current_level_label, 0, 1)
        status_layout.addWidget(QLabel("Unlock Status:"), 0, 2)
        status_layout.addWidget(self.unlock_status_label, 0, 3)
        
        status_layout.addWidget(QLabel("Last Operation:"), 1, 0)
        status_layout.addWidget(self.last_operation_label, 1, 1)
        status_layout.addWidget(QLabel("DLL Status:"), 1, 2)
        status_layout.addWidget(self.dll_status_label, 1, 3)
        
        layout.addLayout(status_layout)
        
        # Operation Log
        self.operation_log = QTextEdit()
        self.operation_log.setMaximumHeight(100)
        self.operation_log.setPlaceholderText("Security operations will be logged here...")
        layout.addWidget(self.operation_log)
        
        # Log Controls
        log_controls = QHBoxLayout()
        clear_log_btn = QPushButton("🗑️ Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        
        export_log_btn = QPushButton("📄 Export Log")
        export_log_btn.clicked.connect(self.export_log)
        
        log_controls.addWidget(clear_log_btn)
        log_controls.addWidget(export_log_btn)
        log_controls.addStretch()
        layout.addLayout(log_controls)
        
        return group
    
    def setup_connections(self):
        """Setup signal connections"""
        self.security_level_combo.currentTextChanged.connect(self.on_security_level_changed)
    
    def update_security_levels(self):
        """Update available security levels"""
        self.security_level_combo.clear()
        
        # Default levels
        default_levels = [
            ("0x01", "Level 1 - Service Mode"),
            ("0x03", "Level 2 - Programming Mode"),
            ("0x05", "Level 3 - Advanced Service"),
            ("0x07", "Level 4 - Advanced Programming"),
            ("0x09", "Level 5 - OEM Service"),
            ("0x0B", "Level 6 - OEM Programming")
        ]
        
        for level_hex, description in default_levels:
            self.security_level_combo.addItem(f"{level_hex} - {description}")
    
    def on_ecu_changed(self, ecu_name: str):
        """Handle ECU selection change"""
        self.current_ecu = ecu_name
        self.log_message(f"Selected ECU: {ecu_name}")
        
        # Update CAN IDs based on ECU name if it contains IDs
        if "_0x" in ecu_name:
            try:
                tx_id = ecu_name.split("_0x")[1]
                if len(tx_id) >= 3:
                    self.tx_id_edit.setText(f"0x{tx_id[:3]}")
                    # Assume RX ID is TX ID + 8
                    rx_id_int = int(tx_id[:3], 16) + 8
                    self.rx_id_edit.setText(f"0x{rx_id_int:03X}")
            except ValueError:
                pass
    
    def on_provider_changed(self, provider: str):
        """Handle algorithm provider change"""
        if "DLL" in provider and not self.dll_interface:
            self.provider_status.setText("❌ No DLL loaded")
            self.provider_status.setStyleSheet("color: red;")
        elif "Built-in" in provider:
            self.provider_status.setText("✅ Built-in ready")
            self.provider_status.setStyleSheet("color: green;")
        else:
            self.provider_status.setText("🔄 Auto mode")
            self.provider_status.setStyleSheet("color: blue;")
    
    def on_security_level_changed(self, level_text: str):
        """Handle security level change"""
        if " - " in level_text:
            description = level_text.split(" - ", 1)[1]
            self.level_description.setText(description)
    
    def on_manual_key_toggled(self, enabled: bool):
        """Handle manual key input toggle"""
        self.key_edit.setReadOnly(not enabled)
        if enabled:
            self.key_edit.setPlaceholderText("Enter key manually...")
        else:
            self.key_edit.setPlaceholderText("Key will be calculated automatically...")
    
    def browse_dll_file(self):
        """Browse for DLL file"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("DLL Files (*.dll);;All Files (*)")
        
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.dll_path_edit.setText(file_path)
    
    def load_dll(self):
        """Load selected DLL"""
        dll_path = self.dll_path_edit.text().strip()
        if not dll_path:
            QMessageBox.warning(self, "No DLL Selected", "Please select a DLL file first.")
            return
        
        if not os.path.exists(dll_path):
            QMessageBox.warning(self, "File Not Found", f"DLL file not found: {dll_path}")
            return
        
        ecu_name = self.ecu_combo.currentText()
        if not ecu_name:
            QMessageBox.warning(self, "No ECU Selected", "Please select an ECU name first.")
            return
        
        # Prepare configuration
        config = {
            "can_tx_id": self.tx_id_edit.text(),
            "can_rx_id": self.rx_id_edit.text(),
            "required_session": self.session_combo.currentText(),
            "timeouts": {
                "seed_request": self.seed_timeout_spin.value(),
                "key_send": self.key_timeout_spin.value()
            }
        }
        
        self.log_message(f"Loading DLL: {dll_path} for ECU: {ecu_name}")
        self.dll_load_requested.emit(dll_path, ecu_name, config)
    
    def request_seed(self):
        """Request security access seed"""
        if not self.current_ecu:
            QMessageBox.warning(self, "No ECU Selected", "Please select an ECU first.")
            return
        
        level_text = self.security_level_combo.currentText()
        try:
            level = int(level_text.split(" - ")[0], 16)
            self.log_message(f"Requesting seed for level 0x{level:02X}")
            self.seed_requested.emit(self.current_ecu, level)
            
            # Enable calculate button
            self.calculate_key_btn.setEnabled(True)
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Level", "Invalid security level format.")
    
    def calculate_key(self):
        """Calculate security key"""
        seed_text = self.seed_edit.text().strip()
        if not seed_text:
            QMessageBox.warning(self, "No Seed", "No seed available. Request seed first.")
            return
        
        try:
            # Parse seed
            seed_parts = seed_text.replace(',', ' ').split()
            seed_bytes = bytes([int(part, 16) for part in seed_parts])
            
            provider = self.provider_combo.currentText()
            
            if "DLL" in provider and self.dll_interface and self.current_ecu:
                # Use DLL calculation
                level_text = self.security_level_combo.currentText()
                level = int(level_text.split(" - ")[0], 16)
                
                calculated_key = self.dll_interface.calculate_key_with_dll(
                    self.current_ecu, seed_bytes, level
                )
                
                if calculated_key:
                    key_hex = ' '.join(f'{b:02X}' for b in calculated_key)
                    self.key_edit.setText(key_hex)
                    self.send_key_btn.setEnabled(True)
                    self.log_message(f"DLL calculated key: {key_hex}")
                else:
                    self.log_message("DLL key calculation failed, trying built-in...")
                    self._calculate_builtin_key(seed_bytes)
            else:
                # Use built-in calculation
                self._calculate_builtin_key(seed_bytes)
                
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Seed", f"Error parsing seed: {e}")
    
    def _calculate_builtin_key(self, seed_bytes: bytes):
        """Calculate key using built-in algorithms"""
        if self.uds_backend:
            key_bytes = self.uds_backend.calculate_security_key(seed_bytes, "xor")
            key_hex = ' '.join(f'{b:02X}' for b in key_bytes)
            self.key_edit.setText(key_hex)
            self.send_key_btn.setEnabled(True)
            self.log_message(f"Built-in calculated key: {key_hex}")
    
    def send_key(self):
        """Send security key"""
        key_text = self.key_edit.text().strip()
        if not key_text:
            QMessageBox.warning(self, "No Key", "No key available. Calculate key first.")
            return
        
        try:
            key_parts = key_text.replace(',', ' ').split()
            key_bytes = bytes([int(part, 16) for part in key_parts])
            
            level_text = self.security_level_combo.currentText()
            level = int(level_text.split(" - ")[0], 16) + 1  # Even level for key send
            
            self.log_message(f"Sending key for level 0x{level:02X}")
            self.key_send_requested.emit(self.current_ecu, level, key_bytes)
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Key", f"Error parsing key: {e}")
    
    def on_dll_loaded(self, ecu_name: str, dll_info: str):
        """Handle DLL loaded signal"""
        self.log_message(f"✅ DLL loaded for {ecu_name}: {dll_info}")
        self.update_dll_table()
        self.dll_status_label.setText(f"DLL: ✅ {ecu_name}")
        self.dll_status_label.setStyleSheet("color: green;")
    
    def on_dll_unloaded(self, ecu_name: str):
        """Handle DLL unloaded signal"""
        self.log_message(f"DLL unloaded for {ecu_name}")
        self.update_dll_table()
    
    def on_dll_error(self, ecu_name: str, error: str):
        """Handle DLL error signal"""
        self.log_message(f"❌ DLL error for {ecu_name}: {error}")
        QMessageBox.warning(self, "DLL Error", f"Error with {ecu_name}:\n{error}")
    
    def on_key_calculated(self, ecu_name: str, seed: bytes, key: bytes):
        """Handle key calculated signal"""
        key_hex = ' '.join(f'{b:02X}' for b in key)
        self.key_edit.setText(key_hex)
        self.send_key_btn.setEnabled(True)
        self.log_message(f"🔑 Key calculated for {ecu_name}: {key_hex}")
    
    def update_dll_table(self):
        """Update the DLL table display"""
        if not self.dll_interface:
            return
        
        ecus = self.dll_interface.get_available_ecus()
        self.dll_table.setRowCount(len(ecus))
        
        for row, ecu_name in enumerate(ecus):
            ecu_info = self.dll_interface.get_ecu_info(ecu_name)
            if ecu_info:
                # ECU Name
                self.dll_table.setItem(row, 0, QTableWidgetItem(ecu_name))
                
                # Status
                status = "✅ Loaded" if ecu_info['initialized'] else "❌ Error"
                self.dll_table.setItem(row, 1, QTableWidgetItem(status))
                
                # Info
                self.dll_table.setItem(row, 2, QTableWidgetItem(ecu_info['dll_info']))
                
                # Levels
                levels = ', '.join(map(str, ecu_info['supported_levels']))
                self.dll_table.setItem(row, 3, QTableWidgetItem(levels))
                
                # Actions
                unload_btn = QPushButton("🗑️ Unload")
                unload_btn.clicked.connect(
                    lambda checked, name=ecu_name: self.dll_unload_requested.emit(name)
                )
                self.dll_table.setCellWidget(row, 4, unload_btn)
    
    def save_dll_config(self):
        """Save DLL configuration"""
        if not self.dll_interface:
            return
        
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("JSON Files (*.json)")
        
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            success = self.dll_interface.save_dll_config(file_path)
            if success:
                self.log_message(f"Configuration saved to {file_path}")
            else:
                QMessageBox.warning(self, "Save Error", "Failed to save configuration.")
    
    def load_dll_config(self):
        """Load DLL configuration"""
        if not self.dll_interface:
            return
        
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("JSON Files (*.json)")
        
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            success = self.dll_interface.load_dll_config(file_path)
            if success:
                self.log_message(f"Configuration loaded from {file_path}")
            else:
                QMessageBox.warning(self, "Load Error", "Failed to load configuration.")
    
    def test_current_dll(self):
        """Test current DLL functionality"""
        if not self.dll_interface or not self.current_ecu:
            QMessageBox.warning(self, "No DLL", "No DLL loaded for current ECU.")
            return
        
        result = self.dll_interface.test_dll_functionality(self.current_ecu)
        
        if result['success']:
            msg = f"DLL Test Successful!\n\n"
            msg += f"Test Seed: {result['test_seed']}\n"
            msg += f"Calculated Key: {result['calculated_key']}\n"
            msg += f"Test Level: {result['test_level']}"
            QMessageBox.information(self, "DLL Test", msg)
        else:
            QMessageBox.warning(self, "DLL Test Failed", f"Error: {result['error']}")
    
    def log_message(self, message: str):
        """Log a message to the operation log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.operation_log.append(formatted_message)
        print(formatted_message)  # Also print to console
    
    def clear_log(self):
        """Clear the operation log"""
        self.operation_log.clear()
    
    def export_log(self):
        """Export the operation log"""
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("Text Files (*.txt)")
        
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.operation_log.toPlainText())
                self.log_message(f"Log exported to {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export log: {e}")
    
    def update_security_status(self, level: int, unlocked: bool, seed: str = ""):
        """Update security status display"""
        self.current_level_label.setText(f"Level: 0x{level:02X}")
        
        if unlocked:
            self.unlock_status_label.setText("Status: 🔓 Unlocked")
            self.unlock_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.security_status_label.setText("🔓 Security Unlocked")
            self.security_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.unlock_status_label.setText("Status: 🔒 Locked") 
            self.unlock_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.security_status_label.setText("🔒 Security Locked")
            self.security_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        if seed:
            self.seed_edit.setText(seed)
            self.calculate_key_btn.setEnabled(True)
