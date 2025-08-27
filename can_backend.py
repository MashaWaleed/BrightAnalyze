import can
import threading
import time
import platform
from PySide6.QtCore import QObject, Signal, QThread
import subprocess
import os
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor

class CANBusManager(QObject):
    message_received = Signal(dict)  # Emitted with message info dict
    bus_state_changed = Signal(str)  # 'connected', 'disconnected', 'error'
    error_occurred = Signal(str)
    isotp_message_received = Signal(dict)  # Emitted with ISOTP message info

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bus = None
        self.recv_thread = None
        self.running = False
        self.interface = None
        self.bitrate = None
        self.is_connected = False
        
        # Message queue for async processing (with size limit)
        self.message_queue = queue.Queue(maxsize=1000)
        self.processing_thread = None
        
        # Thread pool for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="CANWorker")
        
        # ISOTP stacks for UDS communication with thread safety
        self.isotp_stacks = {}
        self.isotp_stacks_lock = threading.Lock()
        
        print("[DEBUG] CANBusManager initialized")

    @staticmethod
    def list_socketcan_interfaces():
        """Return a list of available SocketCAN interfaces (Linux only)."""
        if platform.system() != "Linux":
            return ["vcan0"]  # Fallback for non-Linux systems
            
        try:
            # First, try to list all network interfaces and filter CAN interfaces
            result = subprocess.run(['ip', 'link', 'show'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                interfaces = []
                lines = result.stdout.splitlines()
                for line in lines:
                    # Look for CAN interfaces (usually contain 'can' in the name)
                    if ': can' in line or ': vcan' in line:
                        # Extract interface name
                        parts = line.split(':')
                        if len(parts) >= 2:
                            iface_name = parts[1].strip().split('@')[0]  # Remove @if_name part
                            if iface_name:
                                interfaces.append(iface_name)
                
                # If no CAN interfaces found, try the more specific command
                if not interfaces:
                    result = subprocess.run(['ip', '-details', 'link', 'show', 'type', 'can'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        lines = result.stdout.splitlines()
                        for line in lines:
                            if line.strip() and not line.startswith(' '):
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    iface_name = parts[1].strip().split('@')[0]
                                    interfaces.append(iface_name)
                
                # Add common virtual CAN interfaces if none found
                if not interfaces:
                    interfaces = ["vcan0", "vcan1", "can0", "can1"]
                    
                return sorted(list(set(interfaces)))  # Remove duplicates and sort
        except Exception as e:
            print(f"[DEBUG] Error listing interfaces: {e}")
            return ["vcan0", "can0", "can1"]  # Safe fallback

    def connect(self, interface, bitrate=500000, driver='socketcan', **kwargs):
        """Connect to the specified CAN interface with the specified driver."""
        print(f"[DEBUG] Attempting to connect to {interface} at {bitrate} bps using {driver} driver")
        
        # Disconnect if already connected
        if self.is_connected:
            self.disconnect()
        
        self.interface = interface
        self.bitrate = bitrate
        
        try:
            # Filter out conflicting parameters from kwargs
            # Remove parameters that we set explicitly to avoid conflicts
            clean_kwargs = {k: v for k, v in kwargs.items() if k not in ['channel', 'interface', 'bustype']}
            # Note: Keep 'bitrate' and 'data_bitrate' for proper CAN FD support
            
            # Handle different drivers
            if driver == 'slcan':
                # SLCAN driver for serial USB-to-CAN devices
                print(f"[DEBUG] SLCAN clean_kwargs: {clean_kwargs}")
                
                # Extract CAN FD parameters for special handling
                is_canfd = clean_kwargs.pop('is_canfd', False) or clean_kwargs.pop('fd', False)
                data_bitrate = clean_kwargs.pop('data_bitrate', None)
                fd_non_iso = clean_kwargs.pop('fd_non_iso', False)
                
                # Remove duplicate bitrate from kwargs if present
                clean_kwargs.pop('bitrate', None)
                
                if is_canfd:
                    print(f"[DEBUG] CAN FD mode requested: data_bitrate={data_bitrate}, fd_non_iso={fd_non_iso}")
                    
                    # For SLCAN CAN FD, we need to use BitTimingFd if data_bitrate is specified
                    if data_bitrate:
                        try:
                            from can.bit_timing import BitTimingFd
                            # Calculate timing parameters for CANable (80MHz clock)
                            # These are approximate calculations - may need fine-tuning
                            timing_fd = BitTimingFd(
                                f_clock=80000000,  # 80MHz clock (typical for CANable)
                                nom_brp=int(80000000 / (16 * bitrate)),  # Nominal prescaler
                                nom_tseg1=13,      # Nominal time segment 1
                                nom_tseg2=2,       # Nominal time segment 2  
                                nom_sjw=1,         # Nominal sync jump width
                                data_brp=int(80000000 / (16 * data_bitrate)),  # Data prescaler
                                data_tseg1=13,     # Data time segment 1
                                data_tseg2=2,      # Data time segment 2
                                data_sjw=1         # Data sync jump width
                            )
                            clean_kwargs['timing'] = timing_fd
                            print(f"[DEBUG] Created BitTimingFd for CAN FD: nom={bitrate}bps, data={data_bitrate}bps")
                        except Exception as e:
                            print(f"[WARNING] Failed to create BitTimingFd, falling back to bitrate only: {e}")
                
                self.bus = can.interface.Bus(
                    bustype='slcan',
                    channel=interface,  # e.g., '/dev/ttyACM0' or 'COM3'
                    bitrate=bitrate if 'timing' not in clean_kwargs else None,  # Don't pass bitrate with timing
                    timeout=0.1,
                    **clean_kwargs
                )
                print(f"[DEBUG] Successfully created SLCAN bus for {interface}")
                
            elif driver == 'socketcan':
                # SocketCAN driver for Linux kernel CAN interfaces
                # For real CAN interfaces (not vcan), try to configure the interface
                if not interface.startswith('vcan'):
                    try:
                        # Check if interface exists and is down
                        check_result = subprocess.run(['ip', 'link', 'show', interface], 
                                                    capture_output=True, text=True, timeout=2)
                        if check_result.returncode == 0:
                            # Interface exists, try to bring it up with bitrate
                            subprocess.run([
                                'sudo', 'ip', 'link', 'set', interface, 'down'
                            ], capture_output=True, timeout=5)
                            
                            subprocess.run([
                                'sudo', 'ip', 'link', 'set', interface, 'up',
                                'type', 'can', 'bitrate', str(bitrate)
                            ], capture_output=True, timeout=5)
                            
                            print(f"[DEBUG] Interface {interface} configured with bitrate {bitrate}")
                        else:
                            print(f"[DEBUG] Interface {interface} not found, will try to connect anyway")
                    except subprocess.TimeoutExpired:
                        print(f"[DEBUG] Timeout configuring interface {interface}")
                    except Exception as e:
                        print(f"[DEBUG] Could not configure interface {interface}: {e}")
                
                # Create the SocketCAN bus connection
                # For SocketCAN, don't pass bitrate if it's a vcan interface
                socketcan_kwargs = clean_kwargs.copy()
                if not interface.startswith('vcan'):
                    socketcan_kwargs['bitrate'] = bitrate
                    
                self.bus = can.interface.Bus(
                    bustype='socketcan', 
                    channel=interface,
                    **socketcan_kwargs
                )
                print(f"[DEBUG] Successfully created SocketCAN bus for {interface}")
                
            elif driver in ['vector', 'pcan', 'kvaser', 'ixxat']:
                # Hardware driver for professional CAN interfaces
                # For these, the interface is typically a channel number
                try:
                    channel = int(interface) if interface.isdigit() else kwargs.get('channel', 0)
                except:
                    channel = kwargs.get('channel', 0)
                    
                self.bus = can.interface.Bus(
                    bustype=driver,
                    channel=channel,
                    bitrate=bitrate,
                    **clean_kwargs
                )
                print(f"[DEBUG] Successfully created {driver} bus for channel {channel}")
                
            else:
                # Generic fallback
                self.bus = can.interface.Bus(
                    bustype=driver,
                    channel=interface,
                    bitrate=bitrate,
                    **clean_kwargs
                )
                print(f"[DEBUG] Successfully created {driver} bus for {interface}")
            
            # Start async receiving thread
            self.running = True
            self.recv_thread = threading.Thread(target=self._async_recv_loop, daemon=True)
            self.recv_thread.start()
            
            # Start message processing thread
            self.processing_thread = threading.Thread(target=self._process_messages, daemon=True)
            self.processing_thread.start()
            
            self.is_connected = True
            self.bus_state_changed.emit('connected')
            print(f"[DEBUG] Connected to CAN bus {interface}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to connect to CAN bus {interface}: {error_msg}")
            self.bus = None
            self.is_connected = False
            self.bus_state_changed.emit('error')
            self.error_occurred.emit(f"Connection failed: {error_msg}")

    def disconnect(self):
        """Disconnect from the CAN bus with Windows-safe cleanup."""
        print("[DEBUG] Disconnecting from CAN bus")
        
        # Set running flag to False first
        self.running = False
        self.is_connected = False
        
        # Signal disconnection immediately for UI responsiveness
        self.bus_state_changed.emit('disconnected')
        
        # Windows-safe thread cleanup with longer timeouts
        if self.recv_thread and self.recv_thread.is_alive():
            print("[DEBUG] Stopping receive thread...")
            try:
                self.recv_thread.join(timeout=2.0)  # Longer timeout for Windows
                if self.recv_thread.is_alive():
                    print("[WARNING] Receive thread did not stop gracefully")
            except Exception as e:
                print(f"[DEBUG] Error joining receive thread: {e}")
        
        if self.processing_thread and self.processing_thread.is_alive():
            print("[DEBUG] Stopping processing thread...")
            try:
                self.processing_thread.join(timeout=2.0)  # Longer timeout for Windows
                if self.processing_thread.is_alive():
                    print("[WARNING] Processing thread did not stop gracefully")
            except Exception as e:
                print(f"[DEBUG] Error joining processing thread: {e}")
        
        # Clear the message queue safely
        try:
            queue_size = 0
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                    queue_size += 1
                    if queue_size > 1000:  # Prevent infinite loop
                        print("[WARNING] Large message queue, forcing clear")
                        break
                except queue.Empty:
                    break
            if queue_size > 0:
                print(f"[DEBUG] Cleared {queue_size} messages from queue")
        except Exception as e:
            print(f"[DEBUG] Error clearing message queue: {e}")
        
        # Close the bus with Windows-safe error handling
        if self.bus:
            try:
                print("[DEBUG] Shutting down CAN bus...")
                self.bus.shutdown()
                print("[DEBUG] CAN bus shutdown complete")
            except Exception as e:
                # Windows can have various shutdown errors, log but don't fail
                print(f"[DEBUG] Bus shutdown error (may be normal on Windows): {e}")
            finally:
                self.bus = None
        
        print("[DEBUG] Disconnected from CAN bus")

    def send_message(self, msg_id, data, extended_id=False, fd=False):
        """Send a CAN message with Windows-compatible data handling."""
        if not self.bus or not self.is_connected:
            error_msg = 'Not connected to CAN bus'
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
        
        try:
            # Windows-safe message ID validation and conversion
            try:
                if isinstance(msg_id, str):
                    # Handle hex strings with various formats
                    clean_id = msg_id.strip().lower()
                    if clean_id.startswith('0x'):
                        message_id = int(clean_id, 16)
                    elif clean_id.startswith('0b'):
                        message_id = int(clean_id, 2)
                    else:
                        # Try hex first, then decimal
                        try:
                            message_id = int(clean_id, 16)
                        except ValueError:
                            message_id = int(clean_id, 10)
                else:
                    message_id = int(msg_id)
                
                # Validate CAN ID range
                if extended_id:
                    if not (0 <= message_id <= 0x1FFFFFFF):  # 29-bit extended ID
                        raise ValueError(f"Extended CAN ID out of range: 0x{message_id:X}")
                else:
                    if not (0 <= message_id <= 0x7FF):  # 11-bit standard ID
                        raise ValueError(f"Standard CAN ID out of range: 0x{message_id:X}")
                        
            except (ValueError, TypeError) as e:
                error_msg = f"Invalid message ID '{msg_id}': {e}"
                print(f"[ERROR] {error_msg}")
                self.error_occurred.emit(error_msg)
                return False
            
            # Windows-safe data conversion and validation
            try:
                data_bytes = bytearray()
                
                if data is None:
                    data_bytes = bytearray()
                elif isinstance(data, (bytes, bytearray)):
                    data_bytes = bytearray(data)
                elif isinstance(data, (list, tuple)):
                    # Convert list/tuple to bytes with validation
                    for item in data:
                        byte_val = int(item) & 0xFF  # Ensure byte range 0-255
                        data_bytes.append(byte_val)
                elif isinstance(data, str):
                    # Handle hex string data like "01 02 03" or "010203"
                    clean_data = data.strip().replace(' ', '').replace('0x', '').replace('0X', '')
                    if clean_data:
                        # Ensure even number of hex digits
                        if len(clean_data) % 2:
                            clean_data = '0' + clean_data
                        
                        for i in range(0, len(clean_data), 2):
                            try:
                                byte_val = int(clean_data[i:i+2], 16)
                                data_bytes.append(byte_val)
                            except ValueError:
                                error_msg = f"Invalid hex data at position {i}: '{clean_data[i:i+2]}'"
                                print(f"[ERROR] {error_msg}")
                                self.error_occurred.emit(error_msg)
                                return False
                elif isinstance(data, int):
                    # Single integer as single byte
                    data_bytes.append(int(data) & 0xFF)
                else:
                    # Try to convert to bytes
                    try:
                        data_bytes = bytearray(data)
                    except (TypeError, ValueError):
                        data_bytes = bytearray()
                
                # Validate data length (CAN: 0-8 bytes, CAN-FD: 0-64 bytes)
                max_length = 64 if fd else 8
                if len(data_bytes) > max_length:
                    print(f"[WARNING] Data length {len(data_bytes)} exceeds maximum {max_length}, truncating")
                    data_bytes = data_bytes[:max_length]
                    
            except Exception as e:
                error_msg = f"Data conversion error: {e}"
                print(f"[ERROR] {error_msg}")
                self.error_occurred.emit(error_msg)
                return False
            
            # Create CAN message with validated parameters
            try:
                msg = can.Message(
                    arbitration_id=message_id,
                    data=data_bytes,
                    is_extended_id=bool(extended_id),
                    is_fd=bool(fd)
                )
                
                # Send the message
                self.bus.send(msg)
                
                # Create hex string for logging
                hex_data = ' '.join(f'{b:02X}' for b in data_bytes) if data_bytes else '(no data)'
                print(f"[DEBUG] Sent CAN message: ID=0x{message_id:X}, DLC={len(data_bytes)}, Data={hex_data}, Extended={extended_id}, FD={fd}")
                
                return True
                
            except Exception as e:
                error_msg = f"Failed to create or send CAN message: {e}"
                print(f"[ERROR] {error_msg}")
                self.error_occurred.emit(error_msg)
                return False
            
        except Exception as e:
            error_msg = f"Unexpected error in send_message: {e}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            return False

    def register_isotp_stack(self, tx_id, rx_id, isotp_stack):
        """Register an ISOTP stack for specific CAN IDs with Windows-safe handling"""
        try:
            # Windows-safe ID validation and conversion
            try:
                tx_id_int = int(tx_id, 16) if isinstance(tx_id, str) else int(tx_id)
                rx_id_int = int(rx_id, 16) if isinstance(rx_id, str) else int(rx_id)
                
                # Validate CAN ID ranges
                if not (0 <= tx_id_int <= 0x1FFFFFFF):
                    print(f"[ERROR] Invalid TX CAN ID for ISOTP: 0x{tx_id_int:X}")
                    return False
                if not (0 <= rx_id_int <= 0x1FFFFFFF):
                    print(f"[ERROR] Invalid RX CAN ID for ISOTP: 0x{rx_id_int:X}")
                    return False
                    
            except (ValueError, TypeError) as e:
                print(f"[ERROR] ISOTP ID conversion error: {e}")
                return False
            
            # Windows-safe stack key generation
            stack_key = f"{tx_id_int:X}_{rx_id_int:X}"
            
            # Thread-safe stack registration
            try:
                with self.isotp_stacks_lock:
                    if stack_key in self.isotp_stacks:
                        print(f"[WARNING] ISOTP stack already registered for {stack_key}, replacing")
                    
                    self.isotp_stacks[stack_key] = isotp_stack
                    print(f"[DEBUG] ISOTP stack registered: TX=0x{tx_id_int:X}, RX=0x{rx_id_int:X}")
                    return True
                    
            except Exception as e:
                print(f"[ERROR] ISOTP stack registration error: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR] ISOTP registration error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unregister_isotp_stack(self, tx_id, rx_id):
        """Unregister an ISOTP stack with Windows-safe handling"""
        try:
            print(f"[DEBUG] Attempting to unregister ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
            
            # Windows-safe threading lock
            with self.isotp_stacks_lock:
                # Windows-safe key generation with proper formatting
                key = f"{tx_id:03X}_{rx_id:03X}"
                
                if key in self.isotp_stacks:
                    stack = self.isotp_stacks[key]
                    
                    # Windows-safe stack cleanup
                    if hasattr(stack, 'stop'):
                        try:
                            stack.stop()
                            print(f"[DEBUG] Stopped ISOTP stack for TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                        except Exception as e:
                            print(f"[WARNING] Error stopping ISOTP stack: {e}")
                    
                    # Additional cleanup methods for Windows compatibility
                    cleanup_methods = ['reset', 'close', 'shutdown']
                    for method_name in cleanup_methods:
                        if hasattr(stack, method_name):
                            try:
                                method = getattr(stack, method_name)
                                if callable(method):
                                    method()
                                    print(f"[DEBUG] Called {method_name} on ISOTP stack")
                                    break  # Only call one cleanup method
                            except Exception as e:
                                print(f"[WARNING] Error calling {method_name} on ISOTP stack: {e}")
                    
                    # Remove from registry with Windows-safe error handling
                    try:
                        del self.isotp_stacks[key]
                        print(f"[DEBUG] Successfully unregistered ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                        return True
                    except Exception as e:
                        print(f"[ERROR] Error removing ISOTP stack from registry: {e}")
                        return False
                        
                else:
                    print(f"[DEBUG] No ISOTP stack found for TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] ISOTP unregistration error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_isotp_messages(self, msg_info):
        """Process incoming CAN messages for ISOTP stacks with Windows-safe handling"""
        try:
            # Windows-safe message ID extraction
            try:
                msg_id = int(msg_info.get('id', 0))
                if msg_id <= 0:
                    return  # Invalid message ID
            except (ValueError, TypeError):
                print(f"[WARNING] Invalid ISOTP message ID: {msg_info.get('id', 'None')}")
                return
            
            print(f"[DEBUG] Processing CAN message for ISOTP: ID=0x{msg_id:X}, Data={msg_info.get('data', [])}")
            
            # Windows-safe ISOTP stack iteration
            isotp_stacks_copy = {}
            try:
                with self.isotp_stacks_lock:
                    isotp_stacks_copy = self.isotp_stacks.copy()
            except Exception as e:
                print(f"[DEBUG] Error copying ISOTP stacks: {e}")
                return
            
            # Check if this message is for any registered ISOTP stack
            for key, isotp_stack in isotp_stacks_copy.items():
                try:
                    # Windows-safe key parsing
                    key_parts = str(key).split('_')
                    if len(key_parts) != 2:
                        print(f"[WARNING] Invalid ISOTP stack key format: {key}")
                        continue
                        
                    try:
                        tx_id = int(key_parts[0], 16)
                        rx_id = int(key_parts[1], 16)
                    except (ValueError, TypeError) as e:
                        print(f"[WARNING] Invalid ISOTP stack IDs in key {key}: {e}")
                        continue
                    
                    print(f"[DEBUG] Checking ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                    
                    # For UDS: We send on TX_ID and receive responses on RX_ID
                    # The ECU sends responses to our RX_ID (which is their TX_ID)
                    if msg_id == rx_id:
                        print(f"[DEBUG] Message matches ISOTP stack RX ID: 0x{rx_id:X}")
                        try:
                            # Windows-safe data conversion for ISOTP
                            message_data = msg_info.get('data', [])
                            if not isinstance(message_data, (list, tuple)):
                                print(f"[WARNING] Invalid ISOTP message data type: {type(message_data)}")
                                continue
                            
                            # Create CAN message for ISOTP processing with Windows-safe data
                            try:
                                data_bytes = bytearray()
                                for byte_val in message_data:
                                    data_bytes.append(int(byte_val) & 0xFF)
                            except (ValueError, TypeError) as e:
                                print(f"[WARNING] ISOTP data conversion error: {e}")
                                continue
                            
                            can_msg = can.Message(
                                arbitration_id=msg_id,
                                data=data_bytes,
                                is_extended_id=bool(msg_info.get('extended', False)),
                                is_fd=bool(msg_info.get('fd', False))
                            )
                            
                            print(f"[DEBUG] Created CAN message for ISOTP: ID=0x{can_msg.arbitration_id:X}, Data={list(can_msg.data)}")
                            
                            # Process with ISOTP stack (Windows-safe)
                            if hasattr(isotp_stack, '_process_rx'):
                                isotp_stack._process_rx(can_msg)
                                print(f"[DEBUG] ISOTP stack processed message")
                                
                                # Check if ISOTP has a complete message (Windows-safe)
                                if hasattr(isotp_stack, 'available') and isotp_stack.available():
                                    if hasattr(isotp_stack, 'recv'):
                                        isotp_data = isotp_stack.recv()
                                        if isotp_data:
                                            # Windows-safe ISOTP data conversion
                                            try:
                                                isotp_data_list = []
                                                for byte_val in isotp_data:
                                                    isotp_data_list.append(int(byte_val) & 0xFF)
                                            except (ValueError, TypeError):
                                                isotp_data_list = list(isotp_data)
                                            
                                            isotp_msg_info = {
                                                'timestamp': float(msg_info.get('timestamp', time.time())),
                                                'tx_id': tx_id,
                                                'rx_id': rx_id,
                                                'data': isotp_data_list,
                                                'raw_can_msg': msg_info
                                            }
                                            print(f"[DEBUG] ISOTP complete message: TX=0x{tx_id:X}, RX=0x{rx_id:X}, Data={isotp_data_list}")
                                            self.isotp_message_received.emit(isotp_msg_info)
                                        else:
                                            print(f"[DEBUG] ISOTP stack available but no data received")
                                    else:
                                        print(f"[DEBUG] ISOTP stack has no recv method")
                                else:
                                    print(f"[DEBUG] ISOTP stack not ready (partial message)")
                            else:
                                print(f"[DEBUG] ISOTP stack has no _process_rx method")
                                
                        except Exception as e:
                            print(f"[ERROR] ISOTP processing error for {key}: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"[DEBUG] Message ID 0x{msg_id:X} doesn't match ISOTP RX ID 0x{rx_id:X}")
                        
                except Exception as e:
                    print(f"[ERROR] Error processing ISOTP stack {key}: {e}")
                    continue
                        
        except Exception as e:
            print(f"[ERROR] ISOTP message processing error: {e}")
            import traceback
            traceback.print_exc()

    def _async_recv_loop(self):
        """Async background thread to receive CAN messages and queue them."""
        print("[DEBUG] Starting async CAN receive loop")
        
        while self.running and self.bus:
            try:
                # Receive message with timeout
                msg = self.bus.recv(timeout=0.1)
                if msg and self.running:
                    # Windows-safe timestamp handling
                    try:
                        # Try to get message timestamp, fallback to system time
                        if hasattr(msg, 'timestamp') and msg.timestamp is not None:
                            timestamp = float(msg.timestamp)
                        else:
                            timestamp = time.time()
                    except (ValueError, TypeError, AttributeError):
                        # Fallback for Windows compatibility
                        timestamp = time.time()
                    
                    # Windows-safe data conversion
                    try:
                        # Ensure data is properly converted to list for JSON serialization
                        data_list = []
                        if hasattr(msg, 'data') and msg.data is not None:
                            for byte in msg.data:
                                data_list.append(int(byte) & 0xFF)  # Ensure valid byte values
                        dlc = len(data_list)
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"[WARNING] Data conversion error: {e}")
                        data_list = []
                        dlc = 0
                    
                    # Windows-safe arbitration ID handling
                    try:
                        arbitration_id = int(msg.arbitration_id) & 0x1FFFFFFF  # Mask to valid CAN ID range
                    except (ValueError, TypeError, AttributeError):
                        print(f"[WARNING] Invalid arbitration ID: {getattr(msg, 'arbitration_id', 'None')}")
                        continue  # Skip this message
                    
                    # Create message info dictionary with Windows-safe values
                    msg_info = {
                        'timestamp': timestamp,
                        'id': arbitration_id,
                        'dlc': dlc,
                        'data': data_list,
                        'extended': bool(getattr(msg, 'is_extended_id', False)),
                        'fd': bool(getattr(msg, 'is_fd', False)),
                        'direction': 'RX',
                        'channel': str(self.interface) if self.interface else 'unknown'
                    }
                    
                    # Queue the message for processing
                    try:
                        self.message_queue.put_nowait(msg_info)
                    except queue.Full:
                        print("[WARNING] Message queue full, dropping message")
                    
            except can.CanTimeoutError:
                # Normal timeout, continue
                continue
            except can.CanError as e:
                if self.running:  # Only report errors if we're supposed to be running
                    print(f"[ERROR] CAN error in receive loop: {e}")
                    self.error_occurred.emit(f"CAN error: {str(e)}")
                break
            except Exception as e:
                # Check for common disconnect errors that we can ignore
                error_str = str(e).lower()
                if any(phrase in error_str for phrase in ['bad file descriptor', 'network is down', 'no such device', 'access denied', 'device not found']):
                    if self.running:
                        print(f"[DEBUG] Interface disconnected: {e}")
                    break
                else:
                    if self.running:
                        print(f"[ERROR] Unexpected error in receive loop: {e}")
                        self.error_occurred.emit(f"Receive error: {str(e)}")
                    break
        
        print("[DEBUG] Async CAN receive loop ended")

    def _process_messages(self):
        """Background thread to process queued messages and emit signals."""
        print("[DEBUG] Starting message processing thread")
        
        while self.running:
            try:
                # Get message from queue with timeout
                msg_info = self.message_queue.get(timeout=0.1)
                
                # Process ISOTP messages first
                self._process_isotp_messages(msg_info)
                
                # Emit the message signal for general CAN processing
                self.message_received.emit(msg_info)
                
                # Mark task as done
                self.message_queue.task_done()
                time.sleep(0.001)  # Add small delay to prevent flooding

            except queue.Empty:
                # Timeout, continue loop
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Error processing message: {e}")
        
        print("[DEBUG] Message processing thread ended")

    def get_bus_state(self):
        """Get current bus state information."""
        if not self.bus or not self.is_connected:
            return None
            
        try:
            # Try to get bus state if supported
            state = self.bus.state
            return {
                'state': str(state),
                'interface': self.interface,
                'bitrate': self.bitrate
            }
        except Exception:
            return {
                'state': 'ACTIVE' if self.is_connected else 'DISCONNECTED',
                'interface': self.interface,
                'bitrate': self.bitrate
            }

    def create_virtual_interface(self, interface_name="vcan0"):
        """Create a virtual CAN interface for testing (Linux only)."""
        if platform.system() != "Linux":
            print("[WARNING] Virtual CAN interfaces only supported on Linux")
            return False
            
        try:
            # Load vcan module
            subprocess.run(['sudo', 'modprobe', 'vcan'], 
                         capture_output=True, timeout=5)
            
            # Create virtual interface
            subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', interface_name, 'type', 'vcan'], 
                         capture_output=True, timeout=5)
            
            # Bring interface up
            subprocess.run(['sudo', 'ip', 'link', 'set', 'up', interface_name], 
                         capture_output=True, timeout=5)
            
            print(f"[DEBUG] Created virtual CAN interface: {interface_name}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to create virtual interface {interface_name}: {e}")
            return False

    def remove_virtual_interface(self, interface_name="vcan0"):
        """Remove a virtual CAN interface (Linux only)."""
        if platform.system() != "Linux":
            return False
            
        try:
            subprocess.run(['sudo', 'ip', 'link', 'delete', interface_name], 
                         capture_output=True, timeout=5)
            print(f"[DEBUG] Removed virtual CAN interface: {interface_name}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to remove virtual interface {interface_name}: {e}")
            return False

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.is_connected:
            self.disconnect()
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)