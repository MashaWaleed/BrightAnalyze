#!/usr/bin/env python3
"""
Centralized Threading Workers for CAN Analyzer
Handles all background processing to keep UI responsive
"""

import time
import threading
import collections
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import (QObject, QThread, Signal, Slot, QMutex, QMutexLocker, 
                            QTimer, QWaitCondition)
from PySide6.QtWidgets import QApplication


@dataclass
class CANMessage:
    """Optimized CAN message structure for threading"""
    id: int
    data: bytes
    timestamp: float
    is_extended: bool
    direction: str  # 'RX' or 'TX'
    decoded_signals: Optional[Dict[str, Any]] = None
    dbc_message_name: Optional[str] = None
    dlc: int = 0
    count: int = 1


@dataclass
class DBCSearchRequest:
    """Request structure for DBC searches"""
    request_id: str
    search_term: str
    search_type: str  # 'message', 'signal', 'node', 'value_table'
    max_results: int = 100
    case_sensitive: bool = False


@dataclass
class FilterCriteria:
    """Message filtering criteria"""
    id_min: Optional[int] = None
    id_max: Optional[int] = None
    direction: Optional[str] = None
    data_pattern: Optional[str] = None
    message_name: Optional[str] = None
    signal_name: Optional[str] = None
    enabled: bool = True


class MessageProcessor(QObject):
    """High-performance message processing worker"""
    
    # Signals for thread-safe communication
    batch_processed = Signal(list)  # List[CANMessage]
    statistics_updated = Signal(dict)
    filter_applied = Signal(list)  # Filtered messages
    dbc_decoded = Signal(str, dict)  # message_id, decoded_data
    processing_error = Signal(str)
    
    def __init__(self, max_buffer_size: int = 10000):
        super().__init__()
        
        # Thread-safe message buffer
        self.message_buffer = collections.deque(maxlen=max_buffer_size)
        self._buffer_lock = QMutex()
        
        # Processing state
        self.dbc_manager = None
        self.filter_criteria = FilterCriteria()
        self.processing_enabled = True
        self.batch_size = 50  # Process in batches for efficiency
        
        # Performance statistics
        self.stats = {
            'total_messages': 0,
            'messages_per_second': 0,
            'filtered_count': 0,
            'processing_time_ms': 0,
            'decode_success_rate': 0,
            'last_update_time': time.time()
        }
        
        # Batch processing timer
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self._process_pending_batch)
        self.batch_timer.setSingleShot(True)
        
        self.pending_messages = []
        self._pending_lock = QMutex()
    
    @Slot(dict)
    def add_raw_message(self, raw_message: dict):
        """Add raw CAN message for processing (thread-safe entry point)"""
        if not self.processing_enabled:
            return
        
        try:
            # Convert to optimized structure
            can_message = CANMessage(
                id=raw_message.get('id', 0),
                data=raw_message.get('data', b''),
                timestamp=raw_message.get('timestamp', time.time()),
                is_extended=raw_message.get('is_extended', False),
                direction=raw_message.get('direction', 'RX'),
                dlc=raw_message.get('dlc', len(raw_message.get('data', b'')))
            )
            
            # Add to pending batch (thread-safe)
            with QMutexLocker(self._pending_lock):
                self.pending_messages.append(can_message)
                
                # Trigger batch processing if batch is full or timer not running
                if len(self.pending_messages) >= self.batch_size or not self.batch_timer.isActive():
                    self.batch_timer.start(10)  # 10ms batch window
                    
        except Exception as e:
            self.processing_error.emit(f"Message parsing error: {str(e)}")
    
    def _process_pending_batch(self):
        """Process pending messages in batch (runs in worker thread)"""
        # Get current batch thread-safely
        with QMutexLocker(self._pending_lock):
            if not self.pending_messages:
                return
            
            current_batch = self.pending_messages[:self.batch_size]
            self.pending_messages = self.pending_messages[self.batch_size:]
            
            # Schedule next batch if more messages pending
            if self.pending_messages:
                self.batch_timer.start(5)  # Quick follow-up
        
        if not current_batch:
            return
        
        start_time = time.perf_counter()
        processed_messages = []
        decode_successes = 0
        
        try:
            for message in current_batch:
                # DBC decoding (CPU intensive - done in worker thread)
                if self.dbc_manager:
                    try:
                        decoded = self._decode_message_signals(message)
                        if decoded:
                            message.decoded_signals = decoded
                            message.dbc_message_name = decoded.get('_message_name')
                            decode_successes += 1
                    except Exception as e:
                        # Don't let one decode error stop the batch
                        pass
                
                # Apply filtering (done in worker thread)
                if self._message_passes_filter(message):
                    processed_messages.append(message)
                
                # Add to main buffer
                with QMutexLocker(self._buffer_lock):
                    self.message_buffer.append(message)
            
            # Update statistics
            self.stats['total_messages'] += len(current_batch)
            self.stats['filtered_count'] += len(processed_messages)
            self.stats['decode_success_rate'] = decode_successes / len(current_batch) if current_batch else 0
            self.stats['processing_time_ms'] = (time.perf_counter() - start_time) * 1000
            
            # Emit results to UI thread
            if processed_messages:
                self.batch_processed.emit(processed_messages)
            
            self._update_statistics()
            
        except Exception as e:
            self.processing_error.emit(f"Batch processing error: {str(e)}")
    
    def _decode_message_signals(self, message: CANMessage) -> Optional[Dict[str, Any]]:
        """Decode message signals using DBC (runs in worker thread)"""
        if not self.dbc_manager:
            return None
        
        try:
            # This is the CPU-intensive operation moved to worker thread
            decoded = self.dbc_manager.decode_can_message(message.id, message.data)
            if decoded:
                decoded['_message_name'] = self.dbc_manager.get_message_name(message.id)
                return decoded
        except Exception:
            pass
        return None
    
    def _message_passes_filter(self, message: CANMessage) -> bool:
        """Apply filter criteria (runs in worker thread)"""
        if not self.filter_criteria.enabled:
            return True
        
        # ID range filter
        if (self.filter_criteria.id_min is not None and 
            message.id < self.filter_criteria.id_min):
            return False
        
        if (self.filter_criteria.id_max is not None and 
            message.id > self.filter_criteria.id_max):
            return False
        
        # Direction filter
        if (self.filter_criteria.direction and 
            message.direction != self.filter_criteria.direction):
            return False
        
        # Data pattern filter (expensive - done in worker thread)
        if self.filter_criteria.data_pattern:
            pattern = self.filter_criteria.data_pattern.lower()
            data_hex = message.data.hex().lower()
            if pattern not in data_hex:
                return False
        
        # Message name filter
        if (self.filter_criteria.message_name and message.dbc_message_name and
            self.filter_criteria.message_name.lower() not in message.dbc_message_name.lower()):
            return False
        
        # Signal name filter (check decoded signals)
        if (self.filter_criteria.signal_name and message.decoded_signals):
            signal_match = False
            for signal_name in message.decoded_signals.keys():
                if self.filter_criteria.signal_name.lower() in signal_name.lower():
                    signal_match = True
                    break
            if not signal_match:
                return False
        
        return True
    
    def _update_statistics(self):
        """Update performance statistics"""
        current_time = time.time()
        time_diff = current_time - self.stats['last_update_time']
        
        if time_diff >= 1.0:  # Update every second
            msg_count = self.stats['total_messages']
            self.stats['messages_per_second'] = msg_count / time_diff if time_diff > 0 else 0
            self.stats['last_update_time'] = current_time
            
            # Reset counters for next interval
            self.stats['total_messages'] = 0
            
            # Emit updated statistics
            self.statistics_updated.emit(self.stats.copy())
    
    @Slot(dict)
    def update_filter_criteria(self, criteria_dict: dict):
        """Update filter criteria (thread-safe)"""
        self.filter_criteria = FilterCriteria(**criteria_dict)
        
        # Reprocess existing buffer with new filter
        filtered_messages = []
        with QMutexLocker(self._buffer_lock):
            for message in self.message_buffer:
                if self._message_passes_filter(message):
                    filtered_messages.append(message)
        
        self.filter_applied.emit(filtered_messages)
    
    @Slot(object)
    def set_dbc_manager(self, dbc_manager):
        """Set DBC manager for message decoding"""
        self.dbc_manager = dbc_manager
    
    @Slot(bool)
    def set_processing_enabled(self, enabled: bool):
        """Enable/disable message processing"""
        self.processing_enabled = enabled


class DBCSearchWorker(QObject):
    """Worker for DBC database searches (keeps UI responsive)"""
    
    # Signals
    search_completed = Signal(str, list)  # request_id, results
    search_progress = Signal(str, int, int)  # request_id, current, total
    search_error = Signal(str, str)  # request_id, error_message
    
    def __init__(self):
        super().__init__()
        self.dbc_manager = None
        self.search_cache = {}  # Cache recent searches
        self.cache_lock = QMutex()
    
    @Slot(dict)
    def execute_search(self, search_request_dict: dict):
        """Execute DBC search in worker thread"""
        try:
            request = DBCSearchRequest(**search_request_dict)
            
            # Check cache first
            cache_key = f"{request.search_term}_{request.search_type}_{request.case_sensitive}"
            with QMutexLocker(self.cache_lock):
                if cache_key in self.search_cache:
                    self.search_completed.emit(request.request_id, self.search_cache[cache_key])
                    return
            
            if not self.dbc_manager:
                self.search_error.emit(request.request_id, "No DBC database loaded")
                return
            
            results = []
            
            if request.search_type == 'message':
                results = self._search_messages(request)
            elif request.search_type == 'signal':
                results = self._search_signals(request)
            elif request.search_type == 'node':
                results = self._search_nodes(request)
            elif request.search_type == 'value_table':
                results = self._search_value_tables(request)
            else:
                # Combined search
                results = self._search_all(request)
            
            # Cache results
            with QMutexLocker(self.cache_lock):
                self.search_cache[cache_key] = results
                # Limit cache size
                if len(self.search_cache) > 100:
                    # Remove oldest entries
                    oldest_key = next(iter(self.search_cache))
                    del self.search_cache[oldest_key]
            
            self.search_completed.emit(request.request_id, results)
            
        except Exception as e:
            self.search_error.emit(search_request_dict.get('request_id', 'unknown'), str(e))
    
    def _search_messages(self, request: DBCSearchRequest) -> List[Dict[str, Any]]:
        """Search for messages in DBC database"""
        results = []
        
        if not hasattr(self.dbc_manager, 'database') or not self.dbc_manager.database:
            return results
        
        search_term = request.search_term.lower() if not request.case_sensitive else request.search_term
        
        try:
            messages = self.dbc_manager.database.messages
            total_messages = len(messages)
            
            for i, message in enumerate(messages):
                # Emit progress
                if i % 10 == 0:  # Update every 10 messages
                    self.search_progress.emit(request.request_id, i, total_messages)
                
                message_name = message.name.lower() if not request.case_sensitive else message.name
                
                if search_term in message_name or search_term in f"0x{message.frame_id:X}".lower():
                    results.append({
                        'type': 'message',
                        'name': message.name,
                        'id': f"0x{message.frame_id:X}",
                        'id_decimal': message.frame_id,
                        'dlc': message.length,
                        'signals_count': len(message.signals),
                        'comment': getattr(message, 'comment', ''),
                        'transmitters': list(message.senders) if hasattr(message, 'senders') else []
                    })
                    
                    if len(results) >= request.max_results:
                        break
            
            # Final progress update
            self.search_progress.emit(request.request_id, total_messages, total_messages)
            
        except Exception as e:
            raise Exception(f"Message search error: {str(e)}")
        
        return results
    
    def _search_signals(self, request: DBCSearchRequest) -> List[Dict[str, Any]]:
        """Search for signals in DBC database"""
        results = []
        
        if not hasattr(self.dbc_manager, 'database') or not self.dbc_manager.database:
            return results
        
        search_term = request.search_term.lower() if not request.case_sensitive else request.search_term
        
        try:
            messages = self.dbc_manager.database.messages
            total_signals = sum(len(msg.signals) for msg in messages)
            processed_signals = 0
            
            for message in messages:
                for signal in message.signals:
                    processed_signals += 1
                    
                    # Emit progress
                    if processed_signals % 20 == 0:
                        self.search_progress.emit(request.request_id, processed_signals, total_signals)
                    
                    signal_name = signal.name.lower() if not request.case_sensitive else signal.name
                    
                    if search_term in signal_name:
                        results.append({
                            'type': 'signal',
                            'name': signal.name,
                            'message_name': message.name,
                            'message_id': f"0x{message.frame_id:X}",
                            'message_id_decimal': message.frame_id,
                            'start_bit': signal.start,
                            'length': signal.length,
                            'byte_order': 'big_endian' if signal.byte_order == 'big_endian' else 'little_endian',
                            'value_type': 'signed' if signal.is_signed else 'unsigned',
                            'factor': signal.scale,
                            'offset': signal.offset,
                            'unit': signal.unit,
                            'min_value': signal.minimum,
                            'max_value': signal.maximum,
                            'comment': getattr(signal, 'comment', ''),
                            'receivers': list(signal.receivers) if hasattr(signal, 'receivers') else []
                        })
                        
                        if len(results) >= request.max_results:
                            break
                
                if len(results) >= request.max_results:
                    break
            
            # Final progress update
            self.search_progress.emit(request.request_id, total_signals, total_signals)
            
        except Exception as e:
            raise Exception(f"Signal search error: {str(e)}")
        
        return results
    
    def _search_nodes(self, request: DBCSearchRequest) -> List[Dict[str, Any]]:
        """Search for nodes (ECUs) in DBC database"""
        results = []
        
        if not hasattr(self.dbc_manager, 'database') or not self.dbc_manager.database:
            return results
        
        search_term = request.search_term.lower() if not request.case_sensitive else request.search_term
        
        try:
            nodes = self.dbc_manager.database.nodes
            
            for i, node in enumerate(nodes):
                self.search_progress.emit(request.request_id, i, len(nodes))
                
                node_name = node.name.lower() if not request.case_sensitive else node.name
                
                if search_term in node_name:
                    results.append({
                        'type': 'node',
                        'name': node.name,
                        'comment': getattr(node, 'comment', ''),
                        'transmitted_messages': [],  # Would need to analyze messages
                        'received_messages': []      # Would need to analyze messages
                    })
                    
                    if len(results) >= request.max_results:
                        break
            
        except Exception as e:
            raise Exception(f"Node search error: {str(e)}")
        
        return results
    
    def _search_value_tables(self, request: DBCSearchRequest) -> List[Dict[str, Any]]:
        """Search for value tables in DBC database"""
        results = []
        
        # This would search through value tables if available in the DBC
        # Implementation depends on the DBC library being used
        
        return results
    
    def _search_all(self, request: DBCSearchRequest) -> List[Dict[str, Any]]:
        """Perform combined search across all DBC elements"""
        all_results = []
        
        # Search messages
        message_request = DBCSearchRequest(
            request_id=f"{request.request_id}_msg",
            search_term=request.search_term,
            search_type='message',
            max_results=request.max_results // 3,
            case_sensitive=request.case_sensitive
        )
        all_results.extend(self._search_messages(message_request))
        
        # Search signals
        signal_request = DBCSearchRequest(
            request_id=f"{request.request_id}_sig",
            search_term=request.search_term,
            search_type='signal',
            max_results=request.max_results // 3,
            case_sensitive=request.case_sensitive
        )
        all_results.extend(self._search_signals(signal_request))
        
        # Search nodes
        node_request = DBCSearchRequest(
            request_id=f"{request.request_id}_node",
            search_term=request.search_term,
            search_type='node',
            max_results=request.max_results // 3,
            case_sensitive=request.case_sensitive
        )
        all_results.extend(self._search_nodes(node_request))
        
        return all_results[:request.max_results]
    
    @Slot(object)
    def set_dbc_manager(self, dbc_manager):
        """Set DBC manager for searches"""
        self.dbc_manager = dbc_manager
        
        # Clear cache when DBC changes
        with QMutexLocker(self.cache_lock):
            self.search_cache.clear()
    
    @Slot()
    def clear_cache(self):
        """Clear search cache"""
        with QMutexLocker(self.cache_lock):
            self.search_cache.clear()


class TransmitMessageWorker(QObject):
    """Worker for transmit message operations"""
    
    # Signals
    message_composition_ready = Signal(str, dict)  # request_id, composed_message
    periodic_status_update = Signal(str, dict)     # message_id, status
    transmission_error = Signal(str, str)          # message_id, error
    
    def __init__(self):
        super().__init__()
        self.active_transmissions = {}  # message_id -> transmission_info
        self.transmission_lock = QMutex()
    
    @Slot(dict)
    def compose_message_async(self, request_dict: dict):
        """Compose CAN message with DBC encoding in worker thread"""
        try:
            request_id = request_dict['request_id']
            message_id = request_dict['message_id']
            signal_values = request_dict.get('signal_values', {})
            
            # This is CPU-intensive DBC encoding work done in worker thread
            composed_message = self._encode_message_with_dbc(message_id, signal_values)
            
            self.message_composition_ready.emit(request_id, composed_message)
            
        except Exception as e:
            self.transmission_error.emit(request_dict.get('message_id', 'unknown'), str(e))
    
    def _encode_message_with_dbc(self, message_id: int, signal_values: Dict[str, Any]) -> Dict[str, Any]:
        """Encode message using DBC database (CPU intensive)"""
        # This would use the DBC manager to encode signals into raw data
        # Implementation depends on the DBC library
        
        # Placeholder implementation
        return {
            'id': message_id,
            'data': b'\x00' * 8,  # Would be actual encoded data
            'dlc': 8,
            'is_extended': message_id > 0x7FF,
            'signals': signal_values
        }
    
    @Slot(str, dict)
    def start_periodic_transmission(self, message_id: str, transmission_config: dict):
        """Start periodic message transmission"""
        with QMutexLocker(self.transmission_lock):
            self.active_transmissions[message_id] = {
                'config': transmission_config,
                'start_time': time.time(),
                'sent_count': 0,
                'enabled': True
            }
    
    @Slot(str)
    def stop_periodic_transmission(self, message_id: str):
        """Stop periodic message transmission"""
        with QMutexLocker(self.transmission_lock):
            if message_id in self.active_transmissions:
                self.active_transmissions[message_id]['enabled'] = False


class ThreadingManager(QObject):
    """Central manager for all worker threads"""
    
    def __init__(self):
        super().__init__()
        
        # Create worker threads
        self.message_processor_thread = QThread()
        self.dbc_search_thread = QThread()
        self.transmit_worker_thread = QThread()
        
        # Create workers
        self.message_processor = MessageProcessor()
        self.dbc_search_worker = DBCSearchWorker()
        self.transmit_worker = TransmitMessageWorker()
        
        # Move workers to threads
        self.message_processor.moveToThread(self.message_processor_thread)
        self.dbc_search_worker.moveToThread(self.dbc_search_thread)
        self.transmit_worker.moveToThread(self.transmit_worker_thread)
        
        # Start threads
        self.message_processor_thread.start()
        self.dbc_search_thread.start()
        self.transmit_worker_thread.start()
        
        print("✅ Threading Manager initialized")
        print("   🔧 Message Processor Thread: Running")
        print("   🔍 DBC Search Thread: Running")
        print("   📤 Transmit Worker Thread: Running")
    
    def shutdown(self):
        """Gracefully shutdown all worker threads"""
        print("🔄 Shutting down worker threads...")
        
        # Stop threads
        self.message_processor_thread.quit()
        self.dbc_search_thread.quit()
        self.transmit_worker_thread.quit()
        
        # Wait for threads to finish
        self.message_processor_thread.wait(5000)  # 5 second timeout
        self.dbc_search_thread.wait(5000)
        self.transmit_worker_thread.wait(5000)
        
        print("✅ All worker threads stopped")
    
    def set_dbc_manager(self, dbc_manager):
        """Set DBC manager for all workers that need it"""
        self.message_processor.set_dbc_manager(dbc_manager)
        self.dbc_search_worker.set_dbc_manager(dbc_manager)
