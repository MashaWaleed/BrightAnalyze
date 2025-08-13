"""
Fixed UDS Backend for Professional CAN Analyzer
Resolves ISOTP message processing and UDS response reliability issues
"""

from PySide6.QtCore import QObject, Signal, QTimer
import udsoncan
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection
from udsoncan import services
import isotp
import time
import threading
import time
import traceback
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import queue
import can
import copy


@dataclass
class UDSSessionInfo:
    session_type: int
    name: str
    active: bool = False


@dataclass 
class SecurityAccessInfo:
    level: int
    seed: Optional[bytes] = None
    key: Optional[bytes] = None
    unlocked: bool = False


class DirectCANBus(can.BusABC):
    """Direct CAN bus wrapper that integrates properly with ISOTP"""
    
    def __init__(self, can_manager):
        self.can_manager = can_manager
        self.original_bus = can_manager.bus
        
        # Initialize BusABC
        channel = getattr(can_manager.bus, 'channel', 'direct')
        super().__init__(channel=channel)
        
        # Message queue for ISOTP
        self._isotp_rx_queue = queue.Queue(maxsize=500)
        self._isotp_registered = False
        
    def _log_tx_message(self, msg):
        """Log transmitted CAN message to message log"""
        try:
            # Create message info dictionary in the same format as CAN backend
            msg_info = {
                'timestamp': time.time(),
                'id': msg.arbitration_id,
                'dlc': len(msg.data),
                'data': list(msg.data),
                'extended': msg.is_extended_id,
                'fd': getattr(msg, 'is_fd', False),
                'direction': 'TX',  # Mark as transmitted message
                'channel': 'UDS'    # Mark as UDS channel
            }
            
            # Emit the TX message through the signal
            if hasattr(self.can_manager, 'message_received'):
                self.can_manager.message_received.emit(msg_info)
            
            # Convert data to hex string for debug
            hex_data = ' '.join([f'{b:02X}' for b in msg.data])
            print(f"[DEBUG] TX Message logged: [TX] {msg.arbitration_id:03X}: {hex_data}")
            
        except Exception as e:
            print(f"[ERROR] Failed to log TX message: {e}")

    def send(self, msg, timeout=None):
        """Send message through CAN manager and log TX message"""
        try:
            # Send the message first
            result = self.original_bus.send(msg, timeout)
            
            # Log the TX message to the message log
            self._log_tx_message(msg)
            
            return result
        except Exception as e:
            print(f"[ERROR] DirectCANBus send failed: {e}")
            raise
    
    def recv(self, timeout=None):
        """Receive message from ISOTP queue"""
        try:
            # Get message from our dedicated queue
            return self._isotp_rx_queue.get(timeout=timeout or 0.1)
        except queue.Empty:
            return None
    
    def _feed_isotp_message(self, can_msg):
        """Feed a CAN message to ISOTP processing"""
        try:
            self._isotp_rx_queue.put_nowait(can_msg)
        except queue.Full:
            print("[WARNING] ISOTP RX queue full, dropping message")
    
    def shutdown(self):
        """Shutdown - clear queue"""
        while not self._isotp_rx_queue.empty():
            try:
                self._isotp_rx_queue.get_nowait()
            except queue.Empty:
                break
    
    # Delegate other methods to original bus
    def set_filters(self, can_filters=None):
        if self.original_bus:
            return self.original_bus.set_filters(can_filters)
    
    def flush_tx_buffer(self):
        if self.original_bus:
            return self.original_bus.flush_tx_buffer()
    
    def get_stats(self):
        if self.original_bus:
            return self.original_bus.get_stats()
        return {}
    
    @property
    def state(self):
        if self.original_bus:
            return self.original_bus.state
        return None


class SimpleUDSBackend(QObject):
    """Fixed UDS Backend with reliable ISOTP processing"""
    
    # Signals
    uds_response_received = Signal(dict)  # {service, success, data, error}
    uds_error_occurred = Signal(str)
    session_changed = Signal(dict)  # {session_type, name}
    security_status_changed = Signal(dict)  # {level, unlocked, seed}
    dtc_data_received = Signal(list)  # List of DTCs
    data_identifier_received = Signal(dict)  # {did, data, decoded}
    
    def __init__(self, can_manager, tx_id=0x7E0, rx_id=0x7E8, parent=None):
        super().__init__(parent)
        self.can_manager = can_manager
        self.tx_id = tx_id
        self.rx_id = rx_id
        
        # UDS Components
        self.isotp_stack = None
        self.uds_connection = None
        self.uds_client = None
        self.direct_can_bus = None
        
        # State tracking
        self.current_session = UDSSessionInfo(0x01, "Default Session", True)
        self.security_access = SecurityAccessInfo(0)
        self.is_connected = False
        
        # Thread safety
        self._connection_lock = threading.RLock()
        self._state_lock = threading.RLock()
        
        # Request processing
        self.uds_message_queue = queue.PriorityQueue(maxsize=50)
        self.uds_processing_thread = None
        self._stop_processing = threading.Event()
        self._request_counter = 0
        self._pending_requests = {}
        
        # Setup client configuration
        self.setup_client_config()
        
        # CAN message handler registration
        self._can_filter_registered = False
        
        print(f"[DEBUG] UDS Backend initialized: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
    
    def setup_client_config(self):
        """Setup UDS client configuration with fixed defaults"""
        self.base_client_config = {
            'request_timeout': 5.0,           # Longer timeout for reliability
            'p2_timeout': 5.0,               # P2 timeout for ECU processing (5 seconds)
            'p2_star_timeout': 25.0,         # Extended P2 timeout (25 seconds)
            'exception_on_negative_response': False,
            'exception_on_invalid_response': False,
            'tolerate_zero_padding': True,
            'ignore_all_zero_dtc': True,
            'dtc_snapshot_did_size': 2,
        }
        
        self.client_config = copy.deepcopy(self.base_client_config)
        
        print("[DEBUG] UDS client config initialized:")
        print(f"[DEBUG] - Request timeout: {self.client_config['request_timeout']}s")
        print(f"[DEBUG] - P2 timeout: {self.client_config['p2_timeout']}s")
        print(f"[DEBUG] - P2* timeout: {self.client_config['p2_star_timeout']}s")
        
        # Define common Data Identifiers with proper codec configuration
        # Using raw codecs to avoid decoding issues
        self.client_config['data_identifiers'] = {
            0xF010: udsoncan.DidCodec(udsoncan.AsciiCodec(20)),   # Active Diagnostic Session
            0xF011: udsoncan.DidCodec(udsoncan.AsciiCodec(50)),   # ECU Software Number (increased size)
            0xF012: udsoncan.DidCodec(udsoncan.AsciiCodec(50)),   # ECU Software Version (increased size)
            0xF018: udsoncan.DidCodec(udsoncan.AsciiCodec(50)),   # Application Software Fingerprint (increased size)
            0xF030: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Vehicle Speed (raw bytes)
            0xF031: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Engine RPM (raw bytes)
            0xF032: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Engine Temperature (raw bytes)
            0xF186: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Current Session (raw bytes)
            0xF187: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Supplier Identifier (raw bytes)
            0xF190: udsoncan.DidCodec(udsoncan.AsciiCodec(20)),   # VIN
            # Add more DIDs that might be requested
            0xF040: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Generic DID
            0xF050: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Generic DID
            0xF041: udsoncan.DidCodec(udsoncan.DidCodec(8)),      # Generic DID
        }

    def connect(self) -> bool:
        """Initialize UDS connection with proper ISOTP handling and dynamic DID support"""
        try:
            with self._connection_lock:
                print("[DEBUG] Starting UDS connection")
                
                if not self.can_manager or not self.can_manager.is_connected:
                    error_msg = "CAN bus not connected"
                    print(f"[ERROR] {error_msg}")
                    self.uds_error_occurred.emit(error_msg)
                    return False

                # Disconnect if already connected
                if self.is_connected:
                    print("[DEBUG] Already connected, disconnecting first")
                    self._disconnect_internal()

                print(f"[DEBUG] Connecting UDS: TX=0x{self.tx_id:X}, RX=0x{self.rx_id:X}")

                # Reset client config
                self.client_config = copy.deepcopy(self.base_client_config)

                # Create direct CAN bus wrapper
                self.direct_can_bus = DirectCANBus(self.can_manager)
                
                # Create ISOTP address
                isotp_address = isotp.Address(
                    addressing_mode=isotp.AddressingMode.Normal_11bits,
                    txid=self.tx_id,
                    rxid=self.rx_id
                )
                
                # ISOTP parameters - conservative settings
                isotp_params = {
                    'stmin': 0x00,                    # Separation time minimum
                    'blocksize': 0x08,                # Block size (8 frames before flow control)
                    'wftmax': 0x00,                   # Wait frame max
                    'tx_padding': 0xAA,               # Padding byte
                    'rx_flowcontrol_timeout': 1000,   # Flow control timeout (ms)
                    'rx_consecutive_frame_timeout': 1000,  # Consecutive frame timeout (ms)
                }
                
                # Create ISOTP stack
                self.isotp_stack = isotp.CanStack(
                    bus=self.direct_can_bus,
                    address=isotp_address,
                    params=isotp_params
                )
                
                # Reset ISOTP stack
                if self.isotp_stack:
                    try:
                        self.isotp_stack.reset()
                        print("[DEBUG] ISOTP stack reset")
                    except Exception as e:
                        print(f"[WARNING] Could not reset ISOTP stack: {e}")
                
                print("[DEBUG] ISOTP stack created")
                
                # Register for CAN message filtering
                self._register_can_message_handler()
                
                # Create UDS connection and client
                self.uds_connection = PythonIsoTpConnection(self.isotp_stack)

                # Create client with enhanced config that allows dynamic DID addition
                client_config = copy.deepcopy(self.client_config)
                self.uds_client = Client(conn=self.uds_connection, config=client_config)
                
                # FORCE timeout configuration after client creation - this is critical!
                # The udsoncan library might override our config with defaults
                print(f"[DEBUG] Forcing timeout configuration after client creation")
                self.uds_client.config['request_timeout'] = self.client_config['request_timeout']
                self.uds_client.config['p2_timeout'] = self.client_config['p2_timeout']
                self.uds_client.config['p2_star_timeout'] = self.client_config['p2_star_timeout']
                print(f"[DEBUG] FORCED UDS timeouts: req={self.uds_client.config['request_timeout']}s, p2={self.uds_client.config['p2_timeout']}s, p2*={self.uds_client.config['p2_star_timeout']}s")
                
                # Enable dynamic DID addition - access config as dictionary
                if 'data_identifiers' not in self.uds_client.config:
                    self.uds_client.config['data_identifiers'] = {}
                
                # Add our predefined DIDs to the client config
                for did, codec in self.client_config.get('data_identifiers', {}).items():
                    self.uds_client.config['data_identifiers'][did] = codec
                    print(f"[DEBUG] Added DID 0x{did:04X} to client config")

                # Open the connection
                self.uds_connection.open()
                print("[DEBUG] UDS connection opened")
                
                # Start processing thread
                self._stop_processing.clear()
                self.uds_processing_thread = threading.Thread(
                    target=self._process_uds_messages, 
                    daemon=True, 
                    name="UDS-Processor"
                )
                self.uds_processing_thread.start()
                
                self.is_connected = True
                print("[DEBUG] UDS connected successfully")
                
                return True
                
        except Exception as e:
            error_msg = f"UDS connection failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            self.uds_error_occurred.emit(error_msg)
            return False

    def _register_can_message_handler(self):
        """Register to receive CAN messages for our ISOTP processing"""
        if not self._can_filter_registered:
            self.can_manager.message_received.connect(self._handle_can_message)
            self._can_filter_registered = True
            print(f"[DEBUG] Registered CAN message handler for RX ID 0x{self.rx_id:X}")

    def _unregister_can_message_handler(self):
        """Unregister CAN message handler"""
        if self._can_filter_registered:
            try:
                self.can_manager.message_received.disconnect(self._handle_can_message)
                self._can_filter_registered = False
                print("[DEBUG] Unregistered CAN message handler")
            except:
                pass

    # In SimpleUDSBackend._handle_can_message
    def _handle_can_message(self, msg_info):
        try:
            msg_id = msg_info['id']
            
            # Only process messages for our RX ID (ECU responses)
            if msg_id == self.rx_id and self.is_connected and self.direct_can_bus:
                # Only process messages with data (ignore empty frames)
                if len(msg_info['data']) == 0:
                    return
                    
                print(f"[DEBUG] UDS RX: ID=0x{msg_id:X}, Data={msg_info['data']}")
                
                # Create CAN message for ISOTP
                can_msg = can.Message(
                    arbitration_id=msg_id,
                    data=bytearray(msg_info['data']),
                    is_extended_id=msg_info.get('extended', False),
                    is_fd=msg_info.get('fd', False),
                    timestamp=msg_info.get('timestamp', time.time())
                )
                
                # Feed to ISOTP processing
                self.direct_can_bus._feed_isotp_message(can_msg)
                
        except Exception as e:
            print(f"[ERROR] CAN message handling error: {e}")

    def disconnect(self):
        """Public disconnect method"""
        with self._connection_lock:
            self._disconnect_internal()

    def _disconnect_internal(self):
        """Internal disconnect method"""
        try:
            print("[DEBUG] Disconnecting UDS...")
            
            self.is_connected = False
            self._stop_processing.set()
            
            # Stop processing thread
            if self.uds_processing_thread and self.uds_processing_thread.is_alive():
                print("[DEBUG] Stopping UDS processing thread...")
                self.uds_processing_thread.join(timeout=2.0)
            
            # Clear message queue
            queue_cleared = 0
            while True:
                try:
                    self.uds_message_queue.get_nowait()
                    queue_cleared += 1
                    if queue_cleared > 100:
                        break
                except queue.Empty:
                    break
            if queue_cleared > 0:
                print(f"[DEBUG] Cleared {queue_cleared} queued messages")
            
            self._pending_requests.clear()
            self._request_counter = 0
            
            # Unregister CAN message handler
            self._unregister_can_message_handler()
            
            # Close UDS connection
            if self.uds_connection:
                try:
                    if hasattr(self.uds_connection, 'is_open') and self.uds_connection.is_open():
                        self.uds_connection.close()
                        print("[DEBUG] UDS connection closed")
                except Exception as e:
                    print(f"[DEBUG] Error closing UDS connection: {e}")
                self.uds_connection = None
            
            # Stop ISOTP stack
            if self.isotp_stack:
                try:
                    self.isotp_stack.stop()
                    print("[DEBUG] ISOTP stack stopped")
                except Exception as e:
                    print(f"[DEBUG] Error stopping ISOTP stack: {e}")
                self.isotp_stack = None
            
            # Shutdown direct CAN bus
            if self.direct_can_bus:
                try:
                    self.direct_can_bus.shutdown()
                except Exception as e:
                    print(f"[DEBUG] Error shutting down direct CAN bus: {e}")
                self.direct_can_bus = None
            
            self.uds_client = None
            print("[DEBUG] UDS disconnected")
            
        except Exception as e:
            print(f"[ERROR] UDS disconnect error: {e}")

    def _process_uds_messages(self):
        """Background thread to process UDS messages"""
        print("[DEBUG] Starting UDS message processing thread")
        messages_processed = 0
        errors_encountered = 0
        
        while not self._stop_processing.is_set():
            try:
                try:
                    priority, timestamp, request_id, item = self.uds_message_queue.get(timeout=0.5)
                    messages_processed += 1
                    
                    if request_id in self._pending_requests:
                        del self._pending_requests[request_id]
                        
                        print(f"[DEBUG] Processing UDS request: {item.get('service', 'unknown')}")
                        with self._state_lock:
                            success = self._execute_uds_request_internal(item)
                            if not success:
                                errors_encountered += 1
                    else:
                        print(f"[DEBUG] Skipping expired request {request_id}")
                        
                    self.uds_message_queue.task_done()
                    
                except queue.Empty:
                    continue
                    
            except Exception as e:
                if not self._stop_processing.is_set():
                    errors_encountered += 1
                    print(f"[ERROR] UDS message processing error: {e}")
                    time.sleep(0.1)
        
        print(f"[DEBUG] UDS processing thread ended. Processed: {messages_processed}, Errors: {errors_encountered}")

    def _adjust_timeouts_for_session(self, session_type: int):
        """Adjust timeouts based on session type"""
        if session_type == 0x01:  # Default Session
            # Default session may need longer timeouts
            self.client_config['request_timeout'] = 6.0
            self.client_config['p2_timeout'] = 6.0
            self.client_config['p2_star_timeout'] = 30.0
            print("[DEBUG] Adjusted timeouts for Default Session (longer)")
        elif session_type == 0x03:  # Extended Diagnostic Session
            # Extended session typically has shorter response times
            self.client_config['request_timeout'] = 4.0
            self.client_config['p2_timeout'] = 4.0
            self.client_config['p2_star_timeout'] = 20.0
            print("[DEBUG] Adjusted timeouts for Extended Session (shorter)")
        else:
            # Other sessions use base timeouts
            self.client_config['request_timeout'] = self.base_client_config['request_timeout']
            self.client_config['p2_timeout'] = self.base_client_config['p2_timeout']
            self.client_config['p2_star_timeout'] = self.base_client_config['p2_star_timeout']
            print(f"[DEBUG] Using base timeouts for session 0x{session_type:02X}")
        
        # Update the UDS client config if it exists
        if self.uds_client and hasattr(self.uds_client, 'config'):
            print(f"[DEBUG] BEFORE timeout update - UDS client config:")
            try:
                print(f"[DEBUG] - Current request_timeout: {self.uds_client.config.get('request_timeout', 'NOT_SET')}")
                print(f"[DEBUG] - Current p2_timeout: {self.uds_client.config.get('p2_timeout', 'NOT_SET')}")
                print(f"[DEBUG] - Current p2_star_timeout: {self.uds_client.config.get('p2_star_timeout', 'NOT_SET')}")
            except:
                print(f"[DEBUG] - Could not read current timeout values")
                
            # Handle both dict and object-style config access
            if hasattr(self.uds_client.config, 'request_timeout'):
                # Object-style access
                self.uds_client.config.request_timeout = self.client_config['request_timeout']
                self.uds_client.config.p2_timeout = self.client_config['p2_timeout']
                self.uds_client.config.p2_star_timeout = self.client_config['p2_star_timeout']
                print(f"[DEBUG] Updated timeouts using OBJECT-style access")
            else:
                # Dictionary-style access
                self.uds_client.config['request_timeout'] = self.client_config['request_timeout']
                self.uds_client.config['p2_timeout'] = self.client_config['p2_timeout']
                self.uds_client.config['p2_star_timeout'] = self.client_config['p2_star_timeout']
                print(f"[DEBUG] Updated timeouts using DICTIONARY-style access")
                
            # ALSO update the connection timeout if it exists
            if hasattr(self.uds_client, 'conn') and self.uds_client.conn:
                if hasattr(self.uds_client.conn, 'timeout'):
                    self.uds_client.conn.timeout = self.client_config['request_timeout']
                    print(f"[DEBUG] Updated connection timeout to {self.client_config['request_timeout']}s")
                if hasattr(self.uds_client.conn, 'p2_timeout'):
                    self.uds_client.conn.p2_timeout = self.client_config['p2_timeout']
                    print(f"[DEBUG] Updated connection p2_timeout to {self.client_config['p2_timeout']}s")
                    
            print(f"[DEBUG] AFTER timeout update - Requested timeouts: req={self.client_config['request_timeout']}s, p2={self.client_config['p2_timeout']}s, p2*={self.client_config['p2_star_timeout']}s")
            
            # Verify the update worked
            try:
                actual_req = self.uds_client.config.get('request_timeout', 'NOT_SET')
                actual_p2 = self.uds_client.config.get('p2_timeout', 'NOT_SET')
                actual_p2_star = self.uds_client.config.get('p2_star_timeout', 'NOT_SET')
                print(f"[DEBUG] VERIFICATION - Actual timeouts now: req={actual_req}s, p2={actual_p2}s, p2*={actual_p2_star}s")
            except:
                print(f"[DEBUG] Could not verify timeout update")

    def diagnostic_session_control(self, session_type: int) -> bool:
        """Change diagnostic session"""
        def _callback(response):
            try:
                session_names = {
                    0x01: "Default Session",
                    0x02: "Programming Session", 
                    0x03: "Extended Diagnostic Session",
                    0x40: "EOL Session"
                }

                response_data = response.data if hasattr(response, 'data') else b''
                
                self.current_session = UDSSessionInfo(
                    session_type, 
                    session_names.get(session_type, f"Session 0x{session_type:02X}"),
                    True
                )
                
                # Adjust timeouts based on new session
                self._adjust_timeouts_for_session(session_type)
                
                result = {
                    'service': 'diagnostic_session_control',
                    'success': True,
                    'data': response_data,
                    'session_type': session_type,
                    'session_name': self.current_session.name,
                    'session_params': response_data[2:] if len(response_data) > 2 else b''
                }
                
                self.uds_response_received.emit(result)
                self.session_changed.emit({
                    'session_type': session_type,
                    'name': self.current_session.name
                })
                
            except Exception as e:
                error_msg = f"Session control callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        return self._queue_uds_request(
            self.uds_client.change_session,
            _callback,
            session_type,
            priority=0
        )

    def _execute_uds_request_internal(self, request):
        """Execute UDS request with better error handling"""
        try:
            if not self.is_connected or not self.uds_client:
                return False
            
            # Reset ISOTP stack to clear any residual state
            with self._state_lock:
                if self.isotp_stack:
                    try:
                        self.isotp_stack.reset()
                        print("[DEBUG] ISOTP stack reset before request")
                    except Exception as e:
                        print(f"[WARNING] ISOTP reset error: {e}")
            
            # Ensure connection is open
            if not self.uds_connection or not self.uds_connection.is_open():
                if self.uds_connection:
                    self.uds_connection.open()
                else:
                    raise RuntimeError("UDS connection is None")
            
            # Log active timeouts
            print(f"[DEBUG] Active timeouts: "
                f"request={self.client_config['request_timeout']}, "
                f"p2={self.client_config['p2_timeout']}, "
                f"p2_star={self.client_config['p2_star_timeout']}")
            
            # FORCE timeout configuration before each request - critical fix!
            if self.uds_client and hasattr(self.uds_client, 'config'):
                self.uds_client.config['request_timeout'] = self.client_config['request_timeout']
                self.uds_client.config['p2_timeout'] = self.client_config['p2_timeout']
                self.uds_client.config['p2_star_timeout'] = self.client_config['p2_star_timeout']
                print(f"[DEBUG] FORCE-SET timeouts before request execution: p2={self.client_config['p2_timeout']}s")
                
                # ADDITIONAL FORCE: Update connection-level timeouts if they exist
                if hasattr(self.uds_client, 'conn') and self.uds_client.conn:
                    # Try to force connection timeouts
                    if hasattr(self.uds_client.conn, '_timeout'):
                        self.uds_client.conn._timeout = self.client_config['request_timeout']
                        print(f"[DEBUG] FORCE-SET connection _timeout to {self.client_config['request_timeout']}s")
                    if hasattr(self.uds_client.conn, 'timeout'):
                        self.uds_client.conn.timeout = self.client_config['request_timeout'] 
                        print(f"[DEBUG] FORCE-SET connection timeout to {self.client_config['request_timeout']}s")
                    # Try to access internal ISOTP stack timeouts
                    if hasattr(self.uds_client.conn, '_stack'):
                        stack = self.uds_client.conn._stack
                        if hasattr(stack, 'params'):
                            # Set ISOTP level timeouts to much higher values
                            if 'rx_flowcontrol_timeout' in stack.params:
                                stack.params['rx_flowcontrol_timeout'] = int(self.client_config['p2_timeout'] * 1000)
                                print(f"[DEBUG] FORCE-SET ISOTP rx_flowcontrol_timeout to {stack.params['rx_flowcontrol_timeout']}ms")
                            if 'rx_consecutive_frame_timeout' in stack.params:
                                stack.params['rx_consecutive_frame_timeout'] = int(self.client_config['p2_timeout'] * 1000)
                                print(f"[DEBUG] FORCE-SET ISOTP rx_consecutive_frame_timeout to {stack.params['rx_consecutive_frame_timeout']}ms")
                
                # NUCLEAR OPTION: Try to override any internal udsoncan defaults
                if hasattr(self.uds_client, 'logger'):
                    # Force set all timeout-related attributes we can find
                    for attr_name in dir(self.uds_client.config):
                        if 'timeout' in attr_name.lower():
                            try:
                                if attr_name == 'p2_timeout':
                                    setattr(self.uds_client.config, attr_name, self.client_config['p2_timeout'])
                                    print(f"[DEBUG] NUCLEAR-SET {attr_name} = {self.client_config['p2_timeout']}")
                                elif attr_name == 'request_timeout':
                                    setattr(self.uds_client.config, attr_name, self.client_config['request_timeout'])
                                    print(f"[DEBUG] NUCLEAR-SET {attr_name} = {self.client_config['request_timeout']}")
                            except:
                                pass
            
            # Execute request
            request_func = request['func']
            args = request.get('args', [])
            kwargs = request.get('kwargs', {})
            callback = request['callback']
            service_name = request.get('service', 'unknown')
            
            print(f"[DEBUG] Executing UDS: {service_name}")
            
            try:
                response = request_func(*args, **kwargs)
                print(f"[DEBUG] UDS {service_name} completed successfully, response type: {type(response)}")
                print(f"[DEBUG] Response content: {response.hex() if isinstance(response, bytes) else response}")
                
                # Safe callback execution with None check
                if callback and callable(callback):
                    try:
                        callback(response)
                    except Exception as cb_error:
                        print(f"[ERROR] Callback execution failed for {service_name}: {cb_error}")
                        import traceback
                        print(f"[ERROR] Callback traceback: {traceback.format_exc()}")
                        self.uds_error_occurred.emit(f"Callback error: {str(cb_error)}")
                else:
                    print(f"[WARNING] No valid callback for {service_name}")
                
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] UDS {service_name} failed: {error_msg}")
                import traceback
                print(f"[ERROR] Full traceback: {traceback.format_exc()}")
                
                # Handle specific error types with improved error recovery
                if "timeout" in error_msg.lower():
                    print("[DEBUG] Timeout occurred - recycling UDS connection")
                    try:
                        self._recycle_uds_connection()
                    except Exception as recycle_error:
                        print(f"[ERROR] Connection recycle failed: {recycle_error}")
                elif "negative response" in error_msg.lower():
                    print("[DEBUG] Negative response - may be expected")
                elif "bad file descriptor" in error_msg.lower():
                    print("[DEBUG] Bad file descriptor - forcing reconnection")
                    try:
                        self.disconnect()
                        time.sleep(0.2)
                        self.connect()
                    except Exception as reconnect_error:
                        print(f"[ERROR] Reconnection failed: {reconnect_error}")
                
                # Safe error callback execution
                if 'error_callback' in request and request['error_callback'] and callable(request['error_callback']):
                    try:
                        request['error_callback'](error_msg)
                    except Exception as err_cb_error:
                        print(f"[ERROR] Error callback failed: {err_cb_error}")
                        self.uds_error_occurred.emit(error_msg)
                else:
                    self.uds_error_occurred.emit(error_msg)
                return False
        
        except Exception as e:
            print(f"[ERROR] UDS request setup failed: {e}")
            self.uds_error_occurred.emit(str(e))
            return False
    # ADD NEW METHOD TO SimpleUDSBackend
    def _recycle_uds_connection(self):
        """Recreate UDS connection to reset internal state"""
        print("[DEBUG] Recycling UDS connection...")
        try:
            with self._connection_lock:
                # Save current configuration
                tx_id, rx_id = self.tx_id, self.rx_id
                config_backup = copy.deepcopy(self.client_config)
                
                # Disconnect and reconnect
                self._disconnect_internal()
                time.sleep(0.1)  # Brief pause for cleanup
                
                # Restore configuration
                self.tx_id = tx_id
                self.rx_id = rx_id
                self.client_config = config_backup
                
                # Reconnect
                if self.connect():
                    print("[DEBUG] UDS connection recycled successfully")
                else:
                    print("[ERROR] Failed to reconnect after recycling")
        except Exception as e:
            print(f"[ERROR] Connection recycling failed: {e}")
    
    def _disconnect_internal(self):
        """Internal disconnect without locks (for use within locked contexts)"""
        try:
            print("[DEBUG] Internal UDS disconnect...")
            
            # Set disconnected state first
            self.is_connected = False
            
            # Stop processing thread
            if hasattr(self, '_stop_processing'):
                self._stop_processing.set()
            
            # Clear message queue
            try:
                while not self.uds_message_queue.empty():
                    self.uds_message_queue.get_nowait()
                    self.uds_message_queue.task_done()
            except:
                pass
            
            # Disconnect from CAN manager
            if hasattr(self.can_manager, 'isotp_message_received'):
                try:
                    self.can_manager.isotp_message_received.disconnect(self._handle_isotp_message)
                except:
                    pass
            
            # Close UDS connection
            if self.uds_connection:
                try:
                    self.uds_connection.close()
                except:
                    pass
                self.uds_connection = None
            
            # Stop ISOTP stack
            if self.isotp_stack:
                try:
                    self.isotp_stack.stop()
                except:
                    pass
                self.isotp_stack = None
            
            # Clear client
            self.uds_client = None
            
            print("[DEBUG] Internal UDS disconnect completed")
            
        except Exception as e:
            print(f"[ERROR] Internal disconnect error: {e}")
    def _queue_uds_request(self, request_func, callback, *args, timeout=None, priority=1, error_callback=None, **kwargs):
        """Queue a UDS request for processing with error callback support"""
        if not self.is_connected:
            self.uds_error_occurred.emit("UDS not connected")
            return False
        
        # Validate callback
        if callback is None or not callable(callback):
            func_name = getattr(request_func, '__name__', 'lambda')
            print(f"[WARNING] Invalid callback provided for {func_name}")
            # Create a default callback to prevent None errors
            def _default_callback(response):
                print(f"[DEBUG] Default callback executed for {func_name}")
            callback = _default_callback
        
        self._request_counter += 1
        request_id = self._request_counter
        
        if timeout is None:
            timeout = self.base_client_config['request_timeout']
        
        timeout = max(0.5, min(timeout, 30.0))  # Clamp timeout
        
        # Get a proper service name for the request
        func_name = getattr(request_func, '__name__', 'lambda')
        if func_name == '<lambda>' or func_name == 'lambda':
            # For lambda functions, try to determine service from the stack
            import inspect
            try:
                frame = inspect.currentframe()
                caller_name = frame.f_back.f_code.co_name
                if 'read_data_by_identifier' in caller_name:
                    service_name = 'read_data_by_identifier'
                elif 'write_data_by_identifier' in caller_name:
                    service_name = 'write_data_by_identifier'
                elif 'read_dtc_information' in caller_name:
                    service_name = 'read_dtc_information'
                elif 'clear_diagnostic_information' in caller_name:
                    service_name = 'clear_diagnostic_information'
                elif 'security_access' in caller_name:
                    service_name = 'security_access'
                else:
                    service_name = f'lambda_from_{caller_name}'
            except:
                service_name = 'lambda_unknown'
        else:
            service_name = func_name
        
        request = {
            'func': request_func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback,
            'error_callback': error_callback,  # Add error callback support
            'timeout': timeout,
            'timestamp': time.time(),
            'service': service_name
        }
        
        try:
            self._pending_requests[request_id] = request
            queue_item = (priority, time.time(), request_id, request)
            
            print(f"[DEBUG] Queueing UDS request {request_id}: {request['service']}")
            self.uds_message_queue.put_nowait(queue_item)
            return True
            
        except queue.Full:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            self.uds_error_occurred.emit("UDS request queue full")
            return False

    # === UDS Service Methods ===
    
    def read_data_by_identifier(self, did: int) -> bool:
        """Read data by identifier with improved error handling"""
        def _callback(response):
            try:
                # Check if this is a udsoncan Response object
                if hasattr(response, 'data') and hasattr(response, 'service'):
                    # This is a proper udsoncan Response object
                    response_data = response.data
                    print(f"[DEBUG] DID 0x{did:04X} udsoncan response: service={response.service}, data={response_data.hex()}")
                    
                    # Even for udsoncan Response objects, we need to check if DID echo is included
                    # Some udsoncan versions include the DID echo in the data
                    if len(response_data) >= 2:
                        # Check if first 2 bytes match the DID (big endian)
                        did_bytes = did.to_bytes(2, 'big')
                        if response_data[:2] == did_bytes:
                            # Strip the DID echo
                            actual_data = response_data[2:]
                            print(f"[DEBUG] DID 0x{did:04X} stripped DID echo, actual data: {actual_data.hex()}")
                        else:
                            # No DID echo to strip
                            actual_data = response_data
                            print(f"[DEBUG] DID 0x{did:04X} no DID echo found, using full data: {actual_data.hex()}")
                    else:
                        # Data too short to contain DID echo
                        actual_data = response_data
                        print(f"[DEBUG] DID 0x{did:04X} data too short for DID echo: {actual_data.hex()}")
                elif isinstance(response, bytes):
                    # Raw bytes response - need to parse manually
                    response_data = response
                    # For DID read response, strip the service response byte (0x62) and DID echo
                    # Response format: [0x62][DID_HIGH][DID_LOW][DATA...]
                    if len(response_data) >= 3 and response_data[0] == 0x62:
                        # Extract just the data part (skip service byte + 2 DID bytes)
                        actual_data = response_data[3:]
                        print(f"[DEBUG] DID 0x{did:04X} raw response: service=0x{response_data[0]:02X}, data={actual_data.hex()}")
                    else:
                        actual_data = response_data
                        print(f"[DEBUG] DID 0x{did:04X} unexpected raw response format: {response_data.hex()}")
                else:
                    # Unknown response type - try to extract data
                    response_data = response.data if hasattr(response, 'data') else b''
                    actual_data = response_data
                    print(f"[DEBUG] DID 0x{did:04X} unknown response type: {type(response)}, data={response_data.hex()}")
                
                decoded_data = self._decode_did_response(did, actual_data)
                
                result = {
                    'service': 'read_data_by_identifier',
                    'success': True,
                    'data': actual_data,  # Use actual data without service headers
                    'did': did,
                    'decoded': decoded_data
                }
                
                self.uds_response_received.emit(result)
                self.data_identifier_received.emit({
                    'did': did,
                    'data': actual_data,
                    'decoded': decoded_data
                })
                
            except Exception as e:
                error_msg = f"Read DID callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        # Use raw request instead of read_data_by_identifier to avoid DID codec issues
        def _raw_did_request():
            # Build Read Data By Identifier request: Service 0x22 + DID (2 bytes)
            # Use services.ReadDataByIdentifier instead of raw integer
            from udsoncan import Request, services
            request = Request(service=services.ReadDataByIdentifier, data=did.to_bytes(2, 'big'))
            return self.uds_client.send_request(request)
        
        return self._queue_uds_request(
            _raw_did_request,
            _callback
        )

    def write_data_by_identifier(self, did: int, data: bytes) -> bool:
        """Write data by identifier"""
        def _callback(response):
            try:
                # Raw send_request returns bytes directly, not a response object
                if isinstance(response, bytes):
                    response_data = response
                else:
                    response_data = response.data if hasattr(response, 'data') else b''
                
                # For DID write response, strip the service response byte (0x6E) and DID echo
                # Response format: [0x6E][DID_HIGH][DID_LOW]
                if len(response_data) >= 3 and response_data[0] == 0x6E:
                    # Extract any additional data (usually none for write response)
                    actual_data = response_data[3:] if len(response_data) > 3 else b''
                    print(f"[DEBUG] DID 0x{did:04X} write response: service=0x{response_data[0]:02X}")
                else:
                    actual_data = response_data
                    print(f"[DEBUG] DID 0x{did:04X} write unexpected response format: {response_data.hex()}")
                
                result = {
                    'service': 'write_data_by_identifier',
                    'success': True,
                    'data': actual_data,
                    'did': did,
                    'written_data': data
                }
                self.uds_response_received.emit(result)
                
            except Exception as e:
                error_msg = f"Write DID callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        # Use raw request instead of write_data_by_identifier to avoid DID codec issues
        def _raw_write_did_request():
            # Build Write Data By Identifier request: Service 0x2E + DID (2 bytes) + data
            from udsoncan import Request, services
            request_data = did.to_bytes(2, 'big') + data
            request = Request(service=services.WriteDataByIdentifier, data=request_data)
            return self.uds_client.send_request(request)
        
        return self._queue_uds_request(
            _raw_write_did_request,
            _callback
        )

    def security_access_request_seed(self, level: int) -> bool:
        """Request security access seed"""
        def _callback(response):
            try:
                # Raw send_request returns bytes directly, not a response object
                if isinstance(response, bytes):
                    response_data = response
                else:
                    response_data = response.data if hasattr(response, 'data') else b''
                
                # For security access seed response, strip the service response byte (0x67)
                # Response format: [0x67][LEVEL][SEED_DATA...]
                if len(response_data) >= 2 and response_data[0] == 0x67:
                    # Extract seed data (skip service byte + level byte)
                    seed_data = response_data[2:]
                    print(f"[DEBUG] Security seed response: service=0x{response_data[0]:02X}, level=0x{response_data[1]:02X}, seed={seed_data.hex()}")
                else:
                    seed_data = response_data
                    print(f"[DEBUG] Security seed unexpected response format: {response_data.hex()}")
                
                self.security_access.level = level
                self.security_access.seed = seed_data
                self.security_access.unlocked = False
                
                result = {
                    'service': 'security_access_request_seed',
                    'success': True,
                    'data': seed_data,
                    'level': level,
                    'seed': seed_data.hex().upper()
                }
                
                self.uds_response_received.emit(result)
                self.security_status_changed.emit({
                    'level': level,
                    'unlocked': False,
                    'seed': seed_data.hex().upper()
                })
                
            except Exception as e:
                error_msg = f"Security seed callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        def _raw_security_seed_request():
            from udsoncan import Request, services
            request = Request(service=services.SecurityAccess, data=bytes([level]))
            return self.uds_client.send_request(request)
        
        return self._queue_uds_request(
            _raw_security_seed_request,
            _callback,
            priority=0
        )

    def security_access_send_key(self, level: int, key: bytes) -> bool:
        """Send security access key"""
        def _callback(response):
            try:
                # Raw send_request returns bytes directly, not a response object
                if isinstance(response, bytes):
                    response_data = response
                else:
                    response_data = response.data if hasattr(response, 'data') else b''
                
                # For security access key response, strip the service response byte (0x67)
                # Response format: [0x67][LEVEL]
                if len(response_data) >= 2 and response_data[0] == 0x67:
                    actual_data = response_data[2:]  # Strip service byte + level byte
                    print(f"[DEBUG] Security key response: service=0x{response_data[0]:02X}, level=0x{response_data[1]:02X}")
                else:
                    actual_data = response_data
                    print(f"[DEBUG] Security key unexpected response format: {response_data.hex()}")
                
                self.security_access.key = key
                self.security_access.unlocked = True
                
                result = {
                    'service': 'security_access_send_key',
                    'success': True,
                    'data': actual_data,
                    'level': level,
                    'key': key.hex().upper()
                }
                
                self.uds_response_received.emit(result)
                self.security_status_changed.emit({
                    'level': level,
                    'unlocked': True,
                    'seed': self.security_access.seed.hex().upper() if self.security_access.seed else ""
                })
                
            except Exception as e:
                error_msg = f"Security key callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        def _raw_security_key_request():
            from udsoncan import Request, services
            request_data = bytes([level]) + key
            request = Request(service=services.SecurityAccess, data=request_data)
            return self.uds_client.send_request(request)
        
        return self._queue_uds_request(
            _raw_security_key_request,
            _callback,
            priority=0
        )

    def read_dtc_information(self, subfunction: int = 0x02, status_mask: int = 0xFF) -> bool:
        """Read DTC information"""
        def _callback(response):
            try:
                # Raw send_request returns bytes directly, not a response object
                if isinstance(response, bytes):
                    response_data = response
                else:
                    response_data = response.data if hasattr(response, 'data') else b''
                
                # For DTC read response, strip the service response byte (0x59)
                # Response format: [0x59][SUBFUNCTION][STATUS_MASK][DTC_DATA...]
                if len(response_data) >= 1 and response_data[0] == 0x59:
                    # Keep subfunction and status mask for DTC parsing
                    actual_data = response_data[1:]  # Strip only service byte
                    print(f"[DEBUG] DTC response: service=0x{response_data[0]:02X}, subfunction=0x{actual_data[0]:02X}")
                else:
                    actual_data = response_data
                    print(f"[DEBUG] DTC unexpected response format: {response_data.hex()}")
                
                dtc_list = self._parse_dtc_response(actual_data)
                
                result = {
                    'service': 'read_dtc_information',
                    'success': True,
                    'data': actual_data,
                    'subfunction': subfunction,
                    'dtc_count': len(dtc_list),
                    'dtcs': dtc_list
                }
                
                self.uds_response_received.emit(result)
                self.dtc_data_received.emit(dtc_list)
                
            except Exception as e:
                error_msg = f"DTC read callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        # Use raw request for DTC reading to avoid udsoncan DTC configuration issues
        def _raw_dtc_request():
            # Build Read DTC Information request with proper subfunction
            from udsoncan import Request, services
            try:
                # Create ReadDTCInformation request with proper subfunction
                if subfunction == 0x02:
                    # reportDTCByStatusMask - most common
                    request = Request(service=services.ReadDTCInformation, 
                                    subfunction=services.ReadDTCInformation.Subfunction.reportDTCByStatusMask,
                                    data=bytes([status_mask]))
                elif subfunction == 0x04:
                    # reportDTCSnapshotIdentification  
                    request = Request(service=services.ReadDTCInformation,
                                    subfunction=services.ReadDTCInformation.Subfunction.reportDTCSnapshotIdentification,
                                    data=bytes([status_mask]))
                elif subfunction == 0x06:
                    # reportDTCExtDataRecordByDTCNumber
                    request = Request(service=services.ReadDTCInformation,
                                    subfunction=services.ReadDTCInformation.Subfunction.reportDTCExtDataRecordByDTCNumber,
                                    data=bytes([status_mask]))
                else:
                    # Fallback to generic subfunction for unknown subfunctions
                    request = Request(service=services.ReadDTCInformation,
                                    subfunction=subfunction,
                                    data=bytes([status_mask]))
                
                return self.uds_client.send_request(request)
            except Exception as e:
                print(f"[DEBUG] Failed to create DTC request with subfunction, trying raw approach: {e}")
                # Fallback to completely raw request
                raw_data = bytes([0x19, subfunction, status_mask])
                return self.uds_client.send_request(raw_data)
        
        return self._queue_uds_request(
            _raw_dtc_request,
            _callback
        )

    def clear_diagnostic_information(self, dtc_group: int = 0xFFFFFF) -> bool:
        """Clear diagnostic information"""
        def _callback(response):
            try:
                # Raw send_request returns bytes directly, not a response object
                if isinstance(response, bytes):
                    response_data = response
                else:
                    response_data = response.data if hasattr(response, 'data') else b''
                
                # For clear DTC response, strip the service response byte (0x54)
                # Response format: [0x54]
                if len(response_data) >= 1 and response_data[0] == 0x54:
                    actual_data = response_data[1:]  # Strip service byte
                    print(f"[DEBUG] Clear DTC response: service=0x{response_data[0]:02X}")
                else:
                    actual_data = response_data
                    print(f"[DEBUG] Clear DTC unexpected response format: {response_data.hex()}")
                
                result = {
                    'service': 'clear_diagnostic_information',
                    'success': True,
                    'data': actual_data,
                    'dtc_group': dtc_group
                }
                
                self.uds_response_received.emit(result)
                
            except Exception as e:
                error_msg = f"Clear DTC callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        # Use raw request for clear DTC to avoid udsoncan configuration issues
        def _raw_clear_dtc_request():
            # Build Clear Diagnostic Information request: Service 0x14 + DTC group (3 bytes)
            from udsoncan import Request, services
            dtc_bytes = dtc_group.to_bytes(3, 'big')
            request = Request(service=services.ClearDiagnosticInformation, data=dtc_bytes)
            return self.uds_client.send_request(request)
        
        return self._queue_uds_request(
            _raw_clear_dtc_request,
            _callback
        )

    def ecu_reset(self, reset_type: int = 0x01) -> bool:
        """Perform ECU reset"""
        def _callback(response):
            try:
                result = {
                    'service': 'ecu_reset',
                    'success': True,
                    'data': response.data if hasattr(response, 'data') else b'',
                    'reset_type': reset_type
                }
                
                self.uds_response_received.emit(result)
                
            except Exception as e:
                error_msg = f"ECU reset callback error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        return self._queue_uds_request(
            self.uds_client.ecu_reset,
            _callback,
            reset_type,
            priority=0
        )

    def tester_present(self, suppress_response: bool = False) -> bool:
        """Send tester present message"""
        def _callback(response):
            try:
                if response is None:
                    print("[DEBUG] Tester present: No response (expected if suppress_response=True)")
                    return
                    
                result = {
                    'service': 'tester_present',
                    'success': True,
                    'data': response.data if hasattr(response, 'data') else b'',
                    'suppress_response': suppress_response
                }
                
                self.uds_response_received.emit(result)
                print(f"[DEBUG] Tester present successful: {result}")
                
            except Exception as e:
                print(f"[DEBUG] Tester present response error: {e}")
        
        def _error_callback(error):
            # For tester present, we're more lenient with errors
            error_msg = f"Tester present error: {str(error)}"
            print(f"[WARNING] {error_msg}")
            # Don't emit error signal for tester present failures
            # as they're often expected in certain states
        
        # Use suppress_response parameter for tester present
        if suppress_response:
            return self._queue_uds_request(
                lambda: self.uds_client.tester_present(suppress_response=True),
                _callback,
                priority=2,
                error_callback=_error_callback
            )
        else:
            return self._queue_uds_request(
                self.uds_client.tester_present,
                _callback,
                priority=2,
                error_callback=_error_callback
            )


    def send_raw_request(self, service: int, data: bytes = b'') -> bool:
        """Send raw UDS request"""
        def _callback(response):
            try:
                # Raw send_request returns bytes directly, not a response object
                if isinstance(response, bytes):
                    response_data = response
                else:
                    response_data = response.data if hasattr(response, 'data') else b''
                
                result = {
                    'service': f'raw_0x{service:02X}',
                    'success': True,
                    'data': response_data,
                    'request_data': request_data
                }
                
                self.uds_response_received.emit(result)
                
            except Exception as e:
                error_msg = f"Raw request 0x{service:02X} failed: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.uds_error_occurred.emit(error_msg)
        
        # Build raw request data
        request_data = bytes([service]) + data
        
        # Create proper raw request function that creates the request properly
        def _raw_request():
            from udsoncan import Request, services
            
            # Map service IDs to known service classes
            service_map = {
                0x10: services.DiagnosticSessionControl,
                0x11: services.ECUReset,
                0x14: services.ClearDiagnosticInformation,
                0x19: services.ReadDTCInformation,
                0x22: services.ReadDataByIdentifier,
                0x23: services.ReadMemoryByAddress,
                0x24: services.ReadScalingDataByIdentifier,
                0x27: services.SecurityAccess,
                0x28: services.CommunicationControl,
                0x2A: services.ReadDataByPeriodicIdentifier,
                0x2C: services.DynamicallyDefineDataIdentifier,
                0x2E: services.WriteDataByIdentifier,
                0x2F: services.InputOutputControlByIdentifier,
                0x31: services.RoutineControl,
                0x34: services.RequestDownload,
                0x35: services.RequestUpload,
                0x36: services.TransferData,
                0x37: services.RequestTransferExit,
                0x3E: services.TesterPresent,
                0x83: services.AccessTimingParameter,
                0x84: services.SecuredDataTransmission,
                0x85: services.ControlDTCSetting,
                0x86: services.ResponseOnEvent,
                0x87: services.LinkControl,
            }
            
            # Use known service if available
            if service in service_map:
                print(f"[DEBUG] Using known service class for 0x{service:02X} with data: {data.hex()}")
                service_class = service_map[service]
                
                # Special handling for services that need subfunction parsing
                if service == 0x10:  # DiagnosticSessionControl
                    if len(data) >= 1:
                        session_type = data[0]
                        remaining_data = data[1:] if len(data) > 1 else b''
                        print(f"[DEBUG] DiagnosticSessionControl: session_type=0x{session_type:02X}, remaining_data={remaining_data.hex()}")
                        request = Request(service=service_class, subfunction=session_type, data=remaining_data)
                    else:
                        # Default to session type 1 if no data
                        print(f"[DEBUG] DiagnosticSessionControl: no data, using default session type 0x01")
                        request = Request(service=service_class, subfunction=0x01, data=b'')
                        
                elif service == 0x11:  # ECUReset
                    if len(data) >= 1:
                        reset_type = data[0]
                        remaining_data = data[1:] if len(data) > 1 else b''
                        print(f"[DEBUG] ECUReset: reset_type=0x{reset_type:02X}, remaining_data={remaining_data.hex()}")
                        request = Request(service=service_class, subfunction=reset_type, data=remaining_data)
                    else:
                        # Default to hard reset if no data
                        print(f"[DEBUG] ECUReset: no data, using default reset type 0x01")
                        request = Request(service=service_class, subfunction=0x01, data=b'')
                        
                elif service == 0x19:  # ReadDTCInformation
                    if len(data) >= 1:
                        subfunction = data[0]
                        remaining_data = data[1:] if len(data) > 1 else b''
                        print(f"[DEBUG] ReadDTCInformation: subfunction=0x{subfunction:02X}, remaining_data={remaining_data.hex()}")
                        # Try to map to known subfunctions
                        try:
                            if subfunction == 0x02:
                                request = Request(service=service_class, 
                                                subfunction=services.ReadDTCInformation.Subfunction.reportDTCByStatusMask, 
                                                data=remaining_data)
                            elif subfunction == 0x04:
                                request = Request(service=service_class,
                                                subfunction=services.ReadDTCInformation.Subfunction.reportDTCSnapshotIdentification,
                                                data=remaining_data)
                            elif subfunction == 0x06:
                                request = Request(service=service_class,
                                                subfunction=services.ReadDTCInformation.Subfunction.reportDTCExtDataRecordByDTCNumber,
                                                data=remaining_data)
                            else:
                                # For unknown subfunctions, use raw approach
                                raise ValueError(f"Unknown DTC subfunction 0x{subfunction:02X}")
                        except:
                            # Fallback to raw bytes for unknown DTC subfunctions
                            raw_data = bytes([service]) + data
                            return self._send_raw_bytes_direct(raw_data)
                    else:
                        # Default DTC read
                        request = Request(service=service_class, 
                                        subfunction=services.ReadDTCInformation.Subfunction.reportDTCByStatusMask, 
                                        data=b'\xFF')
                        
                elif service == 0x27:  # SecurityAccess
                    if len(data) >= 1:
                        level = data[0]
                        remaining_data = data[1:] if len(data) > 1 else b''
                        print(f"[DEBUG] SecurityAccess: level=0x{level:02X}, remaining_data={remaining_data.hex()}")
                        request = Request(service=service_class, subfunction=level, data=remaining_data)
                    else:
                        # Default to level 1 seed request
                        print(f"[DEBUG] SecurityAccess: no data, using default level 0x01")
                        request = Request(service=service_class, subfunction=0x01, data=b'')
                        
                elif service == 0x3E:  # TesterPresent
                    if len(data) >= 1:
                        suppress = data[0]
                        remaining_data = data[1:] if len(data) > 1 else b''
                        print(f"[DEBUG] TesterPresent: suppress=0x{suppress:02X}, remaining_data={remaining_data.hex()}")
                        request = Request(service=service_class, subfunction=suppress, data=remaining_data)
                    else:
                        # Default tester present with response
                        print(f"[DEBUG] TesterPresent: no data, using default subfunction 0x00")
                        request = Request(service=service_class, subfunction=0x00, data=b'')
                        
                else:
                    # For other services, pass data as-is (no subfunction expected)
                    print(f"[DEBUG] Service 0x{service:02X}: using data as-is: {data.hex()}")
                    request = Request(service=service_class, data=data)
                
                return self.uds_client.send_request(request)
            else:
                print(f"[DEBUG] Creating raw request for unknown service 0x{service:02X}")
                # For unknown services, send raw bytes directly
                raw_data = bytes([service]) + data
                return self._send_raw_bytes_direct(raw_data)
        
        return self._queue_uds_request(
            _raw_request,
            _callback
        )

    def _send_raw_bytes_direct(self, raw_data: bytes):
        """Send raw bytes directly through the UDS connection"""
        try:
            print(f"[DEBUG] Sending raw bytes directly: {raw_data.hex()}")
            
            # Use the underlying connection to send raw bytes
            if self.uds_connection and hasattr(self.uds_connection, 'send') and hasattr(self.uds_connection, 'wait_frame'):
                self.uds_connection.send(raw_data)
                response_data = self.uds_connection.wait_frame(timeout=self.client_config.get('request_timeout', 5.0))
                if response_data is None:
                    raise TimeoutError("No response received")
                return response_data
            elif self.uds_connection and hasattr(self.uds_connection, 'send_data'):
                # Alternative method name
                self.uds_connection.send_data(raw_data)
                response_data = self.uds_connection.recv_data(timeout=self.client_config.get('request_timeout', 5.0))
                if response_data is None:
                    raise TimeoutError("No response received")
                return response_data
            else:
                raise RuntimeError(f"Cannot send raw bytes - connection doesn't support direct raw sending")
        except Exception as e:
            print(f"[ERROR] Failed to send raw bytes: {e}")
            raise

    # === Helper Methods ===
    
    def _decode_did_response(self, did: int, data: bytes) -> str:
        """Decode DID response data"""
        try:
            if did == 0xF010:  # Active session
                if len(data) >= 1:
                    session_type = data[0]
                    session_names = {
                        0x01: "Default Session",
                        0x02: "Programming Session",
                        0x03: "Extended Diagnostic Session",
                        0x40: "EOL Session"
                    }
                    return session_names.get(session_type, f"Session 0x{session_type:02X}")
            elif did == 0xF011:  # ECU Software Number
                return data.decode('ascii', errors='ignore').strip('\x00')
            elif did == 0xF030:  # Vehicle Speed
                if len(data) >= 2:
                    speed = int.from_bytes(data[:2], 'big')
                    return f"{speed} km/h"
            elif did == 0xF031:  # Engine RPM
                if len(data) >= 2:
                    rpm = int.from_bytes(data[:2], 'big')
                    return f"{rpm} rpm"
            elif did == 0xF032:  # Engine Temperature
                if len(data) >= 1:
                    temp = data[0] - 40  # Offset by 40°C
                    return f"{temp}°C"
            elif did == 0xF190:  # VIN
                return data.decode('ascii', errors='ignore').strip('\x00')
            else:
                # Generic hex representation
                return data.hex().upper()
                
        except Exception as e:
            return f"Decode error: {e}"

    def _parse_dtc_response(self, data: bytes) -> List[Dict]:
        """Parse DTC response data"""
        dtcs = []
        try:
            print(f"[DEBUG] Parsing DTC response: {data.hex()}")
            
            # Skip first byte (subfunction echo)  
            dtc_data = data[1:] if len(data) > 1 else data
            print(f"[DEBUG] DTC data after removing subfunction: {dtc_data.hex()}")
            
            # Skip status mask byte (second byte in response)
            if len(dtc_data) > 1:
                dtc_data = dtc_data[1:]
                print(f"[DEBUG] DTC data after removing status mask: {dtc_data.hex()}")
            
            # Each DTC is typically 4 bytes (3 bytes DTC + 1 byte status)
            for i in range(0, len(dtc_data), 4):
                if i + 3 < len(dtc_data):
                    # Extract DTC bytes
                    dtc_bytes = dtc_data[i:i+3]
                    status_byte = dtc_data[i+3]
                    
                    print(f"[DEBUG] Parsing DTC {i//4}: bytes={dtc_bytes.hex()}, status={status_byte:02X}")
                    
                    # Convert to standard DTC format
                    dtc_code = self._format_dtc_code(dtc_bytes)
                    dtc_status = self._decode_dtc_status(status_byte)
                    
                    dtc_entry = {
                        'code': dtc_code,
                        'status': dtc_status,
                        'raw_bytes': dtc_bytes.hex().upper(),
                        'status_byte': status_byte
                    }
                    
                    print(f"[DEBUG] Created DTC entry {i//4}: {dtc_entry}")
                    dtcs.append(dtc_entry)
                    
        except Exception as e:
            print(f"[ERROR] DTC parsing error: {e}")
            print(f"[ERROR] Raw data was: {data.hex()}")
            
        print(f"[DEBUG] Final parsed DTCs: {dtcs}")
        return dtcs

    def _format_dtc_code(self, dtc_bytes: bytes) -> str:
        """Format DTC bytes to standard DTC code (e.g., P0301)"""
        if len(dtc_bytes) != 3:
            return "INVALID"
        
        # First byte contains the system identifier
        first_byte = dtc_bytes[0]
        system_id = (first_byte >> 6) & 0x03
        
        # System mapping
        system_chars = ['P', 'C', 'B', 'U']  # Powertrain, Chassis, Body, Network
        system_char = system_chars[system_id]
        
        # Extract the DTC number
        dtc_num = ((first_byte & 0x3F) << 8) | dtc_bytes[1]
        dtc_sub = dtc_bytes[2]
        
        return f"{system_char}{dtc_num:02X}{dtc_sub:02X}"

    def _decode_dtc_status(self, status_byte: int) -> str:
        """Decode DTC status byte"""
        status_bits = []
        
        if status_byte & 0x01:
            status_bits.append("TestFailed")
        if status_byte & 0x02:
            status_bits.append("TestFailedThisOpCycle")
        if status_byte & 0x04:
            status_bits.append("PendingDTC")
        if status_byte & 0x08:
            status_bits.append("ConfirmedDTC")
        if status_byte & 0x10:
            status_bits.append("TestNotCompletedSinceLastClear")
        if status_byte & 0x20:
            status_bits.append("TestFailedSinceLastClear")
        if status_byte & 0x40:
            status_bits.append("TestNotCompletedThisOpCycle")
        if status_byte & 0x80:
            status_bits.append("WarningIndicatorRequested")
        
        return ", ".join(status_bits) if status_bits else "No Status"

    def calculate_security_key(self, seed: bytes, algorithm: str = "xor") -> bytes:
        """Calculate security key from seed using specified algorithm"""
        try:
            if not seed:
                return b''
            
            if algorithm == "xor":
                # Simple XOR with constant
                key = bytearray()
                constant = 0x1234
                for i, byte in enumerate(seed):
                    key.append(byte ^ ((constant >> (8 * (i % 2))) & 0xFF))
                return bytes(key)
            
            elif algorithm == "add":
                # Simple addition with constant
                key = bytearray()
                constant = 0x9876
                for i, byte in enumerate(seed):
                    key.append((byte + ((constant >> (8 * (i % 2))) & 0xFF)) & 0xFF)
                return bytes(key)
            
            elif algorithm == "complement":
                # Bitwise complement
                return bytes(~byte & 0xFF for byte in seed)
            
            else:
                # Default to XOR
                return self.calculate_security_key(seed, "xor")
                
        except Exception as e:
            print(f"[ERROR] Security key calculation error: {e}")
            return b''

    def get_connection_status(self) -> Dict:
        """Get current UDS connection status"""
        return {
            'connected': self.is_connected,
            'tx_id': f"0x{self.tx_id:X}",
            'rx_id': f"0x{self.rx_id:X}",
            'current_session': self.current_session.name,
            'session_type': self.current_session.session_type,
            'security_unlocked': self.security_access.unlocked,
            'security_level': self.security_access.level,
            'queue_size': self.uds_message_queue.qsize(),
            'pending_requests': len(self._pending_requests),
            'config_timeout': self.client_config.get('request_timeout', 'unknown')
        }

    def set_can_ids(self, tx_id: int, rx_id: int):
        """Update CAN IDs for UDS communication"""
        if self.is_connected:
            self.disconnect()
        
        self.tx_id = tx_id
        self.rx_id = rx_id
        print(f"[DEBUG] UDS CAN IDs updated: TX=0x{tx_id:X}, RX=0x{rx_id:X}")

    def set_timeout(self, timeout: float):
        """Set UDS request timeout with validation"""
        if timeout < 0.1:
            timeout = 0.1
        elif timeout > 60.0:
            timeout = 60.0
            
        # Update both base config and current config
        self.base_client_config['request_timeout'] = timeout
        self.client_config['request_timeout'] = timeout
        print(f"[DEBUG] UDS timeout set to {timeout}s")

    def get_queue_status(self) -> Dict:
        """Get detailed queue status for debugging"""
        return {
            'queue_size': self.uds_message_queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'pending_requests': len(self._pending_requests),
            'processing_thread_alive': self.uds_processing_thread.is_alive() if self.uds_processing_thread else False,
            'stop_event_set': self._stop_processing.is_set(),
            'is_connected': self.is_connected
        }

    def send_isotp_frame(self, data):
        """Send a raw ISO-TP frame through the CAN manager"""
        if not self.is_connected or not self.isotp_stack:
            print("[WARNING] Cannot send ISO-TP frame - not connected")
            return
            
        try:
            # Create CAN message
            can_msg = {
                'id': self.tx_id,
                'data': list(data),
                'extended': False,
                'fd': False
            }
            
            # Send through CAN manager
            self.can_manager.send_message(
                can_msg['id'],
                can_msg['data'],
                extended_id=can_msg['extended'],
                fd=can_msg['fd']
            )
            print(f"[DEBUG] Sent ISO-TP frame: ID=0x{self.tx_id:X}, Data={list(data)}")
        except Exception as e:
            print(f"[ERROR] Failed to send ISO-TP frame: {e}")
        
    def _handle_isotp_message(self, isotp_msg_info):
        """Handle ISOTP message from CAN manager with improved reliability"""
        try:
            print(f"[DEBUG] UDS received ISOTP message: TX=0x{isotp_msg_info['tx_id']:X}, RX=0x{isotp_msg_info['rx_id']:X}")
            
            if not self.is_connected or not self.isotp_stack:
                print(f"[DEBUG] UDS not connected or no ISOTP stack, ignoring message")
                return
            
            # Check if this message is for us
            if (isotp_msg_info['tx_id'] == self.tx_id and 
                isotp_msg_info['rx_id'] == self.rx_id):
                
                print(f"[DEBUG] ISOTP message is for us, processing...")
                
                # Process the ISOTP message
                isotp_data = bytes(isotp_msg_info['data'])
                print(f"[DEBUG] Processing ISOTP message: {isotp_data.hex().upper()}, Length: {len(isotp_data)} bytes")
                
                # Check if this is a First Frame (FF) that requires Flow Control response
                if isotp_data and (isotp_data[0] >> 4) == 1:  # First Frame indicator
                    print("[DEBUG] First Frame received, sending Flow Control")
                    
                    # Send Flow Control Frame (0x30 - Continue, block size 0, STmin 0)
                    flow_control = bytes([0x30, 0x00, 0x00])
                    self.send_isotp_frame(flow_control)

                def _process_isotp():
                    try:
                        if not self.is_connected or not self.isotp_stack:
                            print("[DEBUG] Cannot process ISOTP - connection lost")
                            return
                        
                        with self._isotp_lock:
                            # Feed the ISOTP data to the UDS connection
                            if self.uds_connection and hasattr(self.uds_connection, '_isotp_stack'):
                                print(f"[DEBUG] Feeding ISOTP data to UDS connection")
                                
                                # Create CAN message for ISOTP processing
                                can_msg = can.Message(
                                    arbitration_id=isotp_msg_info['rx_id'],
                                    data=isotp_data,
                                    is_extended_id=False,
                                    is_fd=False
                                )
                                
                                # Process through ISOTP stack
                                self.isotp_stack._process_rx(can_msg)
                                print(f"[DEBUG] ISOTP message processed successfully")
                            else:
                                print("[WARNING] UDS connection not available for ISOTP processing")
                                
                    except Exception as e:
                        print(f"[ERROR] ISOTP processing failed: {e}")
                        print(f"[ERROR] Traceback: {traceback.format_exc()}")
                
                # Queue the ISOTP processing with highest priority
                try:
                    self._request_counter += 1
                    request_id = self._request_counter
                    self._pending_requests[request_id] = {'type': 'isotp'}
                    
                    queue_item = (0, time.time(), request_id, {
                        'type': 'isotp',
                        'data': isotp_data,
                        'callback': _process_isotp
                    })
                    
                    self.uds_message_queue.put_nowait(queue_item)
                    print(f"[DEBUG] ISOTP processing queued with ID {request_id}")
                    
                except queue.Full:
                    print("[ERROR] Queue full, ISOTP message dropped")
            else:
                print(f"[DEBUG] ISOTP message not for us (expected TX=0x{self.tx_id:X}, got TX=0x{isotp_msg_info['tx_id']:X})")
                    
        except Exception as e:
            print(f"[ERROR] ISOTP message handling error: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

    def get_connection_health(self) -> dict:
        """Get comprehensive connection health information"""
        health_info = {
            'is_connected': self.is_connected(),
            'has_uds_client': self.uds_client is not None,
            'has_isotp_stack': self.isotp_stack is not None,
            'has_can_manager': self.can_manager is not None,
            'queue_size': self.uds_message_queue.qsize() if hasattr(self, 'uds_message_queue') else 0,
            'pending_requests': len(self._pending_requests),
            'thread_alive': self.uds_thread.is_alive() if self.uds_thread else False,
            'tx_id': self.tx_id,
            'rx_id': self.rx_id,
            'connection_params': {
                'device': getattr(self, 'device', None),
                'channel': getattr(self, 'channel', None),
                'bitrate': getattr(self, 'bitrate', None)
            }
        }
        
        # Check ISOTP stack state if available
        if self.isotp_stack:
            try:
                health_info['isotp_state'] = {
                    'tx_queue_size': len(self.isotp_stack.tx_queue) if hasattr(self.isotp_stack, 'tx_queue') else 'unknown',
                    'rx_state': getattr(self.isotp_stack, 'actual_rxdl', 'unknown')
                }
            except:
                health_info['isotp_state'] = 'error_reading_state'
        
        return health_info

    def diagnose_connection_issues(self) -> list:
        """Diagnose potential connection issues"""
        issues = []
        health = self.get_connection_health()
        
        if not health['is_connected']:
            issues.append("UDS backend reports not connected")
            
        if not health['has_uds_client']:
            issues.append("UDS client is None")
            
        if not health['has_isotp_stack']:
            issues.append("ISOTP stack is None")
            
        if not health['has_can_manager']:
            issues.append("CAN manager is None")
            
        if health['queue_size'] > 10:
            issues.append(f"High queue size: {health['queue_size']} items")
            
        if health['pending_requests'] > 5:
            issues.append(f"Many pending requests: {health['pending_requests']}")
            
        if not health['thread_alive']:
            issues.append("UDS processing thread is not alive")
            
        return issues

    def force_connection_reset(self) -> bool:
        """Force a complete connection reset - use with caution"""
        print("[WARNING] Forcing complete UDS connection reset")
        
        try:
            # Stop thread
            if hasattr(self, '_stop_event'):
                self._stop_event.set()
                
            # Clear queues
            if hasattr(self, 'uds_message_queue'):
                while not self.uds_message_queue.empty():
                    try:
                        self.uds_message_queue.get_nowait()
                    except queue.Empty:
                        break
                        
            # Clear pending requests
            self._pending_requests.clear()
            
            # Disconnect and reconnect
            self.disconnect()
            
            # Wait a moment
            time.sleep(0.5)
            
            # Reconnect with current parameters
            if hasattr(self, 'device') and hasattr(self, 'channel'):
                return self.connect(self.device, self.channel, getattr(self, 'bitrate', 500000))
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Force reset failed: {e}")
            return False

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.disconnect()
        except:
            pass