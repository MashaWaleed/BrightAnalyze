"""
Scripting Console for Professional CAN Analyzer
Python scripting and automation capabilities
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QSplitter, QGroupBox, QLabel,
                               QComboBox, QFileDialog, QMessageBox, QListWidget,
                               QListWidgetItem, QTabWidget, QLineEdit)
from PySide6.QtCore import Signal, Qt, QThread, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat
import sys
import io
import traceback
import os

class PythonExecutor(QThread):
    """Thread for executing Python code safely"""
    
    output_ready = Signal(str)
    error_ready = Signal(str)
    execution_finished = Signal()
    
    def __init__(self):
        super().__init__()
        self.code = ""
        self.globals_dict = {}
        
    def set_code(self, code, globals_dict=None):
        """Set code to execute"""
        self.code = code
        if globals_dict:
            self.globals_dict = globals_dict
            
    def run(self):
        """Execute the Python code"""
        try:
            # Redirect stdout and stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Execute the code
            exec(self.code, self.globals_dict)
            
            # Get output
            output = stdout_capture.getvalue()
            if output:
                self.output_ready.emit(output)
                
            # Check for errors
            errors = stderr_capture.getvalue()
            if errors:
                self.error_ready.emit(errors)
                
        except Exception as e:
            self.error_ready.emit(f"Error: {str(e)}\n{traceback.format_exc()}")
            
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.execution_finished.emit()

class ScriptingConsole(QWidget):
    """Professional Python scripting console"""
    
    # Signals
    execute_script = Signal(str)
    script_saved = Signal(str)
    script_loaded = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.script_history = []
        self.current_history_index = -1
        self.python_executor = PythonExecutor()
        self.setup_globals()
        
        self.setup_ui()
        self.setup_connections()
        self.apply_modern_style()
        
    def setup_ui(self):
        """Setup the scripting console UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Console Tab
        self.setup_console_tab()
        
        # Script Editor Tab
        self.setup_editor_tab()
        
        # Examples Tab
        self.setup_examples_tab()
        
        layout.addWidget(self.tab_widget)
        
    def setup_console_tab(self):
        """Setup interactive console tab"""
        console_widget = QWidget()
        layout = QVBoxLayout(console_widget)
        layout.setSpacing(4)
        
        # Output area
        output_group = QGroupBox("🐍 Python Console Output")
        output_layout = QVBoxLayout(output_group)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.append("Welcome to CAN Analyzer Python Console")
        self.output_area.append("Type Python code below and press Execute")
        self.output_area.append("Available objects: can_interface, message_log, dbc_manager")
        self.output_area.append("-" * 50)
        output_layout.addWidget(self.output_area)
        
        layout.addWidget(output_group)
        
        # Input area
        input_group = QGroupBox("📝 Code Input")
        input_layout = QVBoxLayout(input_group)
        
        self.code_input = QTextEdit()
        self.code_input.setFont(QFont("Consolas", 10))
        self.code_input.setMaximumHeight(120)
        self.code_input.setPlaceholderText("Enter Python code here...")
        input_layout.addWidget(self.code_input)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.execute_btn = QPushButton("▶️ Execute")
        self.execute_btn.clicked.connect(self.execute_code)
        button_layout.addWidget(self.execute_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear Output")
        self.clear_btn.clicked.connect(self.clear_output)
        button_layout.addWidget(self.clear_btn)
        
        self.history_btn = QPushButton("📜 History")
        self.history_btn.clicked.connect(self.show_history)
        button_layout.addWidget(self.history_btn)
        
        button_layout.addStretch()
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        input_layout.addLayout(button_layout)
        layout.addWidget(input_group)
        
        self.tab_widget.addTab(console_widget, "🐍 Console")
        
    def setup_editor_tab(self):
        """Setup script editor tab"""
        editor_widget = QWidget()
        layout = QVBoxLayout(editor_widget)
        layout.setSpacing(4)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.new_script_btn = QPushButton("📄 New")
        self.new_script_btn.clicked.connect(self.new_script)
        toolbar_layout.addWidget(self.new_script_btn)
        
        self.open_script_btn = QPushButton("📁 Open")
        self.open_script_btn.clicked.connect(self.open_script)
        toolbar_layout.addWidget(self.open_script_btn)
        
        self.save_script_btn = QPushButton("💾 Save")
        self.save_script_btn.clicked.connect(self.save_script)
        toolbar_layout.addWidget(self.save_script_btn)
        
        toolbar_layout.addStretch()
        
        self.run_script_btn = QPushButton("▶️ Run Script")
        self.run_script_btn.clicked.connect(self.run_script)
        toolbar_layout.addWidget(self.run_script_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Script editor
        editor_group = QGroupBox("📝 Script Editor")
        editor_layout = QVBoxLayout(editor_group)
        
        # File name
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))
        self.filename_label = QLabel("untitled.py")
        self.filename_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(self.filename_label)
        file_layout.addStretch()
        editor_layout.addLayout(file_layout)
        
        # Editor
        self.script_editor = QTextEdit()
        self.script_editor.setFont(QFont("Consolas", 10))
        self.script_editor.setPlainText(self.get_template_script())
        editor_layout.addWidget(self.script_editor)
        
        layout.addWidget(editor_group)
        
        self.tab_widget.addTab(editor_widget, "📝 Editor")
        
    def setup_examples_tab(self):
        """Setup examples tab"""
        examples_widget = QWidget()
        layout = QHBoxLayout(examples_widget)
        layout.setSpacing(8)
        
        # Examples list
        list_group = QGroupBox("📚 Example Scripts")
        list_layout = QVBoxLayout(list_group)
        
        self.examples_list = QListWidget()
        self.populate_examples()
        self.examples_list.itemClicked.connect(self.load_example)
        list_layout.addWidget(self.examples_list)
        
        layout.addWidget(list_group)
        
        # Example preview
        preview_group = QGroupBox("👁️ Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.example_preview = QTextEdit()
        self.example_preview.setReadOnly(True)
        self.example_preview.setFont(QFont("Consolas", 9))
        preview_layout.addWidget(self.example_preview)
        
        # Load to editor button
        load_layout = QHBoxLayout()
        load_layout.addStretch()
        self.load_example_btn = QPushButton("📋 Load to Editor")
        self.load_example_btn.clicked.connect(self.load_example_to_editor)
        self.load_example_btn.setEnabled(False)
        load_layout.addWidget(self.load_example_btn)
        
        preview_layout.addLayout(load_layout)
        layout.addWidget(preview_group)
        
        self.tab_widget.addTab(examples_widget, "📚 Examples")
        
    def setup_connections(self):
        """Setup signal connections"""
        self.python_executor.output_ready.connect(self.append_output)
        self.python_executor.error_ready.connect(self.append_error)
        self.python_executor.execution_finished.connect(self.execution_finished)
        
    def setup_globals(self):
        """Setup global variables for script execution"""
        self.globals_dict = {
            '__builtins__': __builtins__,
            'can_interface': None,  # Will be set by main application
            'message_log': None,    # Will be set by main application
            'dbc_manager': None,    # Will be set by main application
            'print': self.script_print,
            'help': self.script_help
        }
        
    def script_print(self, *args, **kwargs):
        """Custom print function for scripts"""
        output = " ".join(str(arg) for arg in args)
        self.append_output(output + "\n")
        
    def script_help(self, obj=None):
        """Custom help function for scripts"""
        if obj is None:
            help_text = """
Available CAN Analyzer Objects:
- can_interface: CAN bus interface control
- message_log: Message log management
- dbc_manager: DBC file management

Example usage:
  can_interface.send_message(0x123, [0x01, 0x02, 0x03])
  messages = message_log.get_messages()
  dbc_manager.decode_message(0x123, data)
            """
            self.append_output(help_text)
        else:
            self.append_output(f"Help for {obj}: {type(obj)}\n")
            
    def execute_code(self):
        """Execute code from input area"""
        code = self.code_input.toPlainText().strip()
        if not code:
            return
            
        # Add to history
        self.script_history.append(code)
        self.current_history_index = len(self.script_history)
        
        # Display code in output
        self.append_output(f">>> {code}\n")
        
        # Execute
        self.execute_script.emit(code)
        self.python_executor.set_code(code, self.globals_dict)
        self.python_executor.start()
        
        # Update UI
        self.execute_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
    def run_script(self):
        """Run script from editor"""
        code = self.script_editor.toPlainText()
        if not code.strip():
            return
            
        self.append_output(f"Running script: {self.filename_label.text()}\n")
        self.append_output("-" * 40 + "\n")
        
        self.execute_script.emit(code)
        self.python_executor.set_code(code, self.globals_dict)
        self.python_executor.start()
        
        # Switch to console tab to see output
        self.tab_widget.setCurrentIndex(0)
        
    def append_output(self, text):
        """Append text to output area"""
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Set format for normal output
        format = QTextCharFormat()
        format.setForeground(QColor("black"))
        cursor.setCharFormat(format)
        
        cursor.insertText(text)
        self.output_area.setTextCursor(cursor)
        self.output_area.ensureCursorVisible()
        
    def append_error(self, text):
        """Append error text to output area"""
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Set format for error output
        format = QTextCharFormat()
        format.setForeground(QColor("red"))
        cursor.setCharFormat(format)
        
        cursor.insertText(text)
        self.output_area.setTextCursor(cursor)
        self.output_area.ensureCursorVisible()
        
    def execution_finished(self):
        """Handle execution finished"""
        self.execute_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_output("\n")
        
    def clear_output(self):
        """Clear output area"""
        self.output_area.clear()
        self.append_output("Console cleared.\n")
        
    def show_history(self):
        """Show command history"""
        if not self.script_history:
            self.append_output("No command history.\n")
            return
            
        self.append_output("Command History:\n")
        for i, cmd in enumerate(self.script_history[-10:], 1):  # Show last 10
            self.append_output(f"{i}. {cmd}\n")
        self.append_output("\n")
        
    def new_script(self):
        """Create new script"""
        self.script_editor.setPlainText(self.get_template_script())
        self.filename_label.setText("untitled.py")
        
    def open_script(self):
        """Open script file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Script", "", "Python Files (*.py);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                self.script_editor.setPlainText(content)
                self.filename_label.setText(os.path.basename(filename))
                self.script_loaded.emit(filename)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to open file: {str(e)}")
                
    def save_script(self):
        """Save script file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Script", self.filename_label.text(), 
            "Python Files (*.py);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.script_editor.toPlainText())
                self.filename_label.setText(os.path.basename(filename))
                self.script_saved.emit(filename)
                QMessageBox.information(self, "Success", "Script saved successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save file: {str(e)}")
                
    def populate_examples(self):
        """Populate examples list"""
        examples = [
            "Send CAN Message",
            "Monitor Specific ID",
            "Periodic Message Sender",
            "DTC Reader",
            "Signal Decoder",
            "Bus Load Monitor",
            "Error Frame Injection",
            "Log File Analyzer"
        ]
        
        for example in examples:
            self.examples_list.addItem(example)
            
    def load_example(self, item):
        """Load example preview"""
        example_name = item.text()
        example_code = self.get_example_code(example_name)
        self.example_preview.setPlainText(example_code)
        self.load_example_btn.setEnabled(True)
        
    def load_example_to_editor(self):
        """Load example to script editor"""
        self.script_editor.setPlainText(self.example_preview.toPlainText())
        self.filename_label.setText("example.py")
        self.tab_widget.setCurrentIndex(1)  # Switch to editor tab
        
    def get_template_script(self):
        """Get template script content"""
        return '''"""
CAN Analyzer Script Template
"""

# Available objects:
# - can_interface: CAN bus interface
# - message_log: Message log management  
# - dbc_manager: DBC file management

def main():
    """Main script function"""
    print("Script started")
    
    # Example: Send a CAN message
    # can_interface.send_message(0x123, [0x01, 0x02, 0x03, 0x04])
    
    # Example: Get recent messages
    # messages = message_log.get_recent_messages(10)
    # print(f"Found {len(messages)} recent messages")
    
    print("Script completed")

if __name__ == "__main__":
    main()
'''
        
    def get_example_code(self, example_name):
        """Get example code for given example"""
        examples = {
            "Send CAN Message": '''# Send a CAN message
message_id = 0x123
data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]

print(f"Sending message ID: 0x{message_id:03X}")
# can_interface.send_message(message_id, data)
print("Message sent successfully")
''',
            
            "Monitor Specific ID": '''# Monitor specific CAN ID
target_id = 0x456

print(f"Monitoring messages with ID: 0x{target_id:03X}")

# Get all messages and filter
# messages = message_log.get_all_messages()
# filtered = [msg for msg in messages if msg.id == target_id]

# print(f"Found {len(filtered)} messages with ID 0x{target_id:03X}")
''',
            
            "Periodic Message Sender": '''# Send periodic messages
import time
import threading

def send_periodic():
    """Send messages every second"""
    count = 0
    while count < 10:  # Send 10 messages
        data = [count, 0x00, 0x00, 0x00]
        print(f"Sending periodic message {count}")
        # can_interface.send_message(0x100, data)
        time.sleep(1.0)
        count += 1
    print("Periodic sending completed")

# Start periodic sending in background
thread = threading.Thread(target=send_periodic)
thread.start()
''',
            
            "DTC Reader": '''# Read and display DTCs
print("Reading Diagnostic Trouble Codes...")

# Simulate DTC reading
dtcs = [
    {"code": "P0301", "description": "Cylinder 1 Misfire"},
    {"code": "P0171", "description": "System Too Lean (Bank 1)"},
    {"code": "P0440", "description": "EVAP System Malfunction"}
]

print(f"Found {len(dtcs)} DTCs:")
for dtc in dtcs:
    print(f"  {dtc['code']}: {dtc['description']}")
''',
            
            "Signal Decoder": '''# Decode CAN signals using DBC
message_id = 0x123
raw_data = [0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80]

print(f"Decoding message ID: 0x{message_id:03X}")
print(f"Raw data: {' '.join(f'{b:02X}' for b in raw_data)}")

# Decode using DBC
# decoded = dbc_manager.decode_message(message_id, raw_data)
# 
# if decoded:
#     for signal_name, value in decoded.items():
#         print(f"  {signal_name}: {value}")
# else:
#     print("No DBC definition found for this message")
''',
            
            "Bus Load Monitor": '''# Monitor bus load
import time

print("Monitoring CAN bus load...")

# Monitor for 10 seconds
start_time = time.time()
message_count = 0

while time.time() - start_time < 10:
    # Count messages in the last second
    # current_count = message_log.get_message_count()
    # rate = current_count - message_count
    # message_count = current_count
    
    # Calculate bus load (simplified)
    # bus_load = min(100, rate / 1000 * 100)  # Assume 1000 msg/s = 100%
    
    print(f"Messages/sec: {0}, Bus load: {0}%")
    time.sleep(1)

print("Bus load monitoring completed")
''',
            
            "Error Frame Injection": '''# Inject error frames for testing
print("Error frame injection test")

# Inject various error types
error_types = [
    "bit_error",
    "stuff_error", 
    "crc_error",
    "form_error",
    "ack_error"
]

for error_type in error_types:
    print(f"Injecting {error_type}...")
    # can_interface.inject_error(error_type)
    time.sleep(0.5)

print("Error injection test completed")
''',
            
            "Log File Analyzer": '''# Analyze CAN log file
import os

print("CAN Log File Analysis")

# Simulate log analysis
log_stats = {
    "total_messages": 15432,
    "unique_ids": 45,
    "time_span": "00:05:23",
    "avg_rate": "48.2 msg/s",
    "errors": 3
}

print("Log Statistics:")
for key, value in log_stats.items():
    print(f"  {key.replace('_', ' ').title()}: {value}")

# Most frequent IDs
frequent_ids = [
    (0x123, 1234),
    (0x456, 987), 
    (0x789, 765)
]

print("\\nMost Frequent Message IDs:")
for msg_id, count in frequent_ids:
    print(f"  0x{msg_id:03X}: {count} messages")
'''
        }
        
        return examples.get(example_name, "# Example not found")
        
    def set_can_interface(self, interface):
        """Set CAN interface for scripts"""
        self.globals_dict['can_interface'] = interface
        
    def set_message_log(self, message_log):
        """Set message log for scripts"""
        self.globals_dict['message_log'] = message_log
        
    def set_dbc_manager(self, dbc_manager):
        """Set DBC manager for scripts"""
        self.globals_dict['dbc_manager'] = dbc_manager
        
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
            
            QTextEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
            }
            
            QListWidget {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)