#!/usr/bin/env python3
"""
Security Access Test Simulator
Simulates an ECU with security access for testing purposes
Can be used without Windows or proprietary DLLs
"""

import time
import random
from threading import Thread
import can
from can.interfaces import socketcan

class SecurityAccessECU:
    """Simulates an ECU with security access functionality"""
    
    def __init__(self, interface="vcan0", tx_id=0x7E8, rx_id=0x7E0):
        self.interface = interface
        self.tx_id = tx_id  # ECU sends on this ID
        self.rx_id = rx_id  # ECU receives on this ID
        self.bus = None
        self.running = False
        
        # Security state
        self.security_levels = {
            1: {"unlocked": False, "algorithm": "xor", "secret": 0x1234},
            2: {"unlocked": False, "algorithm": "add", "secret": 0x5678},
            3: {"unlocked": False, "algorithm": "complement", "secret": 0x0000}
        }
        
        # Current session
        self.current_session = 0x01  # Default session
        self.supported_sessions = [0x01, 0x02, 0x03, 0x10]
        
        print(f"🚗 Security Test ECU initialized")
        print(f"   Interface: {interface}")
        print(f"   ECU TX: 0x{tx_id:03X}, ECU RX: 0x{rx_id:03X}")
        print(f"   Security Levels: {list(self.security_levels.keys())}")
    
    def start(self):
        """Start the ECU simulator"""
        try:
            # Try to create virtual CAN interface if it doesn't exist
            import subprocess
            try:
                subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', self.interface, 'type', 'vcan'], 
                             check=False, capture_output=True)
                subprocess.run(['sudo', 'ip', 'link', 'set', 'up', self.interface], 
                             check=False, capture_output=True)
                print(f"✅ Virtual CAN interface {self.interface} ready")
            except:
                print(f"⚠️  Assuming {self.interface} already exists")
            
            self.bus = can.interface.Bus(channel=self.interface, interface='socketcan')
            self.running = True
            
            # Start listening thread
            listen_thread = Thread(target=self._listen_loop, daemon=True)
            listen_thread.start()
            
            print(f"🟢 ECU simulator started on {self.interface}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start ECU simulator: {e}")
            return False
    
    def stop(self):
        """Stop the ECU simulator"""
        self.running = False
        if self.bus:
            self.bus.shutdown()
        print(f"🔴 ECU simulator stopped")
    
    def _listen_loop(self):
        """Listen for incoming CAN messages"""
        while self.running:
            try:
                message = self.bus.recv(timeout=0.1)
                if message and message.arbitration_id == self.rx_id:
                    self._process_uds_request(message)
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    print(f"⚠️  ECU listen error: {e}")
                    time.sleep(0.1)
    
    def _process_uds_request(self, message):
        """Process incoming UDS request"""
        data = list(message.data)
        if not data:
            return
            
        service = data[0]
        print(f"📥 ECU received: Service=0x{service:02X}, Data={' '.join(f'{b:02X}' for b in data)}")
        
        # Diagnostic Session Control (0x10)
        if service == 0x10:
            self._handle_session_control(data)
        
        # Security Access (0x27)
        elif service == 0x27:
            self._handle_security_access(data)
        
        # Read Data By Identifier (0x22)
        elif service == 0x22:
            self._handle_read_data(data)
        
        # Write Data By Identifier (0x2E)
        elif service == 0x2E:
            self._handle_write_data(data)
        
        else:
            # Send negative response
            self._send_negative_response(service, 0x11)  # Service not supported
    
    def _handle_session_control(self, data):
        """Handle session control request"""
        if len(data) < 2:
            self._send_negative_response(0x10, 0x13)  # Incorrect message length
            return
        
        session_type = data[1]
        if session_type in self.supported_sessions:
            self.current_session = session_type
            
            # Reset security access when changing sessions
            for level in self.security_levels:
                self.security_levels[level]["unlocked"] = False
            
            # Positive response: 0x50 + session type + additional data
            response = [0x50, session_type, 0x00, 0x32, 0x01, 0xF4]
            self._send_response(response)
            print(f"✅ Session changed to 0x{session_type:02X}")
        else:
            self._send_negative_response(0x10, 0x12)  # Sub-function not supported
    
    def _handle_security_access(self, data):
        """Handle security access request"""
        if len(data) < 2:
            self._send_negative_response(0x27, 0x13)  # Incorrect message length
            return
        
        sub_function = data[1]
        level = (sub_function + 1) // 2  # Convert sub-function to level
        
        # Check if session allows security access
        if self.current_session == 0x01:  # Default session usually doesn't allow security access
            self._send_negative_response(0x27, 0x7E)  # Service not supported in current session
            return
        
        if level not in self.security_levels:
            self._send_negative_response(0x27, 0x12)  # Sub-function not supported
            return
        
        # Seed request (odd sub-functions: 0x01, 0x03, 0x05...)
        if sub_function % 2 == 1:
            self._handle_seed_request(sub_function, level)
        
        # Key send (even sub-functions: 0x02, 0x04, 0x06...)
        else:
            self._handle_key_send(data, sub_function, level)
    
    def _handle_seed_request(self, sub_function, level):
        """Handle seed request"""
        if self.security_levels[level]["unlocked"]:
            # Already unlocked - send zero seed
            response = [0x67, sub_function, 0x00, 0x00]
            self._send_response(response)
            print(f"🔓 Level {level} already unlocked - zero seed sent")
        else:
            # Generate random seed
            seed = [random.randint(0x01, 0xFF) for _ in range(4)]
            self.security_levels[level]["current_seed"] = seed
            
            response = [0x67, sub_function] + seed
            self._send_response(response)
            print(f"🌱 Level {level} seed generated: {' '.join(f'{b:02X}' for b in seed)}")
    
    def _handle_key_send(self, data, sub_function, level):
        """Handle key send and verify"""
        if len(data) < 6:  # Service + sub-function + 4-byte key
            self._send_negative_response(0x27, 0x13)  # Incorrect message length
            return
        
        received_key = data[2:]
        
        # Check if we have a seed for this level
        if "current_seed" not in self.security_levels[level]:
            self._send_negative_response(0x27, 0x24)  # Request sequence error
            return
        
        # Calculate expected key
        seed = self.security_levels[level]["current_seed"]
        algorithm = self.security_levels[level]["algorithm"]
        secret = self.security_levels[level]["secret"]
        
        expected_key = self._calculate_key(seed, algorithm, secret)
        
        print(f"🔑 Level {level} key verification:")
        print(f"   Seed: {' '.join(f'{b:02X}' for b in seed)}")
        print(f"   Algorithm: {algorithm}")
        print(f"   Expected: {' '.join(f'{b:02X}' for b in expected_key)}")
        print(f"   Received: {' '.join(f'{b:02X}' for b in received_key)}")
        
        if received_key == expected_key:
            # Correct key - unlock
            self.security_levels[level]["unlocked"] = True
            response = [0x67, sub_function]
            self._send_response(response)
            print(f"🔓 Level {level} UNLOCKED successfully!")
        else:
            # Wrong key
            self._send_negative_response(0x27, 0x35)  # Invalid key
            print(f"🔒 Level {level} unlock FAILED - wrong key")
    
    def _calculate_key(self, seed, algorithm, secret):
        """Calculate security key based on algorithm"""
        if algorithm == "xor":
            # XOR with secret
            key = []
            for i, byte in enumerate(seed):
                key.append(byte ^ ((secret >> (8 * (i % 2))) & 0xFF))
            return key
        
        elif algorithm == "add":
            # Add secret
            key = []
            for i, byte in enumerate(seed):
                key.append((byte + ((secret >> (8 * (i % 2))) & 0xFF)) & 0xFF)
            return key
        
        elif algorithm == "complement":
            # Bitwise complement
            return [~byte & 0xFF for byte in seed]
        
        else:
            # Default to XOR
            return self._calculate_key(seed, "xor", secret)
    
    def _handle_read_data(self, data):
        """Handle read data by identifier"""
        if len(data) < 3:
            self._send_negative_response(0x22, 0x13)  # Incorrect message length
            return
        
        did = (data[1] << 8) | data[2]
        
        # Check security access for protected DIDs
        if did >= 0xF000 and not any(level["unlocked"] for level in self.security_levels.values()):
            self._send_negative_response(0x22, 0x33)  # Security access denied
            return
        
        # Simulate some data
        if did == 0xF010:  # Software version
            response_data = [0x01, 0x02, 0x03]
        elif did == 0xF015:  # Hardware version  
            response_data = [0x11, 0x22, 0x33]
        elif did == 0xF030:  # Calibration data
            response_data = [0xCA, 0xFE, 0xBA, 0xBE]
        else:
            response_data = [0xFF, 0xFF]  # Default data
        
        response = [0x62, data[1], data[2]] + response_data
        self._send_response(response)
        print(f"📖 Read DID 0x{did:04X}: {' '.join(f'{b:02X}' for b in response_data)}")
    
    def _handle_write_data(self, data):
        """Handle write data by identifier"""
        if len(data) < 4:
            self._send_negative_response(0x2E, 0x13)  # Incorrect message length
            return
        
        did = (data[1] << 8) | data[2]
        write_data = data[3:]
        
        # Check security access for protected DIDs
        if did >= 0xF000 and not any(level["unlocked"] for level in self.security_levels.values()):
            self._send_negative_response(0x2E, 0x33)  # Security access denied
            return
        
        # Simulate successful write
        response = [0x6E, data[1], data[2]]
        self._send_response(response)
        print(f"📝 Write DID 0x{did:04X}: {' '.join(f'{b:02X}' for b in write_data)}")
    
    def _send_response(self, data):
        """Send positive response"""
        try:
            message = can.Message(
                arbitration_id=self.tx_id,
                data=data,
                is_extended_id=False
            )
            self.bus.send(message)
            print(f"📤 ECU sent: {' '.join(f'{b:02X}' for b in data)}")
        except Exception as e:
            print(f"❌ Failed to send response: {e}")
    
    def _send_negative_response(self, service, nrc):
        """Send negative response"""
        data = [0x7F, service, nrc]
        self._send_response(data)
        print(f"❌ Negative response: Service=0x{service:02X}, NRC=0x{nrc:02X}")

def print_test_info():
    """Print test information and algorithms"""
    print("=" * 60)
    print("🔐 SECURITY ACCESS TEST SIMULATOR")
    print("=" * 60)
    print()
    print("📋 Test Scenario:")
    print("   • ECU responds on 0x7E8, listens on 0x7E0")
    print("   • 3 Security levels with different algorithms:")
    print("     - Level 1: XOR with 0x1234")
    print("     - Level 2: ADD with 0x5678") 
    print("     - Level 3: Bitwise complement")
    print()
    print("🔄 Test Procedure:")
    print("   1. Change to programming session (0x10 02)")
    print("   2. Request seed (0x27 01/03/05)")
    print("   3. Calculate key using algorithm")
    print("   4. Send key (0x27 02/04/06)")
    print("   5. Try reading protected DID (0x22 F010)")
    print()
    print("🧮 Key Calculation Examples:")
    print("   XOR: key[i] = seed[i] ^ ((0x1234 >> (8*(i%2))) & 0xFF)")
    print("   ADD: key[i] = (seed[i] + ((0x5678 >> (8*(i%2))) & 0xFF)) & 0xFF")
    print("   COMP: key[i] = ~seed[i] & 0xFF")
    print()

if __name__ == "__main__":
    print_test_info()
    
    # Create and start ECU simulator
    ecu = SecurityAccessECU()
    
    if ecu.start():
        try:
            print("🟢 ECU simulator running... (Ctrl+C to stop)")
            print(f"💡 Connect your CAN analyzer to 'vcan0' interface")
            print(f"💡 Set TX=0x7E0, RX=0x7E8 in your analyzer")
            print()
            
            # Keep running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping ECU simulator...")
            ecu.stop()
    else:
        print("❌ Failed to start ECU simulator")
