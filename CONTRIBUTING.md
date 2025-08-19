# 🤝 Contributing to Professional CAN Bus Analyzer (BrightAnalyze)

Thank you for your interest in contributing to BrightAnalyze! This document provides guidelines and information for contributors.

## 🎯 Ways to Contribute

### 🐛 **Bug Reports**
Found a bug? Help us fix it!
- Check [existing issues](https://github.com/MashaWaleed/BrightAnalyze/issues) first
- Use the bug report template
- Include steps to reproduce, expected vs actual behavior
- Add screenshots, logs, or error messages

### ✨ **Feature Requests**
Have an idea for improvement?
- Check [discussions](https://github.com/MashaWaleed/BrightAnalyze/discussions) for similar ideas
- Describe the problem you're solving
- Explain your proposed solution
- Consider implementation complexity

### 📝 **Documentation**
Help make the project more accessible!
- Improve README clarity
- Add code comments and docstrings
- Create tutorials or guides
- Fix typos and formatting

### 🔧 **Code Contributions**
Ready to dive into the code?
- Fix bugs from the issue tracker
- Implement approved feature requests
- Improve performance and code quality
- Add tests for new functionality

## 🛠️ Development Setup

### 📋 **Prerequisites**
- Python 3.8 or higher
- Git for version control
- CANable hardware or virtual CAN for testing

### 🚀 **Getting Started**

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YourUsername/BrightAnalyze.git
cd BrightAnalyze/can_analyzer

# 3. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install development tools
pip install pytest black flake8 mypy pre-commit

# 6. Set up pre-commit hooks (optional but recommended)
pre-commit install

# 7. Test your setup
python main.py
```

### 🔧 **Development Tools**

#### **Code Formatting**
```bash
# Format code with Black
black can_analyzer/ ui/ *.py

# Check formatting without changes
black --check can_analyzer/ ui/ *.py
```

#### **Linting**
```bash
# Check code style with flake8
flake8 can_analyzer/ ui/ --max-line-length=88 --extend-ignore=E203,W503

# Type checking with mypy
mypy can_analyzer/ ui/
```

#### **Testing**
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=can_analyzer --cov-report=html

# Run specific test file
pytest test_uds_fixes.py -v

# Run tests for specific functionality
pytest -k "test_security_access"
```

## 📐 Coding Standards

### 🐍 **Python Style Guide**

**We follow PEP 8 with these specific guidelines:**

```python
# Line length: 88 characters (Black default)
# Use Black for formatting
# Use type hints where possible

# Good example:
def send_can_message(
    self, 
    can_id: int, 
    data: List[int], 
    extended: bool = False
) -> bool:
    """
    Send a CAN message to the bus.
    
    Args:
        can_id: CAN identifier (11 or 29 bit)
        data: Message data bytes (0-8 bytes)
        extended: Use extended frame format
        
    Returns:
        True if message sent successfully
        
    Raises:
        CANError: If message transmission fails
    """
    try:
        message = can.Message(
            arbitration_id=can_id,
            data=data,
            is_extended_id=extended
        )
        self.bus.send(message)
        return True
    except can.CanError as e:
        print(f"[ERROR] Failed to send message: {e}")
        return False
```

### 📁 **File Organization**

```
can_analyzer/
├── main.py                    # Application entry point
├── can_backend.py            # CAN interface management
├── uds_backend.py            # UDS diagnostic protocols
├── ui/                       # User interface components
│   ├── __init__.py
│   ├── menu_bar.py          # Main menu system
│   ├── left_sidebar.py      # Interface & transmission controls
│   ├── message_log.py       # Real-time message display
│   ├── right_sidebar.py     # DBC management & filters
│   ├── diagnostics_panel.py # UDS diagnostic interface
│   ├── signal_plotter.py    # Real-time signal visualization
│   └── style_manager.py     # Theme and styling
├── tests/                   # Test files
└── docs/                    # Documentation
```

### 🏷️ **Naming Conventions**

```python
# Classes: PascalCase
class CANBusManager:
class UDSBackend:
class MessageLog:

# Functions and variables: snake_case
def send_message():
def get_active_interfaces():
can_interface_list = []

# Constants: UPPER_SNAKE_CASE
DEFAULT_BITRATE = 500000
MAX_CAN_DATA_LENGTH = 8

# Private members: leading underscore
class MyClass:
    def _internal_method(self):
        self._private_variable = 42
```

### 📚 **Documentation Standards**

```python
def complex_function(param1: str, param2: int = 100) -> Dict[str, Any]:
    """
    One-line description of what the function does.
    
    Longer description if needed, explaining the purpose,
    algorithm, or important implementation details.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter with default value
        
    Returns:
        Dictionary containing processed results with keys:
        - 'status': bool indicating success
        - 'data': processed data or None
        - 'error': error message if failed
        
    Raises:
        ValueError: If param1 is empty
        ConnectionError: If CAN interface is not available
        
    Example:
        >>> result = complex_function("test", 50)
        >>> print(result['status'])
        True
    """
```

## 🧪 Testing Guidelines

### ✅ **Writing Tests**

```python
# tests/test_can_backend.py
import pytest
from unittest.mock import Mock, patch
from can_backend import CANBusManager

class TestCANBusManager:
    """Test suite for CAN bus management functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.can_manager = CANBusManager()
        
    def test_interface_connection_success(self):
        """Test successful CAN interface connection."""
        # Arrange
        mock_bus = Mock()
        
        # Act
        with patch('can.Bus', return_value=mock_bus):
            result = self.can_manager.connect_interface(
                driver='socketcan',
                channel='vcan0',
                bitrate=500000
            )
            
        # Assert
        assert result is True
        assert self.can_manager.bus is mock_bus
        
    def test_message_sending_with_invalid_data(self):
        """Test message sending with invalid data raises appropriate error."""
        # Arrange
        self.can_manager.bus = Mock()
        invalid_data = [256, 257]  # Invalid byte values
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid CAN data"):
            self.can_manager.send_message(0x123, invalid_data)
            
    @pytest.mark.parametrize("bitrate,expected", [
        (125000, True),
        (250000, True), 
        (500000, True),
        (1000000, True),
        (123456, False),  # Invalid bitrate
    ])
    def test_bitrate_validation(self, bitrate, expected):
        """Test bitrate validation with various values."""
        result = self.can_manager.validate_bitrate(bitrate)
        assert result == expected
```

### 🎯 **Test Categories**

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions
3. **UI Tests**: Test user interface functionality (limited)
4. **Hardware Tests**: Test with real CAN hardware (optional)

## 🔄 Git Workflow

### 🌿 **Branching Strategy**

```bash
# Main branches:
main          # Stable release code
develop       # Integration branch for features

# Feature branches:
feature/add-j1939-support
feature/improve-signal-plotting
bugfix/fix-uds-timeout-issue
hotfix/critical-security-fix
```

### 📝 **Commit Messages**

Use clear, descriptive commit messages:

```bash
# Good examples:
git commit -m "Add: CANable SLCAN interface support"
git commit -m "Fix: UDS security access timeout handling"
git commit -m "Improve: Signal plotter performance with large datasets"
git commit -m "Docs: Update installation instructions for Linux"

# Message format:
<type>: <description>

# Types:
Add:      New feature or functionality
Fix:      Bug fix
Improve:  Enhancement to existing feature
Refactor: Code restructuring without behavior change
Docs:     Documentation updates
Test:     Adding or modifying tests
Style:    Code formatting changes
```

### 🔀 **Pull Request Process**

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**
   ```bash
   # Make your changes
   python main.py  # Test manually
   pytest          # Run automated tests
   black .         # Format code
   flake8 .        # Check linting
   ```

3. **Commit and Push**
   ```bash
   git add .
   git commit -m "Add: Your feature description"
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request**
   - Use the PR template
   - Reference related issues
   - Add screenshots for UI changes
   - Request review from maintainers

5. **Address Review Feedback**
   - Make requested changes
   - Update tests if needed
   - Respond to review comments

## 🚀 Release Process

### 📦 **Building Releases**

```bash
# Create executables locally for testing
pyinstaller CANAnalyzer-Linux.spec

# Test the executable
./dist/CANAnalyzer-Linux

# Automated builds via GitHub Actions
# Triggered on:
# - Push to main branch
# - Tagged releases (v1.0, v1.1, etc.)
# - Manual workflow dispatch
```

### 🏷️ **Version Numbering**

We use semantic versioning (semver):
- **Major** (1.0): Breaking changes
- **Minor** (1.1): New features, backward compatible
- **Patch** (1.1.1): Bug fixes, backward compatible

## 🆘 Getting Help

### 💬 **Communication Channels**

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Code Review**: Pull request comments
- **Email**: For sensitive security issues

### 📚 **Resources**

- **Python-CAN**: [Documentation](https://python-can.readthedocs.io/)
- **PySide6**: [Qt for Python](https://doc.qt.io/qtforpython/)
- **UDS Protocol**: [ISO 14229 Standard](https://en.wikipedia.org/wiki/Unified_Diagnostic_Services)
- **CAN Protocol**: [Bosch CAN Specification](https://www.bosch-semiconductors.com/ip-modules/can-ip-modules/can-protocol/)

### 🔍 **Debugging Tips**

```bash
# Enable debug logging
python main.py --debug

# Check application logs
tail -f ~/.cache/BrightAnalyze/app.log  # Linux
# %LOCALAPPDATA%\BrightAnalyze\app.log  # Windows

# Monitor CAN traffic directly
candump can0  # Linux with SocketCAN

# Debug Qt issues
export QT_LOGGING_RULES="*=true"  # Linux
set QT_LOGGING_RULES=*=true       # Windows
```

## 🙏 Recognition

Contributors are recognized in several ways:

- **GitHub Contributors**: Automatic recognition in repository
- **Release Notes**: Major contributors mentioned in releases
- **Documentation**: Contributor acknowledgments in README
- **Community**: Shout-outs in discussions and issues

## 📄 License

By contributing to BrightAnalyze, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

**Thank you for contributing to BrightAnalyze!** 🚗✨

*Your contributions help make automotive diagnostics more accessible to everyone.*
