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
            # Remove 'channel' from kwargs since we'll set it explicitly
            clean_kwargs = {k: v for k, v in kwargs.items() if k not in ['channel', 'interface', 'bustype', 'bitrate']}
            
            # Handle different drivers
            if driver == 'slcan':
                # SLCAN driver for serial USB-to-CAN devices
                self.bus = can.interface.Bus(
                    bustype='slcan',
                    channel=interface,  # e.g., '/dev/ttyACM0' or 'COM3'
                    bitrate=bitrate,
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
        """Disconnect from the CAN bus."""
        print("[DEBUG] Disconnecting from CAN bus")
        
        self.running = False
        self.is_connected = False
        
        # Stop the receiving thread
        if self.recv_thread and self.recv_thread.is_alive():
            self.recv_thread.join(timeout=1.0)
        
        # Stop the processing thread
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        
        # Clear the message queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
        
        # Close the bus
        if self.bus:
            try:
                self.bus.shutdown()
                print("[DEBUG] CAN bus shutdown complete")
            except Exception as e:
                print(f"[DEBUG] Error during bus shutdown: {e}")
            finally:
                self.bus = None
        
        self.bus_state_changed.emit('disconnected')
        print("[DEBUG] Disconnected from CAN bus")

    def send_message(self, msg_id, data, extended_id=False, fd=False):
        """Send a CAN message."""
        if not self.bus or not self.is_connected:
            error_msg = 'Not connected to CAN bus'
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
        
        try:
            # Convert data to bytes if needed
            if not isinstance(data, (bytes, bytearray)):
                try:
                    data_bytes = bytes(data)
                except:
                    data_bytes = bytes()
            else:
                data_bytes = data
            # Ensure data is in the correct format
            if isinstance(data, (list, tuple)):
                data_bytes = bytearray(data)
            elif isinstance(data, (bytes, bytearray)):
                data_bytes = bytearray(data)
            else:
                data_bytes = bytearray([data])  # Single byte
            
            # Create CAN message
            msg = can.Message(
                arbitration_id=msg_id,
                data=data_bytes,
                is_extended_id=extended_id,
                is_fd=fd
            )
            
            # Send the message
            self.bus.send(msg)
            
            print(f"[DEBUG] Sent CAN message: ID=0x{msg_id:X}, DLC={len(data_bytes)}, Data={data_bytes.hex().upper()}, Extended={extended_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send message: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            return False

    def register_isotp_stack(self, tx_id, rx_id, isotp_stack):
        """Register an ISOTP stack for message processing"""
        print(f"[DEBUG] Attempting to register ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
        with self.isotp_stacks_lock:
            key = f"{tx_id:03X}_{rx_id:03X}"
            # Check if stack already exists
            if key in self.isotp_stacks:
                print(f"[DEBUG] Replacing existing ISOTP stack for TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                old_stack = self.isotp_stacks[key]
                if hasattr(old_stack, 'stop'):
                    try:
                        old_stack.stop()
                    except Exception as e:
                        print(f"[DEBUG] Error stopping old ISOTP stack: {e}")
            
            self.isotp_stacks[key] = isotp_stack
            print(f"[DEBUG] Successfully registered ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
    
    def unregister_isotp_stack(self, tx_id, rx_id):
        """Unregister an ISOTP stack"""
        print(f"[DEBUG] Attempting to unregister ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
        with self.isotp_stacks_lock:
            key = f"{tx_id:03X}_{rx_id:03X}"
            if key in self.isotp_stacks:
                stack = self.isotp_stacks[key]
                if hasattr(stack, 'stop'):
                    try:
                        stack.stop()
                        print(f"[DEBUG] Stopped ISOTP stack for TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                    except Exception as e:
                        print(f"[DEBUG] Error stopping ISOTP stack: {e}")
                del self.isotp_stacks[key]
                print(f"[DEBUG] Successfully unregistered ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
            else:
                print(f"[DEBUG] No ISOTP stack found for TX=0x{tx_id:X}, RX=0x{rx_id:X}")
    
    def _process_isotp_messages(self, msg_info):
        """Process incoming CAN messages for ISOTP stacks"""
        try:
            msg_id = msg_info['id']
            print(f"[DEBUG] Processing CAN message for ISOTP: ID=0x{msg_id:X}, Data={msg_info['data']}")
            
            # Check if this message is for any registered ISOTP stack
            for key, isotp_stack in self.isotp_stacks.items():
                tx_id, rx_id = key.split('_')
                tx_id = int(tx_id, 16)
                rx_id = int(rx_id, 16)
                
                print(f"[DEBUG] Checking ISOTP stack: TX=0x{tx_id:X}, RX=0x{rx_id:X}")
                
                # For UDS: We send on TX_ID and receive responses on RX_ID
                # The ECU sends responses to our RX_ID (which is their TX_ID)
                if msg_id == rx_id:
                    print(f"[DEBUG] Message matches ISOTP stack RX ID: 0x{rx_id:X}")
                    try:
                        # Create CAN message for ISOTP processing
                        import can
                        can_msg = can.Message(
                            arbitration_id=msg_id,
                            data=bytearray(msg_info['data']),
                            is_extended_id=msg_info['extended'],
                            is_fd=msg_info.get('fd', False)
                        )
                        
                        print(f"[DEBUG] Created CAN message for ISOTP: ID=0x{can_msg.arbitration_id:X}, Data={list(can_msg.data)}")
                        
                        # Process with ISOTP stack
                        isotp_stack._process_rx(can_msg)
                        print(f"[DEBUG] ISOTP stack processed message")
                        
                        # Check if ISOTP has a complete message
                        if isotp_stack.available():
                            isotp_data = isotp_stack.recv()
                            if isotp_data:
                                isotp_msg_info = {
                                    'timestamp': msg_info['timestamp'],
                                    'tx_id': tx_id,
                                    'rx_id': rx_id,
                                    'data': list(isotp_data),
                                    'raw_can_msg': msg_info
                                }
                                print(f"[DEBUG] ISOTP complete message: TX=0x{tx_id:X}, RX=0x{rx_id:X}, Data={list(isotp_data)}")
                                self.isotp_message_received.emit(isotp_msg_info)
                            else:
                                print(f"[DEBUG] ISOTP stack available but no data received")
                        else:
                            print(f"[DEBUG] ISOTP stack not ready (partial message)")
                                
                    except Exception as e:
                        print(f"[ERROR] ISOTP processing error for {key}: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[DEBUG] Message ID 0x{msg_id:X} doesn't match ISOTP RX ID 0x{rx_id:X}")
                        
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
                    # Create message info dictionary
                    msg_info = {
                        'timestamp': msg.timestamp if hasattr(msg, 'timestamp') and msg.timestamp else time.time(),
                        'id': msg.arbitration_id,
                        'dlc': len(msg.data),
                        'data': list(msg.data),
                        'extended': msg.is_extended_id,
                        'fd': getattr(msg, 'is_fd', False),
                        'direction': 'RX',
                        'channel': self.interface
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
                if any(phrase in error_str for phrase in ['bad file descriptor', 'network is down', 'no such device']):
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