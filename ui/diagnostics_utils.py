"""
Utilities for Diagnostics Panel
Contains helper functions and data population methods
"""

from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtGui import QColor
from .diagnostics_constants import *

class DiagnosticsUtils:
    """Utility class for diagnostics panel functionality"""
    
    def __init__(self):
        pass
        
    def populate_obd_data(self, table_widget):
        """Populate OBD data table with sample data"""
        for i, (pid, name, value, unit) in enumerate(SAMPLE_OBD_DATA):
            table_widget.insertRow(i)
            table_widget.setItem(i, 0, QTableWidgetItem(pid))
            table_widget.setItem(i, 1, QTableWidgetItem(name))
            table_widget.setItem(i, 2, QTableWidgetItem(value))
            table_widget.setItem(i, 3, QTableWidgetItem(unit))
            
    def populate_sample_dtcs(self, table_widget):
        """Populate DTC table with sample codes"""
        for i, (code, status, desc, freeze, priority) in enumerate(SAMPLE_DTCS):
            table_widget.insertRow(i)
            table_widget.setItem(i, 0, QTableWidgetItem(code))
            
            status_item = QTableWidgetItem(status)
            if status == "Current":
                status_item.setForeground(QColor("red"))
            elif status == "Pending":
                status_item.setForeground(QColor("orange"))
            else:
                status_item.setForeground(QColor("gray"))
            table_widget.setItem(i, 1, status_item)
            
            table_widget.setItem(i, 2, QTableWidgetItem(desc))
            table_widget.setItem(i, 3, QTableWidgetItem(freeze))
            
            priority_item = QTableWidgetItem(priority)
            if priority == "High":
                priority_item.setForeground(QColor("red"))
            elif priority == "Medium":
                priority_item.setForeground(QColor("orange"))
            else:
                priority_item.setForeground(QColor("green"))
            table_widget.setItem(i, 4, priority_item)
            
    def populate_data_identifiers(self, table_widget):
        """Populate data identifiers table"""
        for i, (did, name, value, format_type) in enumerate(SAMPLE_DATA_IDENTIFIERS):
            table_widget.insertRow(i)
            table_widget.setItem(i, 0, QTableWidgetItem(did))
            table_widget.setItem(i, 1, QTableWidgetItem(name))
            table_widget.setItem(i, 2, QTableWidgetItem(value))
            table_widget.setItem(i, 3, QTableWidgetItem(format_type))
            
    def validate_hex_input(self, text):
        """Validate hexadecimal input"""
        try:
            int(text, 16)
            return True
        except ValueError:
            return False
            
    def format_hex_data(self, data_bytes):
        """Format data bytes as hex string"""
        if isinstance(data_bytes, list):
            return " ".join(f"{b:02X}" for b in data_bytes)
        elif isinstance(data_bytes, str):
            return data_bytes.upper()
        else:
            return str(data_bytes)
            
    def parse_hex_string(self, hex_string):
        """Parse hex string to list of bytes"""
        try:
            # Remove spaces and split into pairs
            hex_clean = hex_string.replace(" ", "").replace("0x", "")
            if len(hex_clean) % 2 != 0:
                hex_clean = "0" + hex_clean
                
            return [int(hex_clean[i:i+2], 16) for i in range(0, len(hex_clean), 2)]
        except ValueError:
            return []
            
    def calculate_security_key(self, seed, algorithm='xor'):
        """Calculate security key from seed"""
        try:
            seed_value = int(seed, 16) if isinstance(seed, str) else seed
            
            if algorithm == 'xor':
                return seed_value ^ 0x1234
            elif algorithm == 'add':
                return (seed_value + 0x9876) & 0xFFFFFFFF
            elif algorithm == 'complement':
                return (~seed_value) & 0xFFFFFFFF
            else:
                # Default XOR
                return seed_value ^ 0x1234
                
        except (ValueError, TypeError):
            return 0
            
    def get_dtc_description(self, dtc_code):
        """Get description for DTC code"""
        dtc_descriptions = {
            'P0301': 'Cylinder 1 Misfire Detected',
            'P0302': 'Cylinder 2 Misfire Detected',
            'P0303': 'Cylinder 3 Misfire Detected',
            'P0304': 'Cylinder 4 Misfire Detected',
            'P0171': 'System Too Lean (Bank 1)',
            'P0172': 'System Too Rich (Bank 1)',
            'P0174': 'System Too Lean (Bank 2)',
            'P0175': 'System Too Rich (Bank 2)',
            'P0300': 'Random/Multiple Cylinder Misfire Detected',
            'P0420': 'Catalyst System Efficiency Below Threshold (Bank 1)',
            'P0430': 'Catalyst System Efficiency Below Threshold (Bank 2)',
            'P0440': 'Evaporative Emission Control System Malfunction',
            'P0442': 'Evaporative Emission Control System Leak Detected (Small Leak)',
            'P0446': 'Evaporative Emission Control System Vent Control Circuit Malfunction',
            'P0455': 'Evaporative Emission Control System Leak Detected (Large Leak)',
            'B1234': 'Body Control Module Communication Error',
            'U0100': 'Lost Communication with ECM/PCM',
            'U0101': 'Lost Communication with TCM',
            'U0140': 'Lost Communication with Body Control Module'
        }
        
        return dtc_descriptions.get(dtc_code, 'Unknown DTC Code')
        
    def get_pid_description(self, pid):
        """Get description for OBD PID"""
        pid_descriptions = {
            '0x00': 'PIDs supported [01 - 20]',
            '0x01': 'Monitor status since DTCs cleared',
            '0x02': 'Freeze DTC',
            '0x03': 'Fuel system status',
            '0x04': 'Calculated engine load',
            '0x05': 'Engine coolant temperature',
            '0x06': 'Short term fuel trim—Bank 1',
            '0x07': 'Long term fuel trim—Bank 1',
            '0x08': 'Short term fuel trim—Bank 2',
            '0x09': 'Long term fuel trim—Bank 2',
            '0x0A': 'Fuel pressure',
            '0x0B': 'Intake manifold absolute pressure',
            '0x0C': 'Engine RPM',
            '0x0D': 'Vehicle speed',
            '0x0E': 'Timing advance',
            '0x0F': 'Intake air temperature',
            '0x10': 'MAF air flow rate',
            '0x11': 'Throttle position',
            '0x12': 'Commanded secondary air status',
            '0x13': 'Oxygen sensors present (in 2 banks)',
            '0x14': 'Oxygen Sensor 1 (Bank 1, Sensor 1)',
            '0x15': 'Oxygen Sensor 2 (Bank 1, Sensor 2)',
            '0x1F': 'Run time since engine start',
            '0x21': 'Distance traveled with malfunction indicator lamp (MIL) on',
            '0x22': 'Fuel Rail Pressure (relative to manifold vacuum)',
            '0x23': 'Fuel Rail Gauge Pressure (diesel, or gasoline direct injection)',
            '0x2F': 'Fuel Tank Level Input',
            '0x30': 'Warm-ups since codes cleared',
            '0x31': 'Distance traveled since codes cleared',
            '0x33': 'Absolute Barometric Pressure'
        }
        
        return pid_descriptions.get(pid, 'Unknown PID')
        
    def format_diagnostic_response(self, service, response_data):
        """Format diagnostic response for display"""
        if not response_data:
            return "No response received"
            
        formatted = f"Service: {service}\n"
        formatted += f"Raw Data: {self.format_hex_data(response_data)}\n"
        
        # Add service-specific formatting
        if service.startswith('0x22'):  # Read Data By Identifier
            if len(response_data) >= 3:
                did = f"0x{response_data[1]:02X}{response_data[2]:02X}"
                data = response_data[3:] if len(response_data) > 3 else []
                formatted += f"DID: {did}\n"
                formatted += f"Data: {self.format_hex_data(data)}\n"
                
        elif service.startswith('0x27'):  # Security Access
            if len(response_data) >= 2:
                level = response_data[1]
                if level % 2 == 1:  # Seed request response
                    seed = response_data[2:] if len(response_data) > 2 else []
                    formatted += f"Seed: {self.format_hex_data(seed)}\n"
                else:  # Key response
                    formatted += "Security access granted\n"
                    
        return formatted
        
    def validate_service_data(self, service, data):
        """Validate service request data"""
        errors = []
        
        if not service:
            errors.append("Service ID is required")
            
        if service.startswith('0x22'):  # Read Data By Identifier
            if not data or len(data.split()) < 2:
                errors.append("DID (2 bytes) is required for Read Data By Identifier")
                
        elif service.startswith('0x2E'):  # Write Data By Identifier
            if not data or len(data.split()) < 3:
                errors.append("DID (2 bytes) and data are required for Write Data By Identifier")
                
        elif service.startswith('0x27'):  # Security Access
            if not data:
                errors.append("Security level is required for Security Access")
                
        return errors
        
    def get_service_description(self, service_id):
        """Get description for UDS service"""
        service_descriptions = {
            '0x10': 'Diagnostic Session Control',
            '0x11': 'ECU Reset',
            '0x14': 'Clear Diagnostic Information',
            '0x19': 'Read DTC Information',
            '0x22': 'Read Data By Identifier',
            '0x23': 'Read Memory By Address',
            '0x24': 'Read Scaling Data By Identifier',
            '0x27': 'Security Access',
            '0x28': 'Communication Control',
            '0x2A': 'Read Data By Periodic Identifier',
            '0x2C': 'Dynamically Define Data Identifier',
            '0x2E': 'Write Data By Identifier',
            '0x2F': 'Input Output Control By Identifier',
            '0x31': 'Routine Control',
            '0x34': 'Request Download',
            '0x35': 'Request Upload',
            '0x36': 'Transfer Data',
            '0x37': 'Request Transfer Exit',
            '0x38': 'Request File Transfer',
            '0x3D': 'Write Memory By Address',
            '0x3E': 'Tester Present',
            '0x83': 'Access Timing Parameter',
            '0x84': 'Secured Data Transmission',
            '0x85': 'Control DTC Setting',
            '0x86': 'Response On Event',
            '0x87': 'Link Control'
        }
        
        return service_descriptions.get(service_id, 'Unknown Service')