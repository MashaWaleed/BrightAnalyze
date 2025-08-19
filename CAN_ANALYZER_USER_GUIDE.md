# Professional CAN Bus Analyzer - User Guide v2.0

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Application Overview](#application-overview)
4. [DBC File Management](#dbc-file-management)
5. [UDS Diagnostics](#uds-diagnostics)
6. [Message Logging and Analysis](#message-logging-and-analysis)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [Appendices](#appendices)

---

## Introduction

The Professional CAN Bus Analyzer is a comprehensive tool for automotive diagnostics, CAN bus analysis, and ECU communication. This application provides advanced features for professional automotive engineers, diagnostic technicians, and researchers working with Controller Area Network (CAN) protocols.

### Key Features

✅ **Multi-Protocol Support**: CAN 2.0A/B, CAN-FD, UDS (ISO 14229), OBD-II  
✅ **Advanced Security Access**: Built-in algorithms and DLL integration  
✅ **Real-time Analysis**: Live message monitoring and signal plotting  
✅ **DBC Integration**: Import/export database files for message interpretation  
✅ **Professional Logging**: Comprehensive message capture and analysis  
✅ **Cross-platform**: Windows, Linux, and macOS support  
✅ **Modern UI**: Intuitive interface with dark/light themes  

### System Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Windows 10+, Linux (Ubuntu 18.04+), macOS 10.14+ |
| Python | 3.8 or newer |
| Memory | 4 GB RAM minimum (8 GB recommended) |
| Storage | 1 GB free space |
| CAN Interface | SocketCAN, PCAN, Vector, or similar |

---

## Application Overview

### Main Interface Layout

![Main Application Interface](screenshots/overview.png)

The application features a modern, professional interface designed for efficiency and ease of use. The main window is divided into several key areas:

1. **Menu Bar**: Access to all application functions and settings
2. **Toolbar**: Quick access to frequently used tools
3. **Left Sidebar**: Connection settings and CAN interface configuration
4. **Central Area**: Main workspace with tabbed panels
5. **Right Sidebar**: Message filters, DBC management, and signal plotting
6. **Status Bar**: Connection status and real-time statistics
7. **Message Log**: Real-time CAN message display and analysis

### Application Themes

The application supports both light and dark themes for optimal viewing in different environments:

- **Light Theme**: Professional appearance for office environments
- **Dark Theme**: Reduced eye strain for extended use
- **Custom Themes**: Configurable color schemes

---

## Getting Started

### Installation

#### Requirements Installation

First, ensure all required Python packages are installed:

```bash
pip install -r requirements.txt
```

#### Application Launch

Start the application using:

```bash
python main.py
```

### Initial Configuration

#### CAN Interface Setup

![CAN Interface Configuration](screenshots/config.png)

To configure your CAN interface:

1. Open the **Settings** menu
2. Select **CAN Interface Configuration**
3. Choose your interface type:
   - **SocketCAN** (Linux): Native Linux CAN support
   - **PCAN**: Peak System CAN interfaces
   - **Vector**: Vector Informatik interfaces
   - **Virtual**: Simulation mode for testing
4. Set the bitrate (typically 250k, 500k, or 1M bps)
5. Configure extended frames if needed
6. Click **Apply** to save settings

### First Connection

1. Ensure your CAN interface is properly connected
2. Set the correct bitrate matching your CAN network
3. Click the 🟢 **Connect** button
4. Verify connection status in the status bar
5. You should see live CAN messages in the message log

---

## DBC File Management

Database CAN (DBC) files contain definitions for CAN messages, signals, and ECU information. The application provides comprehensive DBC management capabilities.

### Loading DBC Files

![DBC File Loading Interface](screenshots/dbc1.png)

To load a DBC file:

1. Navigate to **File** → **Load DBC**
2. Select your DBC file from the file browser
3. The application will parse and validate the file
4. Messages and signals will appear in the DBC panel
5. You can load multiple DBC files simultaneously

### DBC Message Analysis

![DBC Message and Signal Analysis](screenshots/dbc2.png)

The DBC panel provides detailed message analysis:

- **Message List**: All defined messages with IDs and names
- **Signal Details**: Individual signal definitions within messages
- **Value Interpretation**: Real-world values based on scaling factors
- **Units and Ranges**: Engineering units and valid value ranges
- **Real-time Updates**: Live signal values from incoming messages

### Message Transmission

![Message Transmission Panel](screenshots/transmit1.png)

To transmit CAN messages:

1. Select the **Transmit** tab
2. Choose a message from the DBC database or create custom
3. Set individual signal values using the controls
4. Configure transmission options:
   - **Single Shot**: Send once
   - **Periodic**: Repeat at specified interval
   - **Burst**: Send multiple times rapidly
5. Click **Send** to transmit the message

### Advanced Message Transmission

![Advanced Transmission Options](screenshots/transmit2.png)

Advanced transmission features include:

- **Signal Generators**: Sine wave, square wave, ramp signals
- **Sequence Transmission**: Automated message sequences
- **Conditional Logic**: Trigger-based transmission
- **Error Injection**: Deliberate error introduction for testing

### Transmission Scheduling

![Transmission Scheduling and Automation](screenshots/transmit3.png)

The scheduling system allows:

- **Time-based Scheduling**: Send messages at specific times
- **Event-based Triggers**: React to received messages
- **Scripted Sequences**: Python script automation
- **Load Testing**: High-frequency message generation

---

## UDS Diagnostics

Unified Diagnostic Services (UDS) provide standardized communication with automotive ECUs for diagnostics, programming, and maintenance.

### UDS Connection Setup

![UDS Connection and Session Management](screenshots/UDS1.png)

To establish UDS communication:

1. Open the **Diagnostics** tab
2. Configure the ECU connection:
   - **Request ID**: Tester's CAN ID (e.g., 0x7E0)
   - **Response ID**: ECU's response ID (e.g., 0x7E8)
   - **Functional ID**: Functional addressing (optional)
3. Select the diagnostic session type:
   - **Default Session (0x01)**: Standard diagnostic access
   - **Programming Session (0x02)**: ECU programming mode
   - **Extended Session (0x03)**: Enhanced diagnostic functions
4. Click **Connect UDS** to establish communication
5. Enable **Tester Present** to maintain the session

### Diagnostic Trouble Codes (DTCs)

![DTC Reading and Management](screenshots/uds2.png)

The DTC management system provides:

- **Read Active DTCs**: Current fault codes
- **Read Pending DTCs**: Intermittent faults
- **Read Permanent DTCs**: Emission-related persistent codes
- **Clear DTCs**: Reset fault memory
- **DTC Details**: Comprehensive fault information including:
  - DTC number and description
  - Fault status information
  - Environmental data
  - Snapshot records

### Data Identifier Services

![Data Identifier Reading and Writing](screenshots/uds3.png)

Data Identifier (DID) services allow access to ECU parameters:

- **Read Data by Identifier (0x22)**: Read specific parameters
- **Write Data by Identifier (0x2E)**: Modify ECU parameters
- **Common DIDs**: Pre-defined standard identifiers
- **Custom DIDs**: Manufacturer-specific parameters
- **Data Interpretation**: Automatic value scaling and units

Popular DIDs include:
- **0xF186**: ECU Serial Number
- **0xF190**: VIN (Vehicle Identification Number)
- **0xF195**: ECU Software Version
- **0xF197**: ECU Hardware Version

### Security Access

![Security Access Configuration](screenshots/uds4.png)

Security Access (Service 0x27) protects sensitive ECU functions:

#### ECU Configuration

Configure your target ECU:
- **ECU Selection**: Choose from predefined ECU types
- **Custom ECU**: Define your own ECU parameters
- **Security Levels**: Different access levels (0x01, 0x02, 0x03, etc.)

#### Algorithm Provider Selection

Choose your key calculation method:
- **Built-in Algorithms**: XOR, ADD, Complement, CRC16
- **DLL Integration**: Manufacturer-specific DLLs
- **Auto Mode**: DLL with built-in fallback

#### DLL Management

![DLL Management and Testing](screenshots/uds5.png)

The application supports manufacturer DLLs:

1. **Load DLL**: Browse and load security DLL files
2. **DLL Configuration**: Save/load DLL settings
3. **DLL Testing**: Verify DLL functionality with test data
4. **Wine Support**: Windows DLLs on Linux systems
5. **ASAM Compliance**: Standard ODX-D interface support

#### Security Access Procedure

The standard security access procedure:

1. **Request Seed**: Send security access request (0x27 0x01)
2. **Receive Seed**: ECU responds with challenge seed
3. **Calculate Key**: Use algorithm or DLL to compute response
4. **Send Key**: Submit calculated key (0x27 0x02)
5. **Access Granted**: ECU grants security access if key is correct

#### Built-in Algorithms

The application includes several common algorithms:

- **XOR Algorithm**: `key = seed ⊕ 0x12`
- **ADD Algorithm**: `key = (seed + 0x34) & 0xFF`
- **Complement**: `key = ~seed & 0xFF`
- **CRC16**: CRC16-CCITT checksum calculation

---

## Message Logging and Analysis

### Real-time Message Display

![Real-time Message Logging](screenshots/log1.png)

The message log provides comprehensive CAN traffic analysis:

- **Live Updates**: Real-time message display
- **Color Coding**: Different colors for message types
- **Filtering**: Show/hide specific message IDs
- **Search**: Find specific messages or patterns
- **Statistics**: Message count and rate information

### Advanced Logging Features

![Advanced Logging and Analysis Tools](screenshots/log2.png)

Advanced logging capabilities include:

- **Export Formats**: CSV, ASC, BLF, LOG file export
- **Timestamps**: High-resolution timing information
- **Message Replay**: Playback recorded sessions
- **Trigger Recording**: Event-based capture
- **Bandwidth Analysis**: Bus load monitoring

### Message Filtering

Create sophisticated filters to focus on relevant traffic:

- **ID Ranges**: Filter by CAN ID ranges
- **Data Patterns**: Match specific data content
- **Direction**: Separate TX and RX messages
- **Message Types**: Standard, Extended, Error frames
- **Signal-based**: Filter by decoded signal values

---

## Dialog Windows and Popups

### Configuration Dialogs

![Configuration Dialog Example](screenshots/dialog1.png)

The application uses dialog windows for detailed configuration:

- **Modal Operation**: Focus on specific settings
- **Input Validation**: Real-time parameter checking
- **Help Integration**: Context-sensitive assistance
- **Preview Options**: See changes before applying

### Information Dialogs

![Information and Status Dialogs](screenshots/dialog2.png)

Information dialogs provide:

- **Status Updates**: Operation progress and results
- **Error Messages**: Clear error descriptions and solutions
- **Confirmation**: User confirmation for critical operations
- **Detailed Information**: Expandable details for complex data

---

## Advanced Features

### Signal Plotting and Analysis

The signal plotter provides real-time visualization of CAN signals:

- **Multi-signal Plots**: Display multiple signals simultaneously
- **Time-based Analysis**: Historical signal trends
- **Zoom and Pan**: Detailed waveform inspection
- **Trigger Modes**: Capture specific events
- **Export Plots**: Save graphs for documentation

### Scripting Console

Automate complex operations with Python scripting:

- **Interactive Console**: Real-time Python execution
- **Script Library**: Pre-defined diagnostic scripts
- **Custom Scripts**: Write your own automation
- **API Access**: Full application programming interface
- **Batch Processing**: Automated test sequences

### Workspace Management

Organize your work with workspace features:

- **Project Files**: Save complete analysis sessions
- **Configuration Profiles**: Store interface settings
- **Template Systems**: Reusable configurations
- **Import/Export**: Share configurations with colleagues

---

## Troubleshooting

### Common Issues and Solutions

#### Connection Problems

**Issue**: Cannot connect to CAN interface
- Verify physical connections
- Check bitrate settings match the network
- Ensure proper drivers are installed
- Try different CAN channel if available

**Issue**: No messages received
- Verify CAN bus has active traffic
- Check termination resistors (120Ω each end)
- Ensure correct acceptance filters
- Verify power supply to CAN interface

#### UDS Communication Issues

**Issue**: UDS connection fails
- Verify Request/Response ID configuration
- Check ECU is in correct diagnostic session
- Ensure proper timing parameters
- Verify ECU supports UDS protocol

**Issue**: Security access denied
- Verify security level is correct
- Check key calculation algorithm
- Ensure seed is properly received
- Try built-in algorithms if DLL fails

#### Performance Issues

**Issue**: Application runs slowly
- Reduce message log buffer size
- Disable unused signal plotting
- Close unnecessary tabs
- Increase system RAM if needed

### Log File Analysis

When reporting issues, include relevant log files:

- **Application Logs**: Check console output for error messages
- **CAN Logs**: Export message logs for analysis
- **Configuration Files**: Include settings that cause issues
- **System Information**: OS version, Python version, hardware details

---

## Appendices

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| Ctrl+N | New Workspace |
| Ctrl+O | Open Workspace |
| Ctrl+S | Save Workspace |
| Ctrl+Q | Quit Application |
| F5 | Connect/Disconnect |
| F9 | Start/Stop Logging |
| Ctrl+F | Find Messages |
| Ctrl+E | Export Log |
| Ctrl+T | Toggle Theme |
| F1 | Help |

### File Formats

#### Supported Import Formats

- **DBC**: Database CAN files
- **ASC**: ASCII log files
- **BLF**: Binary log files (Vector)
- **CSV**: Comma-separated values
- **LOG**: Generic log format

#### Export Formats

- **CSV**: For spreadsheet analysis
- **ASC**: Vector ASCII format
- **JSON**: Structured data export
- **XML**: Standardized data exchange
- **PDF**: Formatted reports

### API Reference

The application provides a comprehensive Python API for automation:

```python
# Example API usage
from can_analyzer import CANAnalyzer

# Initialize analyzer
analyzer = CANAnalyzer()

# Connect to CAN interface
analyzer.connect(interface='socketcan', channel='can0', bitrate=500000)

# Send a message
message = analyzer.create_message(id=0x123, data=[0x01, 0x02, 0x03])
analyzer.send_message(message)

# Start UDS session
uds = analyzer.get_uds_client(request_id=0x7E0, response_id=0x7E8)
uds.start_session(session_type=0x02)

# Read DTC
dtcs = uds.read_dtc()
print(f"Found {len(dtcs)} DTCs")
```

### Configuration File Format

Configuration files use JSON format:

```json
{
    "can_interface": {
        "type": "socketcan",
        "channel": "can0",
        "bitrate": 500000,
        "extended_frames": true
    },
    "uds_settings": {
        "request_id": "0x7E0",
        "response_id": "0x7E8",
        "timeout": 1.0,
        "tester_present_interval": 2.0
    },
    "ui_settings": {
        "theme": "dark",
        "log_buffer_size": 10000,
        "auto_scroll": true
    }
}
```

---

## Conclusion

The Professional CAN Bus Analyzer provides a comprehensive solution for automotive diagnostic and CAN bus analysis tasks. With its advanced features, intuitive interface, and extensive customization options, it serves as an essential tool for automotive professionals.

### Getting Help

For additional support:

- **Documentation**: Refer to this guide and inline help
- **Community**: Join user forums and discussions
- **Support**: Contact technical support for complex issues
- **Updates**: Check for application updates regularly

### Contributing

The application welcomes contributions:

- **Bug Reports**: Report issues with detailed information
- **Feature Requests**: Suggest new functionality
- **Code Contributions**: Submit improvements and fixes
- **Documentation**: Help improve this guide

---

**Thank you for using Professional CAN Bus Analyzer!**

*For the latest updates and support, visit our project repository.*  
*Version 2.0 - August 2025*
