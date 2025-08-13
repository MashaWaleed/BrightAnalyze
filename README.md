# Professional CAN Bus Analyzer

A comprehensive, modern CAN bus analysis tool built with PySide6, designed to rival professional tools like Vector CANoe and TSMaster.

## 🚀 Features

### Core Functionality
- **Multi-interface Support**: socketcan, PCAN, Vector, Kvaser, IXXAT
- **CAN 2.0 & CAN FD**: Full support for both protocols
- **Real-time Analysis**: High-performance message logging and analysis
- **Professional UI**: Modern, themeable interface with dockable panels

### Advanced Features
- **DBC Integration**: Load, parse, and use DBC files for signal decoding
- **UDS/OBD-II Diagnostics**: Comprehensive diagnostic capabilities
- **Real-time Plotting**: Signal visualization and trending
- **Python Scripting**: Built-in Python console for automation
- **Message Templates**: Save and reuse common message configurations
- **Traffic Simulation**: Generate realistic CAN traffic patterns

### Professional Tools
- **Multi-workspace Support**: Multiple analysis sessions
- **Log Import/Export**: Support for ASC, BLF, CSV formats
- **Error Injection**: Bus error simulation and testing
- **Filtering & Search**: Advanced message filtering capabilities
- **Dark/Light Themes**: Professional appearance options

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- PySide6
- CAN interface hardware (or virtual CAN for testing)

### Quick Install
```bash
# Clone the repository
git clone https://github.com/professional-tools/can-analyzer.git
cd can-analyzer

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Development Install
```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -e .[dev]

# Run tests
pytest
```

## 🚀 Quick Start

### 1. Basic Setup
1. Launch the application: `python main.py`
2. Select your CAN interface from the Bus Configuration panel
3. Configure bitrate and other parameters
4. Click "Connect" to start monitoring

### 2. Load DBC File
1. Go to File → Load DBC File
2. Select your .dbc file
3. Messages will now be decoded automatically in the log

### 3. Send Messages
1. Navigate to the Transmit tab in the left sidebar
2. Configure your message ID, DLC, and data
3. Click "Send Once" or enable periodic transmission

### 4. Real-time Plotting
1. Open the Signal Plotter panel (bottom tabs)
2. Select signals from your loaded DBC
3. Watch real-time signal values update

## 📋 System Requirements

### Operating Systems
- Windows 10/11 (recommended)
- Linux (Ubuntu 20.04+, CentOS 8+)
- macOS 10.15+ (limited CAN interface support)

### Hardware
- Minimum 4GB RAM
- 100MB disk space
- CAN interface device:
  - Peak PCAN-USB
  - Vector VN1630
  - Kvaser Leaf
  - SocketCAN compatible device
  - Or virtual CAN for testing

## 🔧 Configuration

### CAN Interfaces
The application supports multiple CAN interface types:

```python
# Example configuration for different interfaces
interfaces = {
    "socketcan": {"interface": "can0", "bitrate": 500000},
    "pcan": {"channel": "PCAN_USBBUS1", "bitrate": 500000},
    "vector": {"channel": 0, "bitrate": 500000},
    "kvaser": {"channel": 0, "bitrate": 500000}
}
```

### DBC Files
Place your DBC files in the `dbc/` directory or load them via the File menu. The application automatically decodes messages when a matching DBC is loaded.

## 🎨 User Interface

### Layout
- **Left Sidebar**: Bus configuration, message transmission, templates
- **Central Area**: Message log with filtering and search
- **Bottom Panels**: Signal plotter, Python console, diagnostics
- **Right Sidebar**: DBC browser, statistics, documentation

### Themes
Switch between light and dark themes via View → Toggle Dark Mode or `Ctrl+Shift+D`.

### Workspaces
Create multiple workspaces for different projects via Workspace → New Workspace.

## 🔌 Supported CAN Interfaces

| Interface | Status | Notes |
|-----------|--------|-------|
| SocketCAN | ✅ Full | Linux native CAN |
| PCAN-USB | ✅ Full | Peak-System interfaces |
| Vector | ✅ Full | Vector Informatik devices |
| Kvaser | ✅ Full | Kvaser interfaces |
| IXXAT | 🔄 Beta | Limited testing |
| CANoe | 🔄 Planned | Vector CANoe integration |

## 📊 Supported File Formats

### Import
- **ASC**: Vector ASCII format
- **BLF**: Vector Binary Logging Format
- **CSV**: Generic comma-separated values
- **DBC**: CAN database files
- **SYM**: Vector symbol files

### Export
- **ASC**: Vector ASCII format
- **CSV**: Comma-separated values
- **Excel**: XLSX format with formatting
- **JSON**: Structured data format

## 🤖 Scripting & Automation

The built-in Python console provides full access to the CAN interface:

```python
# Example script: Send periodic heartbeat
import time

def send_heartbeat():
    msg = {
        'id': 0x123,
        'data': [0x01, 0x02, 0x03, 0x04],
        'dlc': 4
    }
    
    while True:
        can_interface.send(msg)
        time.sleep(1.0)

# Start heartbeat in background
threading.Thread(target=send_heartbeat, daemon=True).start()
```

## 🧪 Testing

### Virtual CAN Setup (Linux)
```bash
# Create virtual CAN interface
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Test with cansend/candump
cansend vcan0 123#DEADBEEF
```

### Unit Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=can_analyzer

# Run specific test module
pytest tests/test_can_interface.py
```

## 🐛 Troubleshooting

### Common Issues

#### "No CAN interfaces found"
- Ensure CAN hardware is connected
- Install appropriate drivers
- On Linux, check `ip link show` for CAN interfaces

#### "Permission denied" on Linux
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Or run with sudo (not recommended for regular use)
```

#### DBC files not loading
- Verify file format is valid
- Check file encoding (UTF-8 recommended)
- Look for syntax errors in the log

### Debug Mode
Launch with debug logging:
```bash
python main.py --debug
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/yourusername/can-analyzer.git
cd can-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### Code Style
We use Black for code formatting and flake8 for linting:
```bash
# Format code
black can_analyzer/

# Check linting
flake8 can_analyzer/

# Type checking
mypy can_analyzer/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Vector Informatik**: Inspiration from CANoe
- **Tosun**: Inspiration from TSMaster  
- **Python-CAN**: Excellent CAN interface library
- **PySide6**: Modern Qt bindings for Python
- **cantools**: DBC file parsing capabilities

## 📞 Support

- **Documentation**: [https://can-analyzer.readthedocs.io](https://can-analyzer.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/professional-tools/can-analyzer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/professional-tools/can-analyzer/discussions)
- **Email**: support@cananalyzer.pro

## 🗺️ Roadmap

### Version 2.1 (Q2 2024)
- [ ] J1939 protocol support
- [ ] Network management functions
- [ ] Enhanced UDS capabilities
- [ ] Plugin architecture

### Version 2.2 (Q3 2024)
- [ ] Ethernet/DoIP support
- [ ] FlexRay basic support
- [ ] Advanced scripting IDE
- [ ] Cloud data synchronization

### Version 3.0 (Q4 2024)
- [ ] Multi-protocol support (LIN, Ethernet)
- [ ] Real-time operating system support
- [ ] Advanced signal processing
- [ ] Machine learning integration

---

**Professional CAN Bus Analyzer** - Bringing professional-grade CAN analysis to everyone.