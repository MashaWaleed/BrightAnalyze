"""
Signal Plotter for Professional CAN Analyzer
Real-time signal visualization and trending
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QListWidget, QListWidgetItem, QPushButton,
                               QCheckBox, QLabel, QComboBox, QSpinBox,
                               QSlider, QSplitter, QFrame, QFormLayout)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFont
import random
import time
from collections import deque

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

class SimpleSignalPlot(QWidget):
    """Simple signal plotting widget when pyqtgraph is not available"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.signals = {}
        self.time_range = 30  # seconds
        self.max_points = 300
        
    def add_signal(self, name, color=None):
        """Add a signal to plot"""
        if color is None:
            colors = [Qt.red, Qt.blue, Qt.green, Qt.magenta, Qt.cyan]
            color = colors[len(self.signals) % len(colors)]
            
        self.signals[name] = {
            'data': deque(maxlen=self.max_points),
            'times': deque(maxlen=self.max_points),
            'color': color,
            'visible': True
        }
        
    def add_data_point(self, signal_name, value, timestamp=None):
        """Add data point to signal"""
        if signal_name not in self.signals:
            self.add_signal(signal_name)
            
        if timestamp is None:
            timestamp = time.time()
            
        signal = self.signals[signal_name]
        signal['data'].append(value)
        signal['times'].append(timestamp)
        
        self.update()
        
    def clear_signal(self, signal_name):
        """Clear signal data"""
        if signal_name in self.signals:
            self.signals[signal_name]['data'].clear()
            self.signals[signal_name]['times'].clear()
            self.update()
            
    def set_signal_visible(self, signal_name, visible):
        """Set signal visibility"""
        if signal_name in self.signals:
            self.signals[signal_name]['visible'] = visible
            self.update()
            
    def paintEvent(self, event):
        """Paint the plot"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # Draw border
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        if not self.signals:
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(self.rect(), Qt.AlignCenter, "No signals to display")
            return
            
        # Calculate plot area
        margin = 40
        plot_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        
        # Find data ranges
        current_time = time.time()
        min_time = current_time - self.time_range
        
        all_values = []
        for signal in self.signals.values():
            if signal['visible'] and signal['data']:
                all_values.extend(signal['data'])
                
        if not all_values:
            return
            
        min_value = min(all_values)
        max_value = max(all_values)
        value_range = max_value - min_value
        if value_range == 0:
            value_range = 1
            
        # Draw grid
        painter.setPen(QPen(QColor(240, 240, 240), 1))
        for i in range(1, 5):
            y = plot_rect.top() + (plot_rect.height() * i // 5)
            painter.drawLine(plot_rect.left(), y, plot_rect.right(), y)
            
        for i in range(1, 6):
            x = plot_rect.left() + (plot_rect.width() * i // 6)
            painter.drawLine(x, plot_rect.top(), x, plot_rect.bottom())
            
        # Draw signals
        for signal_name, signal in self.signals.items():
            if not signal['visible'] or len(signal['data']) < 2:
                continue
                
            painter.setPen(QPen(QColor(signal['color']), 2))
            
            points = []
            for i, (value, timestamp) in enumerate(zip(signal['data'], signal['times'])):
                if timestamp >= min_time:
                    x = plot_rect.left() + int((timestamp - min_time) / self.time_range * plot_rect.width())
                    y = plot_rect.bottom() - int((value - min_value) / value_range * plot_rect.height())
                    points.append((x, y))
                    
            # Draw lines between points
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
                
        # Draw axes labels
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 8))
        
        # Y-axis labels
        for i in range(6):
            value = min_value + (value_range * i / 5)
            y = plot_rect.bottom() - (plot_rect.height() * i // 5)
            painter.drawText(5, y + 3, f"{value:.1f}")
            
        # X-axis labels (time)
        for i in range(7):
            time_offset = self.time_range * i / 6
            timestamp = current_time - self.time_range + time_offset
            x = plot_rect.left() + (plot_rect.width() * i // 6)
            painter.drawText(x - 20, self.height() - 5, f"-{self.time_range - time_offset:.0f}s")

class SignalPlotter(QWidget):
    """Professional signal plotter with real-time capabilities"""
    
    def refresh_dbc(self):
        """Refresh available signals/messages when DBC changes."""
        # TODO: Implement signal list refresh and UI update
        pass
    
    # Signals
    signal_added = Signal(str)
    signal_removed = Signal(str)
    plotting_started = Signal()
    plotting_stopped = Signal()
    
    def __init__(self, parent=None, dbc_manager=None):
        super().__init__(parent)
        self.dbc_manager = dbc_manager
        self.available_signals = {}
        self.plotted_signals = {}
        self.is_plotting = False
        
        self.setup_ui()
        self.setup_timers()
        self.apply_modern_style()
        
    def setup_ui(self):
        """Setup the signal plotter UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create splitter for signal list and plot area
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - signal controls
        self.setup_signal_controls(splitter)
        
        # Right side - plot area
        self.setup_plot_area(splitter)
        
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        # Bottom controls
        self.setup_plot_controls(layout)
        
    def setup_signal_controls(self, parent):
        """Setup signal control panel"""
        controls_widget = QWidget()
        layout = QVBoxLayout(controls_widget)
        layout.setSpacing(8)
        
        # Available signals
        available_group = QGroupBox("📊 Available Signals")
        available_layout = QVBoxLayout(available_group)
        
        self.available_list = QListWidget()
        self.available_list.setMaximumHeight(150)
        available_layout.addWidget(self.available_list)
        
        # Add/Remove buttons
        button_layout = QHBoxLayout()
        self.add_signal_btn = QPushButton("➕ Add to Plot")
        self.add_signal_btn.clicked.connect(self.add_selected_signal)
        self.add_signal_btn.setEnabled(False)
        button_layout.addWidget(self.add_signal_btn)
        
        self.refresh_signals_btn = QPushButton("🔄 Refresh")
        self.refresh_signals_btn.clicked.connect(self.refresh_available_signals)
        button_layout.addWidget(self.refresh_signals_btn)
        
        available_layout.addLayout(button_layout)
        layout.addWidget(available_group)
        
        # Plotted signals
        plotted_group = QGroupBox("📈 Plotted Signals")
        plotted_layout = QVBoxLayout(plotted_group)
        
        self.plotted_list = QListWidget()
        self.plotted_list.itemChanged.connect(self.signal_visibility_changed)
        plotted_layout.addWidget(self.plotted_list)
        
        # Remove button
        remove_layout = QHBoxLayout()
        self.remove_signal_btn = QPushButton("➖ Remove from Plot")
        self.remove_signal_btn.clicked.connect(self.remove_selected_signal)
        self.remove_signal_btn.setEnabled(False)
        remove_layout.addWidget(self.remove_signal_btn)
        
        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all_signals)
        remove_layout.addWidget(self.clear_all_btn)
        
        plotted_layout.addLayout(remove_layout)
        layout.addWidget(plotted_group)
        
        # Plot settings
        settings_group = QGroupBox("⚙️ Plot Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.time_range_spin = QSpinBox()
        self.time_range_spin.setRange(5, 300)
        self.time_range_spin.setValue(30)
        self.time_range_spin.setSuffix(" seconds")
        self.time_range_spin.valueChanged.connect(self.update_time_range)
        settings_layout.addRow("Time Range:", self.time_range_spin)
        
        self.update_rate_combo = QComboBox()
        self.update_rate_combo.addItems(["10 Hz", "20 Hz", "50 Hz", "100 Hz"])
        self.update_rate_combo.setCurrentText("20 Hz")
        self.update_rate_combo.currentTextChanged.connect(self.update_refresh_rate)
        settings_layout.addRow("Update Rate:", self.update_rate_combo)
        
        self.auto_scale_cb = QCheckBox("Auto Scale Y-Axis")
        self.auto_scale_cb.setChecked(True)
        settings_layout.addRow(self.auto_scale_cb)
        
        layout.addWidget(settings_group)
        layout.addStretch()
        
        # Connect selection signals
        self.available_list.itemSelectionChanged.connect(self.available_selection_changed)
        self.plotted_list.itemSelectionChanged.connect(self.plotted_selection_changed)
        
        parent.addWidget(controls_widget)
        
    def setup_plot_area(self, parent):
        """Setup plot area"""
        plot_widget = QWidget()
        layout = QVBoxLayout(plot_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Plot area
        plot_group = QGroupBox("📈 Real-time Signal Plot")
        plot_layout = QVBoxLayout(plot_group)
        
        if PYQTGRAPH_AVAILABLE:
            # Use pyqtgraph for better performance
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setLabel('left', 'Value')
            self.plot_widget.setLabel('bottom', 'Time (seconds)')
            self.plot_widget.showGrid(x=True, y=True)
            self.plot_widget.setBackground('w')
        else:
            # Use simple custom plot widget
            self.plot_widget = SimpleSignalPlot()
            
        plot_layout.addWidget(self.plot_widget)
        layout.addWidget(plot_group)
        
        # Plot statistics
        stats_group = QGroupBox("📊 Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.signal_count_label = QLabel("0")
        self.update_rate_label = QLabel("0 Hz")
        self.data_points_label = QLabel("0")
        
        stats_layout.addRow("Active Signals:", self.signal_count_label)
        stats_layout.addRow("Actual Rate:", self.update_rate_label)
        stats_layout.addRow("Data Points:", self.data_points_label)
        
        layout.addWidget(stats_group)
        
        parent.addWidget(plot_widget)
        
    def setup_plot_controls(self, parent_layout):
        """Setup plot control buttons"""
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.Box)
        controls_layout = QHBoxLayout(controls_frame)
        
        self.start_plot_btn = QPushButton("▶️ Start Plotting")
        self.start_plot_btn.clicked.connect(self.start_plotting)
        controls_layout.addWidget(self.start_plot_btn)
        
        self.stop_plot_btn = QPushButton("⏹️ Stop Plotting")
        self.stop_plot_btn.clicked.connect(self.stop_plotting)
        self.stop_plot_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_plot_btn)
        
        self.pause_plot_btn = QPushButton("⏸️ Pause")
        self.pause_plot_btn.clicked.connect(self.pause_plotting)
        self.pause_plot_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_plot_btn)
        
        controls_layout.addStretch()
        
        self.export_btn = QPushButton("📤 Export Data")
        self.export_btn.clicked.connect(self.export_plot_data)
        controls_layout.addWidget(self.export_btn)
        
        self.screenshot_btn = QPushButton("📷 Screenshot")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        controls_layout.addWidget(self.screenshot_btn)
        
        parent_layout.addWidget(controls_frame)
        
    def setup_timers(self):
        """Setup update timers"""
        # Data update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot_data)
        
        # Statistics timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(1000)  # Update stats every second
        
        # Sample data generation (for demo)
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.generate_demo_data)
        
    def refresh_available_signals(self):
        """Refresh list of available signals"""
        self.available_list.clear()
        
        # Add sample signals for demo
        sample_signals = [
            "Engine RPM",
            "Vehicle Speed", 
            "Engine Temperature",
            "Throttle Position",
            "Fuel Level",
            "Battery Voltage",
            "Oil Pressure",
            "Intake Air Temperature",
            "Coolant Temperature",
            "Transmission Temperature"
        ]
        
        for signal in sample_signals:
            self.available_signals[signal] = {
                'unit': self.get_signal_unit(signal),
                'range': self.get_signal_range(signal),
                'color': self.get_signal_color(signal)
            }
            
        for signal_name in self.available_signals:
            item = QListWidgetItem(signal_name)
            self.available_list.addItem(item)
            
    def get_signal_unit(self, signal_name):
        """Get unit for signal"""
        units = {
            "Engine RPM": "rpm",
            "Vehicle Speed": "km/h",
            "Engine Temperature": "°C",
            "Throttle Position": "%",
            "Fuel Level": "%",
            "Battery Voltage": "V",
            "Oil Pressure": "bar",
            "Intake Air Temperature": "°C",
            "Coolant Temperature": "°C",
            "Transmission Temperature": "°C"
        }
        return units.get(signal_name, "")
        
    def get_signal_range(self, signal_name):
        """Get expected range for signal"""
        ranges = {
            "Engine RPM": (0, 8000),
            "Vehicle Speed": (0, 200),
            "Engine Temperature": (-40, 150),
            "Throttle Position": (0, 100),
            "Fuel Level": (0, 100),
            "Battery Voltage": (10, 15),
            "Oil Pressure": (0, 10),
            "Intake Air Temperature": (-40, 100),
            "Coolant Temperature": (-40, 150),
            "Transmission Temperature": (-40, 150)
        }
        return ranges.get(signal_name, (0, 100))
        
    def get_signal_color(self, signal_name):
        """Get color for signal"""
        colors = ['red', 'blue', 'green', 'magenta', 'cyan', 'yellow', 'orange', 'purple']
        color_index = hash(signal_name) % len(colors)
        return colors[color_index]
        
    def available_selection_changed(self):
        """Handle available signal selection change"""
        self.add_signal_btn.setEnabled(len(self.available_list.selectedItems()) > 0)
        
    def plotted_selection_changed(self):
        """Handle plotted signal selection change"""
        self.remove_signal_btn.setEnabled(len(self.plotted_list.selectedItems()) > 0)
        
    def add_selected_signal(self):
        """Add selected signal to plot"""
        selected_items = self.available_list.selectedItems()
        for item in selected_items:
            signal_name = item.text()
            if signal_name not in self.plotted_signals:
                self.add_signal_to_plot(signal_name)
                
    def add_signal_to_plot(self, signal_name):
        """Add signal to plot"""
        if signal_name in self.available_signals:
            signal_info = self.available_signals[signal_name]
            
            # Add to plotted signals
            self.plotted_signals[signal_name] = {
                'data': deque(maxlen=1000),
                'times': deque(maxlen=1000),
                'visible': True,
                **signal_info
            }
            
            # Add to plot widget
            if hasattr(self.plot_widget, 'add_signal'):
                self.plot_widget.add_signal(signal_name, signal_info['color'])
            elif PYQTGRAPH_AVAILABLE:
                pen = pg.mkPen(color=signal_info['color'], width=2)
                curve = self.plot_widget.plot([], [], pen=pen, name=signal_name)
                self.plotted_signals[signal_name]['curve'] = curve
                
            # Add to plotted list with checkbox
            item = QListWidgetItem(signal_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.plotted_list.addItem(item)
            
            self.signal_added.emit(signal_name)
            
    def remove_selected_signal(self):
        """Remove selected signal from plot"""
        selected_items = self.plotted_list.selectedItems()
        for item in selected_items:
            signal_name = item.text()
            self.remove_signal_from_plot(signal_name)
            
    def remove_signal_from_plot(self, signal_name):
        """Remove signal from plot"""
        if signal_name in self.plotted_signals:
            # Remove from plot widget
            if hasattr(self.plot_widget, 'signals') and signal_name in self.plot_widget.signals:
                del self.plot_widget.signals[signal_name]
            elif PYQTGRAPH_AVAILABLE and 'curve' in self.plotted_signals[signal_name]:
                self.plot_widget.removeItem(self.plotted_signals[signal_name]['curve'])
                
            # Remove from plotted signals
            del self.plotted_signals[signal_name]
            
            # Remove from list
            for i in range(self.plotted_list.count()):
                item = self.plotted_list.item(i)
                if item.text() == signal_name:
                    self.plotted_list.takeItem(i)
                    break
                    
            self.signal_removed.emit(signal_name)
            
    def clear_all_signals(self):
        """Clear all plotted signals"""
        signal_names = list(self.plotted_signals.keys())
        for signal_name in signal_names:
            self.remove_signal_from_plot(signal_name)
            
    def signal_visibility_changed(self, item):
        """Handle signal visibility change"""
        signal_name = item.text()
        visible = item.checkState() == Qt.Checked
        
        if signal_name in self.plotted_signals:
            self.plotted_signals[signal_name]['visible'] = visible
            
            if hasattr(self.plot_widget, 'set_signal_visible'):
                self.plot_widget.set_signal_visible(signal_name, visible)
            elif PYQTGRAPH_AVAILABLE and 'curve' in self.plotted_signals[signal_name]:
                curve = self.plotted_signals[signal_name]['curve']
                curve.setVisible(visible)
                
    def start_plotting(self):
        """Start real-time plotting"""
        self.is_plotting = True
        
        # Start timers
        rate_text = self.update_rate_combo.currentText()
        rate_hz = int(rate_text.split()[0])
        interval = 1000 // rate_hz  # Convert to milliseconds
        
        self.update_timer.start(interval)
        self.demo_timer.start(100)  # Demo data at 10 Hz
        
        # Update UI
        self.start_plot_btn.setEnabled(False)
        self.stop_plot_btn.setEnabled(True)
        self.pause_plot_btn.setEnabled(True)
        
        self.plotting_started.emit()
        
    def stop_plotting(self):
        """Stop real-time plotting"""
        self.is_plotting = False
        
        # Stop timers
        self.update_timer.stop()
        self.demo_timer.stop()
        
        # Update UI
        self.start_plot_btn.setEnabled(True)
        self.stop_plot_btn.setEnabled(False)
        self.pause_plot_btn.setEnabled(False)
        
        self.plotting_stopped.emit()
        
    def pause_plotting(self):
        """Pause/resume plotting"""
        if self.update_timer.isActive():
            self.update_timer.stop()
            self.demo_timer.stop()
            self.pause_plot_btn.setText("▶️ Resume")
        else:
            rate_text = self.update_rate_combo.currentText()
            rate_hz = int(rate_text.split()[0])
            interval = 1000 // rate_hz
            
            self.update_timer.start(interval)
            self.demo_timer.start(100)
            self.pause_plot_btn.setText("⏸️ Pause")
            
    def update_time_range(self, value):
        """Update time range"""
        if hasattr(self.plot_widget, 'time_range'):
            self.plot_widget.time_range = value
            
    def update_refresh_rate(self, rate_text):
        """Update refresh rate"""
        if self.is_plotting:
            rate_hz = int(rate_text.split()[0])
            interval = 1000 // rate_hz
            self.update_timer.start(interval)
            
    def generate_demo_data(self):
        """Generate demo data for signals"""
        current_time = time.time()
        
        for signal_name, signal_info in self.plotted_signals.items():
            if not signal_info['visible']:
                continue
                
            # Generate realistic demo data
            min_val, max_val = signal_info['range']
            
            if signal_name == "Engine RPM":
                value = 1500 + 500 * (1 + 0.8 * random.random())
            elif signal_name == "Vehicle Speed":
                value = 60 + 20 * random.random()
            elif "Temperature" in signal_name:
                value = 80 + 10 * random.random()
            elif "Position" in signal_name or "Level" in signal_name:
                value = 50 + 30 * random.random()
            elif signal_name == "Battery Voltage":
                value = 12.5 + 0.5 * random.random()
            else:
                value = min_val + (max_val - min_val) * random.random()
                
            self.add_data_point(signal_name, value, current_time)
            
    def add_data_point(self, signal_name, value, timestamp=None):
        """Add data point to signal"""
        if signal_name not in self.plotted_signals:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        signal = self.plotted_signals[signal_name]
        signal['data'].append(value)
        signal['times'].append(timestamp)
        
    def update_plot_data(self):
        """Update plot with new data"""
        if not self.is_plotting:
            return
            
        current_time = time.time()
        time_range = self.time_range_spin.value()
        min_time = current_time - time_range
        
        for signal_name, signal in self.plotted_signals.items():
            if not signal['visible']:
                continue
                
            # Filter data to time range
            valid_indices = [i for i, t in enumerate(signal['times']) if t >= min_time]
            
            if valid_indices:
                times = [signal['times'][i] - current_time for i in valid_indices]
                values = [signal['data'][i] for i in valid_indices]
                
                if hasattr(self.plot_widget, 'add_data_point'):
                    # Simple plot widget
                    for value, timestamp in zip(values, times):
                        self.plot_widget.add_data_point(signal_name, value, current_time + timestamp)
                elif PYQTGRAPH_AVAILABLE and 'curve' in signal:
                    # PyQtGraph
                    signal['curve'].setData(times, values)
                    
        # Update plot widget
        if hasattr(self.plot_widget, 'update'):
            self.plot_widget.update()
            
    def update_statistics(self):
        """Update statistics display"""
        signal_count = len([s for s in self.plotted_signals.values() if s['visible']])
        self.signal_count_label.setText(str(signal_count))
        
        # Calculate actual update rate (simplified)
        if self.is_plotting:
            rate_text = self.update_rate_combo.currentText()
            self.update_rate_label.setText(rate_text)
        else:
            self.update_rate_label.setText("0 Hz")
            
        # Total data points
        total_points = sum(len(s['data']) for s in self.plotted_signals.values())
        self.data_points_label.setText(str(total_points))
        
    def export_plot_data(self):
        """Export plot data to file"""
        # Placeholder for data export functionality
        print("Export plot data (not implemented)")
        
    def take_screenshot(self):
        """Take screenshot of plot"""
        # Placeholder for screenshot functionality  
        print("Take screenshot (not implemented)")
        
    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin: 8px 0;
                padding-top: 12px;
                background-color: #fafafa;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            
            QListWidget {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
            
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e9ecef;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
        """)