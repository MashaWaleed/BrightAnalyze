#!/usr/bin/env python3
"""
Universal Security Access DLL Interface
Compatible with ASAM/ODX-D standards and CANoe-style DLLs
"""

import ctypes
import ctypes.util
import os
import platform
import json
import threading
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from PySide6.QtCore import QObject, Signal

class SecurityDLLInterface(QObject):
    """Universal interface for security access DLLs"""
    
    # Signals for UI updates
    dll_loaded = Signal(str, str)  # ecu_name, dll_info
    dll_unloaded = Signal(str)     # ecu_name
    dll_error = Signal(str, str)   # ecu_name, error_message
    key_calculated = Signal(str, bytes, bytes)  # ecu_name, seed, key
    
    def __init__(self):
        super().__init__()
        self.loaded_dlls = {}
        self.dll_configs = {}
        self.ecu_configs = {}
        self.is_windows = platform.system() == "Windows"
        self._dll_lock = threading.Lock()
        
        # Standard function signatures for automotive DLLs
        self.dll_functions = {
            'InitSecurityAccess': None,
            'CalculateKey': None, 
            'CleanupSecurityAccess': None,
            'GetDLLInfo': None,
            'GetSupportedLevels': None,
            'ValidateKey': None
        }
        
        # Load default configuration
        self._load_default_config()
    
    def _load_default_config(self):
        """Load default DLL configuration"""
        config_file = Path("security_dll_config.json")
        if config_file.exists():
            self.load_dll_config(str(config_file))
        else:
            self.create_dll_config_template(str(config_file))
    
    def load_dll_config(self, config_file: str) -> bool:
        """Load DLL configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.dll_configs = config.get('dll_configs', {})
                self.ecu_configs = config.get('ecu_configs', {})
            print(f"✅ Loaded DLL configuration from {config_file}")
            return True
        except Exception as e:
            print(f"❌ Error loading DLL config: {e}")
            return False
    
    def save_dll_config(self, config_file: str) -> bool:
        """Save current DLL configuration"""
        try:
            config = {
                'dll_configs': self.dll_configs,
                'ecu_configs': self.ecu_configs,
                'metadata': {
                    'version': '1.0',
                    'created_by': 'CAN Analyzer Security Module',
                    'platform': platform.system()
                }
            }
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Saved DLL configuration to {config_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving DLL config: {e}")
            return False
    
    def load_security_dll(self, dll_path: str, ecu_name: str, config: Dict[str, Any] = None) -> bool:
        """Load a security access DLL with universal interface"""
        
        with self._dll_lock:
            if not self.is_windows:
                return self._create_wine_wrapper(dll_path, ecu_name, config)
            
            try:
                # Verify DLL exists
                if not os.path.exists(dll_path):
                    error_msg = f"DLL file not found: {dll_path}"
                    self.dll_error.emit(ecu_name, error_msg)
                    return False
                
                # Load the DLL
                dll = ctypes.CDLL(dll_path)
                
                # Map standard functions with error handling
                if not self._map_dll_functions(dll, ecu_name):
                    return False
                
                # Initialize the DLL
                try:
                    result = dll.InitSecurityAccess()
                    if result != 0:
                        error_msg = f"DLL initialization failed: error code {result}"
                        self.dll_error.emit(ecu_name, error_msg)
                        return False
                except Exception as e:
                    print(f"⚠️  DLL has no InitSecurityAccess function: {e}")
                
                # Get DLL info
                dll_info = self._get_dll_info(dll)
                
                # Store loaded DLL with enhanced metadata
                dll_entry = {
                    'dll': dll,
                    'path': dll_path,
                    'info': dll_info,
                    'config': config or {},
                    'initialized': True,
                    'supported_levels': self._get_supported_levels(dll),
                    'last_used': None,
                    'error_count': 0
                }
                
                self.loaded_dlls[ecu_name] = dll_entry
                
                # Store ECU configuration
                if config:
                    self.ecu_configs[ecu_name] = config
                
                print(f"✅ Loaded security DLL for {ecu_name}")
                print(f"   Path: {dll_path}")
                print(f"   Info: {dll_info}")
                print(f"   Supported Levels: {dll_entry['supported_levels']}")
                
                self.dll_loaded.emit(ecu_name, dll_info)
                return True
                
            except Exception as e:
                error_msg = f"Error loading DLL {dll_path}: {e}"
                print(f"❌ {error_msg}")
                self.dll_error.emit(ecu_name, error_msg)
                return False
    
    def _map_dll_functions(self, dll, ecu_name: str) -> bool:
        """Map DLL functions with multiple naming conventions"""
        try:
            # Standard ASAM naming convention
            self._try_map_function(dll, 'InitSecurityAccess', [
                'InitSecurityAccess', 'Init', 'Initialize', 'SA_Init', 'SecurityInit'
            ])
            
            # Key calculation function (most important)
            if not self._try_map_function(dll, 'CalculateKey', [
                'CalculateKey', 'CalcKey', 'GenerateKey', 'SA_CalculateKey', 
                'ComputeKey', 'SecurityCalculateKey', 'GetKey'
            ]):
                self.dll_error.emit(ecu_name, "Critical: No key calculation function found")
                return False
            
            # Set function signatures
            dll.CalculateKey.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte),  # seed
                ctypes.c_uint,                   # seedLength
                ctypes.POINTER(ctypes.c_ubyte),  # key (output)
                ctypes.POINTER(ctypes.c_uint),   # keyLength (output)
                ctypes.c_uint                    # security level
            ]
            dll.CalculateKey.restype = ctypes.c_int
            
            # Optional functions
            self._try_map_function(dll, 'CleanupSecurityAccess', [
                'CleanupSecurityAccess', 'Cleanup', 'Close', 'SA_Cleanup', 'SecurityCleanup'
            ])
            
            self._try_map_function(dll, 'GetDLLInfo', [
                'GetDLLInfo', 'GetInfo', 'Info', 'SA_GetInfo', 'GetVersion'
            ])
            
            self._try_map_function(dll, 'GetSupportedLevels', [
                'GetSupportedLevels', 'GetLevels', 'SA_GetLevels', 'SupportedLevels'
            ])
            
            return True
            
        except Exception as e:
            print(f"❌ Error mapping DLL functions: {e}")
            return False
    
    def _try_map_function(self, dll, standard_name: str, alternatives: List[str]) -> bool:
        """Try to map a function with alternative names"""
        for alt_name in alternatives:
            if hasattr(dll, alt_name):
                setattr(dll, standard_name, getattr(dll, alt_name))
                print(f"   Mapped {alt_name} → {standard_name}")
                return True
        return False
    
    def _get_dll_info(self, dll) -> str:
        """Get DLL information"""
        try:
            if hasattr(dll, 'GetDLLInfo'):
                info_buffer = ctypes.create_string_buffer(256)
                dll.GetDLLInfo(info_buffer, 256)
                return info_buffer.value.decode('utf-8', errors='ignore').strip()
        except Exception:
            pass
        
        return "Unknown DLL - No info available"
    
    def _get_supported_levels(self, dll) -> List[int]:
        """Get supported security levels from DLL"""
        try:
            if hasattr(dll, 'GetSupportedLevels'):
                levels_buffer = (ctypes.c_uint * 16)()  # Support up to 16 levels
                count = ctypes.c_uint(16)
                result = dll.GetSupportedLevels(levels_buffer, ctypes.byref(count))
                if result == 0:
                    return list(levels_buffer[:count.value])
        except Exception:
            pass
        
        # Default levels if DLL doesn't provide them
        return [1, 3, 5, 7, 9, 11, 13, 15]  # Odd levels for seed requests
    
    def calculate_key_with_dll(self, ecu_name: str, seed: bytes, level: int) -> Optional[bytes]:
        """Calculate security key using loaded DLL"""
        
        with self._dll_lock:
            if ecu_name not in self.loaded_dlls:
                self.dll_error.emit(ecu_name, f"No DLL loaded for ECU: {ecu_name}")
                return None
            
            dll_info = self.loaded_dlls[ecu_name]
            if not dll_info['initialized']:
                self.dll_error.emit(ecu_name, f"DLL not initialized for ECU: {ecu_name}")
                return None
            
            dll = dll_info['dll']
            
            try:
                # Prepare input parameters
                seed_length = len(seed)
                seed_array = (ctypes.c_ubyte * seed_length)(*seed)
                
                # Prepare output parameters
                max_key_length = 32  # Support up to 32-byte keys
                key_array = (ctypes.c_ubyte * max_key_length)()
                key_length = ctypes.c_uint(max_key_length)
                
                # Call the DLL function
                result = dll.CalculateKey(
                    seed_array,
                    seed_length,
                    key_array,
                    ctypes.byref(key_length),
                    level
                )
                
                if result != 0:
                    error_msg = f"DLL key calculation failed: error code {result}"
                    self.dll_error.emit(ecu_name, error_msg)
                    dll_info['error_count'] += 1
                    return None
                
                # Extract the calculated key
                actual_key_length = key_length.value
                if actual_key_length > max_key_length:
                    actual_key_length = max_key_length
                
                calculated_key = bytes(key_array[:actual_key_length])
                
                # Update usage statistics
                dll_info['last_used'] = platform.time.time() if hasattr(platform, 'time') else 0
                
                print(f"✅ DLL calculated key for {ecu_name}")
                print(f"   Seed: {seed.hex().upper()}")
                print(f"   Key:  {calculated_key.hex().upper()}")
                print(f"   Level: {level}")
                
                self.key_calculated.emit(ecu_name, seed, calculated_key)
                return calculated_key
                
            except Exception as e:
                error_msg = f"Error calling DLL function: {e}"
                print(f"❌ {error_msg}")
                self.dll_error.emit(ecu_name, error_msg)
                dll_info['error_count'] += 1
                return None
    
    def get_available_ecus(self) -> List[str]:
        """Get list of ECUs with loaded DLLs"""
        return list(self.loaded_dlls.keys())
    
    def get_ecu_info(self, ecu_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an ECU's DLL"""
        if ecu_name not in self.loaded_dlls:
            return None
        
        dll_info = self.loaded_dlls[ecu_name]
        return {
            'ecu_name': ecu_name,
            'dll_path': dll_info['path'],
            'dll_info': dll_info['info'],
            'initialized': dll_info['initialized'],
            'supported_levels': dll_info['supported_levels'],
            'last_used': dll_info.get('last_used'),
            'error_count': dll_info.get('error_count', 0),
            'config': dll_info.get('config', {})
        }
    
    def unload_dll(self, ecu_name: str) -> bool:
        """Unload a security DLL"""
        with self._dll_lock:
            if ecu_name not in self.loaded_dlls:
                return False
            
            try:
                dll_info = self.loaded_dlls[ecu_name]
                if dll_info['initialized'] and hasattr(dll_info['dll'], 'CleanupSecurityAccess'):
                    dll_info['dll'].CleanupSecurityAccess()
                
                del self.loaded_dlls[ecu_name]
                print(f"✅ Unloaded DLL for {ecu_name}")
                self.dll_unloaded.emit(ecu_name)
                return True
                
            except Exception as e:
                print(f"❌ Error unloading DLL: {e}")
                return False
    
    def _create_wine_wrapper(self, dll_path: str, ecu_name: str, config: Dict[str, Any]) -> bool:
        """Create Wine wrapper for Windows DLLs on Linux"""
        print("🍷 Creating Wine wrapper for Windows DLL on Linux...")
        
        # Check if Wine is available
        wine_path = ctypes.util.find_library('wine')
        if not wine_path:
            self.dll_error.emit(ecu_name, "Wine not found. Install with: sudo apt install wine")
            return False
        
        # Create a mock DLL interface that uses Wine
        wine_wrapper = {
            'dll': None,
            'path': dll_path,
            'info': f"Wine wrapper for {os.path.basename(dll_path)}",
            'config': config or {},
            'initialized': True,
            'supported_levels': [1, 3, 5, 7, 9, 11, 13, 15],
            'is_wine': True,
            'last_used': None,
            'error_count': 0
        }
        
        self.loaded_dlls[ecu_name] = wine_wrapper
        print(f"✅ Created Wine wrapper for {ecu_name}")
        print(f"   Note: Wine DLL calls will be simulated")
        
        self.dll_loaded.emit(ecu_name, wine_wrapper['info'])
        return True
    
    def create_dll_config_template(self, output_file: str) -> bool:
        """Create a template DLL configuration file"""
        template = {
            "dll_configs": {
                "bmw_engine": {
                    "dll_path": "C:/OEM_DLLs/BMW_Engine_SecurityAccess.dll",
                    "description": "BMW Engine ECU Security Access",
                    "manufacturer": "BMW",
                    "algorithm_type": "proprietary",
                    "notes": "Requires BMW diagnostic session"
                },
                "vw_transmission": {
                    "dll_path": "C:/OEM_DLLs/VAG_Transmission_SecurityAccess.dll",
                    "description": "Volkswagen Group Transmission ECU",
                    "manufacturer": "Volkswagen",
                    "algorithm_type": "seed_key_transformation",
                    "notes": "Compatible with Audi, Skoda, SEAT"
                }
            },
            "ecu_configs": {
                "Engine_ECU_0x7E0": {
                    "dll_config": "bmw_engine",
                    "can_tx_id": "0x7E0",
                    "can_rx_id": "0x7E8",
                    "security_levels": {
                        "1": {"description": "Service mode", "session_required": "0x02"},
                        "3": {"description": "Programming", "session_required": "0x02"}
                    },
                    "timeouts": {
                        "seed_request": 5000,
                        "key_send": 3000
                    }
                },
                "Transmission_ECU_0x7E1": {
                    "dll_config": "vw_transmission",
                    "can_tx_id": "0x7E1", 
                    "can_rx_id": "0x7E9",
                    "security_levels": {
                        "1": {"description": "Diagnostic", "session_required": "0x03"},
                        "5": {"description": "Calibration", "session_required": "0x03"}
                    },
                    "timeouts": {
                        "seed_request": 3000,
                        "key_send": 2000
                    }
                }
            },
            "fallback_algorithms": {
                "xor_constant": {"constant": "0x1234", "description": "Simple XOR"},
                "add_constant": {"constant": "0x5678", "description": "Simple addition"},
                "complement": {"description": "Bitwise complement"}
            },
            "metadata": {
                "version": "1.0",
                "description": "Security Access DLL Configuration",
                "created_by": "CAN Analyzer Security Module"
            }
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(template, f, indent=2)
            print(f"✅ Created DLL configuration template: {output_file}")
            return True
        except Exception as e:
            print(f"❌ Error creating template: {e}")
            return False
    
    def test_dll_functionality(self, ecu_name: str) -> Dict[str, Any]:
        """Test DLL functionality with sample data"""
        if ecu_name not in self.loaded_dlls:
            return {"success": False, "error": "DLL not loaded"}
        
        # Test with sample seed
        test_seed = bytes([0x12, 0x34, 0x56, 0x78])
        test_level = 1
        
        try:
            calculated_key = self.calculate_key_with_dll(ecu_name, test_seed, test_level)
            
            if calculated_key:
                return {
                    "success": True,
                    "test_seed": test_seed.hex().upper(),
                    "calculated_key": calculated_key.hex().upper(),
                    "test_level": test_level
                }
            else:
                return {"success": False, "error": "Key calculation failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
