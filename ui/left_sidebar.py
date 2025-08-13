"""
Advanced Left Sidebar for Professional CAN Analyzer
Enhanced bus configuration and transmit functionality - FIXED VERSION
"""

import os
import glob
import platform
import subprocess
import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QRadioButton, QPushButton, QLineEdit,
                               QCheckBox, QSpinBox, QGroupBox, QFormLayout,
                               QButtonGroup, QFrame, QScrollArea, QTabWidget,
                               QTableWidget, QListWidget, QToolBar,
                               QAbstractItemView, QTableWidgetItem, QCheckBox,
                               QSlider, QProgressBar, QTextEdit, QSplitter, 
                               QDialog, QDialogButtonBox, QHeaderView)
from PySide6.QtCore import Signal, Qt, QTimer, QSize
from PySide6.QtGui import QFont, QValidator, QRegularExpressionValidator, QIcon, QIntValidator, QColor
from can_backend import CANBusManager
from dataclasses import dataclass
import copy

@dataclass
class TxMessage:
    """Data class for a transmit message."""
    msg_id: str
    dlc: int
    data: str  # Space-separated hex string
    cycle_ms: int
    count: int  # 0 for infinite
    is_active: bool = False
    total_sent: int = 0  # Track how many messages have been sent
    dbc_name: str = ""  # For DBC integration
    dbc_signals: dict = None  # For DBC signal values
    # CAN control bits
    rtr: bool = False  # Remote Transmission Request
    extended_id: bool = False  # Extended ID (29-bit)
    fd: bool = False  # CAN-FD frame
    brs: bool = False  # Bit Rate Switch (CAN-FD)
    esi: bool = False  # Error State Indicator (CAN-FD)

    def __post_init__(self):
        if self.dbc_signals is None:
            self.dbc_signals = {}

class AdvancedLeftSidebar(QScrollArea):
    """Advanced left sidebar with comprehensive CAN functionality"""
    
    # Connection signals
    connect_requested = Signal(dict)  # Connection parameters
    disconnect_requested = Signal()
    
    # Message signals
    send_message = Signal(dict)
    start_periodic = Signal(dict)
    stop_periodic = Signal(str)  # Message ID
    
    # Configuration signals
    interface_changed = Signal(str)
    bitrate_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.periodic_timers = {}  # Track periodic sending: {row_index: QTimer}
        self.message_templates = []  # Store message templates
        self.dbc_manager = None
        self.dbc_message_cache = {}  # Cache DBC messages to avoid repeated lookups
        self.dbc_cache_valid = False  # Track if cache is valid
        self.setup_ui()
        self.apply_modern_style()
    
    def invalidate_dbc_cache(self):
        """Invalidate DBC cache when DBC file changes."""
        self.dbc_message_cache.clear()
        self.dbc_cache_valid = False
        print("[DEBUG] DBC cache invalidated")
    
    def get_dbc_message_cached(self, msg_id):
        """Get DBC message with caching to avoid repeated lookups."""
        if not self.dbc_manager:
            return None
            
        # Parse message ID to integer
        try:
            if isinstance(msg_id, str):
                if msg_id.startswith(('0x', '0X')):
                    msg_id_int = int(msg_id, 16)
                else:
                    msg_id_int = int(msg_id, 16)  # Assume hex
            else:
                msg_id_int = int(msg_id)
        except (ValueError, TypeError):
            print(f"[DEBUG] Failed to parse message ID: {msg_id}")
            return None
        
        # Rebuild cache if invalid
        if not self.dbc_cache_valid:
            self.rebuild_dbc_cache()
        
        # Check cache first
        if self.dbc_cache_valid and msg_id_int in self.dbc_message_cache:
            print(f"[DEBUG] Cache hit for ID 0x{msg_id_int:X}")
            return self.dbc_message_cache[msg_id_int]
        
        # If not in cache, try fallback lookup directly from DBC manager
        print(f"[DEBUG] Cache miss for ID 0x{msg_id_int:X}, trying direct lookup")
        dbc_msg = self._direct_dbc_lookup(msg_id_int)
        
        # If found via direct lookup, add to cache
        if dbc_msg:
            self.dbc_message_cache[msg_id_int] = dbc_msg
            print(f"[DEBUG] Added ID 0x{msg_id_int:X} to cache via direct lookup")
        
        return dbc_msg
    
    def _direct_dbc_lookup(self, msg_id_int):
        """Direct DBC lookup fallback when cache misses."""
        try:
            # Try different DBC manager methods with proper error handling
            if hasattr(self.dbc_manager, 'get_message_by_id'):
                try:
                    return self.dbc_manager.get_message_by_id(msg_id_int)
                except (KeyError, ValueError, AttributeError):
                    pass
            
            if hasattr(self.dbc_manager, 'active_database') and self.dbc_manager.active_database:
                db = self.dbc_manager.active_database
                
                # Try get_message_by_frame_id
                if hasattr(db, 'get_message_by_frame_id'):
                    try:
                        return db.get_message_by_frame_id(msg_id_int)
                    except (KeyError, ValueError, AttributeError):
                        pass
                
                # Try searching through messages manually
                if hasattr(db, 'messages'):
                    for message in db.messages:
                        frame_id = getattr(message, 'frame_id', None)
                        if frame_id == msg_id_int:
                            return message
            
            print(f"[DEBUG] Direct lookup failed for ID 0x{msg_id_int:X}")
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error in direct DBC lookup for ID 0x{msg_id_int:X}: {e}")
            return None
    
    def rebuild_dbc_cache(self):
        """Rebuild the DBC message cache."""
        if not self.dbc_manager:
            return
            
        self.dbc_message_cache.clear()
        
        try:
            # Try different methods to get all messages
            messages = []
            
            if hasattr(self.dbc_manager, 'get_all_messages'):
                messages = self.dbc_manager.get_all_messages()
            elif hasattr(self.dbc_manager, 'active_database') and self.dbc_manager.active_database:
                db = self.dbc_manager.active_database
                if hasattr(db, 'messages'):
                    messages = db.messages
            
            # Cache all messages by their frame ID
            for msg in messages:
                frame_id = getattr(msg, 'frame_id', None)
                if frame_id is not None:
                    self.dbc_message_cache[frame_id] = msg
            
            self.dbc_cache_valid = True
            print(f"[DEBUG] DBC cache rebuilt with {len(self.dbc_message_cache)} messages")
            
        except Exception as e:
            print(f"[DEBUG] Error rebuilding DBC cache: {e}")
            self.dbc_cache_valid = False
        
    def setup_ui(self):
        """Setup the sidebar UI"""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.tab_widget = QTabWidget()

        # Bus Config Tab
        bus_config_tab = self.setup_bus_config_tab()
        self.tab_widget.addTab(bus_config_tab, "🔧 Bus Config")

        # Transmit Tab (CAN IG)
        transmit_tab = self.setup_transmit_tab()
        self.tab_widget.addTab(transmit_tab, "📤 Transmit")

        # Initialize model and populate table AFTER UI is created
        self._init_tx_model()
        self.populate_tx_table()

        layout.addWidget(self.tab_widget)
        # Set the widget for the scroll area
        self.setWidget(main_widget)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setup_bus_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        
        # Interface Configuration
        interface_group = QGroupBox("🔌 Interface Configuration")
        interface_layout = QFormLayout(interface_group)
        
        # Driver selection with auto-detection
        self.driver_combo = QComboBox()
        self.driver_combo.addItems([
            "auto-detect", "slcan", "socketcan", "vector", "pcan", "kvaser", "ixxat"
        ])
        self.driver_combo.currentTextChanged.connect(self._on_driver_changed)
        interface_layout.addRow("Driver:", self.driver_combo)
        
        # Interface selection (dynamic based on driver)
        interface_widget = QWidget()
        interface_widget_layout = QHBoxLayout(interface_widget)
        interface_widget_layout.setContentsMargins(0, 0, 0, 0)
        
        self.interface_combo = QComboBox()
        self.refresh_interfaces_btn = QPushButton("🔄")
        self.refresh_interfaces_btn.setToolTip("Refresh available interfaces")
        self.refresh_interfaces_btn.setMaximumWidth(30)
        self.refresh_interfaces_btn.clicked.connect(self._refresh_interfaces)
        
        interface_widget_layout.addWidget(self.interface_combo, 1)
        interface_widget_layout.addWidget(self.refresh_interfaces_btn)
        
        interface_layout.addRow("Interface:", interface_widget)
        
        # Populate initial interfaces
        self._refresh_interfaces()
        
        # Channel number (for drivers that need it)
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(0, 15)
        interface_layout.addRow("Channel:", self.channel_spin)
        
        # Store reference to the channel row for show/hide
        self.channel_row_index = interface_layout.rowCount() - 1
        
        # USB Device Info (for SLCAN devices)
        self.device_info_label = QLabel("")
        self.device_info_label.setStyleSheet("color: #666; font-style: italic; font-size: 8pt;")
        self.device_info_label.setWordWrap(True)
        interface_layout.addRow("Device Info:", self.device_info_label)
        
        layout.addWidget(interface_group)
        
        # CAN Configuration
        can_group = QGroupBox("⚙️ CAN Configuration")
        can_layout = QFormLayout(can_group)
        
        # CAN mode selection
        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        
        self.mode_group = QButtonGroup()
        self.can_radio = QRadioButton("CAN 2.0")
        self.canfd_radio = QRadioButton("CAN FD")
        self.can_radio.setChecked(True)
        
        self.mode_group.addButton(self.can_radio, 0)
        self.mode_group.addButton(self.canfd_radio, 1)
        
        mode_layout.addWidget(self.can_radio)
        mode_layout.addWidget(self.canfd_radio)
        mode_layout.addStretch()
        
        can_layout.addRow("Mode:", mode_widget)
        
        # Bitrate configuration
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setEditable(True)
        self.bitrate_combo.addItems([
            "83.333", "125", "250", "500", "800", "1000"
        ])
        self.bitrate_combo.setCurrentText("500")
        self.bitrate_combo.currentTextChanged.connect(
            lambda x: self.bitrate_changed.emit(int(float(x) * 1000))
        )
        can_layout.addRow("Nominal Bitrate (kbps):", self.bitrate_combo)
        
        # Data bitrate for CAN FD
        self.data_bitrate_combo = QComboBox()
        self.data_bitrate_combo.setEditable(True)
        self.data_bitrate_combo.addItems([
            "1000", "2000", "4000", "5000", "8000", "10000"
        ])
        self.data_bitrate_combo.setCurrentText("2000")
        self.data_bitrate_combo.setEnabled(False)
        can_layout.addRow("Data Bitrate (kbps):", self.data_bitrate_combo)
        
        # Sample point
        self.sample_point_slider = QSlider(Qt.Horizontal)
        self.sample_point_slider.setRange(500, 900)
        self.sample_point_slider.setValue(750)
        self.sample_point_label = QLabel("75.0%")
        
        sample_widget = QWidget()
        sample_layout = QHBoxLayout(sample_widget)
        sample_layout.setContentsMargins(0, 0, 0, 0)
        sample_layout.addWidget(self.sample_point_slider)
        sample_layout.addWidget(self.sample_point_label)
        
        self.sample_point_slider.valueChanged.connect(
            lambda v: self.sample_point_label.setText(f"{v/10.0:.1f}%")
        )
        
        can_layout.addRow("Sample Point:", sample_widget)
        
        layout.addWidget(can_group)
        
        # Bus monitoring options
        monitor_group = QGroupBox("👁️ Monitoring Options")
        monitor_layout = QVBoxLayout(monitor_group)
        
        self.listen_only_cb = QCheckBox("Listen-only mode")
        self.fd_non_iso_cb = QCheckBox("FD non-ISO mode")
        self.triple_sampling_cb = QCheckBox("Triple sampling")
        self.one_shot_cb = QCheckBox("One-shot mode")
        
        monitor_layout.addWidget(self.listen_only_cb)
        monitor_layout.addWidget(self.fd_non_iso_cb)
        monitor_layout.addWidget(self.triple_sampling_cb)
        monitor_layout.addWidget(self.one_shot_cb)
        
        layout.addWidget(monitor_group)
        
        # Connection controls
        connection_group = QGroupBox("🔗 Connection")
        connection_layout = QVBoxLayout(connection_group)
        
        # Status display
        self.connection_status = QLabel("🔴 Disconnected")
        self.connection_status.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #ffebee;
                border: 1px solid #ef5350;
                border-radius: 4px;
                color: #c62828;
                font-weight: bold;
            }
        """)
        connection_layout.addWidget(self.connection_status)
        
        # Buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.connect_btn = QPushButton("🔌 Connect")
        self.disconnect_btn = QPushButton("❌ Disconnect")
        self.disconnect_btn.setEnabled(False)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        
        connection_layout.addWidget(button_widget)
        layout.addWidget(connection_group)
        
        layout.addStretch()
        
        # Connect signals
        self.canfd_radio.toggled.connect(self.data_bitrate_combo.setEnabled)
        self.connect_btn.clicked.connect(self.handle_connect)
        self.disconnect_btn.clicked.connect(self.handle_disconnect)
        
        return tab
    
    def _on_driver_changed(self, driver_text):
        """Handle driver selection change to update interface options"""
        print(f"[DEBUG] Driver changed to: {driver_text}")
        self._refresh_interfaces()
        self._update_ui_for_driver(driver_text)
    
    def _update_ui_for_driver(self, driver):
        """Update UI elements based on selected driver"""
        # Show/hide channel field based on driver
        if driver in ["vector", "pcan", "kvaser", "ixxat"]:
            self.channel_spin.setVisible(True)
            # Try to get the label widget and show it
            if hasattr(self, 'channel_row_index'):
                try:
                    layout = self.channel_spin.parent().layout()
                    if hasattr(layout, 'itemAt') and self.channel_row_index < layout.rowCount():
                        label_item = layout.itemAt(self.channel_row_index, QFormLayout.LabelRole)
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(True)
                except:
                    pass
        else:
            self.channel_spin.setVisible(False)
            # Try to hide the label widget
            if hasattr(self, 'channel_row_index'):
                try:
                    layout = self.channel_spin.parent().layout()
                    if hasattr(layout, 'itemAt') and self.channel_row_index < layout.rowCount():
                        label_item = layout.itemAt(self.channel_row_index, QFormLayout.LabelRole)
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(False)
                except:
                    pass
        
        # Update interface selection based on current choice
        current_interface = self.interface_combo.currentText()
        if current_interface and driver != "auto-detect":
            self._update_device_info(current_interface, driver)
    
    def _refresh_interfaces(self):
        """Refresh available interfaces based on selected driver"""
        driver = self.driver_combo.currentText()
        current_selection = self.interface_combo.currentText()
        
        self.interface_combo.clear()
        interfaces = []
        
        if driver == "auto-detect" or driver == "slcan":
            # Detect SLCAN-compatible serial devices
            slcan_devices = self._detect_slcan_devices()
            interfaces.extend(slcan_devices)
            print(f"[DEBUG] Found SLCAN devices: {slcan_devices}")
        
        if driver == "auto-detect" or driver == "socketcan":
            # Detect SocketCAN interfaces
            socketcan_devices = self._detect_socketcan_interfaces()
            interfaces.extend(socketcan_devices)
            print(f"[DEBUG] Found SocketCAN devices: {socketcan_devices}")
        
        # Add fallback options if no interfaces detected
        if not interfaces:
            if driver == "slcan" or driver == "auto-detect":
                interfaces.extend(["/dev/ttyACM0", "/dev/ttyUSB0", "COM3", "COM4"])
            if driver == "socketcan" or driver == "auto-detect":
                interfaces.extend(["can0", "can1", "vcan0"])
        
        self.interface_combo.addItems(interfaces)
        
        # Restore previous selection if available
        if current_selection and current_selection in interfaces:
            self.interface_combo.setCurrentText(current_selection)
        
        # Connect signal after population
        try:
            self.interface_combo.currentTextChanged.disconnect()
        except (TypeError, RuntimeError):
            # Signal was not connected, which is fine
            pass
        self.interface_combo.currentTextChanged.connect(self._on_interface_changed)
        self.interface_combo.currentTextChanged.connect(self.interface_changed.emit)
        
        print(f"[DEBUG] Populated {len(interfaces)} interfaces for driver {driver}")
    
    def _on_interface_changed(self, interface):
        """Handle interface selection change"""
        driver = self.driver_combo.currentText()
        self._update_device_info(interface, driver)
    
    def _update_device_info(self, interface, driver):
        """Update device information display"""
        info_text = ""
        
        if interface.startswith("/dev/tty") or interface.startswith("COM"):
            # This is likely a serial device - get USB info
            usb_info = self._get_usb_device_info(interface)
            if usb_info:
                info_text = f"USB Device: {usb_info['description']}\n"
                if usb_info.get('vendor'):
                    info_text += f"Vendor: {usb_info['vendor']}\n"
                if usb_info.get('product'):
                    info_text += f"Product: {usb_info['product']}\n"
                if usb_info.get('serial'):
                    info_text += f"Serial: {usb_info['serial']}"
            else:
                info_text = f"Serial device: {interface}"
        elif interface.startswith(("can", "vcan")):
            # SocketCAN interface
            socketcan_info = self._get_socketcan_info(interface)
            if socketcan_info:
                info_text = f"SocketCAN Interface: {socketcan_info['status']}\n"
                if socketcan_info.get('bitrate'):
                    info_text += f"Current Bitrate: {socketcan_info['bitrate']} bps"
            else:
                info_text = f"SocketCAN interface: {interface}"
        
        self.device_info_label.setText(info_text)
    
    def _detect_slcan_devices(self):
        """Detect potential SLCAN serial devices with USB-to-CAN identification"""
        slcan_candidates = []
        system = platform.system()
        
        try:
            if system == "Linux":
                # Linux serial device patterns with priority for USB devices
                patterns = [
                    "/dev/serial/by-id/*CAN*",      # CAN devices by ID (priority)
                    "/dev/serial/by-id/*can*",      # CAN devices by ID lowercase
                    "/dev/serial/by-id/*CANable*",  # CANable devices specifically
                    "/dev/ttyACM*",                 # USB-CDC devices (CANable, etc.)
                    "/dev/ttyUSB*",                 # FTDI/CH340 USB-Serial adapters
                ]
                
                for pattern in patterns:
                    for device in glob.glob(pattern):
                        if os.access(device, os.R_OK | os.W_OK):
                            # Resolve symlinks for by-id devices
                            real_device = os.path.realpath(device) if "/by-id/" in device else device
                            if real_device not in slcan_candidates:
                                slcan_candidates.append(real_device)
                
                # If no USB-CAN specific devices found, add generic USB serial
                if not slcan_candidates:
                    for pattern in ["/dev/ttyACM*", "/dev/ttyUSB*"]:
                        for device in glob.glob(pattern):
                            if os.access(device, os.R_OK | os.W_OK):
                                slcan_candidates.append(device)
                
            elif system == "Windows":
                # Windows COM ports - try pyserial for proper detection
                try:
                    import serial.tools.list_ports
                    ports = serial.tools.list_ports.comports()
                    
                    # Prioritize CAN-related devices
                    can_devices = []
                    other_devices = []
                    
                    for port in ports:
                        description = port.description.lower()
                        manufacturer = getattr(port, 'manufacturer', '').lower()
                        product = getattr(port, 'product', '').lower()
                        
                        # Check for CAN-related keywords
                        can_keywords = ['can', 'canable', 'cantact', 'usb2can', 'slcan', 'peak', 'kvaser']
                        is_can_device = any(keyword in description or keyword in manufacturer or keyword in product 
                                          for keyword in can_keywords)
                        
                        if is_can_device:
                            can_devices.append(port.device)
                        else:
                            other_devices.append(port.device)
                    
                    # Add CAN devices first, then others
                    slcan_candidates.extend(can_devices)
                    slcan_candidates.extend(other_devices[:5])  # Limit to first 5 non-CAN devices
                    
                except ImportError:
                    print("[DEBUG] pyserial not available, using fallback COM port detection")
                    # Fallback if pyserial not available
                    slcan_candidates = [f"COM{i}" for i in range(1, 21)]
                    
            elif system == "Darwin":  # macOS
                patterns = [
                    "/dev/cu.usbmodem*CAN*",    # CAN-specific USB modem devices
                    "/dev/cu.usbmodem*",        # USB modem devices
                    "/dev/cu.usbserial*",       # USB serial devices
                ]
                
                for pattern in patterns:
                    slcan_candidates.extend(glob.glob(pattern))
                    
        except Exception as e:
            print(f"[WARNING] Error detecting SLCAN devices: {e}")
            # Fallback
            if system == "Linux":
                slcan_candidates = ["/dev/ttyACM0", "/dev/ttyUSB0"]
            elif system == "Windows":
                slcan_candidates = ["COM3", "COM4", "COM5"]
            else:
                slcan_candidates = ["/dev/cu.usbmodem1", "/dev/cu.usbserial1"]
        
        # Remove duplicates while preserving order
        unique_candidates = []
        for device in slcan_candidates:
            if device not in unique_candidates:
                unique_candidates.append(device)
        
        print(f"[DEBUG] Detected SLCAN candidates: {unique_candidates}")
        return unique_candidates
    
    def _detect_socketcan_interfaces(self):
        """Detect available SocketCAN interfaces"""
        try:
            # Import the CAN manager to use its detection method
            interfaces = CANBusManager.list_socketcan_interfaces()
            if not interfaces:
                # Fallback detection
                import glob
                interfaces = []
                # Check /sys/class/net for CAN interfaces
                for interface_path in glob.glob("/sys/class/net/can*"):
                    interface_name = os.path.basename(interface_path)
                    interfaces.append(interface_name)
                # Also check for vcan interfaces
                for interface_path in glob.glob("/sys/class/net/vcan*"):
                    interface_name = os.path.basename(interface_path)
                    interfaces.append(interface_name)
                    
                # If still nothing, add common defaults
                if not interfaces:
                    interfaces = ["can0", "can1", "vcan0"]
                    
        except Exception as e:
            print(f"[WARNING] Error detecting SocketCAN interfaces: {e}")
            interfaces = ["can0", "can1", "vcan0"]
            
        return interfaces
    
    def _get_usb_device_info(self, device_path):
        """Get USB device information for a serial device"""
        try:
            import platform
            system = platform.system()
            
            if system == "Linux":
                # Try to get info from udev or sysfs
                import subprocess
                try:
                    # Use udevadm to get device info
                    result = subprocess.run(
                        ["udevadm", "info", "--name", device_path], 
                        capture_output=True, text=True, timeout=2
                    )
                    if result.returncode == 0:
                        info = {}
                        for line in result.stdout.split('\n'):
                            if 'ID_VENDOR=' in line:
                                info['vendor'] = line.split('=')[1].strip()
                            elif 'ID_MODEL=' in line:
                                info['product'] = line.split('=')[1].strip()
                            elif 'ID_SERIAL_SHORT=' in line:
                                info['serial'] = line.split('=')[1].strip()
                            elif 'ID_USB_INTERFACE_NUM=' in line:
                                info['interface'] = line.split('=')[1].strip()
                        
                        # Create description
                        if info.get('vendor') and info.get('product'):
                            info['description'] = f"{info['vendor']} {info['product']}"
                        else:
                            info['description'] = "USB Serial Device"
                            
                        return info
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
                    
            elif system == "Windows":
                # Use serial.tools.list_ports for Windows
                try:
                    import serial.tools.list_ports
                    ports = serial.tools.list_ports.comports()
                    for port in ports:
                        if port.device == device_path:
                            return {
                                'description': port.description,
                                'vendor': getattr(port, 'manufacturer', None),
                                'product': getattr(port, 'product', None),
                                'serial': getattr(port, 'serial_number', None)
                            }
                except ImportError:
                    pass
                    
        except Exception as e:
            print(f"[DEBUG] Could not get USB info for {device_path}: {e}")
            
        return None
    
    def _get_socketcan_info(self, interface):
        """Get SocketCAN interface information"""
        try:
            import subprocess
            # Get interface status
            result = subprocess.run(
                ["ip", "link", "show", interface], 
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                output = result.stdout
                status = "UP" if "UP" in output else "DOWN"
                
                # Try to get bitrate info
                bitrate = None
                try:
                    result = subprocess.run(
                        ["ip", "-details", "link", "show", interface], 
                        capture_output=True, text=True, timeout=2
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'bitrate' in line:
                                # Extract bitrate value
                                import re
                                match = re.search(r'bitrate (\d+)', line)
                                if match:
                                    bitrate = match.group(1)
                                break
                except:
                    pass
                    
                return {
                    'status': status,
                    'bitrate': bitrate
                }
        except Exception as e:
            print(f"[DEBUG] Could not get SocketCAN info for {interface}: {e}")
            
        return None

    def setup_transmit_tab(self):
        """Setup transmit tab with a professional CAN IG style."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Main GroupBox
        ig_group = QGroupBox("📤 Interactive Generator (CAN IG)")
        ig_layout = QVBoxLayout(ig_group)
        ig_layout.setContentsMargins(3, 3, 3, 3)
        ig_layout.setSpacing(2)

        # Toolbar for message management
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))

        # Add actions with proper icons (fallback to text if no theme icons)
        self.add_action = toolbar.addAction("➕", "Add Message")
        self.add_action.setToolTip("Add new message")
        
        self.edit_action = toolbar.addAction("✏️", "Edit Message")
        self.edit_action.setToolTip("Edit selected message")
        
        self.delete_action = toolbar.addAction("🗑️", "Delete Message")
        self.delete_action.setToolTip("Delete selected message")
        
        toolbar.addSeparator()
        
        self.clear_action = toolbar.addAction("🧹", "Clear All")
        self.clear_action.setToolTip("Clear all messages")
        
        toolbar.addSeparator()
        
        self.start_stop_action = toolbar.addAction("▶️", "Start/Stop All")
        self.start_stop_action.setCheckable(True)
        self.start_stop_action.setToolTip("Start/Stop all periodic messages")

        # Quick send controls
        quick_send_widget = QWidget()
        quick_layout = QHBoxLayout(quick_send_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        
        self.send_once_btn = QPushButton("📨 Send Once")
        self.send_once_btn.setToolTip("Send selected message once")
        
        self.send_all_btn = QPushButton("📤 Send All")
        self.send_all_btn.setToolTip("Send all active messages once")
        
        quick_layout.addWidget(self.send_once_btn)
        quick_layout.addWidget(self.send_all_btn)
        quick_layout.addStretch()
        
        toolbar.addWidget(quick_send_widget)

        ig_layout.addWidget(toolbar)

        # Create table with enhanced columns
        self.tx_table = QTableWidget(0, 10)
        headers = ["Send", "ID", "DBC Name", "DLC", "Data", "Period (ms)", "Count", "Sent", "Control", "Signals"]
        self.tx_table.setHorizontalHeaderLabels(headers)
        
        # Set compact table properties
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setAlternatingRowColors(True)
        self.tx_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tx_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Set compact font and row height for better space usage
        table_font = QFont()
        table_font.setPointSize(8)  # Smaller font size
        self.tx_table.setFont(table_font)
        self.tx_table.verticalHeader().setDefaultSectionSize(22)  # Compact row height
        
        # Set optimized column widths for compact display
        header = self.tx_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)    # Send checkbox
        header.setSectionResizeMode(1, QHeaderView.Fixed)    # ID
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # DBC Name - allow manual resize
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # DLC
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Data - takes remaining space
        header.setSectionResizeMode(5, QHeaderView.Fixed)    # Period
        header.setSectionResizeMode(6, QHeaderView.Fixed)    # Count
        header.setSectionResizeMode(7, QHeaderView.Fixed)    # Sent
        header.setSectionResizeMode(8, QHeaderView.Fixed)    # Control
        header.setSectionResizeMode(9, QHeaderView.Fixed)    # Signals
        
        # Compact column widths - optimized for space efficiency
        self.tx_table.setColumnWidth(0, 45)   # Send - reduced from 60
        self.tx_table.setColumnWidth(1, 65)   # ID - reduced from 80  
        self.tx_table.setColumnWidth(2, 80)   # DBC Name - compact but readable
        self.tx_table.setColumnWidth(3, 40)   # DLC - reduced from 50
        self.tx_table.setColumnWidth(5, 65)   # Period - reduced from 80
        self.tx_table.setColumnWidth(6, 50)   # Count - reduced from 60
        self.tx_table.setColumnWidth(7, 45)   # Sent - reduced from 60
        self.tx_table.setColumnWidth(8, 55)   # Control - compact buttons
        self.tx_table.setColumnWidth(9, 50)   # Signals - compact
        
        # Create splitter for CANoe-style layout
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tx_table)
        
        # Lower section for message editing
        self.tx_editor_widget = self.create_tx_editor_section()
        splitter.addWidget(self.tx_editor_widget)
        
        # Set splitter proportions (table takes 60%, editor takes 40%)
        splitter.setSizes([300, 200])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        
        ig_layout.addWidget(splitter)

        # Status info
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tx_status_label = QLabel("Ready")
        self.tx_status_label.setStyleSheet("color: #666; font-style: italic;")
        
        self.active_count_label = QLabel("Active: 0")
        self.active_count_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        
        status_layout.addWidget(self.tx_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.active_count_label)
        
        ig_layout.addWidget(status_widget)

        layout.addWidget(ig_group)

        # Connect signals
        self.add_action.triggered.connect(self.add_tx_message)
        self.edit_action.triggered.connect(self.edit_tx_message)
        self.delete_action.triggered.connect(self.delete_tx_message)
        self.clear_action.triggered.connect(self.clear_tx_messages)
        self.start_stop_action.toggled.connect(self.toggle_all_periodic)
        self.send_once_btn.clicked.connect(self.send_selected_once)
        self.send_all_btn.clicked.connect(self.send_all_once)
        
        # Table selection change
        self.tx_table.selectionModel().selectionChanged.connect(self.update_button_states)
        self.tx_table.selectionModel().selectionChanged.connect(self.on_tx_selection_changed)

        return tab
        
    def set_dbc_manager(self, dbc_manager):
        """Set the DBC manager for this sidebar"""
        self.dbc_manager = dbc_manager
        self.invalidate_dbc_cache()
        print("[DEBUG] DBC manager set and cache invalidated")

    def create_tx_editor_section(self):
        """Create the lower section for editing selected TX message (CANoe-style)."""
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(2, 2, 2, 2)
        editor_layout.setSpacing(2)
        
        # Header
        header_label = QLabel("📝 Message Editor")
        header_label.setStyleSheet("font-weight: bold; color: #1976d2; margin-bottom: 2px; font-size: 9pt;")
        editor_layout.addWidget(header_label)
        
        # Tab widget for Raw Data and Signals
        self.tx_editor_tabs = QTabWidget()
        
        # Raw Data tab
        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        raw_layout.setContentsMargins(2, 2, 2, 2)
        raw_layout.setSpacing(2)
        
        # Message info display
        info_group = QGroupBox("Message Information")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(2, 2, 2, 2)
        info_layout.setSpacing(1)
        
        self.selected_msg_id_label = QLabel("None")
        self.selected_msg_dlc_label = QLabel("0")
        self.selected_msg_name_label = QLabel("N/A")
        
        info_layout.addRow("ID:", self.selected_msg_id_label)
        info_layout.addRow("DLC:", self.selected_msg_dlc_label)
        info_layout.addRow("DBC Name:", self.selected_msg_name_label)
        
        raw_layout.addWidget(info_group)
        
        # Raw data editor
        data_group = QGroupBox("Raw Data (Hex)")
        data_layout = QVBoxLayout(data_group)
        
        self.raw_data_edit = QLineEdit()
        self.raw_data_edit.setPlaceholderText("Enter hex bytes (e.g., 01 02 03 04)")
        self.raw_data_edit.textChanged.connect(self.on_raw_data_changed)
        data_layout.addWidget(self.raw_data_edit)
        
        # Hex viewer
        self.hex_viewer = QTextEdit()
        self.hex_viewer.setMaximumHeight(80)
        self.hex_viewer.setReadOnly(True)
        self.hex_viewer.setFont(QFont("Courier", 9))
        data_layout.addWidget(self.hex_viewer)
        
        raw_layout.addWidget(data_group)
        
        self.tx_editor_tabs.addTab(raw_tab, "Raw Data")
        
        # Signals tab
        signals_tab = QWidget()
        signals_layout = QVBoxLayout(signals_tab)
        
        # Signals table
        signals_group = QGroupBox("DBC Signals")
        signals_group_layout = QVBoxLayout(signals_group)
        signals_group_layout.setContentsMargins(2, 2, 2, 2)
        signals_group_layout.setSpacing(1)
        
        self.signals_table = QTableWidget(0, 4)
        self.signals_table.setHorizontalHeaderLabels(["Signal", "Value", "Unit", "Description"])
        
        # Set compact table properties for signals table
        signals_font = QFont()
        signals_font.setPointSize(9)  # Slightly larger font for better dropdown readability
        self.signals_table.setFont(signals_font)
        self.signals_table.verticalHeader().setVisible(False)
        self.signals_table.verticalHeader().setDefaultSectionSize(26)  # Increased row height for dropdown widgets
        self.signals_table.setAlternatingRowColors(True)
        
        # Optimize column sizing for signals table
        signals_header = self.signals_table.horizontalHeader()
        signals_header.setSectionResizeMode(0, QHeaderView.Interactive)  # Signal name
        signals_header.setSectionResizeMode(1, QHeaderView.Fixed)        # Value
        signals_header.setSectionResizeMode(2, QHeaderView.Fixed)        # Unit  
        signals_header.setSectionResizeMode(3, QHeaderView.Stretch)      # Description
        
        # Set compact column widths
        self.signals_table.setColumnWidth(0, 80)   # Signal name - compact but readable
        self.signals_table.setColumnWidth(1, 85)   # Value - increased for dropdown readability
        self.signals_table.setColumnWidth(2, 50)   # Unit - compact for unit text
        
        # Connect table item changes to signal value change handler
        self.signals_table.itemChanged.connect(self.on_signal_value_changed)
        signals_group_layout.addWidget(self.signals_table)
        
        signals_layout.addWidget(signals_group)
        
        self.tx_editor_tabs.addTab(signals_tab, "Signals")
        
        editor_layout.addWidget(self.tx_editor_tabs)
        
        # Apply/Cancel buttons
        button_layout = QHBoxLayout()
        
        self.apply_changes_btn = QPushButton("✅ Apply Changes")
        self.apply_changes_btn.clicked.connect(self.apply_editor_changes)
        self.apply_changes_btn.setEnabled(False)
        
        self.revert_changes_btn = QPushButton("↶ Revert")
        self.revert_changes_btn.clicked.connect(self.revert_editor_changes)
        self.revert_changes_btn.setEnabled(False)
        
        button_layout.addWidget(self.apply_changes_btn)
        button_layout.addWidget(self.revert_changes_btn)
        button_layout.addStretch()
        
        editor_layout.addLayout(button_layout)
        
        # Initially disabled until a message is selected
        editor_widget.setEnabled(False)
        
        return editor_widget

    def on_tx_selection_changed(self):
        """Handle TX table selection change to update the editor."""
        selected_rows = self.tx_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.tx_messages):
                # Check if we're selecting the same message that's already being edited
                if hasattr(self, 'current_editing_row') and self.current_editing_row == row:
                    # Same message selected, don't reload to preserve edits
                    return
                    
                msg = self.tx_messages[row]
                self.load_message_in_editor(msg, row)
                self.tx_editor_widget.setEnabled(True)
            else:
                self.tx_editor_widget.setEnabled(False)
        else:
            self.tx_editor_widget.setEnabled(False)
    
    def load_message_in_editor(self, msg, row_index):
        """Load a message into the editor section."""
        print(f"[DEBUG] Loading message in editor: row {row_index}, ID {msg.msg_id}")
        self.current_editing_row = row_index
        # Store a copy of the original message state for revert functionality
        self.original_message_data = copy.deepcopy(msg) if hasattr(msg, '__dict__') else msg
        
        # Temporarily disconnect signals to prevent recursive updates
        try:
            self.signals_table.itemChanged.disconnect()
        except:
            pass  # May not be connected yet
        
        # Update message info
        self.selected_msg_id_label.setText(str(msg.msg_id))
        self.selected_msg_dlc_label.setText(str(msg.dlc))
        self.selected_msg_name_label.setText(msg.dbc_name if msg.dbc_name else "N/A")
        
        # Update raw data
        self.raw_data_edit.setText(msg.data)
        self.update_hex_viewer(msg.data)
        
        # Update signals table if DBC signals exist
        self.populate_signals_table(msg)
        
        # Reconnect signals
        self.signals_table.itemChanged.connect(self.on_signal_value_changed)
        
        # Reset button states
        self.apply_changes_btn.setEnabled(False)
        self.revert_changes_btn.setEnabled(False)
        
        print(f"[DEBUG] Message loaded in editor successfully")
    
    def populate_signals_table(self, msg):
        """Populate the signals table with DBC signal data."""
        # Clear table content gently to prevent UI artifacts
        self.signals_table.clearContents()
        self.signals_table.setRowCount(0)
        
        # Temporarily disable updates to prevent flickering
        self.signals_table.setUpdatesEnabled(False)
        
        if not self.dbc_manager:
            print("[DEBUG] No DBC manager available")
            return
        
        # Get DBC message definition using cached lookup
        try:
            # Parse message ID first (needed for both success and error cases)
            msg_id_int = None
            try:
                if isinstance(msg.msg_id, str):
                    if msg.msg_id.startswith(('0x', '0X')):
                        msg_id_int = int(msg.msg_id, 16)
                    else:
                        msg_id_int = int(msg.msg_id, 16)
                else:
                    msg_id_int = int(msg.msg_id)
            except (ValueError, TypeError):
                msg_id_int = 0  # Default fallback
            
            dbc_msg = self.get_dbc_message_cached(msg.msg_id)
            
            if dbc_msg:
                print(f"[DEBUG] Found cached DBC message with ID: 0x{msg_id_int:X}")
            
            if dbc_msg and hasattr(dbc_msg, 'signals'):
                print(f"[DEBUG] Found DBC message '{getattr(dbc_msg, 'name', 'Unknown')}' with {len(dbc_msg.signals)} signals")
                
                for i, signal in enumerate(dbc_msg.signals):
                    self.signals_table.insertRow(i)
                    
                    # Signal name
                    self.signals_table.setItem(i, 0, QTableWidgetItem(signal.name))
                    
                    # Current value (from msg.dbc_signals or default)
                    current_value = 0
                    if msg.dbc_signals and signal.name in msg.dbc_signals:
                        current_value = msg.dbc_signals[signal.name]
                    
                    # Create appropriate editor based on signal type
                    if hasattr(signal, 'choices') and signal.choices:
                        # Dropdown for enumerated values
                        combo = QComboBox()
                        
                        # Set font and styling for better readability
                        combo_font = QFont()
                        combo_font.setPointSize(9)  # Match table font
                        combo.setFont(combo_font)
                        combo.setMaximumHeight(24)  # Constrain height to fit row
                        combo.setStyleSheet("""
                            QComboBox {
                                padding: 2px 4px;
                                border: 1px solid #ccc;
                            }
                            QComboBox::drop-down {
                                width: 15px;
                            }
                            QComboBox QAbstractItemView {
                                font-size: 9pt;
                                selection-background-color: #3daee9;
                            }
                        """)
                        
                        for value, description in signal.choices.items():
                            combo.addItem(f"{description} ({value})", value)
                        # Set current value
                        for j in range(combo.count()):
                            if combo.itemData(j) == current_value:
                                combo.setCurrentIndex(j)
                                break
                        combo.currentIndexChanged.connect(self.on_signal_value_changed)
                        self.signals_table.setCellWidget(i, 1, combo)
                    else:
                        # Regular input for numeric values
                        value_item = QTableWidgetItem(str(current_value))
                        value_item.setFlags(value_item.flags() | Qt.ItemIsEditable)
                        self.signals_table.setItem(i, 1, value_item)
                    
                    # Unit
                    unit = getattr(signal, 'unit', '') or ''
                    self.signals_table.setItem(i, 2, QTableWidgetItem(unit))
                    
                    # Description
                    comment = getattr(signal, 'comment', '') or ''
                    self.signals_table.setItem(i, 3, QTableWidgetItem(comment))
            else:
                print(f"[DEBUG] No DBC message found for ID 0x{msg_id_int:X} or message has no signals")
                if dbc_msg:
                    print(f"[DEBUG] DBC message found but signals attribute: {hasattr(dbc_msg, 'signals')}")
                
                # Show user-friendly message when no signals are available
                self.signals_table.insertRow(0)
                no_signals_item = QTableWidgetItem("No DBC signals available for this message ID")
                no_signals_item.setFlags(no_signals_item.flags() & ~Qt.ItemIsEditable)
                self.signals_table.setItem(0, 0, no_signals_item)
                self.signals_table.setSpan(0, 0, 1, 4)  # Span across all columns
                    
        except Exception as e:
            print(f"[DEBUG] Error populating signals table: {e}")
            # Show error message in table
            self.signals_table.insertRow(0)
            error_item = QTableWidgetItem(f"Error loading DBC signals: {str(e)}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemIsEditable)
            self.signals_table.setItem(0, 0, error_item)
            self.signals_table.setSpan(0, 0, 1, 4)
        
        finally:
            # Always re-enable updates to prevent the table from staying frozen
            self.signals_table.setUpdatesEnabled(True)
            # Force a single clean repaint to prevent artifacts
            self.signals_table.repaint()
    
    def on_raw_data_changed(self):
        """Handle raw data text change."""
        self.update_hex_viewer(self.raw_data_edit.text())
        self.apply_changes_btn.setEnabled(True)
        self.revert_changes_btn.setEnabled(True)
    
    def on_signal_value_changed(self):
        """Handle signal value change."""
        try:
            # Update signal values from the table
            if hasattr(self, 'current_editing_row') and self.current_editing_row < len(self.tx_messages):
                msg = self.tx_messages[self.current_editing_row]
                
                # Ensure dbc_signals dict exists
                if not msg.dbc_signals:
                    msg.dbc_signals = {}
                
                # Update signal values from table
                for i in range(self.signals_table.rowCount()):
                    signal_name_item = self.signals_table.item(i, 0)
                    if signal_name_item:
                        signal_name = signal_name_item.text()
                        
                        # Get value from widget
                        value_widget = self.signals_table.cellWidget(i, 1)
                        if isinstance(value_widget, QComboBox):
                            # Dropdown - get selected value
                            msg.dbc_signals[signal_name] = value_widget.currentData()
                        else:
                            # Text input - get text value
                            value_item = self.signals_table.item(i, 1)
                            if value_item:
                                try:
                                    msg.dbc_signals[signal_name] = float(value_item.text())
                                except ValueError:
                                    msg.dbc_signals[signal_name] = 0
                
                # Try to update raw data from signals if DBC manager supports it
                self.update_raw_data_from_signals(msg)
                
            self.apply_changes_btn.setEnabled(True)
            self.revert_changes_btn.setEnabled(True)
            
        except Exception as e:
            print(f"[DEBUG] Error in signal value change: {e}")
    
    def update_raw_data_from_signals(self, msg):
        """Update raw data from signal values using DBC encoding."""
        try:
            if not self.dbc_manager or not msg.dbc_signals:
                return
            
            # Get DBC message definition
            msg_id_int = None
            if isinstance(msg.msg_id, str):
                if msg.msg_id.startswith(('0x', '0X')):
                    msg_id_int = int(msg.msg_id, 16)
                else:
                    msg_id_int = int(msg.msg_id, 16)
            else:
                msg_id_int = int(msg.msg_id)
            
            # Try to encode the message using DBC manager
            if hasattr(self.dbc_manager, 'encode_message'):
                try:
                    # Use DBC manager to encode signal values to raw data
                    encoded_data = self.dbc_manager.encode_message(msg_id_int, msg.dbc_signals)
                    if encoded_data:
                        # Update raw data display
                        hex_string = ' '.join(f'{b:02X}' for b in encoded_data)
                        self.raw_data_edit.setText(hex_string)
                        self.update_hex_viewer(hex_string)
                        
                        # Update message data
                        msg.data = hex_string
                        msg.dlc = len(encoded_data)
                        
                        print(f"[DEBUG] Updated raw data from signals: {hex_string}")
                        return
                except Exception as e:
                    print(f"[DEBUG] Error encoding message: {e}")
            
            # Fallback: try direct DBC database encoding
            if hasattr(self.dbc_manager, 'active_database') and self.dbc_manager.active_database:
                db = self.dbc_manager.active_database
                try:
                    if hasattr(db, 'encode_message'):
                        encoded_data = db.encode_message(msg_id_int, msg.dbc_signals)
                        if encoded_data:
                            hex_string = ' '.join(f'{b:02X}' for b in encoded_data)
                            self.raw_data_edit.setText(hex_string)
                            self.update_hex_viewer(hex_string)
                            msg.data = hex_string
                            msg.dlc = len(encoded_data)
                            print(f"[DEBUG] Updated raw data from signals (fallback): {hex_string}")
                            return
                except Exception as e:
                    print(f"[DEBUG] Error with fallback encoding: {e}")
            
            print(f"[DEBUG] Could not encode signals to raw data - DBC encoding not available")
            
        except Exception as e:
            print(f"[DEBUG] Error updating raw data from signals: {e}")
    
    def update_hex_viewer(self, data_text):
        """Update the hex viewer with formatted data."""
        try:
            # Parse hex data
            hex_bytes = []
            if data_text.strip():
                # Remove spaces and parse hex
                clean_data = data_text.replace(' ', '').replace('0x', '')
                for i in range(0, len(clean_data), 2):
                    if i + 1 < len(clean_data):
                        hex_bytes.append(int(clean_data[i:i+2], 16))
            
            # Format as hex dump
            if hex_bytes:
                hex_line = ' '.join(f'{b:02X}' for b in hex_bytes)
                ascii_line = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in hex_bytes)
                formatted = f"Hex: {hex_line}\nASC: {ascii_line}\nDec: {' '.join(str(b) for b in hex_bytes)}"
            else:
                formatted = "No data"
            
            self.hex_viewer.setPlainText(formatted)
        except Exception as e:
            self.hex_viewer.setPlainText(f"Invalid hex data: {e}")
    
    def apply_editor_changes(self):
        """Apply changes from the editor to the message."""
        if not hasattr(self, 'current_editing_row'):
            return
        
        row = self.current_editing_row
        if row >= len(self.tx_messages):
            return
        
        msg = self.tx_messages[row]
        print(f"[DEBUG] Applying editor changes for message {msg.msg_id}")
        
        # Update raw data
        msg.data = self.raw_data_edit.text()
        
        # Update DLC based on data length
        try:
            clean_data = msg.data.replace(' ', '').replace('0x', '')
            msg.dlc = len(clean_data) // 2
        except:
            pass
        
        # Update signals from table
        if not msg.dbc_signals:
            msg.dbc_signals = {}
            
        for i in range(self.signals_table.rowCount()):
            signal_name_item = self.signals_table.item(i, 0)
            if signal_name_item:
                signal_name = signal_name_item.text()
                
                # Get value from widget
                value_widget = self.signals_table.cellWidget(i, 1)
                if isinstance(value_widget, QComboBox):
                    msg.dbc_signals[signal_name] = value_widget.currentData()
                    print(f"[DEBUG] Updated signal {signal_name} = {value_widget.currentData()} (dropdown)")
                else:
                    value_item = self.signals_table.item(i, 1)
                    if value_item:
                        try:
                            msg.dbc_signals[signal_name] = float(value_item.text())
                            print(f"[DEBUG] Updated signal {signal_name} = {value_item.text()} (text)")
                        except ValueError:
                            print(f"[DEBUG] Invalid value for signal {signal_name}: {value_item.text()}")
        
        # Temporarily disconnect selection changes to prevent editor reload
        self.tx_table.selectionModel().selectionChanged.disconnect()
        
        # Refresh only the specific row in the table to avoid full reload
        self.update_tx_table_row(row, msg)
        
        # Reconnect selection changes
        self.tx_table.selectionModel().selectionChanged.connect(self.on_tx_selection_changed)
        
        # Reset button states
        self.apply_changes_btn.setEnabled(False)
        self.revert_changes_btn.setEnabled(False)
        
        print(f"[DEBUG] Changes applied successfully, editor remains active")
    
    def update_tx_table_row(self, row, msg):
        """Update a specific row in the TX table without full refresh."""
        try:
            # Column mapping: ["Send", "ID", "DBC Name", "DLC", "Data", "Period (ms)", "Count", "Sent", "Control", "Signals"]
            # Update the table items for this specific row with correct column indices
            
            # Column 1: ID
            self.tx_table.setItem(row, 1, QTableWidgetItem(str(msg.msg_id)))
            
            # Column 2: DBC Name
            self.tx_table.setItem(row, 2, QTableWidgetItem(msg.dbc_name if msg.dbc_name else "N/A"))
            
            # Column 3: DLC
            self.tx_table.setItem(row, 3, QTableWidgetItem(str(msg.dlc)))
            
            # Column 4: Data
            self.tx_table.setItem(row, 4, QTableWidgetItem(msg.data))
            
            # Column 5: Period (ms)
            self.tx_table.setItem(row, 5, QTableWidgetItem(str(msg.cycle_ms)))
            
            # Column 6: Count (total_sent)
            self.tx_table.setItem(row, 6, QTableWidgetItem(str(msg.total_sent)))
            
            # Column 7: Sent (same as total_sent for now)
            self.tx_table.setItem(row, 7, QTableWidgetItem(str(msg.total_sent)))
            
            # Column 8: Control bits
            control_bits = []
            if msg.rtr:
                control_bits.append("RTR")
            if msg.extended_id:
                control_bits.append("EXT")
            if msg.fd:
                control_bits.append("FD")
            if msg.brs:
                control_bits.append("BRS")
            if msg.esi:
                control_bits.append("ESI")
            control_text = ", ".join(control_bits) if control_bits else "STD"
            self.tx_table.setItem(row, 8, QTableWidgetItem(control_text))
            
            # Column 9: Signals count
            signal_count = len(msg.dbc_signals) if msg.dbc_signals else 0
            self.tx_table.setItem(row, 9, QTableWidgetItem(str(signal_count)))
            
            print(f"[DEBUG] Updated TX table row {row} for message {msg.msg_id} with correct column mapping")
            
        except Exception as e:
            print(f"[DEBUG] Error updating TX table row {row}: {e}")
    
    def revert_editor_changes(self):
        """Revert editor changes to original message data."""
        if hasattr(self, 'original_message_data') and hasattr(self, 'current_editing_row'):
            self.load_message_in_editor(self.original_message_data, self.current_editing_row)

    def _init_tx_model(self):
        """Initialize the data model for the transmit tab."""
        self.tx_messages = [
            # Sample messages for demonstration
            TxMessage('0x100', 8, '11 22 33 44 55 66 77 88', 100, 0, False),
            TxMessage('0x2A0', 4, 'DE AD BE EF', 500, 10, False)
        ]
        self.tx_periodic_timers = {}  # key: row_index, value: QTimer

    def populate_tx_table(self):
        """Populate the transmit table with messages from the model."""
        self.tx_table.blockSignals(True)
        self.tx_table.setRowCount(0)
        
        for i, msg in enumerate(self.tx_messages):
            self.tx_table.insertRow(i)
            
            # Checkbox for active state
            send_checkbox = QCheckBox()
            send_checkbox.setChecked(msg.is_active)
            # Store row index as property to avoid lambda closure issues
            send_checkbox.row_index = i
            send_checkbox.toggled.connect(lambda checked, checkbox=send_checkbox: 
                                        self.update_message_active_state(checkbox.row_index, checked))
            self.tx_table.setCellWidget(i, 0, send_checkbox)
            
            # Message ID
            self.tx_table.setItem(i, 1, QTableWidgetItem(str(msg.msg_id)))
            
            # DBC Name
            dbc_name = msg.dbc_name if msg.dbc_name else "N/A"
            self.tx_table.setItem(i, 2, QTableWidgetItem(dbc_name))
            
            # DLC
            self.tx_table.setItem(i, 3, QTableWidgetItem(str(msg.dlc)))
            
            # Data
            self.tx_table.setItem(i, 4, QTableWidgetItem(msg.data))
            
            # Cycle time
            cycle_text = str(msg.cycle_ms) if msg.cycle_ms > 0 else 'Manual'
            self.tx_table.setItem(i, 5, QTableWidgetItem(cycle_text))
            
            # Count
            count_text = str(msg.count) if msg.count > 0 else '∞'
            self.tx_table.setItem(i, 6, QTableWidgetItem(count_text))
            
            # Sent counter
            self.tx_table.setItem(i, 7, QTableWidgetItem(str(msg.total_sent)))
            
            # Control bits
            control_bits = []
            if msg.rtr: control_bits.append("RTR")
            if msg.extended_id: control_bits.append("EXT")
            if msg.fd: control_bits.append("FD")
            if msg.brs: control_bits.append("BRS")
            if msg.esi: control_bits.append("ESI")
            control_text = ", ".join(control_bits) if control_bits else "STD"
            self.tx_table.setItem(i, 8, QTableWidgetItem(control_text))
            
            # Signals count
            signals_count = len(msg.dbc_signals) if msg.dbc_signals else 0
            signals_text = f"{signals_count} signals" if signals_count > 0 else "No signals"
            self.tx_table.setItem(i, 9, QTableWidgetItem(signals_text))
            
            # Color code active rows
            if msg.is_active:
                for col in range(self.tx_table.columnCount()):
                    item = self.tx_table.item(i, col)
                    if item:
                        item.setBackground(QColor("lightgreen"))
                        
        self.tx_table.blockSignals(False)
        self.update_status_labels()
        self.update_button_states()

    def update_status_labels(self):
        """Update status labels in the transmit tab"""
        active_count = sum(1 for msg in self.tx_messages if msg.is_active)
        self.active_count_label.setText(f"Active: {active_count}")
        
        if any(timer.isActive() for timer in self.tx_periodic_timers.values()):
            self.tx_status_label.setText("🟢 Transmitting...")
            self.tx_status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.tx_status_label.setText("Ready")
            self.tx_status_label.setStyleSheet("color: #666; font-style: italic;")

    def update_button_states(self):
        """Update button enabled states based on selection and content"""
        has_selection = bool(self.tx_table.selectionModel().selectedRows())
        has_messages = len(self.tx_messages) > 0
        
        self.edit_action.setEnabled(has_selection)
        self.delete_action.setEnabled(has_selection)
        self.send_once_btn.setEnabled(has_selection)
        self.send_all_btn.setEnabled(has_messages)
        self.clear_action.setEnabled(has_messages)

    def add_tx_message(self):
        """Add a new message via dialog"""
        print("[DEBUG] Opening add message dialog")
        
        dialog = self.TxMessageDialog(self)
        dialog_result = dialog.exec()
        
        # Ensure dialog is properly cleaned up
        dialog.deleteLater()
        
        if dialog_result == QDialog.Accepted:
            new_msg = dialog.get_message()
            self.tx_messages.append(new_msg)
            
            # Use full table rebuild for new messages (needed for proper row setup)
            self.populate_tx_table()
            
            # Select the newly added message
            new_row = len(self.tx_messages) - 1
            self.tx_table.selectRow(new_row)
            
            print(f"[DEBUG] New message {new_msg.msg_id} added successfully")
        else:
            print("[DEBUG] Add message dialog cancelled")
        
        # Ensure buttons are properly updated
        self.update_button_states()

    def edit_tx_message(self):
        """Edit the selected transmit message in a dialog."""
        selected_rows = self.tx_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row >= len(self.tx_messages):
            return
            
        # IMPORTANT: Apply any pending editor changes before opening dialog
        # This ensures the dialog sees the current editor state, not the original message
        if (hasattr(self, 'current_editing_row') and 
            self.current_editing_row == row and 
            hasattr(self, 'raw_data_edit')):
            print("[DEBUG] Auto-applying editor changes before opening edit dialog")
            self.apply_editor_changes()
            
        msg = self.tx_messages[row]
        print(f"[DEBUG] Opening edit dialog for message {msg.msg_id} at row {row}")
        
        # Store current selection to restore later
        current_selection = row
        
        dialog = self.TxMessageDialog(self, msg)
        dialog_result = dialog.exec()
        
        # Ensure dialog is properly cleaned up
        dialog.deleteLater()
        
        if dialog_result == QDialog.Accepted:
            # Update the message in the list
            updated_msg = dialog.get_message()
            self.tx_messages[row] = updated_msg
            
            # Use selective update instead of full table rebuild
            self.update_tx_table_row(row, updated_msg)
            
            # IMPORTANT: Sync the editor with dialog changes if it's showing the same message
            if (hasattr(self, 'current_editing_row') and 
                self.current_editing_row == row):
                print("[DEBUG] Syncing editor with dialog changes")
                self.load_message_in_editor(updated_msg, row)
            
            # Restore selection to maintain button states
            self.tx_table.selectRow(current_selection)
            
            print(f"[DEBUG] Message {updated_msg.msg_id} updated successfully")
        else:
            print(f"[DEBUG] Edit dialog cancelled for message {msg.msg_id}")
        
        # Ensure buttons remain enabled after dialog
        self.update_button_states()
    
    def update_button_states(self):
        """Update the state of edit/delete buttons based on selection."""
        try:
            has_selection = bool(self.tx_table.selectionModel().selectedRows())
            
            # Enable/disable buttons based on selection
            self.edit_action.setEnabled(has_selection)
            self.delete_action.setEnabled(has_selection)
            
            # Also update send buttons
            self.send_once_btn.setEnabled(has_selection)
            
            print(f"[DEBUG] Button states updated: selection={has_selection}")
            
        except Exception as e:
            print(f"[DEBUG] Error updating button states: {e}")
    
    def delete_tx_message(self):
        """Delete the selected message from the transmit table."""
        selected_rows = self.tx_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        # Stop any active timer for deleted rows
        rows_to_delete = [index.row() for index in selected_rows]
        for row in rows_to_delete:
            if row in self.tx_periodic_timers:
                self.tx_periodic_timers[row].stop()
                del self.tx_periodic_timers[row]

        # Sort rows in descending order to avoid index shifting issues
        for row in sorted(rows_to_delete, reverse=True):
            if row < len(self.tx_messages):
                del self.tx_messages[row]
        
        # Update timer dictionary keys after deletion
        new_timers = {}
        for old_row, timer in self.tx_periodic_timers.items():
            new_row = old_row
            for deleted_row in sorted(rows_to_delete):
                if old_row > deleted_row:
                    new_row -= 1
            if new_row >= 0:
                new_timers[new_row] = timer
        self.tx_periodic_timers = new_timers
        
        self.populate_tx_table()

    def clear_tx_messages(self):
        """Clear all messages from the transmit table."""
        # Stop all timers
        for timer in self.tx_periodic_timers.values():
            timer.stop()
        self.tx_periodic_timers.clear()
        
        self.tx_messages.clear()
        self.populate_tx_table()

    def send_selected_once(self):
        """Send selected message once"""
        selected_rows = self.tx_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        if row < len(self.tx_messages):
            self.send_single_message(row)

    def send_all_once(self):
        """Send all messages once"""
        for i in range(len(self.tx_messages)):
            self.send_single_message(i)

    def send_single_message(self, row):
        """Send a single message and update counters"""
        if row >= len(self.tx_messages):
            return

        msg = self.tx_messages[row]
        
        try:
            # Parse message ID
            if isinstance(msg.msg_id, str):
                if msg.msg_id.startswith('0x') or msg.msg_id.startswith('0X'):
                    msg_id = int(msg.msg_id, 16)
                else:
                    msg_id = int(msg.msg_id, 16)  # Assume hex even without 0x prefix
            else:
                msg_id = int(msg.msg_id)

            # Parse data bytes
            data_bytes = []
            if msg.data.strip():
                for byte_str in msg.data.split():
                    if byte_str.strip():
                        # Handle both hex (with/without 0x) and decimal
                        if byte_str.startswith('0x') or byte_str.startswith('0X'):
                            data_bytes.append(int(byte_str, 16))
                        else:
                            try:
                                # Try hex first
                                data_bytes.append(int(byte_str, 16))
                            except ValueError:
                                # Fall back to decimal
                                data_bytes.append(int(byte_str))

            # Ensure DLC matches data length or pad/truncate as needed
            if len(data_bytes) < msg.dlc:
                data_bytes.extend([0] * (msg.dlc - len(data_bytes)))  # Pad with zeros
            elif len(data_bytes) > msg.dlc:
                data_bytes = data_bytes[:msg.dlc]  # Truncate

            # Create message dictionary for backend
            message_data = {
                'id': msg_id,
                'dlc': msg.dlc,
                'data': data_bytes,
                'extended': msg_id > 0x7FF,  # Auto-detect extended ID
            }
            
            # Emit signal to send message
            self.send_message.emit(message_data)
            
            # Update sent counter
            msg.total_sent += 1
            
            # Update the table display
            if row < self.tx_table.rowCount():
                sent_item = self.tx_table.item(row, 6)
                if sent_item:
                    sent_item.setText(str(msg.total_sent))
                    
            print(f"[DEBUG] Sent message: ID=0x{msg_id:X}, DLC={msg.dlc}, Data={data_bytes}")
            
        except Exception as e:
            print(f"[ERROR] Failed to send message at row {row}: {e}")
            # Could emit an error signal here if needed

    def toggle_all_periodic(self, start):
        """Start or stop all active periodic messages."""
        if start:
            self.start_stop_action.setText("⏹️")
            self.start_stop_action.setToolTip("Stop all periodic messages")
            
            # Start timers for all active messages with cycle > 0
            for i, msg in enumerate(self.tx_messages):
                if msg.is_active and msg.cycle_ms > 0:
                    if i not in self.tx_periodic_timers:
                        timer = QTimer(self)
                        timer.timeout.connect(lambda row=i: self.send_periodic_message(row))
                        timer.start(msg.cycle_ms)
                        self.tx_periodic_timers[i] = timer
                        
        else:
            self.start_stop_action.setText("▶️")
            self.start_stop_action.setToolTip("Start all periodic messages")
            
            # Stop all timers
            for timer in self.tx_periodic_timers.values():
                timer.stop()
            self.tx_periodic_timers.clear()
            
        self.update_status_labels()

    def send_periodic_message(self, row):
        """Send a single message periodically and handle the count."""
        if row >= len(self.tx_messages):
            return

        msg = self.tx_messages[row]
        
        # Send the message
        self.send_single_message(row)
        
        # Handle count-limited messages
        if msg.count > 0:
            msg.count -= 1
            if msg.count == 0:
                # Stop timer and deactivate message
                if row in self.tx_periodic_timers:
                    self.tx_periodic_timers[row].stop()
                    del self.tx_periodic_timers[row]
                msg.is_active = False
                self.populate_tx_table()
                
                # If no more active timers, update the start/stop button
                if not any(timer.isActive() for timer in self.tx_periodic_timers.values()):
                    self.start_stop_action.setChecked(False)
                    self.update_status_labels()

    def update_message_active_state(self, row, is_checked):
        """Update the is_active state of a message when its checkbox is toggled."""
        if row < len(self.tx_messages):
            self.tx_messages[row].is_active = is_checked
            
            # Update visual feedback
            for col in range(self.tx_table.columnCount()):
                item = self.tx_table.item(row, col)
                if item:
                    if is_checked:
                        item.setBackground(QColor("lightgreen"))
                    else:
                        item.setBackground(QColor("white"))
            
            # If periodic transmission is running, restart affected timers
            if self.start_stop_action.isChecked():
                if is_checked and self.tx_messages[row].cycle_ms > 0:
                    # Start timer for newly activated message
                    if row not in self.tx_periodic_timers:
                        timer = QTimer(self)
                        timer.timeout.connect(lambda r=row: self.send_periodic_message(r))
                        timer.start(self.tx_messages[row].cycle_ms)
                        self.tx_periodic_timers[row] = timer
                else:
                    # Stop timer for deactivated message
                    if row in self.tx_periodic_timers:
                        self.tx_periodic_timers[row].stop()
                        del self.tx_periodic_timers[row]
                        
            self.update_status_labels()

    def get_current_connection_config(self):
        """Get current connection configuration with auto-detection support"""
        driver = self.driver_combo.currentText()
        interface = self.interface_combo.currentText()
        
        # Auto-detect driver based on interface if needed
        if driver == "auto-detect":
            if interface.startswith(("/dev/tty", "COM")):
                driver = "slcan"
                print(f"[DEBUG] Auto-detected SLCAN for interface {interface}")
            elif interface.startswith(("can", "vcan")):
                driver = "socketcan"
                print(f"[DEBUG] Auto-detected SocketCAN for interface {interface}")
            else:
                # Default to SLCAN for unknown interfaces
                driver = "slcan"
                print(f"[DEBUG] Auto-detection fallback to SLCAN for interface {interface}")
        
        config = {
            'interface': interface,
            'driver': driver,
            'channel': interface if driver == "slcan" else self.channel_spin.value(),
            'bitrate': int(float(self.bitrate_combo.currentText()) * 1000),
            'data_bitrate': int(self.data_bitrate_combo.currentText()) * 1000 if self.canfd_radio.isChecked() else None,
            'is_canfd': self.canfd_radio.isChecked(),
            'listen_only': self.listen_only_cb.isChecked(),
            'fd_non_iso': self.fd_non_iso_cb.isChecked(),
            # Additional info for debugging
            'auto_detected': self.driver_combo.currentText() == "auto-detect",
            'original_driver_selection': self.driver_combo.currentText()
        }
        
        print(f"[DEBUG] Connection config: {config}")
        return config

    class TxMessageDialog(QDialog):
    
        def __init__(self, parent=None, msg=None):
            super().__init__(parent)
            self.setWindowTitle("Edit TX Message" if msg else "Add TX Message")
            self.setModal(True)
            self.setMinimumWidth(600)
            self.setMinimumHeight(850)
            
            self.message = msg
            self.dbc_manager = getattr(parent, 'dbc_manager', None)
            self.selected_dbc_msg = None
            self.dbc_signals = {}
            self.signal_edits = {}
            self.value_table_combos = {}
            
            # Flag to prevent DBC from overwriting data during restoration
            self._is_restoring_message = False
            
            self.setup_ui()
            # Move this AFTER setup_ui()
            if self.dbc_msg_combo:  # Add null check
                self.populate_dbc_messages()
            
            # If editing existing message, try to restore state
            if self.message:
                self.restore_message_data()
                
        def setup_ui(self):
            """Setup the enhanced dialog UI"""
            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Create tab widget for organized UI
            self.tab_widget = QTabWidget()
            layout.addWidget(self.tab_widget)

            # Basic Message Tab
            basic_tab = self.create_basic_tab()
            self.tab_widget.addTab(basic_tab, "📝 Basic Message")

            # DBC Integration Tab
            dbc_tab = self.create_dbc_tab()
            self.tab_widget.addTab(dbc_tab, "🗃️ DBC Integration")

            # Advanced Options Tab
            advanced_tab = self.create_advanced_tab()
            self.tab_widget.addTab(advanced_tab, "⚙️ Advanced")

            # Dialog buttons
            btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btn_box.accepted.connect(self.accept)
            btn_box.rejected.connect(self.reject)
            layout.addWidget(btn_box)

            

        def create_basic_tab(self):
            """Create the basic message configuration tab"""
            tab = QWidget()
            layout = QFormLayout(tab)
            layout.setSpacing(8)

            # Message identification
            id_group = self.create_id_group()
            layout.addRow(id_group)

            # Data configuration
            data_group = self.create_data_group()
            layout.addRow(data_group)

            # CAN Control Bits
            control_group = self.create_control_bits_group()
            layout.addRow(control_group)

            # Timing configuration
            timing_group = self.create_timing_group()
            layout.addRow(timing_group)

            return tab

        def create_id_group(self):
            """Create message ID configuration group"""
            group = QGroupBox("Message Identification")
            layout = QFormLayout(group)

            # Message ID with format selection
            id_widget = QWidget()
            id_layout = QHBoxLayout(id_widget)
            id_layout.setContentsMargins(0, 0, 0, 0)

            self.id_edit = QLineEdit()
            self.id_edit.setPlaceholderText("e.g., 0x123, 291, or 123")
            
            self.id_format_combo = QComboBox()
            self.id_format_combo.addItems(["Hex (0x123)", "Decimal (291)", "Binary (0b100100011)"])
            self.id_format_combo.setCurrentIndex(0)
            self.id_format_combo.currentTextChanged.connect(self._on_id_format_changed)

            id_layout.addWidget(self.id_edit, 2)
            id_layout.addWidget(self.id_format_combo, 1)

            layout.addRow("Message ID:", id_widget)

            return group

        def create_control_bits_group(self):
            """Create CAN control bits configuration group"""
            group = QGroupBox("CAN Control Bits")
            layout = QFormLayout(group)

            self.rtr_cb = QCheckBox("Remote Transmission Request")
            self.rtr_cb.setToolTip("Set RTR bit for remote frame requests")
            layout.addRow("RTR:", self.rtr_cb)

            self.extended_id_cb = QCheckBox("Extended ID (29-bit)")
            self.extended_id_cb.setToolTip("Use 29-bit extended CAN ID instead of 11-bit standard")
            self.extended_id_cb.toggled.connect(self._on_extended_toggled)
            layout.addRow("Extended ID:", self.extended_id_cb)

            self.fd_cb = QCheckBox("CAN-FD Frame")
            self.fd_cb.setToolTip("Enable CAN-FD frame format")
            self.fd_cb.toggled.connect(self._on_fd_toggled)
            layout.addRow("CAN-FD:", self.fd_cb)

            self.brs_cb = QCheckBox("Bit Rate Switch")
            self.brs_cb.setToolTip("Enable bit rate switching (CAN-FD only)")
            self.brs_cb.setEnabled(False)
            layout.addRow("BRS:", self.brs_cb)

            self.esi_cb = QCheckBox("Error State Indicator")
            self.esi_cb.setToolTip("Set error state indicator (CAN-FD only)")
            self.esi_cb.setEnabled(False)
            layout.addRow("ESI:", self.esi_cb)

            return group

        def create_data_group(self):
            """Create data configuration group"""
            group = QGroupBox("Message Data")
            layout = QFormLayout(group)

            # DLC with slider and spinbox
            dlc_widget = QWidget()
            dlc_layout = QHBoxLayout(dlc_widget)
            dlc_layout.setContentsMargins(0, 0, 0, 0)

            self.dlc_spin = QSpinBox()
            self.dlc_spin.setRange(0, 64)
            self.dlc_spin.setSuffix(" bytes")
            self.dlc_spin.valueChanged.connect(self._on_dlc_changed)

            self.dlc_slider = QSlider(Qt.Horizontal)
            self.dlc_slider.setRange(0, 64)
            self.dlc_slider.valueChanged.connect(self.dlc_spin.setValue)
            self.dlc_spin.valueChanged.connect(self.dlc_slider.setValue)

            dlc_layout.addWidget(self.dlc_spin)
            dlc_layout.addWidget(self.dlc_slider, 1)

            layout.addRow("DLC (Length):", dlc_widget)

            # Data input with format options
            data_widget = QWidget()
            data_layout = QVBoxLayout(data_widget)
            data_layout.setContentsMargins(0, 0, 0, 0)

            # Data format selection
            format_widget = QWidget()
            format_layout = QHBoxLayout(format_widget)
            format_layout.setContentsMargins(0, 0, 0, 0)

            self.data_format_combo = QComboBox()
            self.data_format_combo.addItems([
                "Hex Spaced (01 02 03)",
                "Hex Compact (010203)",
                "Decimal (1 2 3)",
                "Binary (00000001 00000010)"
            ])
            self.data_format_combo.currentTextChanged.connect(self._on_data_format_changed)

            self.random_data_btn = QPushButton("🎲 Random")
            self.random_data_btn.setToolTip("Generate random data")
            self.random_data_btn.clicked.connect(self._generate_random_data)

            self.clear_data_btn = QPushButton("🧹 Clear")
            self.clear_data_btn.setToolTip("Clear all data bytes")
            self.clear_data_btn.clicked.connect(self._clear_data)

            format_layout.addWidget(QLabel("Format:"))
            format_layout.addWidget(self.data_format_combo, 1)
            format_layout.addWidget(self.random_data_btn)
            format_layout.addWidget(self.clear_data_btn)

            data_layout.addWidget(format_widget)

            # Data input field
            self.data_edit = QLineEdit()
            self.data_edit.setPlaceholderText("e.g., 01 02 03 04 or 01020304")
            self.data_edit.textChanged.connect(self._validate_data_input)
            data_layout.addWidget(self.data_edit)

            # Data preview (hex dump style)
            self.data_preview = QTextEdit()
            self.data_preview.setMaximumHeight(80)
            self.data_preview.setReadOnly(True)
            self.data_preview.setFont(QFont("Courier", 9))
            data_layout.addWidget(self.data_preview)

            layout.addRow("Data Bytes:", data_widget)

            return group

        def create_timing_group(self):
            """Create timing configuration group"""
            group = QGroupBox("Transmission Timing")
            layout = QFormLayout(group)

            # Transmission mode
            mode_widget = QWidget()
            mode_layout = QHBoxLayout(mode_widget)
            mode_layout.setContentsMargins(0, 0, 0, 0)

            self.mode_group = QButtonGroup()
            self.single_shot_radio = QRadioButton("Single Shot")
            self.periodic_radio = QRadioButton("Periodic")
            self.burst_radio = QRadioButton("Burst")

            self.mode_group.addButton(self.single_shot_radio, 0)
            self.mode_group.addButton(self.periodic_radio, 1)
            self.mode_group.addButton(self.burst_radio, 2)

            self.single_shot_radio.setChecked(True)
            self.periodic_radio.toggled.connect(self._on_mode_changed)
            self.burst_radio.toggled.connect(self._on_mode_changed)

            mode_layout.addWidget(self.single_shot_radio)
            mode_layout.addWidget(self.periodic_radio)
            mode_layout.addWidget(self.burst_radio)
            mode_layout.addStretch()

            layout.addRow("Mode:", mode_widget)

            # Cycle time with presets
            cycle_widget = QWidget()
            cycle_layout = QHBoxLayout(cycle_widget)
            cycle_layout.setContentsMargins(0, 0, 0, 0)

            self.cycle_spin = QSpinBox()
            self.cycle_spin.setRange(1, 999999)
            self.cycle_spin.setSuffix(" ms")
            self.cycle_spin.setValue(1000)
            self.cycle_spin.setEnabled(False)

            cycle_presets = QComboBox()
            cycle_presets.addItems(["Custom", "10ms", "20ms", "50ms", "100ms", "500ms", "1000ms"])
            cycle_presets.currentTextChanged.connect(self._on_cycle_preset_changed)

            cycle_layout.addWidget(self.cycle_spin, 2)
            cycle_layout.addWidget(QLabel("Preset:"))
            cycle_layout.addWidget(cycle_presets, 1)

            layout.addRow("Cycle Time:", cycle_widget)

            # Count with infinity option
            count_widget = QWidget()
            count_layout = QHBoxLayout(count_widget)
            count_layout.setContentsMargins(0, 0, 0, 0)

            self.count_spin = QSpinBox()
            self.count_spin.setRange(0, 1000000)
            self.count_spin.setSpecialValueText("∞ Infinite")
            self.count_spin.setValue(0)
            self.count_spin.setEnabled(False)

            self.count_infinite_cb = QCheckBox("Infinite")
            self.count_infinite_cb.setChecked(True)
            self.count_infinite_cb.toggled.connect(self._on_infinite_toggled)

            count_layout.addWidget(self.count_spin, 2)
            count_layout.addWidget(self.count_infinite_cb)

            layout.addRow("Count:", count_widget)

            return group

        def create_dbc_tab(self):
            """Create the DBC integration tab"""
            tab = QWidget()
            layout = QVBoxLayout(tab)

            # DBC message selection
            dbc_group = QGroupBox("DBC Message Selection")
            dbc_layout = QFormLayout(dbc_group)

            self.dbc_msg_combo = QComboBox()
            self.dbc_msg_combo.currentTextChanged.connect(self._on_dbc_msg_selected)
            dbc_layout.addRow("DBC Message:", self.dbc_msg_combo)

            # Message info display
            self.msg_info_text = QTextEdit()
            self.msg_info_text.setMaximumHeight(100)
            self.msg_info_text.setReadOnly(True)
            dbc_layout.addRow("Message Info:", self.msg_info_text)

            layout.addWidget(dbc_group)

            # Signal editors group
            self.signal_group = QGroupBox("Signal Values")
            self.signal_scroll = QScrollArea()
            self.signal_widget = QWidget()
            self.signal_layout = QFormLayout(self.signal_widget)
            self.signal_scroll.setWidget(self.signal_widget)
            self.signal_scroll.setWidgetResizable(True)
            self.signal_scroll.setMaximumHeight(300)
            
            signal_group_layout = QVBoxLayout(self.signal_group)
            signal_group_layout.addWidget(self.signal_scroll)
            
            layout.addWidget(self.signal_group)
            
            self.signal_group.setVisible(False)

            return tab

        def create_advanced_tab(self):
            """Create advanced options tab"""
            tab = QWidget()
            layout = QVBoxLayout(tab)

            # Message validation
            validation_group = QGroupBox("Message Validation")
            validation_layout = QFormLayout(validation_group)

            self.validate_dlc_cb = QCheckBox("Validate DLC matches data")
            self.validate_dlc_cb.setChecked(True)
            validation_layout.addRow("", self.validate_dlc_cb)

            self.validate_id_cb = QCheckBox("Validate ID range")
            self.validate_id_cb.setChecked(True)
            validation_layout.addRow("", self.validate_id_cb)

            layout.addWidget(validation_group)

            # Error injection
            error_group = QGroupBox("Error Injection (Testing)")
            error_layout = QFormLayout(error_group)

            self.inject_crc_error_cb = QCheckBox("Inject CRC error")
            error_layout.addRow("", self.inject_crc_error_cb)

            self.inject_stuff_error_cb = QCheckBox("Inject bit stuffing error")
            error_layout.addRow("", self.inject_stuff_error_cb)

            layout.addWidget(error_group)

            # Message templates
            template_group = QGroupBox("Message Templates")
            template_layout = QVBoxLayout(template_group)

            template_buttons = QWidget()
            template_btn_layout = QHBoxLayout(template_buttons)
            template_btn_layout.setContentsMargins(0, 0, 0, 0)

            save_template_btn = QPushButton("💾 Save as Template")
            load_template_btn = QPushButton("📂 Load Template")
            
            save_template_btn.clicked.connect(self._save_template)
            load_template_btn.clicked.connect(self._load_template)

            template_btn_layout.addWidget(save_template_btn)
            template_btn_layout.addWidget(load_template_btn)
            template_btn_layout.addStretch()

            template_layout.addWidget(template_buttons)
            layout.addWidget(template_group)

            layout.addStretch()
            return tab

        def _on_fd_toggled(self, enabled):
            """Handle CAN-FD checkbox toggle to enable/disable BRS and ESI."""
            self.brs_cb.setEnabled(enabled)
            self.esi_cb.setEnabled(enabled)
            if not enabled:
                self.brs_cb.setChecked(False)
                self.esi_cb.setChecked(False)

        def populate_dbc_messages(self):
            """Populate DBC message dropdown"""
            if not self.dbc_msg_combo:
                return
        
            self.dbc_msg_combo.clear()
            self.dbc_msg_combo.addItem("(Manual Entry)")
            self.dbc_msg_map = {"(Manual Entry)": None}

            if not self.dbc_manager or not hasattr(self.dbc_manager, 'active_database') or not self.dbc_manager.active_database:
                return

            try:
                # Handle different DBC manager interfaces
                if hasattr(self.dbc_manager, 'get_all_messages'):
                    messages = self.dbc_manager.get_all_messages()
                    if isinstance(messages, dict):
                        for msg_id, dbc_msg in messages.items():
                            msg_name = getattr(dbc_msg, 'name', f'Message_{msg_id}')
                            label = f"{msg_name} (ID: 0x{msg_id:X}, DLC: {getattr(dbc_msg, 'length', 8)})"
                            self.dbc_msg_combo.addItem(label)
                            self.dbc_msg_map[label] = dbc_msg
                    elif isinstance(messages, list):
                        for dbc_msg in messages:
                            msg_id = getattr(dbc_msg, 'frame_id', getattr(dbc_msg, 'message_id', None))
                            if msg_id is not None:
                                msg_name = getattr(dbc_msg, 'name', f'Message_{msg_id}')
                                label = f"{msg_name} (ID: 0x{msg_id:X}, DLC: {getattr(dbc_msg, 'length', 8)})"
                                self.dbc_msg_combo.addItem(label)
                                self.dbc_msg_map[label] = dbc_msg
                elif hasattr(self.dbc_manager, 'active_database') and hasattr(self.dbc_manager.active_database, 'messages'):
                    # Handle cantools database format
                    db = self.dbc_manager.active_database
                    if hasattr(db, 'messages'):
                        messages = db.messages if isinstance(db.messages, list) else []
                        for dbc_msg in messages:
                            msg_id = getattr(dbc_msg, 'frame_id', getattr(dbc_msg, 'message_id', None))
                            if msg_id is not None:
                                msg_name = getattr(dbc_msg, 'name', f'Message_{msg_id}')
                                label = f"{msg_name} (ID: 0x{msg_id:X}, DLC: {getattr(dbc_msg, 'length', 8)})"
                                self.dbc_msg_combo.addItem(label)
                                self.dbc_msg_map[label] = dbc_msg
                    # Create a descriptive label
                    msg_name = getattr(dbc_msg, 'name', f'Message_{msg_id}')
                    label = f"{msg_name} (ID: 0x{msg_id:X}, DLC: {getattr(dbc_msg, 'length', 8)})"
                    
                    self.dbc_msg_combo.addItem(label)
                    self.dbc_msg_map[label] = dbc_msg
                    
            except Exception as e:
                print(f"[DEBUG] Could not load DBC messages: {e}")

        def restore_message_data(self):
            """Restore data when editing an existing message"""
            if not self.message:
                return

            # Set flag to indicate we're restoring (prevents DBC from overwriting data)
            self._is_restoring_message = True
            
            try:
                # Restore basic fields FIRST (before DBC selection)
                self.id_edit.setText(str(self.message.msg_id))
                self.dlc_spin.setValue(self.message.dlc)
                self.data_edit.setText(self.message.data)
                
                # Restore signal values from the current message (not DBC defaults)
                if hasattr(self.message, 'dbc_signals') and self.message.dbc_signals:
                    self.dbc_signals = self.message.dbc_signals.copy()
                    print(f"[DEBUG] Restored {len(self.dbc_signals)} signal values from message")
                else:
                    self.dbc_signals = {}
                
                # Restore timing
                if self.message.cycle_ms > 0:
                    self.periodic_radio.setChecked(True)
                    self.cycle_spin.setValue(self.message.cycle_ms)
                else:
                    self.single_shot_radio.setChecked(True)
                    
                self.count_spin.setValue(self.message.count)
                if self.message.count == 0:
                    self.count_infinite_cb.setChecked(True)
                else:
                    self.count_infinite_cb.setChecked(False)

                # Restore DBC selection if available (this will trigger _on_dbc_msg_selected)
                if hasattr(self.message, 'dbc_name') and self.message.dbc_name:
                    for i in range(self.dbc_msg_combo.count()):
                        if self.message.dbc_name in self.dbc_msg_combo.itemText(i):
                            self.dbc_msg_combo.setCurrentIndex(i)
                            break

                # Restore CAN control bits
                if hasattr(self.message, 'rtr'):
                    self.rtr_cb.setChecked(self.message.rtr)
                if hasattr(self.message, 'extended_id'):
                    self.extended_id_cb.setChecked(self.message.extended_id)
                if hasattr(self.message, 'fd'):
                    self.fd_cb.setChecked(self.message.fd)
                    # Trigger the toggle to enable/disable dependent controls
                    self._on_fd_toggled(self.message.fd)
                if hasattr(self.message, 'brs'):
                    self.brs_cb.setChecked(self.message.brs)
                if hasattr(self.message, 'esi'):
                    self.esi_cb.setChecked(self.message.esi)
                    
            finally:
                # Clear restoration flag
                self._is_restoring_message = False
                print("[DEBUG] Message data restored successfully, preserving edited values")

        def _on_dbc_msg_selected(self, text):
            """Handle DBC message selection"""
            if not hasattr(self, 'dbc_msg_map') or text not in self.dbc_msg_map:
                return
                
            if self.dbc_msg_map[text] is not None:
                dbc_msg = self.dbc_msg_map[text]
                self.selected_dbc_msg = dbc_msg
                
                # Check if we're restoring an existing message to preserve its data
                is_restoring = (hasattr(self, '_is_restoring_message') and self._is_restoring_message)
                
                if not is_restoring:
                    # Only auto-fill basic fields for NEW DBC message selection
                    msg_id = getattr(dbc_msg, 'frame_id', getattr(dbc_msg, 'message_id', 0))
                    self.id_edit.setText(f"0x{msg_id:X}")
                    self.dlc_spin.setValue(getattr(dbc_msg, 'length', 8))
                    
                    # Initialize signal values with defaults only for new messages
                    if not self.dbc_signals:  # Only initialize if not already loaded
                        for signal in getattr(dbc_msg, 'signals', []):
                            default_val = getattr(signal, 'minimum', 0) if hasattr(signal, 'minimum') and signal.minimum is not None else 0
                            self.dbc_signals[signal.name] = default_val
                
                # Always populate signal editors (but preserve existing values when restoring)
                self._populate_signal_editors(dbc_msg)
                
                if not is_restoring:
                    # Only update data from signals for new selections, not when restoring
                    self._update_data_from_signals()
                
                # Make fields read-only when DBC is selected
                self.id_edit.setReadOnly(True)
                self.dlc_spin.setReadOnly(True)
                self.data_edit.setReadOnly(True)
                self.signal_group.setVisible(True)
                
            else:
                # Manual entry mode
                self.selected_dbc_msg = None
                self.signal_group.setVisible(False)
                
                # Enable manual editing
                self.id_edit.setReadOnly(False)
                self.dlc_spin.setReadOnly(False)
                self.data_edit.setReadOnly(False)

        def _populate_signal_editors(self, dbc_msg):
            """Create editors for each signal in the DBC message"""
            # Clear existing editors
            for i in reversed(range(self.signal_layout.count())):
                item = self.signal_layout.takeAt(i)
                if item.widget():
                    item.widget().deleteLater()
            
            self.signal_edits = {}
            
            is_restoring = getattr(self, '_is_restoring_message', False)
            if is_restoring:
                print(f"[DEBUG] Populating signal editors during restoration with {len(self.dbc_signals)} existing values")
            
            for signal in getattr(dbc_msg, 'signals', []):
                # Create editor
                edit = QLineEdit()
                current_value = self.dbc_signals.get(signal.name, 0)
                edit.setText(str(current_value))
                
                if is_restoring and signal.name in self.dbc_signals:
                    print(f"[DEBUG] Restored signal {signal.name} = {current_value}")
                
                # Set tooltip with signal info
                tooltip_parts = []
                if hasattr(signal, 'minimum') and hasattr(signal, 'maximum'):
                    tooltip_parts.append(f"Range: {signal.minimum} to {signal.maximum}")
                if hasattr(signal, 'unit') and signal.unit:
                    tooltip_parts.append(f"Unit: {signal.unit}")
                if hasattr(signal, 'comment') and signal.comment:
                    tooltip_parts.append(f"Comment: {signal.comment}")
                
                if tooltip_parts:
                    edit.setToolTip("\n".join(tooltip_parts))
                
                # Connect change handler
                edit.textChanged.connect(lambda text, s=signal: self._on_signal_changed(s, text))
                
                # Create label with units
                label_text = signal.name
                if hasattr(signal, 'unit') and signal.unit:
                    label_text += f" ({signal.unit})"
                
                self.signal_layout.addRow(label_text, edit)
                self.signal_edits[signal.name] = edit

        def _on_signal_changed(self, signal, text):
            """Handle signal value change"""
            try:
                value = float(text) if text else 0
                # Clamp to signal range if available
                if hasattr(signal, 'minimum') and signal.minimum is not None:
                    value = max(value, signal.minimum)
                if hasattr(signal, 'maximum') and signal.maximum is not None:
                    value = min(value, signal.maximum)
                    
                self.dbc_signals[signal.name] = value
                self._update_data_from_signals()
            except ValueError:
                # Invalid input, revert to previous value
                if signal.name in self.dbc_signals and signal.name in self.signal_edits:
                    self.signal_edits[signal.name].setText(str(self.dbc_signals[signal.name]))

        def _update_data_from_signals(self):
            """Update the data field based on current signal values"""
            if not self.selected_dbc_msg:
                return
                
            try:
                # Use DBC encoding to generate data bytes
                if hasattr(self.selected_dbc_msg, 'encode'):
                    data_bytes = self.selected_dbc_msg.encode(self.dbc_signals)
                    # Convert to hex string
                    hex_string = ' '.join(f'{b:02X}' for b in data_bytes)
                    self.data_edit.setText(hex_string)
                else:
                    print("[DEBUG] DBC message has no encode method")
            except Exception as e:
                print(f"[DEBUG] Error encoding DBC message: {e}")

        def _on_signal_combo_changed(self, signal, value):
            """Handle signal combo box change"""
            self.dbc_signals[signal.name] = value
            self._update_data_from_signals()

        def _on_dlc_changed(self, new_dlc):
            """Handle DLC change"""
            if self.selected_dbc_msg is None:  # Manual mode only
                current_data = self.data_edit.text().strip()
                if current_data:
                    # Parse existing bytes based on current format
                    bytes_list = self._parse_data_input(current_data)
                else:
                    bytes_list = []
                
                # Adjust to new DLC
                if len(bytes_list) < new_dlc:
                    bytes_list.extend([0] * (new_dlc - len(bytes_list)))
                elif len(bytes_list) > new_dlc:
                    bytes_list = bytes_list[:new_dlc]
                
                # Update display based on current format
                self._update_data_display(bytes_list)
            
            self._update_data_preview()

        def _parse_data_input(self, data_text):
            """Parse data input based on current format"""
            format_text = self.data_format_combo.currentText()
            bytes_list = []
            
            try:
                if "Hex Spaced" in format_text:
                    for byte_str in data_text.split():
                        if byte_str:
                            bytes_list.append(int(byte_str, 16))
                elif "Hex Compact" in format_text:
                    # Parse pairs of hex characters
                    clean_text = data_text.replace(' ', '')
                    for i in range(0, len(clean_text), 2):
                        if i + 1 < len(clean_text):
                            bytes_list.append(int(clean_text[i:i+2], 16))
                elif "Decimal" in format_text:
                    for byte_str in data_text.split():
                        if byte_str:
                            val = int(byte_str)
                            bytes_list.append(min(255, max(0, val)))
                elif "Binary" in format_text:
                    for byte_str in data_text.split():
                        if byte_str:
                            bytes_list.append(int(byte_str, 2))
            except ValueError:
                pass  # Return empty list on parse error
                
            return bytes_list

        def _update_data_display(self, bytes_list):
            """Update data display based on current format"""
            format_text = self.data_format_combo.currentText()
            
            if "Hex Spaced" in format_text:
                display_text = ' '.join(f'{b:02X}' for b in bytes_list)
            elif "Hex Compact" in format_text:
                display_text = ''.join(f'{b:02X}' for b in bytes_list)
            elif "Decimal" in format_text:
                display_text = ' '.join(str(b) for b in bytes_list)
            elif "Binary" in format_text:
                display_text = ' '.join(f'{b:08b}' for b in bytes_list)
            else:
                display_text = ' '.join(f'{b:02X}' for b in bytes_list)
                
            self.data_edit.setText(display_text)

        def _validate_data_input(self):
            """Validate and update data input"""
            self._update_data_preview()

        def _update_data_preview(self):
            """Update the hex dump style preview"""
            try:
                bytes_list = self._parse_data_input(self.data_edit.text())
                
                # Create hex dump style preview
                preview_text = "Offset  Hex                                      ASCII\n"
                preview_text += "------  -----------------------------------------------\n"
                
                for i in range(0, len(bytes_list), 8):
                    chunk = bytes_list[i:i+8]
                    hex_part = ' '.join(f'{b:02X}' for b in chunk)
                    hex_part = hex_part.ljust(23)  # Pad to consistent width
                    
                    ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                    
                    preview_text += f"{i:04X}    {hex_part}  {ascii_part}\n"
                    
                self.data_preview.setText(preview_text)
            except Exception:
                self.data_preview.setText("Invalid data format")

        # Event handlers for UI controls
        def _on_id_format_changed(self, format_text):
            """Handle ID format change"""
            # Convert current ID to new format
            current_text = self.id_edit.text().strip()
            if not current_text:
                return
                
            try:
                # Parse current value
                if current_text.startswith('0x') or current_text.startswith('0X'):
                    current_value = int(current_text, 16)
                elif current_text.startswith('0b'):
                    current_value = int(current_text, 2)
                else:
                    current_value = int(current_text)
                
                # Convert to new format
                if "Hex" in format_text:
                    self.id_edit.setText(f"0x{current_value:X}")
                elif "Decimal" in format_text:
                    self.id_edit.setText(str(current_value))
                elif "Binary" in format_text:
                    self.id_edit.setText(f"0b{current_value:b}")
            except ValueError:
                pass

        def _on_extended_toggled(self, checked):
            """Handle extended ID toggle"""
            # Update ID validator range
            pass

        def _on_canfd_toggled(self, checked):
            """Handle CAN FD toggle"""
            if checked:
                self.dlc_spin.setMaximum(64)
                self.dlc_slider.setMaximum(64)
            else:
                self.dlc_spin.setMaximum(8)
                self.dlc_slider.setMaximum(8)
                # Update DLC if current value exceeds CAN 2.0 limit
                if self.dlc_spin.value() > 8:
                    self.dlc_spin.setValue(8)

        def _on_mode_changed(self):
            """Handle transmission mode change"""
            is_periodic = self.periodic_radio.isChecked()
            is_burst = self.burst_radio.isChecked()
            
            self.cycle_spin.setEnabled(is_periodic or is_burst)
            self.count_spin.setEnabled(is_periodic or is_burst)
            self.count_infinite_cb.setEnabled(is_periodic or is_burst)

        def _on_cycle_preset_changed(self, preset):
            """Handle cycle time preset selection"""
            if preset != "Custom":
                try:
                    cycle_ms = int(preset.replace("ms", ""))
                    self.cycle_spin.setValue(cycle_ms)
                except ValueError:
                    pass

        def _on_infinite_toggled(self, checked):
            """Handle infinite count toggle"""
            self.count_spin.setEnabled(not checked)
            if checked:
                self.count_spin.setValue(0)

        def _on_data_format_changed(self, format_text):
            """Handle data format change"""
            current_text = self.data_edit.text().strip()
            if not current_text:
                return
                
            # Parse current data
            bytes_list = self._parse_data_input(current_text)
            
            # Update display in new format
            self._update_data_display(bytes_list)

        def _generate_random_data(self):
            """Generate random data based on current DLC"""
            import random
            dlc = self.dlc_spin.value()
            random_bytes = [random.randint(0, 255) for _ in range(dlc)]
            self._update_data_display(random_bytes)

        def _clear_data(self):
            """Clear all data bytes (set to zero)"""
            dlc = self.dlc_spin.value()
            zero_bytes = [0] * dlc
            self._update_data_display(zero_bytes)

        def _save_template(self):
            """Save current message as template"""
            from PySide6.QtWidgets import QInputDialog
            
            name, ok = QInputDialog.getText(self, "Save Template", "Template name:")
            if ok and name:
                template = {
                    'name': name,
                    'id': self.id_edit.text(),
                    'dlc': self.dlc_spin.value(),
                    'data': self.data_edit.text(),
                    'cycle_ms': self.cycle_spin.value(),
                    'count': self.count_spin.value(),
                    'extended': self.extended_id_cb.isChecked(),
                    'fd': self.fd_cb.isChecked()
                }
                
                # Save to parent's template list
                if hasattr(self.parent(), 'message_templates'):
                    self.parent().message_templates.append(template)
                
                # Could also save to file here
                print(f"[DEBUG] Saved template: {name}")

        def _load_template(self):
            """Load a message template"""
            from PySide6.QtWidgets import QInputDialog
            
            if not hasattr(self.parent(), 'message_templates') or not self.parent().message_templates:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "No Templates", "No templates available.")
                return
            
            template_names = [t['name'] for t in self.parent().message_templates]
            name, ok = QInputDialog.getItem(self, "Load Template", "Select template:", template_names, 0, False)
            
            if ok and name:
                # Find template
                template = next((t for t in self.parent().message_templates if t['name'] == name), None)
                if template:
                    # Apply template values
                    self.id_edit.setText(template['id'])
                    self.dlc_spin.setValue(template['dlc'])
                    self.data_edit.setText(template['data'])
                    self.cycle_spin.setValue(template['cycle_ms'])
                    self.count_spin.setValue(template['count'])
                    self.extended_id_cb.setChecked(template.get('extended', False))
                    self.fd_cb.setChecked(template.get('fd', False))
                    
                    # Update mode based on cycle time
                    if template['cycle_ms'] > 0:
                        self.periodic_radio.setChecked(True)
                    else:
                        self.single_shot_radio.setChecked(True)

        def accept(self):
            """Override accept to validate input"""
            if not self._validate_input():
                return
                
            # Prepare message data for return
            try:
                # Parse message ID
                id_text = self.id_edit.text().strip()
                if id_text.startswith(('0x', '0X')):
                    msg_id = int(id_text, 16)
                elif id_text.startswith('0b'):
                    msg_id = int(id_text, 2)
                else:
                    msg_id = int(id_text)
                
                # Validate ID range
                if self.validate_id_cb.isChecked():
                    max_id = 0x1FFFFFFF if self.extended_id_cb.isChecked() else 0x7FF
                    if msg_id > max_id:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "Invalid ID", 
                                        f"Message ID 0x{msg_id:X} exceeds maximum for {'extended' if self.extended_id_cb.isChecked() else 'standard'} frame")
                        return
                
                # Parse and validate data
                data_bytes = self._parse_data_input(self.data_edit.text())
                dlc = self.dlc_spin.value()
                
                if self.validate_dlc_cb.isChecked() and len(data_bytes) != dlc:
                    from PySide6.QtWidgets import QMessageBox
                    reply = QMessageBox.question(self, "DLC Mismatch", 
                                            f"Data length ({len(data_bytes)}) doesn't match DLC ({dlc}). Continue anyway?")
                    if reply != QMessageBox.Yes:
                        return
                
                # Create message object
                
                # Determine transmission mode
                if self.single_shot_radio.isChecked():
                    cycle_ms = 0
                    count = 1
                elif self.periodic_radio.isChecked():
                    cycle_ms = self.cycle_spin.value()
                    count = 0 if self.count_infinite_cb.isChecked() else self.count_spin.value()
                else:  # burst mode
                    cycle_ms = self.cycle_spin.value()
                    count = self.count_spin.value()
                
                # Preserve existing state if editing
                is_active = self.message.is_active if self.message else False
                total_sent = self.message.total_sent if self.message else 0
                
                from dataclasses import dataclass
                # TxMessage is already defined at the top of the file, so just use it directly
                self.result_message = TxMessage(
                    msg_id=f"0x{msg_id:X}",
                    dlc=dlc,
                    data=' '.join(f'{b:02X}' for b in data_bytes),
                    cycle_ms=cycle_ms,
                    count=count,
                    is_active=is_active,
                    total_sent=total_sent,
                    # CAN control bits
                    rtr=self.rtr_cb.isChecked(),
                    extended_id=self.extended_id_cb.isChecked(),
                    fd=self.fd_cb.isChecked(),
                    brs=self.brs_cb.isChecked(),
                    esi=self.esi_cb.isChecked()
                )
                
                # Add DBC information if applicable
                if self.selected_dbc_msg:
                    self.result_message.dbc_name = self.selected_dbc_msg.name
                    self.result_message.dbc_signals = self.dbc_signals.copy()
                
                super().accept()
                
            except ValueError as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Input", f"Please check your input: {str(e)}")
                return
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
                return

        def _validate_input(self):
            """Validate all input fields"""
            errors = []
            
            # Validate ID
            id_text = self.id_edit.text().strip()
            if not id_text:
                errors.append("Message ID is required")
            else:
                try:
                    if id_text.startswith(('0x', '0X')):
                        msg_id = int(id_text, 16)
                    elif id_text.startswith('0b'):
                        msg_id = int(id_text, 2)
                    else:
                        msg_id = int(id_text)
                        
                    if msg_id < 0:
                        errors.append("Message ID must be positive")
                except ValueError:
                    errors.append("Invalid Message ID format")
            
            # Validate DLC
            dlc = self.dlc_spin.value()
            if self.fd_cb.isChecked():
                if dlc > 64:
                    errors.append("CAN FD DLC cannot exceed 64 bytes")
            else:
                if dlc > 8:
                    errors.append("CAN 2.0 DLC cannot exceed 8 bytes")
            
            # Validate data
            data_text = self.data_edit.text().strip()
            if data_text and not self.selected_dbc_msg:  # Skip validation for DBC messages
                try:
                    data_bytes = self._parse_data_input(data_text)
                    for byte_val in data_bytes:
                        if not (0 <= byte_val <= 255):
                            errors.append(f"Data byte value {byte_val} is out of range (0-255)")
                            break
                except:
                    errors.append("Invalid data format")
            
            # Validate timing
            if self.periodic_radio.isChecked() or self.burst_radio.isChecked():
                if self.cycle_spin.value() <= 0:
                    errors.append("Cycle time must be greater than 0 for periodic/burst transmission")
            
            # Show errors if any
            if errors:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
                return False
            
            return True

        def get_message(self):
            """Return the configured message"""
            return getattr(self, 'result_message', None)
        
    def handle_connect(self):
        """Handle connection request"""
        config = self.get_current_connection_config()
        print(f"[DEBUG] Connect requested with config: {config}")
        self.connect_requested.emit(config)
        
    def handle_disconnect(self):
        """Handle disconnection request"""
        print("[DEBUG] Disconnect requested")
        self.disconnect_requested.emit()
        
    def set_connection_state(self, connected):
        """Update connection state UI"""
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        
        if connected:
            self.connection_status.setText("🟢 Connected")
            self.connection_status.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    background-color: #e8f5e8;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                    color: #2e7d32;
                    font-weight: bold;
                }
            """)
        else:
            self.connection_status.setText("🔴 Disconnected")
            self.connection_status.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    background-color: #ffebee;
                    border: 1px solid #ef5350;
                    border-radius: 4px;
                    color: #c62828;
                    font-weight: bold;
                }
            """)
            
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
            
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                font-size: 8pt;  /* Compact font size */
            }
            
            QTableWidget::item {
                padding: 2px 4px;  /* Reduced padding for compactness */
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #007acc;
                color: white;
            }
            
            QHeaderView::section {
                background-color: #f1f3f4;
                padding: 3px 6px;  /* Compact header padding */
                border: 1px solid #dadce0;
                font-weight: bold;
                font-size: 8pt;  /* Smaller header font */
            }
            
            QToolBar {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px;
            }
            
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #005a9e;
            }
            
            QPushButton:pressed {
                background-color: #004578;
            }
            
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)