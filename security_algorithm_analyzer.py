#!/usr/bin/env python3
"""
Security Algorithm Analysis Tool
Helps understand and reverse-engineer security access algorithms
"""

import struct
import hashlib

class SecurityAlgorithmAnalyzer:
    """Analyze and test different security access algorithms"""
    
    def __init__(self):
        self.known_algorithms = {
            "xor_constant": self._xor_constant,
            "add_constant": self._add_constant,
            "complement": self._complement,
            "rotate_left": self._rotate_left,
            "rotate_right": self._rotate_right,
            "lookup_table": self._lookup_table,
            "crc16": self._crc16_based,
            "checksum": self._checksum_based,
            "custom_oem1": self._custom_oem1,
            "custom_oem2": self._custom_oem2
        }
        
        # Common constants used by different manufacturers
        self.common_constants = [
            0x1234, 0x5678, 0x9ABC, 0xDEF0,
            0xCAFE, 0xBEEF, 0xDEAD, 0xFEED,
            0x1111, 0x2222, 0x3333, 0x4444,
            0x5555, 0x6666, 0x7777, 0x8888,
            0x9999, 0xAAAA, 0xBBBB, 0xCCCC,
            0xDDDD, 0xEEEE, 0xFFFF
        ]
        
        # Sample lookup table (simplified)
        self.lookup_table = list(range(256))
        for i in range(256):
            self.lookup_table[i] = (i * 7 + 13) & 0xFF
    
    def test_all_algorithms(self, seed_hex: str):
        """Test all known algorithms with given seed"""
        print(f"🧮 Testing algorithms with seed: {seed_hex}")
        print("=" * 60)
        
        # Parse seed
        seed_bytes = self._parse_hex_string(seed_hex)
        if not seed_bytes:
            print("❌ Invalid seed format")
            return
        
        results = {}
        
        for name, algorithm in self.known_algorithms.items():
            try:
                key = algorithm(seed_bytes)
                key_hex = ' '.join(f'{b:02X}' for b in key)
                results[name] = key
                print(f"{name:15} → {key_hex}")
            except Exception as e:
                print(f"{name:15} → ERROR: {e}")
        
        return results
    
    def analyze_seed_key_pairs(self, pairs):
        """Analyze multiple seed/key pairs to identify algorithm"""
        print(f"🔍 Analyzing {len(pairs)} seed/key pairs...")
        print("=" * 60)
        
        for algo_name, algorithm in self.known_algorithms.items():
            matches = 0
            total = 0
            
            for seed_hex, expected_key_hex in pairs:
                try:
                    seed_bytes = self._parse_hex_string(seed_hex)
                    expected_key_bytes = self._parse_hex_string(expected_key_hex)
                    
                    if not seed_bytes or not expected_key_bytes:
                        continue
                    
                    calculated_key = algorithm(seed_bytes)
                    
                    if calculated_key == expected_key_bytes:
                        matches += 1
                    total += 1
                    
                except Exception:
                    continue
            
            if total > 0:
                confidence = (matches / total) * 100
                print(f"{algo_name:15} → {matches}/{total} matches ({confidence:.1f}%)")
                
                if confidence == 100.0:
                    print(f"🎯 ALGORITHM IDENTIFIED: {algo_name}")
                    return algo_name
        
        print("❓ No algorithm identified with 100% confidence")
        return None
    
    def brute_force_constants(self, seed_hex: str, expected_key_hex: str):
        """Brute force common constants for XOR/ADD algorithms"""
        print(f"🔨 Brute forcing constants...")
        print(f"Seed: {seed_hex}")
        print(f"Expected Key: {expected_key_hex}")
        print("=" * 40)
        
        seed_bytes = self._parse_hex_string(seed_hex)
        expected_key_bytes = self._parse_hex_string(expected_key_hex)
        
        if not seed_bytes or not expected_key_bytes:
            print("❌ Invalid input format")
            return
        
        # Test XOR with common constants
        print("XOR Algorithm Tests:")
        for constant in self.common_constants:
            key = self._xor_with_constant(seed_bytes, constant)
            if key == expected_key_bytes:
                print(f"✅ XOR with 0x{constant:04X} → MATCH!")
                return ("xor", constant)
            else:
                key_hex = ' '.join(f'{b:02X}' for b in key)
                print(f"   0x{constant:04X} → {key_hex}")
        
        print("\nADD Algorithm Tests:")
        for constant in self.common_constants:
            key = self._add_with_constant(seed_bytes, constant)
            if key == expected_key_bytes:
                print(f"✅ ADD with 0x{constant:04X} → MATCH!")
                return ("add", constant)
            else:
                key_hex = ' '.join(f'{b:02X}' for b in key)
                print(f"   0x{constant:04X} → {key_hex}")
        
        print("❌ No common constant found")
        return None
    
    def generate_test_vectors(self, algorithm_name: str, count: int = 5):
        """Generate test vectors for a specific algorithm"""
        print(f"🧪 Generating {count} test vectors for {algorithm_name}")
        print("=" * 50)
        
        if algorithm_name not in self.known_algorithms:
            print("❌ Unknown algorithm")
            return []
        
        algorithm = self.known_algorithms[algorithm_name]
        test_vectors = []
        
        import random
        
        for i in range(count):
            # Generate random seed
            seed = [random.randint(0, 255) for _ in range(4)]
            key = algorithm(seed)
            
            seed_hex = ' '.join(f'{b:02X}' for b in seed)
            key_hex = ' '.join(f'{b:02X}' for b in key)
            
            test_vectors.append((seed_hex, key_hex))
            print(f"Vector {i+1}: {seed_hex} → {key_hex}")
        
        return test_vectors
    
    # Algorithm implementations
    
    def _xor_constant(self, seed):
        """XOR with alternating constant (common in automotive)"""
        return self._xor_with_constant(seed, 0x1234)
    
    def _add_constant(self, seed):
        """ADD with alternating constant"""
        return self._add_with_constant(seed, 0x5678)
    
    def _xor_with_constant(self, seed, constant):
        """XOR with specified constant"""
        key = []
        for i, byte in enumerate(seed):
            key.append(byte ^ ((constant >> (8 * (i % 2))) & 0xFF))
        return key
    
    def _add_with_constant(self, seed, constant):
        """ADD with specified constant"""
        key = []
        for i, byte in enumerate(seed):
            key.append((byte + ((constant >> (8 * (i % 2))) & 0xFF)) & 0xFF)
        return key
    
    def _complement(self, seed):
        """Bitwise complement"""
        return [~byte & 0xFF for byte in seed]
    
    def _rotate_left(self, seed):
        """Rotate left by 1 bit"""
        key = []
        for byte in seed:
            rotated = ((byte << 1) | (byte >> 7)) & 0xFF
            key.append(rotated)
        return key
    
    def _rotate_right(self, seed):
        """Rotate right by 1 bit"""
        key = []
        for byte in seed:
            rotated = ((byte >> 1) | (byte << 7)) & 0xFF
            key.append(rotated)
        return key
    
    def _lookup_table(self, seed):
        """Lookup table transformation"""
        return [self.lookup_table[byte] for byte in seed]
    
    def _crc16_based(self, seed):
        """CRC16-based algorithm"""
        # Simplified CRC16
        data = bytes(seed)
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        
        # Convert CRC to key
        key = [(crc >> (8 * i)) & 0xFF for i in range(len(seed))]
        return key[:len(seed)]
    
    def _checksum_based(self, seed):
        """Checksum-based algorithm"""
        checksum = sum(seed) & 0xFFFF
        key = []
        for i in range(len(seed)):
            key.append((checksum >> (8 * (i % 2))) & 0xFF)
        return key
    
    def _custom_oem1(self, seed):
        """Custom OEM algorithm 1 (example)"""
        # Simulate a complex proprietary algorithm
        key = []
        for i, byte in enumerate(seed):
            # Complex transformation
            transformed = (byte * 3 + i * 7 + 0x42) & 0xFF
            transformed ^= 0xAA if i % 2 == 0 else 0x55
            key.append(transformed)
        return key
    
    def _custom_oem2(self, seed):
        """Custom OEM algorithm 2 (example)"""
        # Another simulated algorithm
        key = []
        cumulative = 0
        for i, byte in enumerate(seed):
            cumulative = (cumulative + byte) & 0xFF
            transformed = (byte ^ cumulative ^ (i * 17)) & 0xFF
            key.append(transformed)
        return key
    
    def _parse_hex_string(self, hex_string):
        """Parse hex string to bytes"""
        try:
            # Remove spaces, commas, 0x prefixes
            cleaned = hex_string.replace(' ', '').replace(',', '').replace('0x', '').replace('0X', '')
            
            # Ensure even length
            if len(cleaned) % 2:
                cleaned = '0' + cleaned
            
            # Convert to bytes
            return [int(cleaned[i:i+2], 16) for i in range(0, len(cleaned), 2)]
        except ValueError:
            return None

def main():
    """Interactive security algorithm analysis"""
    analyzer = SecurityAlgorithmAnalyzer()
    
    print("🔐 Security Algorithm Analysis Tool")
    print("=" * 50)
    print()
    print("1. Test all algorithms with seed")
    print("2. Analyze seed/key pairs") 
    print("3. Brute force constants")
    print("4. Generate test vectors")
    print("5. Exit")
    print()
    
    while True:
        choice = input("Select option (1-5): ").strip()
        
        if choice == "1":
            seed = input("Enter seed (hex): ").strip()
            print()
            analyzer.test_all_algorithms(seed)
            print()
            
        elif choice == "2":
            pairs = []
            print("Enter seed/key pairs (empty line to finish):")
            while True:
                pair_input = input("Seed Key: ").strip()
                if not pair_input:
                    break
                parts = pair_input.split()
                if len(parts) >= 2:
                    seed = parts[0]
                    key = ' '.join(parts[1:])
                    pairs.append((seed, key))
            
            if pairs:
                print()
                analyzer.analyze_seed_key_pairs(pairs)
            print()
            
        elif choice == "3":
            seed = input("Enter seed (hex): ").strip()
            key = input("Enter expected key (hex): ").strip()
            print()
            analyzer.brute_force_constants(seed, key)
            print()
            
        elif choice == "4":
            algo = input("Algorithm name: ").strip()
            count = int(input("Number of vectors [5]: ") or "5")
            print()
            analyzer.generate_test_vectors(algo, count)
            print()
            
        elif choice == "5":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
