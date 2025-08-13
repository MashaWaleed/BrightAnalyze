#!/usr/bin/env python3
"""
Debug script to test SLCAN connection to CANable device
"""

import can
import time
import os

def test_device_access():
    """Test if we can access the device file"""
    device = '/dev/ttyACM0'
    
    print(f"Testing device access: {device}")
    print(f"Device exists: {os.path.exists(device)}")
    print(f"Device readable: {os.access(device, os.R_OK)}")
    print(f"Device writable: {os.access(device, os.W_OK)}")
    
    # Check permissions
    try:
        stat_info = os.stat(device)
        print(f"Device permissions: {oct(stat_info.st_mode)}")
        print(f"Device owner: {stat_info.st_uid}")
        print(f"Device group: {stat_info.st_gid}")
    except Exception as e:
        print(f"Error getting device stats: {e}")
    
    # Check if user is in dialout group
    import grp
    import pwd
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
        groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
        print(f"User: {user}")
        print(f"User groups: {groups}")
        print(f"In dialout group: {'dialout' in groups}")
    except Exception as e:
        print(f"Error checking groups: {e}")

def test_slcan_connection():
    """Test SLCAN connection"""
    device = '/dev/ttyACM0'
    
    print(f"\nTesting SLCAN connection to {device}")
    
    try:
        # Test with minimal parameters
        print("Attempting to create SLCAN bus...")
        bus = can.interface.Bus(
            bustype='slcan',
            channel=device,
            bitrate=500000,
            timeout=1.0
        )
        print("✅ SLCAN bus created successfully!")
        
        # Try to send a test message
        print("Sending test message...")
        test_msg = can.Message(
            arbitration_id=0x123,
            data=[0x01, 0x02, 0x03, 0x04],
            is_extended_id=False
        )
        
        bus.send(test_msg)
        print("✅ Test message sent successfully!")
        
        # Try to receive messages (with timeout)
        print("Listening for messages (5 seconds)...")
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < 5.0:
            msg = bus.recv(timeout=0.1)
            if msg:
                message_count += 1
                print(f"📨 Received: ID=0x{msg.arbitration_id:X}, Data={msg.data.hex()}")
        
        print(f"Received {message_count} messages in 5 seconds")
        
        bus.shutdown()
        print("✅ SLCAN connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ SLCAN connection failed: {e}")
        import traceback
        traceback.print_exc()

def test_socketcan_fallback():
    """Test SocketCAN as fallback"""
    interface = 'vcan0'
    
    print(f"\nTesting SocketCAN fallback with {interface}")
    
    try:
        # Create vcan interface if it doesn't exist
        import subprocess
        result = subprocess.run(['ip', 'link', 'show', interface], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Creating {interface}...")
            subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', interface, 'type', 'vcan'], 
                         check=True)
            subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], 
                         check=True)
            print(f"✅ Created and activated {interface}")
        
        bus = can.interface.Bus(
            bustype='socketcan',
            channel=interface
        )
        print("✅ SocketCAN bus created successfully!")
        
        # Send test message
        test_msg = can.Message(
            arbitration_id=0x456,
            data=[0x05, 0x06, 0x07, 0x08],
            is_extended_id=False
        )
        
        bus.send(test_msg)
        print("✅ Test message sent to SocketCAN!")
        
        bus.shutdown()
        
    except Exception as e:
        print(f"❌ SocketCAN test failed: {e}")

if __name__ == "__main__":
    print("🔧 CANable SLCAN Debug Tool")
    print("=" * 40)
    
    test_device_access()
    test_slcan_connection()
    test_socketcan_fallback()
    
    print("\n🏁 Debug complete!")
