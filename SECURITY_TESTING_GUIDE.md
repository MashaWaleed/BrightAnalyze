# 🔐 Security Access Testing Guide

## Overview
This guide shows you how to test UDS security access functionality in your CAN analyzer without needing Windows or proprietary DLLs from your company.

## 🧪 Test Setup Options

### Option 1: Linux Virtual CAN (Recommended)
```bash
# Create virtual CAN interface
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Run the test ECU simulator
python3 security_test_simulator.py

# In another terminal, run your CAN analyzer
python3 main.py
```

### Option 2: Hardware Loopback (CANable/SLCAN)
Connect TX to RX on your CANable device for loopback testing.

### Option 3: CAN Bus Simulation Tools
- **python-can**: Virtual interfaces
- **SocketCAN**: Linux virtual CAN
- **BUSMASTER**: Free CAN simulation tool

## 📋 Step-by-Step Testing Procedure

### 1. Setup Your CAN Analyzer
1. Open your CAN analyzer
2. Go to Interface settings in the left sidebar
3. Set interface to `vcan0` (for virtual CAN)
4. Set TX ID: `0x7E0` (to ECU)
5. Set RX ID: `0x7E8` (from ECU)
6. Click Connect

### 2. Start the Test ECU Simulator
```bash
python3 security_test_simulator.py
```
You should see:
```
🚗 Security Test ECU initialized
   Interface: vcan0
   ECU TX: 0x7E8, ECU RX: 0x7E0
   Security Levels: [1, 2, 3]
🟢 ECU simulator running...
```

### 3. Test Session Control
1. In your analyzer, go to the Diagnostics panel
2. Open the "UDS Services" tab
3. Send Session Control: `10 02` (Programming Session)
4. You should see response: `50 02 00 32 01 F4`

### 4. Test Security Access Level 1 (XOR Algorithm)

#### Request Seed:
1. Go to "Security" tab in diagnostics
2. Select "0x01 - Level 1 (Seed Request)"
3. Click "🌱 Request Seed"
4. Watch the message log for: `27 01`
5. ECU responds with: `67 01 XX XX XX XX` (where XX XX XX XX is the random seed)

#### Calculate Key:
1. The seed will appear in the "Seed:" field
2. Click "🤖 Auto XOR" button
3. Your analyzer calculates the key using: `key[i] = seed[i] XOR ((0x1234 >> (8*(i%2))) & 0xFF)`
4. The calculated key appears in the "Key:" field

#### Send Key:
1. Click "🔑 Send Key"
2. Watch for message: `27 02 YY YY YY YY` (calculated key)
3. ECU responds with: `67 02` (success) or `7F 27 35` (wrong key)
4. Status changes to "🔓 Security Unlocked"

### 5. Test Security Access Level 2 (ADD Algorithm)
1. Select "0x03 - Level 2 (Seed Request)"
2. Click "🌱 Request Seed"
3. Click "🤖 Auto ADD" for key calculation
4. Click "🔑 Send Key"

### 6. Test Security Access Level 3 (Complement Algorithm)
1. Select "0x05 - Level 3 (Seed Request)"  
2. Click "🌱 Request Seed"
3. Click "🤖 Auto Complement" for key calculation
4. Click "🔑 Send Key"

### 7. Test Protected Data Access
After unlocking any security level:
1. Try reading protected DID: `22 F0 10`
2. Should get response: `62 F0 10 01 02 03`
3. Without security access, you'd get: `7F 22 33` (Security Access Denied)

## 🧮 Manual Key Calculation Examples

### XOR Algorithm (Level 1):
```python
seed = [0x12, 0x34, 0x56, 0x78]
secret = 0x1234
key = []
for i, byte in enumerate(seed):
    key.append(byte ^ ((secret >> (8 * (i % 2))) & 0xFF))
# Result: key = [0x46, 0x22, 0x40, 0x4C]
```

### ADD Algorithm (Level 2):
```python
seed = [0x12, 0x34, 0x56, 0x78]
secret = 0x5678
key = []
for i, byte in enumerate(seed):
    key.append((byte + ((secret >> (8 * (i % 2))) & 0xFF)) & 0xFF)
# Result: key = [0x90, 0x90, 0xD4, 0xD4]
```

### Complement Algorithm (Level 3):
```python
seed = [0x12, 0x34, 0x56, 0x78]
key = [~byte & 0xFF for byte in seed]
# Result: key = [0xED, 0xCB, 0xA9, 0x87]
```

## 📊 Expected Message Flow

```
Analyzer → ECU: 10 02        (Session Control - Programming)
ECU → Analyzer: 50 02 00 32 01 F4

Analyzer → ECU: 27 01        (Security Access - Request Seed Level 1)
ECU → Analyzer: 67 01 12 34 56 78

Analyzer → ECU: 27 02 46 22 40 4C  (Send calculated key)
ECU → Analyzer: 67 02        (Positive response - Unlocked!)

Analyzer → ECU: 22 F0 10     (Read protected DID)
ECU → Analyzer: 62 F0 10 01 02 03  (Success - data returned)
```

## 🐛 Troubleshooting

### "No seed value available"
- Make sure you requested seed first
- Check that ECU simulator is running
- Verify CAN interface connection

### "Wrong key" error
- Check algorithm selection matches ECU level
- Verify seed parsing (should be hex bytes)
- Manual calculation vs auto-calculation

### "Security Access Denied"
- Must be in programming session (not default)
- Security level must be unlocked first
- Check ECU simulator logs

### Interface connection issues
```bash
# Check virtual CAN interface
ip link show vcan0

# Monitor CAN traffic
candump vcan0

# Send manual CAN frame
cansend vcan0 7E0#1002
```

## 🎯 Learning Outcomes

By completing this test, you'll understand:

1. **UDS Security Access Protocol**: Seed/key exchange mechanism
2. **Algorithm Implementation**: How XOR/ADD/Complement work in practice  
3. **Message Flow**: Request/response patterns in UDS
4. **Error Handling**: Negative response codes and troubleshooting
5. **Tool Integration**: How CAN tools integrate with security algorithms

This gives you hands-on experience with security access without needing proprietary DLLs or Windows tools! 🎉
