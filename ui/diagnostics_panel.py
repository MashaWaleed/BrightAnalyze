"""
Updated Diagnostics Panel for Professional CAN Analyzer
Integrated with UDS Backend using udsoncan and python-can-isotp
"""

import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QGroupBox, QFormLayout, QLabel, QLineEdit,
                               QPushButton, QComboBox, QTextEdit, QTableWidget,
                               QTableWidgetItem, QCheckBox, QSpinBox, QProgressBar,
                               QSplitter, QTreeWidget, QTreeWidgetItem, QMessageBox,
                               QApplication, QFileDialog, QScrollArea, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QColor

from .diagnostics_constants import *
from .diagnostics_utils import DiagnosticsUtils

class DiagnosticsPanel(QWidget):
    """Professional diagnostics panel with full UDS integration"""
    
    # Signals
    uds_connect_requested = Signal(dict)  # {tx_id, rx_id}
    uds_disconnect_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.uds_backend = None
        self.utils = DiagnosticsUtils()
        
        # State tracking
        self.current_session = {"type": 0x01, "name": "Default Session"}
        self.security_status = {"level": 0, "unlocked": False, "seed": ""}
        self.dtc_list = []
        self.connection_status = {"connected": False, "tx_id": "0x7E0", "rx_id": "0x7E8"}
        
        # Auto-refresh timers
        self.tester_present_timer = QTimer()
        self.tester_present_timer.timeout.connect(self.send_tester_present)
        
        self.setup_ui()
        self.apply_professional_style()
        
    def set_uds_backend(self, uds_backend):
        """Set the UDS backend and connect signals"""
        self.uds_backend = uds_backend
        if self.uds_backend:
            # Connect UDS backend signals with thread-safe connections
            self.uds_backend.uds_response_received.connect(self.handle_uds_response, Qt.QueuedConnection)
            self.uds_backend.uds_error_occurred.connect(self.handle_uds_error, Qt.QueuedConnection)
            self.uds_backend.session_changed.connect(self.handle_session_changed, Qt.QueuedConnection)
            self.uds_backend.security_status_changed.connect(self.handle_security_status_changed, Qt.QueuedConnection)
            self.uds_backend.dtc_data_received.connect(self.handle_dtc_data, Qt.QueuedConnection)
            self.uds_backend.data_identifier_received.connect(self.handle_data_identifier, Qt.QueuedConnection)
            
            # Update connection controls
            self.update_connection_status()
        
    def setup_ui(self):
        """Setup the diagnostics panel UI with scroll areas that expand to fill available space"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Remove fixed height - let the panel expand to fill available space in the stacked widget
        # The panel will expand to the upper boundary of the status bar automatically
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connection controls at top (always visible)
        self.setup_connection_controls(layout)
        
        # Create tab widget for different diagnostic functions with scroll areas
        self.tab_widget = QTabWidget()
        # Let tab widget expand to fill remaining space after connection controls
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Setup tabs with scroll areas
        self.setup_uds_services_tab()
        self.setup_dtc_tab()
        self.setup_data_by_id_tab()
        self.setup_security_tab()
        # Removed OBD tab as not needed
        
        layout.addWidget(self.tab_widget)
        # Removed addStretch() to allow tab widget to expand and fill available space
        
    def setup_connection_controls(self, layout):
        """Setup UDS connection controls"""
        connection_group = QGroupBox("🔗 UDS Connection")
        connection_layout = QFormLayout(connection_group)
        
        # CAN IDs
        ids_layout = QHBoxLayout()
        self.tx_id_edit = QLineEdit("7E0")
        self.tx_id_edit.setPlaceholderText("TX ID (hex)")
        self.tx_id_edit.setMaximumWidth(80)
        
        self.rx_id_edit = QLineEdit("7E8")
        self.rx_id_edit.setPlaceholderText("RX ID (hex)")
        self.rx_id_edit.setMaximumWidth(80)
        
        ids_layout.addWidget(QLabel("TX:"))
        ids_layout.addWidget(self.tx_id_edit)
        ids_layout.addWidget(QLabel("RX:"))
        ids_layout.addWidget(self.rx_id_edit)
        ids_layout.addStretch()
        
        connection_layout.addRow("CAN IDs:", ids_layout)
        
        # Connection controls
        conn_buttons = QHBoxLayout()
        self.connect_uds_btn = QPushButton("🔌 Connect UDS")
        self.connect_uds_btn.clicked.connect(self.connect_uds)
        
        self.disconnect_uds_btn = QPushButton("🔌 Disconnect UDS")
        self.disconnect_uds_btn.clicked.connect(self.disconnect_uds)
        self.disconnect_uds_btn.setEnabled(False)
        
        self.tester_present_checkbox = QCheckBox("Auto Tester Present")
        self.tester_present_checkbox.toggled.connect(self.toggle_tester_present)
        
        conn_buttons.addWidget(self.connect_uds_btn)
        conn_buttons.addWidget(self.disconnect_uds_btn)
        conn_buttons.addWidget(self.tester_present_checkbox)
        conn_buttons.addStretch()
        
        connection_layout.addRow(conn_buttons)
        
        # Status display
        self.connection_status_label = QLabel("🔴 UDS Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        connection_layout.addRow("Status:", self.connection_status_label)
        
        layout.addWidget(connection_group)
        
    def setup_uds_services_tab(self):
        """Setup UDS services tab with scroll area"""
        # Create main widget for the tab content
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Session management
        session_group = QGroupBox("🔐 Session Management")
        session_layout = QFormLayout(session_group)
        
        self.session_combo = QComboBox()
        self.session_combo.addItems(UDS_SESSIONS)
        session_layout.addRow("Target Session:", self.session_combo)
        
        self.current_session_label = QLabel("Default Session")
        self.current_session_label.setStyleSheet("font-weight: bold; color: blue;")
        session_layout.addRow("Current Session:", self.current_session_label)
        
        session_buttons = QHBoxLayout()
        self.start_session_btn = QPushButton("🚀 Change Session")
        self.start_session_btn.clicked.connect(self.change_diagnostic_session)
        session_buttons.addWidget(self.start_session_btn)
        session_layout.addRow(session_buttons)
        
        layout.addWidget(session_group)
        
        # Service request
        service_group = QGroupBox("🛠️ Service Request")
        service_layout = QFormLayout(service_group)
        
        self.service_combo = QComboBox()
        self.service_combo.addItems(UDS_SERVICES)
        service_layout.addRow("Service:", self.service_combo)
        
        self.sub_function_edit = QLineEdit("00")
        self.sub_function_edit.setPlaceholderText("Sub-function (hex)")
        service_layout.addRow("Sub-function:", self.sub_function_edit)
        
        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("Data bytes (hex, space separated)")
        service_layout.addRow("Data:", self.data_edit)
        
        service_buttons = QHBoxLayout()
        self.send_request_btn = QPushButton("📤 Send Request")
        self.send_request_btn.clicked.connect(self.send_uds_request)
        
        self.send_raw_btn = QPushButton("📤 Send Raw")
        self.send_raw_btn.clicked.connect(self.send_raw_request)
        
        service_buttons.addWidget(self.send_request_btn)
        service_buttons.addWidget(self.send_raw_btn)
        service_layout.addRow(service_buttons)
        
        layout.addWidget(service_group)
        
        # ECU Reset
        reset_group = QGroupBox("🔄 ECU Reset")
        reset_layout = QFormLayout(reset_group)
        
        self.reset_type_combo = QComboBox()
        self.reset_type_combo.addItems([
            "0x01 - Hard Reset",
            "0x02 - Key Off On Reset", 
            "0x03 - Soft Reset"
        ])
        reset_layout.addRow("Reset Type:", self.reset_type_combo)
        
        self.ecu_reset_btn = QPushButton("🔄 ECU Reset")
        self.ecu_reset_btn.clicked.connect(self.perform_ecu_reset)
        reset_layout.addRow(self.ecu_reset_btn)
        
        layout.addWidget(reset_group)
        
        # Response display
        response_group = QGroupBox("📥 Response Log")
        response_layout = QVBoxLayout(response_group)
        
        self.response_text = QTextEdit()
        self.response_text.setMaximumHeight(200)
        self.response_text.setFont(QFont("Consolas", 9))
        self.response_text.setReadOnly(True)
        response_layout.addWidget(self.response_text)
        
        clear_btn = QPushButton("🗑️ Clear Log")
        clear_btn.clicked.connect(self.response_text.clear)
        response_layout.addWidget(clear_btn)
        
        layout.addWidget(response_group)
        layout.addStretch()
        
        # Create scroll area and add content widget
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(scroll_area, "🛠️ UDS Services")
        
    def setup_dtc_tab(self):
        """Setup DTC management tab with scroll area"""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # DTC controls
        control_group = QGroupBox("🚨 DTC Management")
        control_layout = QHBoxLayout(control_group)
        
        self.read_dtc_btn = QPushButton("📖 Read DTCs")
        self.read_dtc_btn.clicked.connect(self.read_dtcs)
        control_layout.addWidget(self.read_dtc_btn)
        
        self.read_pending_btn = QPushButton("⏳ Read Pending")
        self.read_pending_btn.clicked.connect(self.read_pending_dtcs)
        control_layout.addWidget(self.read_pending_btn)
        
        self.clear_dtc_btn = QPushButton("🗑️ Clear DTCs")
        self.clear_dtc_btn.clicked.connect(self.clear_dtcs_clicked)
        control_layout.addWidget(self.clear_dtc_btn)
        
        control_layout.addStretch()
        layout.addWidget(control_group)
        
        # DTC list
        dtc_list_group = QGroupBox("📋 Diagnostic Trouble Codes")
        dtc_list_layout = QVBoxLayout(dtc_list_group)
        
        self.dtc_table = QTableWidget(0, 6)
        self.dtc_table.setHorizontalHeaderLabels([
            "DTC Code", "Status", "Description", "Raw Bytes", "Status Byte", "Priority"
        ])
        self.dtc_table.horizontalHeader().setStretchLastSection(True)
        self.dtc_table.itemSelectionChanged.connect(self.show_dtc_details)
        dtc_list_layout.addWidget(self.dtc_table)
        
        # DTC count label
        self.dtc_count_label = QLabel("DTCs: 0")
        self.dtc_count_label.setStyleSheet("font-weight: bold;")
        dtc_list_layout.addWidget(self.dtc_count_label)
        
        layout.addWidget(dtc_list_group)
        
        # DTC details
        details_group = QGroupBox("🔍 DTC Details")
        details_layout = QVBoxLayout(details_group)
        
        self.dtc_details = QTextEdit()
        self.dtc_details.setMaximumHeight(100)
        self.dtc_details.setReadOnly(True)
        details_layout.addWidget(self.dtc_details)
        
        layout.addWidget(details_group)
        layout.addStretch()
        
        # Create scroll area and add content widget
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(scroll_area, "🚨 DTCs")
        
    def setup_data_by_id_tab(self):
        """Setup data by identifier tab with scroll area"""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Data identifier controls
        id_group = QGroupBox("🆔 Data Identifier")
        id_layout = QFormLayout(id_group)
        
        self.did_combo = QComboBox()
        self.did_combo.setEditable(True)
        self.did_combo.addItems(DATA_IDENTIFIERS)
        id_layout.addRow("Data Identifier:", self.did_combo)
        
        did_buttons = QHBoxLayout()
        self.read_did_btn = QPushButton("📖 Read DID")
        self.read_did_btn.clicked.connect(self.read_data_identifier)
        
        self.write_did_btn = QPushButton("✏️ Write DID")
        self.write_did_btn.clicked.connect(self.write_data_identifier)
        
        self.read_all_btn = QPushButton("📖 Read All Common")
        self.read_all_btn.clicked.connect(self.read_all_common_dids)
        
        did_buttons.addWidget(self.read_did_btn)
        did_buttons.addWidget(self.write_did_btn)
        did_buttons.addWidget(self.read_all_btn)
        id_layout.addRow(did_buttons)
        
        # Write data
        self.write_data_edit = QLineEdit()
        self.write_data_edit.setPlaceholderText("Data to write (hex, space separated)")
        id_layout.addRow("Write Data:", self.write_data_edit)
        
        layout.addWidget(id_group)
        
        # Data values table
        values_group = QGroupBox("📊 Data Values")
        values_layout = QVBoxLayout(values_group)
        
        self.data_values_table = QTableWidget(0, 5)
        self.data_values_table.setHorizontalHeaderLabels([
            "DID", "Name", "Raw Data", "Decoded Value", "Timestamp"
        ])
        self.data_values_table.horizontalHeader().setStretchLastSection(True)
        values_layout.addWidget(self.data_values_table)
        
        layout.addWidget(values_group)
        layout.addStretch()
        
        # Create scroll area and add content widget
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(scroll_area, "🆔 Data by ID")
        
    def setup_security_tab(self):
        """Setup enhanced security access tab with DLL support and scroll area"""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Import the DLL interface
        try:
            from security_dll_interface import SecurityDLLInterface
            self.dll_interface = SecurityDLLInterface()
        except ImportError:
            self.dll_interface = None
            print("⚠️  Security DLL interface not available")
        
        # ECU Configuration Section
        ecu_group = QGroupBox("🚗 ECU Configuration")
        ecu_layout = QFormLayout(ecu_group)
        
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
        ecu_layout.addRow("ECU Name:", self.ecu_combo)
        
        # Algorithm Provider Selection
        provider_layout = QHBoxLayout()
        self.algorithm_provider_combo = QComboBox()
        self.algorithm_provider_combo.addItems([
            "🤖 Built-in Algorithms",
            "📚 DLL (if loaded)",
            "🔄 Auto (DLL first, fallback)"
        ])
        self.algorithm_provider_combo.currentTextChanged.connect(self.on_provider_changed)
        
        self.provider_status_label = QLabel("✅ Ready")
        self.provider_status_label.setStyleSheet("color: green; font-weight: bold;")
        
        provider_layout.addWidget(self.algorithm_provider_combo)
        provider_layout.addWidget(self.provider_status_label)
        ecu_layout.addRow("Algorithm Provider:", provider_layout)
        
        layout.addWidget(ecu_group)
        
        # DLL Management Section
        if self.dll_interface:
            dll_group = QGroupBox("📚 DLL Management")
            dll_layout = QVBoxLayout(dll_group)
            
            # DLL Loading
            dll_load_layout = QHBoxLayout()
            self.dll_path_edit = QLineEdit()
            self.dll_path_edit.setPlaceholderText("Select security access DLL...")
            
            browse_dll_btn = QPushButton("📁 Browse")
            browse_dll_btn.clicked.connect(self.browse_dll_file)
            
            load_dll_btn = QPushButton("⬇️ Load DLL")
            load_dll_btn.clicked.connect(self.load_dll)
            
            dll_load_layout.addWidget(self.dll_path_edit)
            dll_load_layout.addWidget(browse_dll_btn)
            dll_load_layout.addWidget(load_dll_btn)
            dll_layout.addLayout(dll_load_layout)
            
            # DLL Status
            self.dll_status_label = QLabel("📚 No DLL loaded")
            self.dll_status_label.setStyleSheet("color: #666; font-style: italic;")
            dll_layout.addWidget(self.dll_status_label)
            
            # DLL Configuration Buttons
            dll_config_layout = QHBoxLayout()
            
            save_config_btn = QPushButton("💾 Save Config")
            save_config_btn.clicked.connect(self.save_dll_config)
            
            load_config_btn = QPushButton("📂 Load Config")
            load_config_btn.clicked.connect(self.load_dll_config)
            
            test_dll_btn = QPushButton("🧪 Test DLL")
            test_dll_btn.clicked.connect(self.test_dll)
            
            dll_config_layout.addWidget(save_config_btn)
            dll_config_layout.addWidget(load_config_btn)
            dll_config_layout.addWidget(test_dll_btn)
            dll_config_layout.addStretch()
            dll_layout.addLayout(dll_config_layout)
            
            layout.addWidget(dll_group)
        
        # Security Operations (Enhanced)
        level_group = QGroupBox("🔐 Security Access Operations")
        level_layout = QFormLayout(level_group)
        
        # Enhanced Security Level Selection
        self.security_level_combo = QComboBox()
        self.security_level_combo.addItems(SECURITY_LEVELS)
        self.security_level_combo.currentTextChanged.connect(self.on_security_level_changed)
        level_layout.addRow("Security Level:", self.security_level_combo)
        
        # Level Description
        self.level_description_label = QLabel("Service mode access")
        self.level_description_label.setStyleSheet("color: #666; font-style: italic;")
        level_layout.addRow("Description:", self.level_description_label)
        
        # Seed Display (Enhanced)
        seed_layout = QHBoxLayout()
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("Seed value (will be received)")
        self.seed_edit.setReadOnly(True)
        
        self.seed_copy_btn = QPushButton("📋")
        self.seed_copy_btn.setMaximumWidth(30)
        self.seed_copy_btn.setToolTip("Copy seed to clipboard")
        self.seed_copy_btn.clicked.connect(self.copy_seed)
        
        seed_layout.addWidget(self.seed_edit)
        seed_layout.addWidget(self.seed_copy_btn)
        level_layout.addRow("Received Seed:", seed_layout)
        
        # Key Input/Display (Enhanced)
        key_layout = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Key will be calculated or enter manually")
        
        self.key_copy_btn = QPushButton("📋")
        self.key_copy_btn.setMaximumWidth(30)
        self.key_copy_btn.setToolTip("Copy key to clipboard")
        self.key_copy_btn.clicked.connect(self.copy_key)
        
        self.manual_key_checkbox = QCheckBox("Manual")
        self.manual_key_checkbox.toggled.connect(self.on_manual_key_toggled)
        
        key_layout.addWidget(self.key_edit)
        key_layout.addWidget(self.key_copy_btn)
        key_layout.addWidget(self.manual_key_checkbox)
        level_layout.addRow("Security Key:", key_layout)
        
        # Enhanced Operation Buttons
        security_buttons = QHBoxLayout()
        self.request_seed_btn = QPushButton("🌱 Request Seed")
        self.request_seed_btn.clicked.connect(self.request_security_seed)
        
        self.calculate_key_btn = QPushButton("🧮 Calculate Key")
        self.calculate_key_btn.clicked.connect(self.calculate_security_key)
        self.calculate_key_btn.setEnabled(False)
        
        self.send_key_btn = QPushButton("🔑 Send Key")
        self.send_key_btn.clicked.connect(self.send_security_key)
        self.send_key_btn.setEnabled(False)
        
        # Additional buttons
        self.clear_security_btn = QPushButton("🗑️ Clear")
        self.clear_security_btn.clicked.connect(self.clear_security_data)
        
        security_buttons.addWidget(self.request_seed_btn)
        security_buttons.addWidget(self.calculate_key_btn)
        security_buttons.addWidget(self.send_key_btn)
        security_buttons.addWidget(self.clear_security_btn)
        level_layout.addRow("Operations:", security_buttons)
        
        # Enhanced Security Status
        status_layout = QHBoxLayout()
        self.security_status_label = QLabel("🔒 Security Locked")
        self.security_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        self.current_level_label = QLabel("Level: None")
        self.current_level_label.setStyleSheet("color: #666;")
        
        status_layout.addWidget(self.security_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.current_level_label)
        level_layout.addRow("Status:", status_layout)
        
        layout.addWidget(level_group)
        
        # Enhanced Key Calculation Help
        calc_group = QGroupBox("🧮 Key Calculation Methods")
        calc_layout = QVBoxLayout(calc_group)
        
        calc_info = QTextEdit()
        calc_info.setMaximumHeight(120)
        calc_info.setReadOnly(True)
        calc_info.setHtml(self._get_enhanced_help_text())
        calc_layout.addWidget(calc_info)
        
        calc_buttons = QHBoxLayout()
        self.auto_calc_btn = QPushButton("🤖 Auto XOR")
        self.auto_calc_btn.clicked.connect(lambda: self.auto_calculate_key("xor"))
        
        self.auto_calc_add_btn = QPushButton("🤖 Auto ADD")
        self.auto_calc_add_btn.clicked.connect(lambda: self.auto_calculate_key("add"))
        
        self.auto_calc_comp_btn = QPushButton("🤖 Auto Complement")
        self.auto_calc_comp_btn.clicked.connect(lambda: self.auto_calculate_key("complement"))
        
        # Advanced algorithm buttons
        self.auto_calc_crc_btn = QPushButton("🤖 CRC16")
        self.auto_calc_crc_btn.clicked.connect(lambda: self.auto_calculate_key("crc16"))
        
        calc_buttons.addWidget(self.auto_calc_btn)
        calc_buttons.addWidget(self.auto_calc_add_btn)
        calc_buttons.addWidget(self.auto_calc_comp_btn)
        calc_buttons.addWidget(self.auto_calc_crc_btn)
        calc_buttons.addStretch()
        calc_layout.addLayout(calc_buttons)
        
        layout.addWidget(calc_group)
        
        # Security Session Integration
        session_group = QGroupBox("🔗 Session Integration")
        session_layout = QFormLayout(session_group)
        
        self.auto_session_checkbox = QCheckBox("Auto change to required session")
        self.auto_session_checkbox.setChecked(True)
        session_layout.addRow("Session Control:", self.auto_session_checkbox)
        
        self.required_session_combo = QComboBox()
        self.required_session_combo.addItems([
            "0x01 - Default Session",
            "0x02 - Programming Session",
            "0x03 - Extended Session"
        ])
        self.required_session_combo.setCurrentText("0x02 - Programming Session")
        session_layout.addRow("Required Session:", self.required_session_combo)
        
        layout.addWidget(session_group)
        
        layout.addStretch()
        
        # Create scroll area and add content widget
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(scroll_area, "🔐 Security")
        
        # Connect DLL interface signals if available
        if self.dll_interface:
            self.dll_interface.dll_loaded.connect(self.on_dll_loaded)
            self.dll_interface.dll_unloaded.connect(self.on_dll_unloaded)
            self.dll_interface.dll_error.connect(self.on_dll_error)
            self.dll_interface.key_calculated.connect(self.on_dll_key_calculated)
        
    def setup_obd_tab(self):
        """Setup OBD-II tab with scroll area"""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # OBD-II Mode selection
        mode_group = QGroupBox("📊 OBD-II Modes")
        mode_layout = QFormLayout(mode_group)
        
        self.obd_mode_combo = QComboBox()
        self.obd_mode_combo.addItems(OBD_MODES)
        mode_layout.addRow("Mode:", self.obd_mode_combo)
        
        self.pid_edit = QLineEdit("00")
        self.pid_edit.setPlaceholderText("PID (hex)")
        mode_layout.addRow("PID:", self.pid_edit)
        
        obd_buttons = QHBoxLayout()
        self.send_obd_btn = QPushButton("📤 Send OBD Request")
        self.send_obd_btn.clicked.connect(self.send_obd_request)
        obd_buttons.addWidget(self.send_obd_btn)
        mode_layout.addRow(obd_buttons)
        
        layout.addWidget(mode_group)
        
        # Live data display
        live_group = QGroupBox("📈 Live OBD Data")
        live_layout = QVBoxLayout(live_group)
        
        self.obd_data_table = QTableWidget(0, 4)
        self.obd_data_table.setHorizontalHeaderLabels(["PID", "Parameter", "Value", "Unit"])
        self.obd_data_table.horizontalHeader().setStretchLastSection(True)
        live_layout.addWidget(self.obd_data_table)
        
        # Populate with sample data initially
        self.utils.populate_obd_data(self.obd_data_table)
        
        layout.addWidget(live_group)
        layout.addStretch()
        
        # Create scroll area and add content widget
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(scroll_area, "🚗 OBD-II")
        
    # === Connection Methods ===
    
    def connect_uds(self):
        """Connect UDS backend"""
        try:
            tx_id = int(self.tx_id_edit.text(), 16)
            rx_id = int(self.rx_id_edit.text(), 16)
            
            if self.uds_backend:
                self.uds_backend.set_can_ids(tx_id, rx_id)
                success = self.uds_backend.connect()
                
                if success:
                    self.connection_status["connected"] = True
                    self.connection_status["tx_id"] = f"0x{tx_id:X}"
                    self.connection_status["rx_id"] = f"0x{rx_id:X}"
                    self.update_connection_status()
                    self.log_response("UDS connected successfully")
                else:
                    QMessageBox.warning(self, "Connection Failed", "Failed to connect UDS")
            else:
                QMessageBox.warning(self, "No Backend", "UDS backend not available")
                
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid hex CAN IDs")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"UDS connection error: {str(e)}")
    
    def disconnect_uds(self):
        """Disconnect UDS backend"""
        if self.uds_backend:
            self.uds_backend.disconnect()
            
        self.connection_status["connected"] = False
        self.update_connection_status()
        self.log_response("UDS disconnected")
    
    def update_connection_status(self):
        """Update connection status display"""
        if self.connection_status["connected"]:
            status_text = f"🟢 UDS Connected ({self.connection_status['tx_id']} → {self.connection_status['rx_id']})"
            self.connection_status_label.setText(status_text)
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            self.connect_uds_btn.setEnabled(False)
            self.disconnect_uds_btn.setEnabled(True)
            
            # Enable service buttons
            self.send_request_btn.setEnabled(True)
            self.send_raw_btn.setEnabled(True)
            self.start_session_btn.setEnabled(True)
            self.ecu_reset_btn.setEnabled(True)
            self.read_dtc_btn.setEnabled(True)
            self.read_did_btn.setEnabled(True)
            self.request_seed_btn.setEnabled(True)
        else:
            self.connection_status_label.setText("🔴 UDS Disconnected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            
            self.connect_uds_btn.setEnabled(True)
            self.disconnect_uds_btn.setEnabled(False)
            
            # Disable service buttons
            self.send_request_btn.setEnabled(False)
            self.send_raw_btn.setEnabled(False)
            self.start_session_btn.setEnabled(False)
            self.ecu_reset_btn.setEnabled(False)
            self.read_dtc_btn.setEnabled(False)
            self.read_did_btn.setEnabled(False)
            self.request_seed_btn.setEnabled(False)
            self.send_key_btn.setEnabled(False)
    
    def toggle_tester_present(self, enabled):
        """Toggle automatic tester present"""
        if enabled and self.connection_status["connected"]:
            self.tester_present_timer.start(1000)  # Every 1 seconds
            self.log_response("Auto tester present enabled")
        else:
            self.tester_present_timer.stop()
            self.log_response("Auto tester present disabled")
    
    def send_tester_present(self):
        """Send tester present message"""
        if self.uds_backend and self.connection_status["connected"]:
            self.uds_backend.tester_present()
    
    # === UDS Service Methods ===
    
    def change_diagnostic_session(self):
        """Change diagnostic session"""
        if not self.uds_backend:
            return
            
        session_text = self.session_combo.currentText()
        session_type = int(session_text.split(" - ")[0], 16)
        
        self.uds_backend.diagnostic_session_control(session_type)
        self.log_response(f"→ Session Control: {session_text}")
    
    def send_uds_request(self):
        """Send UDS service request"""
        if not self.uds_backend:
            return
            
        service_text = self.service_combo.currentText()
        service = int(service_text.split(" - ")[0], 16)
        
        try:
            # Parse sub-function and data
            sub_func_text = self.sub_function_edit.text().strip()
            data_text = self.data_edit.text().strip()
            
            # Build data bytes
            data_bytes = b''
            if sub_func_text:
                data_bytes += bytes([int(sub_func_text, 16)])
            if data_text:
                hex_parts = data_text.replace(',', ' ').split()
                data_bytes += bytes([int(part, 16) for part in hex_parts if part])
            
            self.uds_backend.send_raw_request(service, data_bytes)
            self.log_response(f"→ Raw Request: 0x{service:02X} {data_bytes.hex().upper()}")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Invalid hex data: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Request Error", f"Failed to send request: {str(e)}")
    
    def send_raw_request(self):
        """Send raw UDS request"""
        self.send_uds_request()  # Same implementation
    
    def perform_ecu_reset(self):
        """Perform ECU reset"""
        if not self.uds_backend:
            return
            
        reset_text = self.reset_type_combo.currentText()
        reset_type = int(reset_text.split(" - ")[0], 16)
        
        # Confirm reset action
        reply = QMessageBox.question(self, "Confirm ECU Reset", 
                                   f"Are you sure you want to perform {reset_text}?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.uds_backend.ecu_reset(reset_type)
            self.log_response(f"→ ECU Reset: {reset_text}")
    
    def read_dtcs(self):
        """Read diagnostic trouble codes"""
        if not self.uds_backend:
            return
            
        self.uds_backend.read_dtc_information(0x02)  # reportDTCByStatusMask
        self.log_response("→ Reading DTCs...")
    
    def read_pending_dtcs(self):
        """Read pending DTCs"""
        if not self.uds_backend:
            return
            
        self.uds_backend.read_dtc_information(0x04)  # reportDTCSnapshotIdentification
        self.log_response("→ Reading pending DTCs...")
    
    def clear_dtcs_clicked(self):
        """Clear DTCs"""
        if not self.uds_backend:
            return
            
        reply = QMessageBox.question(self, "Confirm Clear DTCs", 
                                   "Are you sure you want to clear all DTCs?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.uds_backend.clear_diagnostic_information()
            self.log_response("→ Clearing DTCs...")
    
    def read_data_identifier(self):
        """Read data by identifier"""
        if not self.uds_backend:
            return
            
        did_text = self.did_combo.currentText()
        try:
            if " - " in did_text:
                did_str = did_text.split(" - ")[0]
            else:
                did_str = did_text
                
            did = int(did_str, 16)
            self.uds_backend.read_data_by_identifier(did)
            self.log_response(f"→ Reading DID 0x{did:04X}")
            
        except ValueError:
            QMessageBox.warning(self, "Invalid DID", "Please enter a valid hex DID")
    
    def write_data_identifier(self):
        """Write data by identifier"""
        if not self.uds_backend:
            return
            
        did_text = self.did_combo.currentText()
        data_text = self.write_data_edit.text().strip()
        
        if not data_text:
            QMessageBox.warning(self, "No Data", "Please enter data to write")
            return
            
        try:
            if " - " in did_text:
                did_str = did_text.split(" - ")[0]
            else:
                did_str = did_text
                
            did = int(did_str, 16)
            
            # Parse data bytes
            hex_parts = data_text.replace(',', ' ').split()
            data_bytes = bytes([int(part, 16) for part in hex_parts if part])
            
            self.uds_backend.write_data_by_identifier(did, data_bytes)
            self.log_response(f"→ Writing DID 0x{did:04X}: {data_bytes.hex().upper()}")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Invalid hex data: {str(e)}")
    
    def read_all_common_dids(self):
        """Read all common DIDs"""
        if not self.uds_backend:
            return
            
        common_dids = [0xF010, 0xF011, 0xF018, 0xF030, 0xF031, 0xF032, 0xF186, 0xF190]
        
        for did in common_dids:
            self.uds_backend.read_data_by_identifier(did)
            
        self.log_response("→ Reading all common DIDs...")
    
    def request_security_seed(self):
        """Request security access seed"""
        if not self.uds_backend:
            return
            
        level_text = self.security_level_combo.currentText()
        level = int(level_text.split(" - ")[0], 16)
        
        self.uds_backend.security_access_request_seed(level)
        self.log_response(f"→ Requesting seed for level 0x{level:02X}")
    
    def send_security_key(self):
        """Send security access key"""
        if not self.uds_backend:
            return
            
        key_text = self.key_edit.text().strip()
        if not key_text:
            QMessageBox.warning(self, "No Key", "Please enter security key")
            return
            
        try:
            # Parse key bytes
            hex_parts = key_text.replace(',', ' ').split()
            key_bytes = bytes([int(part, 16) for part in hex_parts if part])
            
            level_text = self.security_level_combo.currentText()
            level = int(level_text.split(" - ")[0], 16)
            
            # Increment level for key send (odd for seed, even for key)
            key_level = level + 1
            
            self.uds_backend.security_access_send_key(key_level, key_bytes)
            self.log_response(f"→ Sending key for level 0x{key_level:02X}: {key_bytes.hex().upper()}")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Key", f"Invalid hex key: {str(e)}")

    def send_obd_request(self):
        """Send OBD-II request"""
        if not self.uds_backend:
            return
            
        mode_text = self.obd_mode_combo.currentText()
        mode = int(mode_text.split(" - ")[0].replace("Mode ", ""), 16)
        
        try:
            pid = int(self.pid_edit.text().strip(), 16)
            
            # Build OBD request data
            data = bytes([mode, pid])
            
            # Send as raw UDS request (OBD uses service 0x01 for mode 01, etc.)
            self.uds_backend.send_raw_request(mode, bytes([pid]))
            self.log_response(f"→ OBD Request: Mode {mode:02X}, PID {pid:02X}")
            
        except ValueError:
            QMessageBox.warning(self, "Invalid PID", "Please enter a valid hex PID")
    
    def show_dtc_details(self):
        """Show details for selected DTC"""
        selected_items = self.dtc_table.selectedItems()
        if not selected_items:
            self.dtc_details.clear()
            return
            
        row = selected_items[0].row()
        dtc_code = self.dtc_table.item(row, 0).text()
        status = self.dtc_table.item(row, 1).text()
        description = self.dtc_table.item(row, 2).text()
        raw_bytes = self.dtc_table.item(row, 3).text()
        status_byte = self.dtc_table.item(row, 4).text()
        
        details_text = f"""DTC: {dtc_code}
Status: {status}
Description: {description}
Raw Bytes: {raw_bytes}
Status Byte: 0x{status_byte}

Status Breakdown:
{self.decode_status_details(status_byte)}"""
        
        self.dtc_details.setPlainText(details_text)
    
    def decode_status_details(self, status_byte_str):
        """Decode DTC status byte details"""
        try:
            status_byte = int(status_byte_str, 16) if isinstance(status_byte_str, str) else status_byte_str
            
            details = []
            if status_byte & 0x01:
                details.append("• Test Failed")
            if status_byte & 0x02:
                details.append("• Test Failed This Operation Cycle")
            if status_byte & 0x04:
                details.append("• Pending DTC")
            if status_byte & 0x08:
                details.append("• Confirmed DTC")
            if status_byte & 0x10:
                details.append("• Test Not Completed Since Last Clear")
            if status_byte & 0x20:
                details.append("• Test Failed Since Last Clear")
            if status_byte & 0x40:
                details.append("• Test Not Completed This Operation Cycle")
            if status_byte & 0x80:
                details.append("• Warning Indicator Requested")
                
            return "\n".join(details) if details else "No active status flags"
            
        except:
            return "Unable to decode status"
    
    def auto_calculate_key(self, algorithm):
        """Auto-calculate security key using specified algorithm"""
        seed_text = self.seed_edit.text().strip()
        if not seed_text:
            QMessageBox.warning(self, "No Seed", "No seed value available")
            return
            
        try:
            # Parse seed
            hex_parts = seed_text.replace(',', ' ').split()
            seed_bytes = bytes([int(part, 16) for part in hex_parts if part])
            
            # Calculate key using UDS backend
            if self.uds_backend:
                key_bytes = self.uds_backend.calculate_security_key(seed_bytes, algorithm)
                key_hex = key_bytes.hex().upper()
                
                # Format with spaces
                key_formatted = ' '.join(key_hex[i:i+2] for i in range(0, len(key_hex), 2))
                self.key_edit.setText(key_formatted)
                
                self.log_response(f"Key calculated using {algorithm}: {key_formatted}")
            else:
                # Fallback calculation
                key_bytes = self.utils.calculate_security_key(seed_text, algorithm)
                key_hex = f"{key_bytes:08X}"
                key_formatted = ' '.join(key_hex[i:i+2] for i in range(0, len(key_hex), 2))
                self.key_edit.setText(key_formatted)
                
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Seed", f"Invalid hex seed: {str(e)}")
    
    # === UDS Backend Response Handlers ===
    
    def handle_uds_response(self, response):
        """Handle UDS response from backend"""
        service = response.get('service', 'unknown')
        success = response.get('success', False)
        data = response.get('data', b'')
        
        if success:
            self.log_response(f"← {service}: {data.hex().upper() if data else 'OK'}")
            
            # Handle specific service responses
            if service == 'diagnostic_session_control':
                session_name = response.get('session_name', 'Unknown')
                self.current_session_label.setText(session_name)
                
            elif service == 'security_access_request_seed':
                seed = response.get('seed', '')
                self.seed_edit.setText(seed)
                self.send_key_btn.setEnabled(True)
                
            elif service == 'security_access_send_key':
                self.security_status_label.setText("🔓 Security Unlocked")
                self.security_status_label.setStyleSheet("color: green; font-weight: bold;")
                
        else:
            error = response.get('error', 'Unknown error')
            self.log_response(f"✗ {service} failed: {error}")
    
    def handle_uds_error(self, error):
        """Handle UDS error"""
        self.log_response(f"✗ UDS Error: {error}")
    
    def handle_session_changed(self, session_info):
        """Handle session change notification"""
        session_name = session_info.get('name', 'Unknown Session')
        self.current_session_label.setText(session_name)
        self.log_response(f"Session changed to: {session_name}")
    
    def handle_security_status_changed(self, security_info):
        """Handle security status change"""
        level = security_info.get('level', 0)
        unlocked = security_info.get('unlocked', False)
        seed = security_info.get('seed', '')
        
        if unlocked:
            self.security_status_label.setText(f"🔓 Level {level} Unlocked")
            self.security_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.send_key_btn.setEnabled(False)
        else:
            self.security_status_label.setText(f"🔒 Level {level} Locked")
            self.security_status_label.setStyleSheet("color: red; font-weight: bold;")
            if seed:
                self.seed_edit.setText(seed)
                self.send_key_btn.setEnabled(True)
    
    def handle_dtc_data(self, dtc_list):
        """Handle DTC data from backend"""
        print(f"[DEBUG] handle_dtc_data called with {len(dtc_list)} DTCs")
        
        # Disable sorting temporarily to prevent row reordering during population
        was_sorting_enabled = self.dtc_table.isSortingEnabled()
        self.dtc_table.setSortingEnabled(False)
        
        # Clear existing data
        self.dtc_table.clearContents()
        self.dtc_table.setRowCount(len(dtc_list))
        
        for i, dtc in enumerate(dtc_list):
            print(f"[DEBUG] Processing DTC {i}: {dtc}")
            
            # Create all items first to ensure they exist
            items = [None] * 6  # 6 columns
            
            # DTC Code - Column 0
            code_text = str(dtc.get('code', 'Unknown'))
            items[0] = QTableWidgetItem(code_text)
            items[0].setFlags(items[0].flags() & ~Qt.ItemIsEditable)  # Make read-only
            
            # Status - Column 1
            status = str(dtc.get('status', 'Unknown'))
            items[1] = QTableWidgetItem(status)
            items[1].setFlags(items[1].flags() & ~Qt.ItemIsEditable)  # Make read-only
            
            # Color code status by severity
            if 'Confirmed' in status or 'TestFailed' in status:
                items[1].setForeground(QColor("red"))
            elif 'Pending' in status:
                items[1].setForeground(QColor("orange"))
            else:
                items[1].setForeground(QColor("gray"))
            
            # Description - Column 2
            description = self.utils.get_dtc_description(dtc.get('code', ''))
            items[2] = QTableWidgetItem(str(description))
            items[2].setFlags(items[2].flags() & ~Qt.ItemIsEditable)  # Make read-only
            
            # Raw bytes - Column 3
            raw_bytes = str(dtc.get('raw_bytes', ''))
            items[3] = QTableWidgetItem(raw_bytes)
            items[3].setFlags(items[3].flags() & ~Qt.ItemIsEditable)  # Make read-only
            
            # Status byte - Column 4
            status_byte = dtc.get('status_byte', 0)
            items[4] = QTableWidgetItem(f"{status_byte:02X}")
            items[4].setFlags(items[4].flags() & ~Qt.ItemIsEditable)  # Make read-only
            
            # Priority - Column 5
            priority = "High" if 'Confirmed' in status else "Medium" if 'Pending' in status else "Low"
            items[5] = QTableWidgetItem(priority)
            items[5].setFlags(items[5].flags() & ~Qt.ItemIsEditable)  # Make read-only
            
            if priority == "High":
                items[5].setForeground(QColor("red"))
            elif priority == "Medium":
                items[5].setForeground(QColor("orange"))
            else:
                items[5].setForeground(QColor("green"))
            
            # Now set all items at once
            for col, item in enumerate(items):
                if item is not None:
                    self.dtc_table.setItem(i, col, item)
                    print(f"[DEBUG] Set DTC {i} col {col}: '{item.text()}'")
                else:
                    print(f"[ERROR] DTC {i} col {col}: NULL ITEM!")
            
            print(f"[DEBUG] DTC {i} added to table: Code={code_text}, Status={status}")
        
        # Re-enable sorting after all data is populated
        self.dtc_table.setSortingEnabled(was_sorting_enabled)
        
        # Update count
        self.dtc_count_label.setText(f"DTCs: {len(dtc_list)}")
        
        # Auto-resize columns
        self.dtc_table.resizeColumnsToContents()
        
        # Force table refresh and update
        self.dtc_table.viewport().update()
        self.dtc_table.repaint()
        
        # Log for debugging
        print(f"[DEBUG] DTC table updated with {len(dtc_list)} DTCs, table now has {self.dtc_table.rowCount()} rows")
        
        # Verify all items are set
        for row in range(self.dtc_table.rowCount()):
            for col in range(self.dtc_table.columnCount()):
                item = self.dtc_table.item(row, col)
                if item is None:
                    print(f"[WARNING] Missing item at row {row}, col {col}")
                else:
                    print(f"[DEBUG] Row {row}, Col {col}: '{item.text()}'")
                    
        # Schedule a delayed update to ensure UI refresh
        QTimer.singleShot(0, self.dtc_table.repaint)
    
    def handle_data_identifier(self, did_info):
        """Handle data identifier response"""
        did = did_info.get('did', 0)
        data = did_info.get('data', b'')
        decoded = did_info.get('decoded', '')
        
        print(f"[DEBUG] handle_data_identifier called for DID 0x{did:04X}")
        print(f"[DEBUG] Raw did_info: {did_info}")
        print(f"[DEBUG] Data: {data}, Decoded: {decoded}")
        
        # Disable sorting temporarily to prevent row reordering during population
        was_sorting_enabled = self.data_values_table.isSortingEnabled()
        self.data_values_table.setSortingEnabled(False)
        
        # Add to data values table - use setRowCount instead of insertRow
        row_count = self.data_values_table.rowCount()
        self.data_values_table.setRowCount(row_count + 1)
        
        # DID
        did_text = f"0x{did:04X}"
        did_item = QTableWidgetItem(did_text)
        did_item.setFlags(did_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
        self.data_values_table.setItem(row_count, 0, did_item)
        print(f"[DEBUG] Set DID item: '{did_text}'")
        
        # Name (get from constants or generate)
        name = self.get_did_name(did)
        name_text = str(name) if name else f"DID 0x{did:04X}"
        name_item = QTableWidgetItem(name_text)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
        self.data_values_table.setItem(row_count, 1, name_item)
        print(f"[DEBUG] Set name item: '{name_text}'")
        
        # Raw data
        if data and len(data) > 0:
            raw_hex = data.hex().upper()
            raw_formatted = ' '.join(raw_hex[i:i+2] for i in range(0, len(raw_hex), 2))
        else:
            raw_formatted = "No Data"
        raw_item = QTableWidgetItem(raw_formatted)
        raw_item.setFlags(raw_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
        self.data_values_table.setItem(row_count, 2, raw_item)
        print(f"[DEBUG] Set raw data item: '{raw_formatted}'")
        
        # Decoded value
        decoded_text = str(decoded) if decoded else "Not Decoded"
        decoded_item = QTableWidgetItem(decoded_text)
        decoded_item.setFlags(decoded_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
        self.data_values_table.setItem(row_count, 3, decoded_item)
        print(f"[DEBUG] Set decoded item: '{decoded_text}'")
        
        # Timestamp
        timestamp = time.strftime("%H:%M:%S")
        timestamp_item = QTableWidgetItem(timestamp)
        timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
        self.data_values_table.setItem(row_count, 4, timestamp_item)
        print(f"[DEBUG] Set timestamp item: '{timestamp}'")
        
        # Auto-resize columns
        self.data_values_table.resizeColumnsToContents()
        
        # Force table refresh and update with multiple methods
        self.data_values_table.viewport().update()
        self.data_values_table.repaint()
        
        # Also try to force a model refresh
        if hasattr(self.data_values_table, 'model'):
            model = self.data_values_table.model()
            if model:
                model.layoutChanged.emit()
        
        # Force the widget to be visible and ensure it's not hidden
        self.data_values_table.setVisible(True)
        self.data_values_table.show()
        
        # Log for debugging
        print(f"[DEBUG] DID table updated with DID 0x{did:04X}, table now has {self.data_values_table.rowCount()} rows")
        print(f"[DEBUG] Table visible: {self.data_values_table.isVisible()}, enabled: {self.data_values_table.isEnabled()}")
        print(f"[DEBUG] Table size: {self.data_values_table.size()}, geometry: {self.data_values_table.geometry()}")
        
        # Verify all items are set for this row
        for col in range(self.data_values_table.columnCount()):
            item = self.data_values_table.item(row_count, col)
            if item is None:
                print(f"[WARNING] Missing DID item at row {row_count}, col {col}")
                # Create a placeholder item if missing
                placeholder_item = QTableWidgetItem("Missing")
                placeholder_item.setFlags(placeholder_item.flags() & ~Qt.ItemIsEditable)
                self.data_values_table.setItem(row_count, col, placeholder_item)
            else:
                print(f"[DEBUG] DID Row {row_count}, Col {col}: '{item.text()}'")
        
        # Re-enable sorting after all data is populated
        self.data_values_table.setSortingEnabled(was_sorting_enabled)
                
        # Schedule a delayed update to ensure UI refresh
        QTimer.singleShot(0, self.data_values_table.repaint)
        QTimer.singleShot(100, self.data_values_table.resizeColumnsToContents)
        
        # Add comprehensive debugging
        QTimer.singleShot(200, lambda: self._debug_table_state(row_count))
    
    def get_did_name(self, did):
        """Get human-readable name for DID"""
        did_names = {
            0xF010: "Active Diagnostic Session",
            0xF011: "ECU Software Number",
            0xF012: "ECU Software Version", 
            0xF013: "System Name",
            0xF018: "Application Software Fingerprint",
            0xF019: "Application Data Fingerprint",
            0xF01A: "Boot Software Fingerprint",
            0xF030: "Vehicle Speed",
            0xF031: "Engine RPM",
            0xF032: "Engine Temperature",
            0xF186: "Current Session",
            0xF187: "Supplier Identifier",
            0xF188: "ECU Manufacturing Date",
            0xF189: "ECU Serial Number",
            0xF18A: "Supported Functional Units",
            0xF190: "VIN Data Identifier"
        }
        
        return did_names.get(did, f"DID 0x{did:04X}")
    
    def log_response(self, message):
        """Log response message"""
        import datetime
        now = datetime.datetime.now()
        timestamp = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"  # Include milliseconds
        formatted_message = f"[{timestamp}] {message}"
        
        self.response_text.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.response_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.response_text.setTextCursor(cursor)

        # Limit text length to prevent memory issues
        if self.response_text.document().blockCount() > 1000:
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
    
    def apply_professional_style(self):
        """Apply professional styling to the panel"""
        self.setStyleSheet(DIAGNOSTICS_STYLESHEET + """
        /* Enhanced scroll area styling */
        QScrollArea {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background-color: #fafafa;
        }
        
        QScrollArea > QWidget > QWidget {
            background-color: white;
        }
        
        QScrollBar:vertical {
            background-color: #f5f5f5;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """)
        
        # Set fonts
        mono_font = QFont("Consolas", 9)
        if hasattr(self, 'response_text'):
            self.response_text.setFont(mono_font)
        
        # Table styling - check if tables exist before styling
        tables_to_style = []
        if hasattr(self, 'dtc_table'):
            tables_to_style.append(self.dtc_table)
        if hasattr(self, 'data_values_table'):
            tables_to_style.append(self.data_values_table)
        if hasattr(self, 'obd_data_table'):
            tables_to_style.append(self.obd_data_table)
            
        for table in tables_to_style:
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setShowGrid(True)
            table.setSortingEnabled(True)
        
        # Status labels styling
        if hasattr(self, 'current_session_label'):
            self.current_session_label.setStyleSheet(
                "QLabel { background-color: #e3f2fd; padding: 4px; border-radius: 4px; }"
            )
    
    def _debug_table_state(self, row_index):
        """Debug method to examine table state after updates"""
        print(f"[DETAILED_DEBUG] Table state check for row {row_index}:")
        print(f"[DETAILED_DEBUG] - Table rows: {self.data_values_table.rowCount()}")
        print(f"[DETAILED_DEBUG] - Table columns: {self.data_values_table.columnCount()}")
        print(f"[DETAILED_DEBUG] - Table visible: {self.data_values_table.isVisible()}")
        print(f"[DETAILED_DEBUG] - Table enabled: {self.data_values_table.isEnabled()}")
        print(f"[DETAILED_DEBUG] - Parent visible: {self.data_values_table.parent().isVisible() if self.data_values_table.parent() else 'No parent'}")
        
        # Check the specific row we just added
        print(f"[DETAILED_DEBUG] Checking row {row_index} contents:")
        for col in range(self.data_values_table.columnCount()):
            item = self.data_values_table.item(row_index, col)
            if item:
                print(f"[DETAILED_DEBUG] - Col {col}: '{item.text()}' (flags: {item.flags()})")
            else:
                print(f"[DETAILED_DEBUG] - Col {col}: NULL ITEM")
        
        # Check if items are properly visible
        test_item = self.data_values_table.item(row_index, 0)
        if test_item:
            print(f"[DETAILED_DEBUG] Test item details:")
            print(f"[DETAILED_DEBUG] - Text: '{test_item.text()}'")
            print(f"[DETAILED_DEBUG] - Font: {test_item.font()}")
            print(f"[DETAILED_DEBUG] - Background: {test_item.background()}")
            print(f"[DETAILED_DEBUG] - Foreground: {test_item.foreground()}")
        
        # Force one more repaint
        self.data_values_table.repaint()
        
    def populate_sample_data(self):
        """Populate tables with sample data for demonstration"""
        # Populate sample DTCs
        self.utils.populate_sample_dtcs(self.dtc_table)
        self.dtc_count_label.setText(f"DTCs: {self.dtc_table.rowCount()}")
        
        # Populate sample data identifiers
        self.utils.populate_data_identifiers(self.data_values_table)
        
        # OBD data is already populated in setup
        
    def clear_all_data(self):
        """Clear all data from tables"""
        self.dtc_table.setRowCount(0)
        self.data_values_table.setRowCount(0)
        self.obd_data_table.setRowCount(0)
        self.response_text.clear()
        self.dtc_count_label.setText("DTCs: 0")
    
    # Enhanced Security Access Methods
    def _calculate_crc16_key(self, seed_bytes):
        """Calculate CRC16-based key"""
        # CRC16-CCITT polynomial
        crc = 0xFFFF
        for byte in seed_bytes:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        
        # Return CRC as 2-byte key
        return bytes([(crc >> 8) & 0xFF, crc & 0xFF])
    
    def on_ecu_changed(self, ecu_name):
        """Handle ECU selection change"""
        self.add_log_entry(f"🚗 Selected ECU: {ecu_name}")
        # Clear previous security data when changing ECU
        self.clear_security_data()
    
    def on_provider_changed(self, provider):
        """Handle algorithm provider change"""
        if hasattr(self, 'provider_status_label'):
            if "DLL" in provider and not (hasattr(self, 'dll_interface') and self.dll_interface and self.dll_interface.is_dll_loaded()):
                self.provider_status_label.setText("❌ No DLL loaded")
                self.provider_status_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.provider_status_label.setText("✅ Ready")
                self.provider_status_label.setStyleSheet("color: green; font-weight: bold;")
        
        self.add_log_entry(f"🔧 Algorithm provider changed to: {provider}")
    
    def on_security_level_changed(self, level):
        """Handle security level change"""
        descriptions = {
            "0x01": "Service mode access",
            "0x02": "Programming mode access", 
            "0x03": "Extended diagnostic access",
            "0x04": "Safety system access",
            "0x05": "Development mode access"
        }
        
        level_num = level.split()[0]
        description = descriptions.get(level_num, "Unknown security level")
        if hasattr(self, 'level_description_label'):
            self.level_description_label.setText(description)
        self.add_log_entry(f"🔐 Security level changed to: {level}")
    
    def on_manual_key_toggled(self, checked):
        """Handle manual key input toggle"""
        if hasattr(self, 'key_edit'):
            self.key_edit.setReadOnly(not checked)
            if checked:
                self.key_edit.setPlaceholderText("Enter key manually")
                if hasattr(self, 'calculate_key_btn'):
                    self.calculate_key_btn.setEnabled(False)
            else:
                self.key_edit.setPlaceholderText("Key will be calculated")
                if hasattr(self, 'calculate_key_btn'):
                    self.calculate_key_btn.setEnabled(bool(self.seed_edit.text().strip()))
    
    def copy_seed(self):
        """Copy seed to clipboard"""
        if hasattr(self, 'seed_edit') and self.seed_edit.text():
            QApplication.clipboard().setText(self.seed_edit.text())
            self.add_log_entry("📋 Seed copied to clipboard")
    
    def copy_key(self):
        """Copy key to clipboard"""
        if hasattr(self, 'key_edit') and self.key_edit.text():
            QApplication.clipboard().setText(self.key_edit.text())
            self.add_log_entry("📋 Key copied to clipboard")
    
    def clear_security_data(self):
        """Clear all security access data"""
        if hasattr(self, 'seed_edit'):
            self.seed_edit.clear()
        if hasattr(self, 'key_edit'):
            self.key_edit.clear()
        if hasattr(self, 'security_status_label'):
            self.security_status_label.setText("🔒 Security Locked")
            self.security_status_label.setStyleSheet("color: red; font-weight: bold;")
        if hasattr(self, 'current_level_label'):
            self.current_level_label.setText("Level: None")
        if hasattr(self, 'send_key_btn'):
            self.send_key_btn.setEnabled(False)
        if hasattr(self, 'calculate_key_btn'):
            self.calculate_key_btn.setEnabled(False)
        self.add_log_entry("🗑️ Security data cleared")
    
    def browse_dll_file(self):
        """Browse for security DLL file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Security Access DLL", 
            "", 
            "DLL Files (*.dll);;All Files (*)"
        )
        if file_path and hasattr(self, 'dll_path_edit'):
            self.dll_path_edit.setText(file_path)
    
    def load_dll(self):
        """Load security access DLL"""
        if not hasattr(self, 'dll_interface') or not self.dll_interface:
            QMessageBox.warning(self, "DLL Interface Error", "DLL interface not available")
            return
            
        if not hasattr(self, 'dll_path_edit'):
            return
            
        dll_path = self.dll_path_edit.text().strip()
        if not dll_path:
            QMessageBox.warning(self, "No DLL Selected", "Please select a DLL file first")
            return
            
        ecu_name = self.ecu_combo.currentText() if hasattr(self, 'ecu_combo') else "Default_ECU"
            
        try:
            if self.dll_interface.load_security_dll(dll_path, ecu_name):
                self.add_log_entry(f"📚 Successfully loaded DLL: {dll_path}")
            else:
                QMessageBox.critical(self, "DLL Load Error", "Failed to load DLL")
        except Exception as e:
            QMessageBox.critical(self, "DLL Load Error", f"Error loading DLL: {str(e)}")
    
    def save_dll_config(self):
        """Save current DLL configuration"""
        if not hasattr(self, 'dll_interface') or not self.dll_interface:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save DLL Configuration", 
            "", 
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                self.dll_interface.save_configuration(file_path)
                self.add_log_entry(f"💾 DLL configuration saved: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Error saving configuration: {str(e)}")
    
    def load_dll_config(self):
        """Load DLL configuration"""
        if not hasattr(self, 'dll_interface') or not self.dll_interface:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load DLL Configuration", 
            "", 
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                self.dll_interface.load_configuration(file_path)
                self.add_log_entry(f"📂 DLL configuration loaded: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Error loading configuration: {str(e)}")
    
    def test_dll(self):
        """Test DLL functionality"""
        if not hasattr(self, 'dll_interface') or not self.dll_interface or not self.dll_interface.is_dll_loaded():
            QMessageBox.warning(self, "No DLL", "Please load a DLL first")
            return
            
        # Test with sample data
        test_seed = b'\x12\x34\x56\x78'
        try:
            ecu_name = self.ecu_combo.currentText() if hasattr(self, 'ecu_combo') else "Test_ECU"
            test_key = self.dll_interface.calculate_key_with_dll(
                ecu_name=ecu_name,
                seed=test_seed, 
                level=1
            )
            if test_key:
                test_key_hex = " ".join([f"{b:02X}" for b in test_key])
                QMessageBox.information(
                    self, 
                    "DLL Test Successful", 
                    f"Test seed: {test_seed.hex().upper()}\nCalculated key: {test_key_hex}"
                )
                self.add_log_entry(f"🧪 DLL test successful - Key: {test_key_hex}")
            else:
                QMessageBox.warning(self, "DLL Test Failed", "DLL returned no key")
        except Exception as e:
            QMessageBox.critical(self, "DLL Test Error", f"Error testing DLL: {str(e)}")
    
    def calculate_security_key(self):
        """Calculate security key using selected provider"""
        if not hasattr(self, 'seed_edit'):
            return
            
        seed_hex = self.seed_edit.text().strip()
        if not seed_hex:
            QMessageBox.warning(self, "No Seed", "Please request a seed first")
            return
            
        try:
            # Convert hex string to bytes
            seed_bytes = bytes.fromhex(seed_hex.replace("0x", "").replace(" ", ""))
            provider = self.algorithm_provider_combo.currentText() if hasattr(self, 'algorithm_provider_combo') else "Built-in"
            
            key_bytes = None
            
            if "DLL" in provider and hasattr(self, 'dll_interface') and self.dll_interface and self.dll_interface.is_dll_loaded():
                # Use DLL for calculation
                try:
                    security_level = int(self.security_level_combo.currentText().split()[0], 16) if hasattr(self, 'security_level_combo') else 1
                    ecu_name = self.ecu_combo.currentText() if hasattr(self, 'ecu_combo') else "Default_ECU"
                    key_bytes = self.dll_interface.calculate_key_with_dll(
                        ecu_name=ecu_name,
                        seed=seed_bytes, 
                        level=security_level
                    )
                    
                    if key_bytes:
                        self.add_log_entry("🧮 Key calculated using DLL")
                    else:
                        raise ValueError("DLL returned no key")
                        
                except Exception as dll_error:
                    if "Auto" in provider:
                        self.add_log_entry(f"⚠️ DLL failed: {str(dll_error)}, falling back to built-in")
                        key_bytes = None  # Will fall through to built-in
                    else:
                        raise dll_error
            
            if key_bytes is None:
                # Use built-in algorithm (default to XOR)
                key_bytes = bytes([b ^ 0x12 for b in seed_bytes])
                self.add_log_entry("🧮 Key calculated using built-in XOR algorithm")
            
            # Convert back to hex
            key_hex = " ".join([f"{b:02X}" for b in key_bytes])
            if hasattr(self, 'key_edit'):
                self.key_edit.setText(key_hex)
            if hasattr(self, 'send_key_btn'):
                self.send_key_btn.setEnabled(True)
            
        except ValueError as e:
            QMessageBox.critical(self, "Calculation Error", f"Error calculating key: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")
    
    def on_dll_loaded(self, dll_path):
        """Handle DLL loaded signal"""
        if hasattr(self, 'dll_status_label'):
            self.dll_status_label.setText(f"✅ DLL loaded: {dll_path}")
            self.dll_status_label.setStyleSheet("color: green; font-weight: bold;")
        if hasattr(self, 'algorithm_provider_combo'):
            self.on_provider_changed(self.algorithm_provider_combo.currentText())
    
    def on_dll_unloaded(self):
        """Handle DLL unloaded signal"""
        if hasattr(self, 'dll_status_label'):
            self.dll_status_label.setText("📚 No DLL loaded")
            self.dll_status_label.setStyleSheet("color: #666; font-style: italic;")
        if hasattr(self, 'algorithm_provider_combo'):
            self.on_provider_changed(self.algorithm_provider_combo.currentText())
    
    def on_dll_error(self, error_message):
        """Handle DLL error signal"""
        if hasattr(self, 'dll_status_label'):
            self.dll_status_label.setText(f"❌ DLL Error: {error_message}")
            self.dll_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.add_log_entry(f"❌ DLL Error: {error_message}")
    
    def on_dll_key_calculated(self, key_bytes):
        """Handle DLL key calculation result"""
        key_hex = " ".join([f"{b:02X}" for b in key_bytes])
        if hasattr(self, 'key_edit'):
            self.key_edit.setText(key_hex)
        if hasattr(self, 'send_key_btn'):
            self.send_key_btn.setEnabled(True)
        self.add_log_entry(f"🔑 DLL calculated key: {key_hex}")
    
    def _get_enhanced_help_text(self):
        """Get enhanced help text for key calculation"""
        return """
        <b>🧮 Key Calculation Methods:</b><br>
        <b>Built-in Algorithms:</b><br>
        • <b>XOR:</b> seed ⊕ 0x12 (most common)<br>
        • <b>ADD:</b> (seed + 0x34) & 0xFF<br>
        • <b>Complement:</b> ~seed & 0xFF<br>
        • <b>CRC16:</b> CRC16-CCITT checksum<br><br>
        <b>DLL Integration:</b><br>
        • Load manufacturer-specific DLLs<br>
        • Auto-fallback to built-in algorithms<br>
        • ASAM/ODX-D compatible interface<br><br>
        <b>Usage:</b> Request seed first, then calculate or enter key manually
        """