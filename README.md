# 🚗 Professional CAN Bus Analyzer (BrightAnalyze)

[![Build Status](https://github.com/MashaWaleed/BrightAnalyze/workflows/Build%20Cross-Platform%20Executables/badge.svg)](https://github.com/MashaWaleed/BrightAnalyze/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows|Linux|macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/MashaWaleed/BrightAnalyze/releases)

> 📺 **Quick Demo**: [Watch the application overview video](https://youtu.be/YOUR_VIDEO_ID) to see all features in action!

A **comprehensive, modern CAN bus analysis tool** built with PySide6 and Python, designed for automotive engineers, diagnostic technicians, and researchers. Features professional-grade UDS diagnostics, DBC file management, real-time signal plotting, and **CANable open-source hardware support**.

![Application Screenshot](screenshots/overview.png)

## ✨ Key Features

### 🔌 **Hardware Support**
- **CANable Open Source** - Tested with CANable USB-to-CAN adapter (recommended low-cost solution)
- **SocketCAN** - Native Linux CAN interface support
- **PCAN** - Peak System CAN interfaces
- **Vector** - Vector Informatik devices
- **Virtual CAN** - Simulation mode for testing

### 🛠️ **Core Functionality**
- **Real-time CAN Analysis** - High-performance message monitoring with filtering
- **UDS Diagnostics** - Complete ISO 14229 implementation with security access
- **DBC File Support** - Load, parse, and decode messages with signal interpretation
- **Message Transmission** - Send single-shot, periodic, or burst messages
- **Professional UI** - Modern dark/light themes with dockable panels

### 🚀 **Advanced Features**
- **Security Access Algorithms** - Built-in XOR, ADD, CRC16 + DLL integration
- **Real-time Signal Plotting** - Live visualization of decoded signals
- **Python Scripting Console** - Built-in automation and custom scripts
- **Multi-format Export** - CSV, ASC, BLF, JSON export capabilities
- **Workspace Management** - Save and restore complete analysis sessions

## 📦 Quick Installation

### 🎯 **Option 1: Pre-built Releases (Recommended)**

Download ready-to-run executables from [GitHub Releases](https://github.com/MashaWaleed/BrightAnalyze/releases):

**Windows:**
```bash
# Download CANAnalyzer-Windows.exe
# Double-click to run - no installation required!
```

**Linux:**
```bash
# Download CANAnalyzer-Linux
chmod +x CANAnalyzer-Linux
./CANAnalyzer-Linux
```

### 🔧 **Option 2: Source Installation**

```bash
# 1. Clone the repository
git clone https://github.com/MashaWaleed/BrightAnalyze.git
cd BrightAnalyze/can_analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

### 🐍 **Dependencies**
```bash
# Core requirements (auto-installed)
PySide6>=6.4.0        # Modern Qt GUI framework
python-can>=4.2.0     # CAN interface library
udsoncan>=1.21        # UDS diagnostic protocols
can-isotp>=1.7        # ISO-TP transport protocol
pyserial>=3.5         # Serial communication
cantools>=37.0        # DBC file parsing
```

## 🚀 Quick Start Guide

### 1️⃣ **Hardware Setup**
1. **Connect your CANable device** to USB port
2. **Install drivers** (if needed - usually auto-detected)
3. **Note the COM port** (Windows) or `/dev/ttyACM*` (Linux)

### 2️⃣ **First Connection**
1. **Launch application**: Run executable or `python main.py`
2. **Select interface**: Choose "SLCAN" for CANable or "SocketCAN" for Linux
3. **Configure port**: Select your device's COM port or CAN interface
4. **Set bitrate**: Choose 250k, 500k, or 1M bps (match your CAN network)
5. **Click Connect**: Green status indicates successful connection

### 3️⃣ **Load DBC File**
```python
# Example: Loading automotive DBC
File → Load DBC → Select your .dbc file
# Messages now decode automatically in the log!
```

### 4️⃣ **Send Your First Message**
```python
# In the Transmit tab:
CAN ID: 0x123
Data: 01 02 03 04 05 06 07 08
DLC: 8
Mode: Single Shot → Send
```

### 5️⃣ **UDS Diagnostics**
```python
# Configure UDS connection:
Request ID: 0x7E0    # Tester CAN ID
Response ID: 0x7E8   # ECU response ID
Session: Extended (0x03)
# Click "Connect UDS" → Start diagnostics!
```

## 🏗️ Architecture Overview

```
Professional CAN Bus Analyzer/
├── 📁 main.py                 # Main application entry point
├── 📁 can_backend.py          # CAN interface management
├── 📁 uds_backend.py          # UDS diagnostic protocols
├── 📁 ui/                     # User interface components
│   ├── menu_bar.py           # Application menu system
│   ├── toolbar.py            # Quick action toolbar
│   ├── left_sidebar.py       # Connection & transmission controls
│   ├── message_log.py        # Real-time CAN message display
│   ├── right_sidebar.py      # DBC management & filters
│   ├── status_bar.py         # Connection status & statistics
│   ├── diagnostics_panel.py  # UDS diagnostic interface
│   ├── signal_plotter.py     # Real-time signal visualization
│   ├── scripting_console.py  # Python automation console
│   └── style_manager.py      # Theme and styling system
├── 📁 screenshots/            # Application screenshots
├── 📁 workspaces/            # Saved analysis sessions
└── 📁 requirements.txt       # Python dependencies
```

## 🔧 Core Components Explained

### 🖥️ **Main Application (`main.py`)**
```python
class CANAnalyzerMainWindow(QMainWindow):
    """
    Main window orchestrates all UI components and manages:
    - Window layout and docking
    - Theme management (dark/light)
    - Workspace persistence
    - Global shortcuts and menu actions
    """
```

### 🚌 **CAN Backend (`can_backend.py`)**
```python
class CANBusManager:
    """
    Handles all CAN communication:
    - Multi-interface support (SLCAN, SocketCAN, PCAN, Vector)
    - Message transmission and reception
    - Error handling and reconnection
    - Hardware detection and configuration
    """
    
    def connect_interface(self, driver, **kwargs):
        """Connect to specified CAN interface"""
        
    def send_message(self, can_id, data, extended=False):
        """Send CAN message with error handling"""
        
    def start_receiving(self):
        """Start background message reception thread"""
```

### 🔍 **UDS Backend (`uds_backend.py`)**
```python
class SimpleUDSBackend:
    """
    Implements UDS (ISO 14229) diagnostic services:
    - Session management (Default, Programming, Extended)
    - Security Access with algorithm support
    - DTC (Diagnostic Trouble Code) operations
    - Data Identifier (DID) read/write
    - ECU communication timeout handling
    """
    
    def request_security_access(self, level=0x01):
        """Perform security access sequence"""
        
    def read_dtc(self, status_mask=0x0A):
        """Read diagnostic trouble codes"""
```

### 🎨 **UI Components (`ui/`)**

#### **Left Sidebar (`left_sidebar.py`)**
```python
class AdvancedLeftSidebar:
    """
    Controls CAN interface and message transmission:
    - Hardware detection and configuration
    - Message template management
    - Periodic transmission scheduling
    - DBC-based signal encoding
    """
```

#### **Message Log (`message_log.py`)**
```python
class ProfessionalMessageLog:
    """
    Real-time CAN message display:
    - High-performance message rendering
    - Advanced filtering and search
    - Color-coded message types
    - Export to multiple formats
    """
```

#### **Diagnostics Panel (`diagnostics_panel.py`)**
```python
class DiagnosticsPanel:
    """
    UDS diagnostic interface:
    - Session management controls
    - DTC reading and clearing
    - Security access configuration
    - DID reading and writing
    """
```

#### **Signal Plotter (`signal_plotter.py`)**
```python
class SignalPlotter:
    """
    Real-time signal visualization:
    - Multi-signal plotting
    - Time-based signal analysis
    - Zoom and pan capabilities
    - Signal value statistics
    """
```

## 🛠️ Development Guide

### 🔨 **Setting Up Development Environment**

```bash
# 1. Fork and clone the repository
git clone https://github.com/YourUsername/BrightAnalyze.git
cd BrightAnalyze/can_analyzer

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# 3. Install development dependencies
pip install -e .
pip install pytest black flake8 mypy

# 4. Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### 🧪 **Running Tests**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=can_analyzer

# Run specific test file
pytest test_uds_fixes.py -v

# Test specific functionality
pytest -k "test_security_access"
```

### 🎨 **Code Style and Formatting**

```bash
# Format code with Black
black can_analyzer/ ui/ *.py

# Check linting with flake8
flake8 can_analyzer/ ui/ --max-line-length=88

# Type checking with mypy
mypy can_analyzer/ ui/
```

### 🔧 **Adding New Features**

#### **1. Adding a New CAN Interface**
```python
# In can_backend.py
def setup_new_interface(self, **config):
    """Add support for new CAN hardware"""
    try:
        import can
        # Configure new interface type
        self.bus = can.Bus(
            interface='your_interface',
            channel=config.get('channel'),
            bitrate=config.get('bitrate', 500000)
        )
        return True
    except Exception as e:
        print(f"Interface setup failed: {e}")
        return False
```

#### **2. Adding New UDS Service**
```python
# In uds_backend.py
def read_memory_by_address(self, address, size):
    """Implement ReadMemoryByAddress service (0x23)"""
    request = [0x23] + list(address.to_bytes(4, 'big')) + [size]
    response = self.send_uds_request(request)
    return response
```

#### **3. Creating Custom UI Widget**
```python
# In ui/your_widget.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

class YourCustomWidget(QWidget):
    # Define signals for communication
    data_updated = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize widget layout and components"""
        layout = QVBoxLayout(self)
        # Add your components here
```

### 🐛 **Debugging Tips**

```python
# Enable debug logging
python main.py --debug

# Common debug patterns in the code:
print(f"[DEBUG] Message received: {msg}")
print(f"[DEBUG] UDS response: {response.hex()}")
print(f"[DEBUG] Interface status: {self.bus.state}")

# Use Qt debugging for UI issues:
export QT_LOGGING_RULES="*=true"  # Linux
set QT_LOGGING_RULES=*=true       # Windows
```

## 🔌 Hardware Configuration

### 🛠️ **CANable Setup**

**Hardware Requirements:**
- CANable with SLCAN firmware
- USB cable
- CAN bus connection (120Ω termination required)

**Configuration:**
```python
# In the application:
Interface: SLCAN
Port: /dev/ttyACM0 (Linux) or COM3 (Windows)  
Bitrate: 500000 (or match your network)
```

**Linux SocketCAN Alternative:**
```bash
# Create SLCAN interface from CANable
sudo slcand -o -c -f -s6 /dev/ttyACM0 can0
sudo ip link set can0 up

# Use SocketCAN interface in application
Interface: SocketCAN
Channel: can0
```

### 🔧 **Virtual CAN Setup (Testing)**

**Linux:**
```bash
# Load virtual CAN module
sudo modprobe vcan

# Create virtual interface
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Test with command line tools
cansend vcan0 123#DEADBEEF
candump vcan0
```

**Windows:**
```bash
# Use built-in Virtual CAN in application
Interface: Virtual
Channel: virtual_can
# No additional setup required
```

## 📊 File Formats and Data Exchange

### 📥 **Supported Import Formats**

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| **DBC** | `.dbc` | CAN Database | Message/signal definitions |
| **ASC** | `.asc` | Vector ASCII | Log file import |
| **BLF** | `.blf` | Vector Binary | High-performance logs |
| **CSV** | `.csv` | Comma Separated | Spreadsheet analysis |

### 📤 **Export Capabilities**

```python
# Export message log
File → Export → Choose Format:
- CSV: Spreadsheet analysis
- ASC: Vector tool compatibility  
- JSON: Custom processing
- Raw: Text format

# Export signal data
Right-click signal plot → Export Data
- CSV with timestamps
- Excel with formatting
- JSON with metadata
```

## 🚨 Troubleshooting

### ⚡ **Common Issues**

#### **🔌 "No CAN interfaces found"**
```bash
# Check hardware connection
lsusb | grep -i can  # Linux
# Device Manager → Ports  # Windows

# Verify drivers installed
# CANable: Should appear as "USB Serial Device"
# PCAN: Install PEAK drivers
# Vector: Install Vector drivers
```

#### **🔒 "Permission denied" (Linux)**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Logout and login again

# Or check device permissions
ls -l /dev/ttyACM*
sudo chmod 666 /dev/ttyACM0  # Temporary fix
```

#### **🚫 "UDS connection failed"**
```python
# Check CAN IDs match ECU:
Request ID: 0x7E0   # Tester ID
Response ID: 0x7E8  # ECU response ID
# ECU must be awake and responsive

# Verify bus traffic:
# Should see response within 50ms of request
```

#### **📁 "DBC file won't load"**
```python
# Check file encoding (must be UTF-8)
file -i your_file.dbc

# Validate DBC syntax
# Look for syntax errors in application log
# Common issues: Missing semicolons, invalid characters
```

### 🔍 **Debug Mode**

```bash
# Enable verbose logging
python main.py --debug

# Check application logs
tail -f ~/.cache/BrightAnalyze/app.log  # Linux
# %LOCALAPPDATA%\BrightAnalyze\app.log  # Windows

# Monitor CAN bus directly
candump can0  # Linux with SocketCAN
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### 🎯 **Ways to Contribute**

- **🐛 Bug Reports**: Found an issue? [Open an issue](https://github.com/MashaWaleed/BrightAnalyze/issues)
- **✨ Feature Requests**: Have an idea? [Start a discussion](https://github.com/MashaWaleed/BrightAnalyze/discussions)
- **📝 Documentation**: Improve this README or add code comments
- **🔧 Code**: Fix bugs or implement new features

### 📋 **Development Workflow**

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YourUsername/BrightAnalyze.git

# 3. Create feature branch
git checkout -b feature/your-feature-name

# 4. Make changes and test
pytest
black can_analyzer/ ui/

# 5. Commit and push
git commit -m "Add: Your feature description"
git push origin feature/your-feature-name

# 6. Create Pull Request on GitHub
```

### 📐 **Code Guidelines**

- **Python Style**: Follow PEP 8, use Black formatter
- **Documentation**: Add docstrings to new functions
- **Testing**: Add tests for new functionality
- **Commits**: Use clear, descriptive commit messages

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[CANable](https://canable.io/)** - Open source USB-to-CAN adapter design
- **[python-can](https://python-can.readthedocs.io/)** - Excellent CAN interface library
- **[PySide6](https://doc.qt.io/qtforpython/)** - Modern Qt bindings for Python
- **[cantools](https://cantools.readthedocs.io/)** - DBC file parsing capabilities
- **[UDSonCAN](https://udsoncan.readthedocs.io/)** - UDS protocol implementation

## 📞 Support & Community

- **📖 Documentation**: [User Guide](CAN_ANALYZER_USER_GUIDE.md)
- **🐛 Issues**: [GitHub Issues](https://github.com/MashaWaleed/BrightAnalyze/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/MashaWaleed/BrightAnalyze/discussions)
- **📺 Video Tutorial**: [Application Overview](https://youtu.be/YOUR_VIDEO_ID)

## 🗺️ Roadmap

### 🎯 **Version 1.1** (Current)
- ✅ CANable SLCAN support
- ✅ UDS diagnostics with security access
- ✅ Professional UI with themes
- ✅ Cross-platform executables
- ✅ DBC file management

### 🚀 **Version 1.2** (Q1 2025)
- [ ] J1939 protocol support
- [ ] Enhanced signal processing
- [ ] Automated testing framework
- [ ] Plugin architecture foundation
- [ ] Advanced filtering options

### 🌟 **Version 2.0** (Q2 2025)  
- [ ] Ethernet/DoIP support
- [ ] FlexRay basic implementation
- [ ] Cloud workspace synchronization
- [ ] Machine learning diagnostics
- [ ] Multi-protocol analysis

---

**🚗 Professional CAN Bus Analyzer (BrightAnalyze)** - *Making automotive diagnostics accessible to everyone.*

*Built with ❤️ for the automotive community*