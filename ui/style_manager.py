"""
Modern Style Manager for Professional CAN Analyzer
Provides consistent theming and styling across the application
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor

class ModernStyleManager(QObject):
    """Manages application styling and themes"""
    
    theme_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        
    def apply_theme(self, widget, theme="light"):
        """Apply the specified theme to the application"""
        self.current_theme = theme
        
        if theme == "dark":
            self.apply_dark_theme(widget)
        else:
            self.apply_light_theme(widget)
            
        self.theme_changed.emit(theme)
        
    def apply_light_theme(self, widget):
        """Apply light theme styling"""
        style = """
        /* Main Application Styling */
        QMainWindow {
            background-color: #ffffff;
            color: #2c3e50;
            font-family: "Segoe UI", "Arial", sans-serif;
        }
        
        /* Menu Bar Styling */
        QMenuBar {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #ffffff, stop: 1 #f8f9fa);
            border-bottom: 1px solid #e9ecef;
            padding: 4px;
        }
        
        QMenuBar::item {
            background: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        QMenu {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #e0e0e0;
            margin: 4px 0;
        }
        
        /* Button Styling */
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #ffffff, stop: 1 #f8f9fa);
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f9fa, stop: 1 #e9ecef);
            border-color: #adb5bd;
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #e9ecef, stop: 1 #dee2e6);
        }
        
        QPushButton:checked {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #007bff, stop: 1 #0056b3);
            border-color: #0056b3;
            color: white;
            font-weight: bold;
        }
        
        QPushButton:disabled {
            background-color: #f8f9fa;
            border-color: #e9ecef;
            color: #6c757d;
        }
        
        /* Input Controls */
        QLineEdit {
            background-color: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 14px;
        }
        
        QLineEdit:focus {
            border-color: #007bff;
            background-color: #fff;
            outline: none;
        }
        
        QLineEdit:disabled {
            background-color: #f8f9fa;
            color: #6c757d;
        }
        
        QComboBox {
            background-color: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px 12px;
            min-width: 100px;
        }
        
        QComboBox:hover {
            border-color: #80bdff;
        }
        
        QComboBox:focus {
            border-color: #007bff;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid #6c757d;
        }
        
        QSpinBox {
            background-color: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px;
            min-width: 60px;
        }
        
        QSpinBox:focus {
            border-color: #007bff;
        }
        
        /* Table Styling */
        QTableWidget {
            gridline-color: #e9ecef;
            background-color: white;
            alternate-background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        }
        
        QTableWidget::item {
            padding: 8px;
            border: none;
        }
        
        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        QHeaderView::section {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f9fa, stop: 1 #e9ecef);
            border: 1px solid #dee2e6;
            padding: 8px;
            font-weight: bold;
            color: #495057;
        }
        
        QHeaderView::section:hover {
            background-color: #e9ecef;
        }
        
        /* Tab Widget Styling */
        QTabWidget::pane {
            border: 1px solid #dee2e6;
            background-color: white;
            border-radius: 6px;
        }
        
        QTabBar::tab {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f9fa, stop: 1 #e9ecef);
            border: 1px solid #dee2e6;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-weight: 500;
        }
        
        QTabBar::tab:selected {
            background: white;
            border-bottom: 1px solid white;
            font-weight: bold;
            color: #007bff;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #e9ecef;
        }
        
        /* Group Box Styling */
        QGroupBox {
            font-weight: bold;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            margin: 12px 0;
            padding-top: 16px;
            background-color: #fafafa;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px 0 8px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            color: #495057;
        }
        
        /* Scroll Area */
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        
        QScrollBar:vertical {
            background-color: #f8f9fa;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #ced4da;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #adb5bd;
        }
        
        /* Status Bar */
        QStatusBar {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f9fa, stop: 1 #e9ecef);
            border-top: 1px solid #dee2e6;
            color: #495057;
        }
        
        /* Splitter */
        QSplitter::handle {
            background-color: #e9ecef;
        }
        
        QSplitter::handle:horizontal {
            width: 2px;
        }
        
        QSplitter::handle:vertical {
            height: 2px;
        }
        
        QSplitter::handle:hover {
            background-color: #007bff;
        }
        
        /* Checkbox and Radio Button */
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #ced4da;
            border-radius: 3px;
            background-color: white;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007bff;
            border-color: #007bff;
            image: none;
        }
        
        QCheckBox::indicator:checked:after {
            content: "✓";
            color: white;
            font-weight: bold;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #ced4da;
            border-radius: 8px;
            background-color: white;
        }
        
        QRadioButton::indicator:checked {
            background-color: #007bff;
            border-color: #007bff;
        }
        
        /* Slider */
        QSlider::groove:horizontal {
            border: 1px solid #ced4da;
            height: 6px;
            background-color: #f8f9fa;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background-color: #007bff;
            border: 1px solid #0056b3;
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #0056b3;
        }
        
        /* Progress Bar */
        QProgressBar {
            border: 1px solid #ced4da;
            border-radius: 4px;
            text-align: center;
            background-color: #f8f9fa;
        }
        
        QProgressBar::chunk {
            background-color: #28a745;
            border-radius: 3px;
        }
        """
        
        widget.setStyleSheet(style)
        
    def apply_dark_theme(self, widget):
        """Apply dark theme styling"""
        style = """
        /* Dark Theme Styling */
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: "Segoe UI", "Arial", sans-serif;
        }
        
        /* Menu Bar Styling - Dark */
        QMenuBar {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #2d2d2d, stop: 1 #1e1e1e);
            border-bottom: 1px solid #404040;
            color: #ffffff;
            padding: 4px;
        }
        
        QMenuBar::item {
            background: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #404040;
            color: #64b5f6;
        }
        
        QMenu {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 6px;
            padding: 4px;
            color: #ffffff;
        }
        
        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #404040;
            color: #64b5f6;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #404040;
            margin: 4px 0;
        }
        
        /* Button Styling - Dark */
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #404040, stop: 1 #2d2d2d);
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            color: #ffffff;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #4a4a4a, stop: 1 #353535);
            border-color: #666666;
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #2d2d2d, stop: 1 #1e1e1e);
        }
        
        QPushButton:checked {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #1976d2, stop: 1 #0d47a1);
            border-color: #0d47a1;
            color: white;
            font-weight: bold;
        }
        
        QPushButton:disabled {
            background-color: #1e1e1e;
            border-color: #2d2d2d;
            color: #666666;
        }
        
        /* Input Controls - Dark */
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 12px;
            color: #ffffff;
            font-size: 14px;
        }
        
        QLineEdit:focus {
            border-color: #1976d2;
            background-color: #353535;
        }
        
        QLineEdit:disabled {
            background-color: #1e1e1e;
            color: #666666;
        }
        
        QComboBox {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px 12px;
            color: #ffffff;
            min-width: 100px;
        }
        
        QComboBox:hover {
            border-color: #666666;
        }
        
        QComboBox:focus {
            border-color: #1976d2;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #555555;
            selection-background-color: #404040;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid #ffffff;
        }
        
        QSpinBox {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
            min-width: 60px;
        }
        
        QSpinBox:focus {
            border-color: #1976d2;
        }
        
        /* Table Styling - Dark */
        QTableWidget {
            gridline-color: #404040;
            background-color: #1e1e1e;
            alternate-background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 6px;
            color: #ffffff;
        }
        
        QTableWidget::item {
            padding: 8px;
            border: none;
        }
        
        QTableWidget::item:selected {
            background-color: #404040;
            color: #64b5f6;
        }
        
        QHeaderView::section {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #404040, stop: 1 #2d2d2d);
            border: 1px solid #555555;
            padding: 8px;
            font-weight: bold;
            color: #ffffff;
        }
        
        /* Group Box Styling - Dark */
        QGroupBox {
            font-weight: bold;
            border: 2px solid #404040;
            border-radius: 8px;
            margin: 12px 0;
            padding-top: 16px;
            background-color: #2d2d2d;
            color: #ffffff;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px 0 8px;
            background-color: #1e1e1e;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
        }
        
        /* Scroll Bar - Dark */
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        /* Status Bar - Dark */
        QStatusBar {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #2d2d2d, stop: 1 #1e1e1e);
            border-top: 1px solid #404040;
            color: #ffffff;
        }
        
        /* Tab Widget - Dark */
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #1e1e1e;
            border-radius: 6px;
        }
        
        QTabBar::tab {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #404040, stop: 1 #2d2d2d);
            border: 1px solid #555555;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            color: #ffffff;
            font-weight: 500;
        }
        
        QTabBar::tab:selected {
            background: #1e1e1e;
            border-bottom: 1px solid #1e1e1e;
            font-weight: bold;
            color: #64b5f6;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #353535;
        }
        
        /* Checkbox - Dark */
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #555555;
            border-radius: 3px;
            background-color: #2d2d2d;
        }
        
        QCheckBox::indicator:checked {
            background-color: #1976d2;
            border-color: #1976d2;
        }
        
        QRadioButton {
            color: #ffffff;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #555555;
            border-radius: 8px;
            background-color: #2d2d2d;
        }
        
        QRadioButton::indicator:checked {
            background-color: #1976d2;
            border-color: #1976d2;
        }
        
        /* Labels - Dark */
        QLabel {
            color: #ffffff;
        }
        """
        
        widget.setStyleSheet(style)
        
    def get_current_theme(self):
        """Get the current theme"""
        return self.current_theme
        
    def toggle_theme(self, widget):
        """Toggle between light and dark themes"""
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(widget, new_theme)