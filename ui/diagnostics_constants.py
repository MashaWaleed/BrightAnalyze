"""
Constants for Diagnostics Panel
Contains all constant data, sample responses, and styling
"""

# UDS Session types
UDS_SESSIONS = [
    "0x01 - Default Session",
    "0x02 - Programming Session", 
    "0x03 - Extended Diagnostic Session",
    "0x40 - EOL Session"
]

# UDS Services
UDS_SERVICES = [
    "0x10 - Diagnostic Session Control",
    "0x11 - ECU Reset",
    "0x22 - Read Data By Identifier",
    "0x23 - Read Memory By Address",
    "0x27 - Security Access",
    "0x2E - Write Data By Identifier",
    "0x31 - Routine Control",
    "0x34 - Request Download",
    "0x35 - Request Upload",
    "0x36 - Transfer Data",
    "0x37 - Request Transfer Exit"
]

# OBD-II Modes
OBD_MODES = [
    "Mode 01 - Current Powertrain Data",
    "Mode 02 - Freeze Frame Data",
    "Mode 03 - Diagnostic Trouble Codes",
    "Mode 04 - Clear DTCs",
    "Mode 05 - Oxygen Sensor Test Results",
    "Mode 06 - Test Results (Non-continuously)",
    "Mode 07 - Pending DTCs",
    "Mode 08 - Control Operation",
    "Mode 09 - Vehicle Information",
    "Mode 0A - Permanent DTCs"
]

# Data Identifiers
DATA_IDENTIFIERS = [
    "0xF010 - Active Diagnostic Session",
    "0xF011 - ECU Software Number",
    "0xF012 - ECU Software Version",
    "0xF013 - System Name",
    "0xF018 - Application Software Fingerprint",
    "0xF019 - Application Data Fingerprint",
    "0xF01A - Boot Software Fingerprint",
    "0xF030 - Vehicle Speed",
    "0xF031 - Engine RPM",
    "0xF032 - Engine Temperature",
    "0xF186 - Current Session",
    "0xF187 - Supplier Identifier",
    "0xF188 - ECU Manufacturing Date",
    "0xF189 - ECU Serial Number",
    "0xF18A - Supported Functional Units",
    "0xF190 - VIN Data Identifier"
]

# Security Access Levels
SECURITY_LEVELS = [
    "0x01 - Level 1 (Seed Request)",
    "0x02 - Level 1 (Key Response)",
    "0x03 - Level 2 (Seed Request)",
    "0x04 - Level 2 (Key Response)",
    "0x05 - Level 3 (Seed Request)",
    "0x06 - Level 3 (Key Response)"
]

# Sample diagnostic responses
SAMPLE_RESPONSES = {
    "session_control": "50 01 00 32 01 F4",
    "ecu_reset": "51 01",
    "read_data": "62 F0 10 01",
    "security_seed": "67 01 12 34 56 78"
}

# Sample OBD data
SAMPLE_OBD_DATA = [
    ("0x01", "Engine Load", "45.5", "%"),
    ("0x05", "Coolant Temperature", "85", "°C"),
    ("0x0C", "Engine RPM", "2150", "rpm"),
    ("0x0D", "Vehicle Speed", "65", "km/h"),
    ("0x0F", "Intake Air Temperature", "25", "°C"),
    ("0x11", "Throttle Position", "32.5", "%"),
    ("0x1F", "Runtime Since Start", "1245", "seconds"),
    ("0x21", "Distance with MIL On", "0", "km"),
    ("0x2F", "Fuel Tank Level", "75.5", "%"),
    ("0x33", "Barometric Pressure", "101.3", "kPa")
]

# Sample DTCs
SAMPLE_DTCS = [
    ("P0301", "Current", "Cylinder 1 Misfire Detected", "Yes", "High"),
    ("P0171", "Pending", "System Too Lean (Bank 1)", "No", "Medium"),
    ("P0440", "Stored", "Evaporative Emission Control System Malfunction", "Yes", "Low"),
    ("B1234", "Current", "Body Control Module Communication Error", "No", "Medium"),
    ("U0100", "Stored", "Lost Communication with ECM/PCM", "No", "High")
]

# Sample Data Identifiers
SAMPLE_DATA_IDENTIFIERS = [
    ("0xF010", "Active Diagnostic Session", "01", "Hex"),
    ("0xF011", "ECU Software Number", "12345", "ASCII"),
    ("0xF018", "Application Software Fingerprint", "AB CD EF 12", "Hex"),
    ("0xF030", "Vehicle Speed", "65.5", "Float km/h"),
    ("0xF031", "Engine RPM", "2150", "Int16 rpm"),
    ("0xF032", "Engine Temperature", "85", "Int8 °C"),
    ("0xF186", "Current Session", "03", "Hex"),
    ("0xF190", "VIN", "1HGBH41JXMN109186", "ASCII")
]

# Help text for key calculation
KEY_CALC_HELP_TEXT = """
<h4>Key Calculation Methods:</h4>
<ul>
<li><b>Simple XOR:</b> Key = Seed XOR 0x1234</li>
<li><b>Addition:</b> Key = Seed + 0x9876</li>
<li><b>Custom Algorithm:</b> Implement ECU-specific calculation</li>
</ul>
<p><i>Note: Real implementations require ECU-specific algorithms</i></p>
"""

# Professional styling for diagnostics panel
DIAGNOSTICS_STYLESHEET = """
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

QTabWidget::pane {
    border: 1px solid #e0e0e0;
    background-color: white;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 1px solid white;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #e9ecef;
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

QPushButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #ffffff, stop: 1 #f8f9fa);
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
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

QPushButton:disabled {
    background-color: #f8f9fa;
    border-color: #e9ecef;
    color: #6c757d;
}

QLineEdit {
    background-color: white;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 8px;
}

QLineEdit:focus {
    border-color: #007bff;
}

QComboBox {
    background-color: white;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 8px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #80bdff;
}

QComboBox:focus {
    border-color: #007bff;
}

QTextEdit {
    background-color: white;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
}
"""