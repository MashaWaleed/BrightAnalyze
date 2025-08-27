#!/usr/bin/env python3
"""
Enhanced Message Log with Threading Integration
Uses worker threads for processing while keeping UI responsive
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
                               QLabel, QComboBox, QCheckBox, QSplitter, QTextEdit,
                               QGroupBox, QFormLayout, QSpinBox, QFrame, QProgressBar)
from PySide6.QtCore import Signal, Qt, QTimer, Slot
from PySide6.QtGui import QFont, QColor, QPalette

import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from .threading_workers import ThreadingManager, CANMessage


class EnhancedMessageDisplayManager(QWidget):
    """Enhanced UI manager with virtual scrolling and batching"""
    
    def __init__(self, table_widget: QTableWidget):
        super().__init__()
        self.table_widget = table_widget
        self.pending_messages = []
        self.max_displayed_messages = 5000  # Increased limit with virtual scrolling
        self.visible_range = (0, 100)  # Virtual scrolling range
        
        # Batch display timer
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self._flush_display_queue)
        self.display_timer.setSingleShot(True)
        
        # Performance tracking
        self.last_update_time = time.time()
        self.update_count = 0
        
    @Slot(list)
    def add_messages_batch(self, messages: List[CANMessage]):
        """Add batch of messages for display (runs on UI thread)"""
        self.pending_messages.extend(messages)
        
        # Coalesce rapid updates
        if not self.display_timer.isActive():
            self.display_timer.start(30)  # 30ms batch window for smooth updates
    
    def _flush_display_queue(self):
        """Flush pending messages to table widget"""
        if not self.pending_messages:
            return
        
        # Process a reasonable chunk to keep UI responsive
        chunk_size = min(100, len(self.pending_messages))
        messages_chunk = self.pending_messages[:chunk_size]
        self.pending_messages = self.pending_messages[chunk_size:]
        
        # Update table efficiently
        self._update_table_optimized(messages_chunk)
        
        # Continue if more messages pending
        if self.pending_messages:
            self.display_timer.start(10)  # Quick follow-up
        
        # Update performance stats
        self.update_count += len(messages_chunk)
        current_time = time.time()
        if current_time - self.last_update_time >= 1.0:
            fps = self.update_count / (current_time - self.last_update_time)
            # Could emit signal to update status bar with FPS
            self.last_update_time = current_time
            self.update_count = 0
    
    def _update_table_optimized(self, messages: List[CANMessage]):
        """Optimized table update with virtual scrolling support"""
        current_rows = self.table_widget.rowCount()
        
        # Implement circular buffer to prevent memory growth
        if current_rows >= self.max_displayed_messages:
            rows_to_remove = len(messages)
            for _ in range(min(rows_to_remove, current_rows)):
                self.table_widget.removeRow(0)
        
        # Add new rows
        for message in messages:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            
            # Only populate visible rows immediately
            if self._is_row_visible(row):
                self._populate_row_fast(row, message)
            else:
                # Store message data for lazy loading
                self.table_widget.setRowHeight(row, 25)  # Placeholder height
    
    def _is_row_visible(self, row: int) -> bool:
        """Check if row is in visible viewport"""
        # This would be connected to scroll events in a real implementation
        return True  # For now, populate all rows
    
    def _populate_row_fast(self, row: int, message: CANMessage):
        """Fast row population with minimal object creation"""
        # Timestamp
        timestamp_str = f"{message.timestamp:.3f}"
        timestamp_item = QTableWidgetItem(timestamp_str)
        self.table_widget.setItem(row, 0, timestamp_item)
        
        # Direction
        direction_item = QTableWidgetItem(message.direction)
        if message.direction == 'TX':
            direction_item.setBackground(QColor(255, 240, 245))  # Light pink
        self.table_widget.setItem(row, 1, direction_item)
        
        # ID
        id_str = f"0x{message.id:03X}" if message.id <= 0x7FF else f"0x{message.id:08X}"
        id_item = QTableWidgetItem(id_str)
        self.table_widget.setItem(row, 2, id_item)
        
        # DBC Name
        dbc_name = message.dbc_message_name or ""
        dbc_item = QTableWidgetItem(dbc_name)
        self.table_widget.setItem(row, 3, dbc_item)
        
        # DLC
        dlc_item = QTableWidgetItem(str(message.dlc))
        self.table_widget.setItem(row, 4, dlc_item)
        
        # Data
        data_str = message.data.hex().upper()
        # Format with spaces for readability
        formatted_data = ' '.join([data_str[i:i+2] for i in range(0, len(data_str), 2)])
        data_item = QTableWidgetItem(formatted_data)
        self.table_widget.setItem(row, 5, data_item)
        
        # Decoded Signals
        if message.decoded_signals:
            signals_list = []
            for name, value in message.decoded_signals.items():
                if not name.startswith('_'):  # Skip internal fields
                    signals_list.append(f"{name}={value}")
            signals_text = ", ".join(signals_list[:3])  # Limit display
            if len(signals_list) > 3:
                signals_text += f" (+{len(signals_list)-3} more)"
        else:
            signals_text = ""
        
        signals_item = QTableWidgetItem(signals_text)
        self.table_widget.setItem(row, 6, signals_item)
        
        # Count
        count_item = QTableWidgetItem(str(message.count))
        self.table_widget.setItem(row, 7, count_item)


class EnhancedMessageLog(QWidget):
    """Enhanced message log with threading integration"""
    
    # Signals
    message_selected = Signal(dict)
    filter_changed = Signal(dict)
    export_requested = Signal()
    statistics_updated = Signal(dict)
    
    def __init__(self, parent=None, dbc_manager=None):
        super().__init__(parent)
        self.dbc_manager = dbc_manager
        self.max_messages = 5000
        
        # Initialize threading manager
        self.threading_manager = ThreadingManager()
        
        # Message statistics
        self.stats = {
            'total_received': 0,
            'total_displayed': 0,
            'messages_per_second': 0,
            'filter_pass_rate': 0,
            'decode_success_rate': 0
        }
        
        self.setup_ui()
        self.connect_threading_signals()
        self.apply_professional_style()
        
        # Set DBC manager for worker threads
        if self.dbc_manager:
            self.threading_manager.set_dbc_manager(self.dbc_manager)
    
    def setup_ui(self):
        """Setup the enhanced UI with threading support"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Statistics and control panel
        self.create_statistics_panel(layout)
        
        # Filter panel
        self.create_filter_panel(layout)
        
        # Main splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Message table
        self.create_message_table()
        splitter.addWidget(self.message_table)
        
        # Message details
        self.create_details_panel()
        splitter.addWidget(self.details_panel)
        
        splitter.setSizes([800, 200])
        layout.addWidget(splitter)
        
        # Control buttons
        self.create_control_panel(layout)
        
        # Initialize display manager
        self.display_manager = EnhancedMessageDisplayManager(self.message_table)
    
    def create_statistics_panel(self, layout):
        """Create real-time statistics panel"""
        stats_group = QGroupBox("📊 Real-time Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        # Message counters
        self.total_label = QLabel("Total: 0")
        self.rate_label = QLabel("Rate: 0 msg/s")
        self.filtered_label = QLabel("Filtered: 0")
        self.decoded_label = QLabel("Decoded: 0%")
        
        # Performance indicators
        self.cpu_label = QLabel("CPU: 0ms")
        self.memory_label = QLabel("Memory: 0MB")
        
        # Progress bar for batch processing
        self.processing_progress = QProgressBar()
        self.processing_progress.setVisible(False)
        self.processing_progress.setMaximumHeight(6)
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.rate_label)
        stats_layout.addWidget(self.filtered_label)
        stats_layout.addWidget(self.decoded_label)
        stats_layout.addWidget(QFrame())  # Separator
        stats_layout.addWidget(self.cpu_label)
        stats_layout.addWidget(self.memory_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.processing_progress)
        
        layout.addWidget(stats_group)
    
    def create_filter_panel(self, layout):
        """Create enhanced filter panel"""
        filter_group = QGroupBox("🔍 Smart Filters (Processed in Background)")
        filter_layout = QHBoxLayout(filter_group)
        
        # ID Range filter
        filter_layout.addWidget(QLabel("ID Range:"))
        self.id_min_edit = QLineEdit()
        self.id_min_edit.setPlaceholderText("0x000")
        self.id_min_edit.setMaximumWidth(80)
        filter_layout.addWidget(self.id_min_edit)
        
        filter_layout.addWidget(QLabel("-"))
        self.id_max_edit = QLineEdit()
        self.id_max_edit.setPlaceholderText("0x7FF")
        self.id_max_edit.setMaximumWidth(80)
        filter_layout.addWidget(self.id_max_edit)
        
        # Direction filter
        filter_layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["All", "RX", "TX"])
        filter_layout.addWidget(self.direction_combo)
        
        # Data pattern filter
        filter_layout.addWidget(QLabel("Data Pattern:"))
        self.data_pattern_edit = QLineEdit()
        self.data_pattern_edit.setPlaceholderText("DEADBEEF")
        filter_layout.addWidget(self.data_pattern_edit)
        
        # Message name filter
        filter_layout.addWidget(QLabel("Message:"))
        self.message_name_edit = QLineEdit()
        self.message_name_edit.setPlaceholderText("Engine_Data")
        filter_layout.addWidget(self.message_name_edit)
        
        # Signal name filter
        filter_layout.addWidget(QLabel("Signal:"))
        self.signal_name_edit = QLineEdit()
        self.signal_name_edit.setPlaceholderText("RPM")
        filter_layout.addWidget(self.signal_name_edit)
        
        # Apply button
        self.apply_filter_btn = QPushButton("Apply Filters")
        self.apply_filter_btn.clicked.connect(self.apply_filters_async)
        filter_layout.addWidget(self.apply_filter_btn)
        
        # Clear button
        self.clear_filter_btn = QPushButton("Clear")
        self.clear_filter_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(self.clear_filter_btn)
        
        layout.addWidget(filter_group)
    
    def create_message_table(self):
        """Create optimized message table"""
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(8)
        
        headers = ["Timestamp", "Dir", "ID", "DBC Name", "DLC", "Data", "Decoded Signals", "Count"]
        self.message_table.setHorizontalHeaderLabels(headers)
        
        # Optimize table for performance
        self.message_table.setAlternatingRowColors(True)
        self.message_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.message_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.message_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        
        # Set column widths
        header = self.message_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(1, QHeaderView.Fixed)             # Direction
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # DBC Name
        header.setSectionResizeMode(4, QHeaderView.Fixed)             # DLC
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # Data
        header.setSectionResizeMode(6, QHeaderView.Stretch)           # Signals
        header.setSectionResizeMode(7, QHeaderView.Fixed)             # Count
        
        self.message_table.setColumnWidth(1, 45)  # Direction
        self.message_table.setColumnWidth(4, 45)  # DLC
        self.message_table.setColumnWidth(7, 60)  # Count
        
        # Connect selection signal
        self.message_table.itemSelectionChanged.connect(self.on_message_selected)
    
    def create_details_panel(self):
        """Create message details panel"""
        self.details_panel = QGroupBox("📋 Message Details")
        layout = QHBoxLayout(self.details_panel)
        
        # Raw data view
        raw_group = QGroupBox("Raw Data")
        raw_layout = QVBoxLayout(raw_group)
        self.raw_data_text = QTextEdit()
        self.raw_data_text.setMaximumHeight(100)
        self.raw_data_text.setFont(QFont("Consolas", 10))
        raw_layout.addWidget(self.raw_data_text)
        layout.addWidget(raw_group)
        
        # Decoded signals view
        signals_group = QGroupBox("Decoded Signals")
        signals_layout = QVBoxLayout(signals_group)
        self.signals_text = QTextEdit()
        self.signals_text.setMaximumHeight(100)
        signals_layout.addWidget(self.signals_text)
        layout.addWidget(signals_group)
    
    def create_control_panel(self, layout):
        """Create control panel"""
        control_group = QGroupBox("⚙️ Controls")
        control_layout = QHBoxLayout(control_group)
        
        # Auto-scroll
        self.auto_scroll_cb = QCheckBox("Auto Scroll")
        self.auto_scroll_cb.setChecked(True)
        control_layout.addWidget(self.auto_scroll_cb)
        
        # Group by ID
        self.group_by_id_cb = QCheckBox("Group by ID")
        control_layout.addWidget(self.group_by_id_cb)
        
        # Max messages
        control_layout.addWidget(QLabel("Max Messages:"))
        self.max_msg_spin = QSpinBox()
        self.max_msg_spin.setRange(100, 50000)
        self.max_msg_spin.setValue(self.max_messages)
        self.max_msg_spin.valueChanged.connect(self.update_max_messages)
        control_layout.addWidget(self.max_msg_spin)
        
        control_layout.addStretch()
        
        # Action buttons
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.clicked.connect(self.toggle_processing)
        control_layout.addWidget(self.pause_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_messages)
        control_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_messages)
        control_layout.addWidget(self.export_btn)
        
        layout.addWidget(control_group)
    
    def connect_threading_signals(self):
        """Connect signals from worker threads"""
        # Message processing signals
        processor = self.threading_manager.message_processor
        processor.batch_processed.connect(self.display_manager.add_messages_batch)
        processor.statistics_updated.connect(self.update_statistics_display)
        processor.processing_error.connect(self.handle_processing_error)
        
        # Filter signals
        processor.filter_applied.connect(self.on_filter_applied)
    
    @Slot(dict)
    def add_can_message(self, raw_message: dict):
        """Public interface to add CAN message (thread-safe entry point)"""
        # This immediately queues the message for background processing
        self.threading_manager.message_processor.add_raw_message(raw_message)
        
        # Update total counter on UI thread
        self.stats['total_received'] += 1
    
    def apply_filters_async(self):
        """Apply filters using worker thread"""
        try:
            # Parse filter criteria
            criteria = {
                'enabled': True,
                'id_min': self._parse_id(self.id_min_edit.text()) if self.id_min_edit.text() else None,
                'id_max': self._parse_id(self.id_max_edit.text()) if self.id_max_edit.text() else None,
                'direction': self.direction_combo.currentText() if self.direction_combo.currentText() != "All" else None,
                'data_pattern': self.data_pattern_edit.text().replace(' ', '') if self.data_pattern_edit.text() else None,
                'message_name': self.message_name_edit.text() if self.message_name_edit.text() else None,
                'signal_name': self.signal_name_edit.text() if self.signal_name_edit.text() else None
            }
            
            # Send to worker thread for processing
            self.threading_manager.message_processor.update_filter_criteria(criteria)
            
            # Show progress indicator
            self.processing_progress.setVisible(True)
            self.processing_progress.setValue(0)
            
        except Exception as e:
            print(f"❌ Filter application error: {e}")
    
    def _parse_id(self, id_str: str) -> Optional[int]:
        """Parse CAN ID from string"""
        if not id_str:
            return None
        
        try:
            if id_str.startswith('0x') or id_str.startswith('0X'):
                return int(id_str, 16)
            else:
                return int(id_str)
        except ValueError:
            return None
    
    def clear_filters(self):
        """Clear all filter fields"""
        self.id_min_edit.clear()
        self.id_max_edit.clear()
        self.direction_combo.setCurrentIndex(0)
        self.data_pattern_edit.clear()
        self.message_name_edit.clear()
        self.signal_name_edit.clear()
        
        # Apply empty filter
        criteria = {'enabled': False}
        self.threading_manager.message_processor.update_filter_criteria(criteria)
    
    @Slot(dict)
    def update_statistics_display(self, stats: dict):
        """Update statistics display (runs on UI thread)"""
        self.stats.update(stats)
        
        # Update labels
        self.total_label.setText(f"Total: {self.stats['total_received']}")
        self.rate_label.setText(f"Rate: {self.stats['messages_per_second']:.0f} msg/s")
        self.filtered_label.setText(f"Filtered: {self.stats['filtered_count']}")
        self.decoded_label.setText(f"Decoded: {self.stats['decode_success_rate']*100:.1f}%")
        self.cpu_label.setText(f"CPU: {self.stats['processing_time_ms']:.1f}ms")
        
        # Emit statistics signal
        self.statistics_updated.emit(self.stats)
    
    @Slot(list)
    def on_filter_applied(self, filtered_messages: List[CANMessage]):
        """Handle filter application results"""
        # Clear table and display filtered results
        self.message_table.setRowCount(0)
        
        if filtered_messages:
            self.display_manager.add_messages_batch(filtered_messages)
        
        # Hide progress indicator
        self.processing_progress.setVisible(False)
        
        print(f"✅ Filter applied: {len(filtered_messages)} messages match criteria")
    
    @Slot(str)
    def handle_processing_error(self, error_message: str):
        """Handle processing errors from worker threads"""
        print(f"❌ Processing error: {error_message}")
        # Could show error in status bar or notification
    
    def on_message_selected(self):
        """Handle message selection"""
        current_row = self.message_table.currentRow()
        if current_row >= 0:
            # Get message data from table
            id_item = self.message_table.item(current_row, 2)
            data_item = self.message_table.item(current_row, 5)
            signals_item = self.message_table.item(current_row, 6)
            
            if id_item and data_item:
                # Update details panel
                raw_data = f"ID: {id_item.text()}\\nData: {data_item.text()}"
                self.raw_data_text.setPlainText(raw_data)
                
                if signals_item and signals_item.text():
                    self.signals_text.setPlainText(signals_item.text())
                else:
                    self.signals_text.setPlainText("No decoded signals available")
                
                # Emit selection signal
                message_data = {
                    'id': id_item.text(),
                    'data': data_item.text(),
                    'signals': signals_item.text() if signals_item else ""
                }
                self.message_selected.emit(message_data)
    
    def toggle_processing(self):
        """Toggle message processing"""
        if self.pause_btn.text() == "⏸️ Pause":
            self.threading_manager.message_processor.set_processing_enabled(False)
            self.pause_btn.setText("▶️ Resume")
        else:
            self.threading_manager.message_processor.set_processing_enabled(True)
            self.pause_btn.setText("⏸️ Pause")
    
    def clear_messages(self):
        """Clear all messages"""
        self.message_table.setRowCount(0)
        self.raw_data_text.clear()
        self.signals_text.clear()
        self.stats['total_received'] = 0
        self.stats['total_displayed'] = 0
        print("🗑️ Message log cleared")
    
    def update_max_messages(self, value: int):
        """Update maximum message limit"""
        self.max_messages = value
        self.display_manager.max_displayed_messages = value
    
    def export_messages(self):
        """Export messages (placeholder)"""
        self.export_requested.emit()
        print("📤 Export requested")
    
    def set_dbc_manager(self, dbc_manager):
        """Set DBC manager and update worker threads"""
        self.dbc_manager = dbc_manager
        self.threading_manager.set_dbc_manager(dbc_manager)
        print("🔄 DBC manager updated in worker threads")
    
    def refresh_dbc(self):
        """Refresh DBC decoding (handled by worker threads)"""
        if self.dbc_manager:
            self.threading_manager.set_dbc_manager(self.dbc_manager)
            print("🔄 DBC refresh triggered in worker threads")
    
    def apply_professional_style(self):
        """Apply professional styling"""
        style = """
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 5px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTableWidget {
            gridline-color: #e0e0e0;
            selection-background-color: #3498db;
            alternate-background-color: #f8f9fa;
        }
        QProgressBar {
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            background-color: #ecf0f1;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 2px;
        }
        """
        self.setStyleSheet(style)
    
    def closeEvent(self, event):
        """Clean shutdown of worker threads"""
        print("🔄 Shutting down message log worker threads...")
        self.threading_manager.shutdown()
        event.accept()


# Alias for compatibility
ProfessionalMessageLog = EnhancedMessageLog
