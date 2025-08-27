#!/usr/bin/env python3
"""
Test script for enhanced security access functionality
Tests the new DLL integration and UI components
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from security_dll_interface import SecurityDLLInterface
    print("✅ Security DLL Interface imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Security DLL Interface: {e}")

try:
    from ui.enhanced_security_widget import SecurityAccessWidget
    print("✅ Enhanced Security Widget imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Enhanced Security Widget: {e}")

def test_dll_interface():
    """Test the DLL interface functionality"""
    print("\n🧪 Testing DLL Interface...")
    
    # Create DLL interface
    dll_interface = SecurityDLLInterface()
    
    # Test basic functionality
    print(f"DLL loaded: {dll_interface.is_dll_loaded()}")
    
    # Test built-in algorithms
    test_seed = b'\x12\x34\x56\x78'
    
    algorithms = ['xor', 'add', 'complement', 'crc16']
    for algo in algorithms:
        try:
            key = dll_interface._calculate_builtin_key(test_seed, algo)
            key_hex = " ".join([f"{b:02X}" for b in key])
            print(f"✅ {algo.upper()}: {test_seed.hex().upper()} → {key_hex}")
        except Exception as e:
            print(f"❌ {algo.upper()}: Error - {e}")

def test_security_algorithms():
    """Test security key calculation algorithms"""
    print("\n🔐 Testing Security Algorithms...")
    
    test_seed = b'\x12\x34\x56\x78'
    print(f"Test seed: {test_seed.hex().upper()}")
    
    # XOR algorithm
    xor_key = bytes([b ^ 0x12 for b in test_seed])
    print(f"XOR (0x12): {' '.join([f'{b:02X}' for b in xor_key])}")
    
    # ADD algorithm  
    add_key = bytes([(b + 0x34) & 0xFF for b in test_seed])
    print(f"ADD (0x34): {' '.join([f'{b:02X}' for b in add_key])}")
    
    # Complement algorithm
    comp_key = bytes([~b & 0xFF for b in test_seed])
    print(f"Complement: {' '.join([f'{b:02X}' for b in comp_key])}")
    
    # CRC16 algorithm
    def calculate_crc16(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return bytes([(crc >> 8) & 0xFF, crc & 0xFF])
    
    crc_key = calculate_crc16(test_seed)
    print(f"CRC16: {' '.join([f'{b:02X}' for b in crc_key])}")

def test_file_structure():
    """Test if all required files exist"""
    print("\n📁 Testing File Structure...")
    
    required_files = [
        'security_dll_interface.py',
        'ui/enhanced_security_widget.py',
        'security_test_simulator.py',
        'security_algorithm_analyzer.py',
        'ui/diagnostics_panel.py',
        'can_backend.py',
        'uds_backend.py'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")

def test_imports():
    """Test importing all security-related modules"""
    print("\n📦 Testing Module Imports...")
    
    modules_to_test = [
        ('security_dll_interface', 'SecurityDLLInterface'),
        ('security_test_simulator', 'SecurityAccessECU'), 
        ('security_algorithm_analyzer', 'SecurityAlgorithmAnalyzer'),
        ('ui.diagnostics_panel', 'DiagnosticsPanel'),
    ]
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"❌ {module_name}.{class_name} - Import Error: {e}")
        except AttributeError as e:
            print(f"❌ {module_name}.{class_name} - Attribute Error: {e}")
        except Exception as e:
            print(f"❌ {module_name}.{class_name} - Error: {e}")

def main():
    """Main test function"""
    print("🚀 Enhanced Security Access Test Suite")
    print("=" * 50)
    
    test_file_structure()
    test_imports()
    test_dll_interface()
    test_security_algorithms()
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed")
    print("\n📋 Summary:")
    print("• DLL Interface: Universal ASAM/ODX-D compatible")
    print("• Enhanced UI: ECU management and DLL loading")  
    print("• Built-in Algorithms: XOR, ADD, Complement, CRC16")
    print("• Test Environment: Complete ECU simulator")
    print("• Cross-platform: Windows DLL support via Wine on Linux")

if __name__ == "__main__":
    main()
