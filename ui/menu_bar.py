"""
Enhanced Menu Bar for Professional CAN Analyzer
Includes comprehensive menu structure with icons and shortcuts
"""

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter
from PySide6.QtCore import Signal, Qt

class EnhancedMenuBar(QMenuBar):
    """Professional menu bar with comprehensive functionality"""
    
    # File menu signals
    new_project = Signal()
    open_project = Signal()
    save_project = Signal()
    save_project_as = Signal()
    import_dbc = Signal()
    load_dbc = Signal()
    export_log = Signal()
    import_log = Signal()
    recent_files = Signal(str)
    exit_app = Signal()
    
    # Edit menu signals
    clear_log = Signal()
    copy_messages = Signal()
    select_all = Signal()
    find_message = Signal()
    preferences = Signal()
    
    # View menu signals
    show_filters = Signal(bool)
    show_statistics = Signal(bool)
    show_scripting = Signal(bool)
    show_diagnostics = Signal(bool)
    show_plotter = Signal(bool)
    toggle_theme = Signal()
    fullscreen = Signal()
    reset_layout = Signal()
    
    # Tools menu signals
    message_generator = Signal()
    error_injection = Signal()
    bus_statistics = Signal()
    dbc_editor = Signal()
    signal_editor = Signal()
    log_converter = Signal()
    
    # Workspace menu signals
    new_workspace = Signal()
    clone_workspace = Signal()
    rename_workspace = Signal()
    
    # Help menu signals
    show_documentation = Signal()
    show_shortcuts = Signal()
    check_updates = Signal()
    show_about = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icons = {}
        self.create_icons()
        self.setup_menus()
        
    def create_icons(self):
        """Create custom icons for menu items"""
        self.icons = {}
        
        # Create simple icons programmatically
        icon_specs = [
            ("new", Qt.blue, "📄"),
            ("open", Qt.green, "📁"),
            ("save", Qt.darkBlue, "💾"),
            ("dbc", Qt.magenta, "🗃️"),
            ("export", Qt.darkGreen, "📤"),
            ("import", Qt.darkCyan, "📥"),
            ("clear", Qt.red, "🗑️"),
            ("copy", Qt.gray, "📋"),
            ("find", Qt.yellow, "🔍"),  # Qt.darkYellow replaced with Qt.yellow
            ("settings", Qt.darkGray, "⚙️"),
            ("theme", Qt.black, "🌓"),
            ("workspace", Qt.blue, "🗂️"),
            ("plot", Qt.green, "📈"),
            ("script", Qt.black, "🐍"),  # Qt.purple replaced with Qt.black
            ("diagnostic", Qt.red, "🔧"),  # Qt.orange replaced with Qt.red
            ("help", Qt.blue, "❓")
        ]
        
        for name, color, emoji in icon_specs:
            self.icons[name] = self.create_emoji_icon(emoji)
    
    def create_emoji_icon(self, emoji, size=16):
        """Create an icon from emoji"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw emoji as text
        font = painter.font()
        font.setPixelSize(size - 2)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignCenter, emoji)
        
        painter.end()
        return QIcon(pixmap)
        
    def setup_menus(self):
        """Setup all menu items with modern organization"""
        self.setup_file_menu()
        self.setup_edit_menu()
        self.setup_view_menu()
        self.setup_tools_menu()
        self.setup_workspace_menu()
        self.setup_help_menu()
        
    def setup_file_menu(self):
        """Setup File menu"""
        file_menu = self.addMenu("&File")
        
        # Project operations
        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.setIcon(self.icons.get("new", QIcon()))
        new_action.triggered.connect(self.new_project.emit)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setIcon(self.icons.get("open", QIcon()))
        open_action.triggered.connect(self.open_project.emit)
        file_menu.addAction(open_action)
        
        # Recent files submenu
        recent_menu = file_menu.addMenu("Recent Projects")
        # Would be populated dynamically
        
        file_menu.addSeparator()
        
        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setIcon(self.icons.get("save", QIcon()))
        save_action.triggered.connect(self.save_project.emit)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save Project &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_project_as.emit)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # DBC operations
        load_dbc_action = QAction("Load &DBC File...", self)
        load_dbc_action.setShortcut("Ctrl+D")
        load_dbc_action.setIcon(self.icons.get("dbc", QIcon()))
        load_dbc_action.triggered.connect(self.load_dbc.emit)
        file_menu.addAction(load_dbc_action)
        
        import_dbc_action = QAction("&Import DBC...", self)
        import_dbc_action.setIcon(self.icons.get("import", QIcon()))
        import_dbc_action.triggered.connect(self.import_dbc.emit)
        file_menu.addAction(import_dbc_action)
        
        file_menu.addSeparator()
        
        # Log operations
        export_log_action = QAction("&Export Log...", self)
        export_log_action.setShortcut("Ctrl+E")
        export_log_action.setIcon(self.icons.get("export", QIcon()))
        export_log_action.triggered.connect(self.export_log.emit)
        file_menu.addAction(export_log_action)
        
        import_log_action = QAction("&Import Log...", self)
        import_log_action.setIcon(self.icons.get("import", QIcon()))
        import_log_action.triggered.connect(self.import_log.emit)
        file_menu.addAction(import_log_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.exit_app.emit)
        file_menu.addAction(exit_action)
        
    def setup_edit_menu(self):
        """Setup Edit menu"""
        edit_menu = self.addMenu("&Edit")
        
        clear_action = QAction("&Clear Log", self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.setIcon(self.icons.get("clear", QIcon()))
        clear_action.triggered.connect(self.clear_log.emit)
        edit_menu.addAction(clear_action)
        
        edit_menu.addSeparator()
        
        copy_action = QAction("&Copy Messages", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.setIcon(self.icons.get("copy", QIcon()))
        copy_action.triggered.connect(self.copy_messages.emit)
        edit_menu.addAction(copy_action)
        
        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.select_all.emit)
        edit_menu.addAction(select_all_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("&Find Message...", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.setIcon(self.icons.get("find", QIcon()))
        find_action.triggered.connect(self.find_message.emit)
        edit_menu.addAction(find_action)
        
        edit_menu.addSeparator()
        
        prefs_action = QAction("&Preferences...", self)
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.setIcon(self.icons.get("settings", QIcon()))
        prefs_action.triggered.connect(self.preferences.emit)
        edit_menu.addAction(prefs_action)
        
    def setup_view_menu(self):
        """Setup View menu"""
        view_menu = self.addMenu("&View")
        
        # Panel toggles
        panels_menu = view_menu.addMenu("Panels")
        
        filters_action = QAction("Show &Filters", self)
        filters_action.setCheckable(True)
        filters_action.setChecked(True)
        filters_action.setShortcut("F2")
        filters_action.triggered.connect(self.show_filters.emit)
        panels_menu.addAction(filters_action)
        
        stats_action = QAction("Show &Statistics", self)
        stats_action.setCheckable(True)
        stats_action.setChecked(True)
        stats_action.setShortcut("F3")
        stats_action.triggered.connect(self.show_statistics.emit)
        panels_menu.addAction(stats_action)
        
        plotter_action = QAction("Show Signal &Plotter", self)
        plotter_action.setCheckable(True)
        plotter_action.setChecked(True)
        plotter_action.setShortcut("F4")
        plotter_action.setIcon(self.icons.get("plot", QIcon()))
        plotter_action.triggered.connect(self.show_plotter.emit)
        panels_menu.addAction(plotter_action)
        
        script_action = QAction("Show &Scripting Console", self)
        script_action.setCheckable(True)
        script_action.setChecked(False)
        script_action.setShortcut("F5")
        script_action.setIcon(self.icons.get("script", QIcon()))
        script_action.triggered.connect(self.show_scripting.emit)
        panels_menu.addAction(script_action)
        
        diag_action = QAction("Show &Diagnostics", self)
        diag_action.setCheckable(True)
        diag_action.setChecked(False)
        diag_action.setShortcut("F6")
        diag_action.setIcon(self.icons.get("diagnostic", QIcon()))
        diag_action.triggered.connect(self.show_diagnostics.emit)
        panels_menu.addAction(diag_action)
        
        view_menu.addSeparator()
        
        # Theme and layout
        theme_action = QAction("Toggle &Dark Mode", self)
        theme_action.setShortcut("Ctrl+Shift+D")
        theme_action.setIcon(self.icons.get("theme", QIcon()))
        theme_action.triggered.connect(self.toggle_theme.emit)
        view_menu.addAction(theme_action)
        
        fullscreen_action = QAction("&Full Screen", self)
        fullscreen_action.setShortcut(QKeySequence.FullScreen)
        fullscreen_action.triggered.connect(self.fullscreen.emit)
        view_menu.addAction(fullscreen_action)
        
        view_menu.addSeparator()
        
        reset_layout_action = QAction("&Reset Layout", self)
        reset_layout_action.triggered.connect(self.reset_layout.emit)
        view_menu.addAction(reset_layout_action)
        
    def setup_tools_menu(self):
        """Setup Tools menu"""
        tools_menu = self.addMenu("&Tools")
        
        msg_gen_action = QAction("Message &Generator", self)
        msg_gen_action.setShortcut("Ctrl+G")
        msg_gen_action.triggered.connect(self.message_generator.emit)
        tools_menu.addAction(msg_gen_action)
        
        error_inj_action = QAction("&Error Injection", self)
        error_inj_action.setShortcut("Ctrl+Shift+E")
        error_inj_action.triggered.connect(self.error_injection.emit)
        tools_menu.addAction(error_inj_action)
        
        tools_menu.addSeparator()
        
        bus_stats_action = QAction("&Bus Statistics", self)
        bus_stats_action.setShortcut("Ctrl+B")
        bus_stats_action.triggered.connect(self.bus_statistics.emit)
        tools_menu.addAction(bus_stats_action)
        
        tools_menu.addSeparator()
        
        dbc_editor_action = QAction("&DBC Editor", self)
        dbc_editor_action.setIcon(self.icons.get("dbc", QIcon()))
        dbc_editor_action.triggered.connect(self.dbc_editor.emit)
        tools_menu.addAction(dbc_editor_action)
        
        signal_editor_action = QAction("&Signal Editor", self)
        signal_editor_action.triggered.connect(self.signal_editor.emit)
        tools_menu.addAction(signal_editor_action)
        
        tools_menu.addSeparator()
        
        converter_action = QAction("Log &Converter", self)
        converter_action.triggered.connect(self.log_converter.emit)
        tools_menu.addAction(converter_action)
        
    def setup_workspace_menu(self):
        """Setup Workspace menu"""
        workspace_menu = self.addMenu("&Workspace")
        
        new_ws_action = QAction("&New Workspace", self)
        new_ws_action.setShortcut("Ctrl+Shift+N")
        new_ws_action.setIcon(self.icons.get("workspace", QIcon()))
        new_ws_action.triggered.connect(self.new_workspace.emit)
        workspace_menu.addAction(new_ws_action)
        
        clone_ws_action = QAction("&Clone Current Workspace", self)
        clone_ws_action.setShortcut("Ctrl+Shift+C")
        clone_ws_action.triggered.connect(self.clone_workspace.emit)
        workspace_menu.addAction(clone_ws_action)
        
        rename_ws_action = QAction("&Rename Workspace", self)
        rename_ws_action.triggered.connect(self.rename_workspace.emit)
        workspace_menu.addAction(rename_ws_action)
        
    def setup_help_menu(self):
        """Setup Help menu"""
        help_menu = self.addMenu("&Help")
        
        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut(QKeySequence.HelpContents)
        docs_action.setIcon(self.icons.get("help", QIcon()))
        docs_action.triggered.connect(self.show_documentation.emit)
        help_menu.addAction(docs_action)
        
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_shortcuts.emit)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        updates_action = QAction("Check for &Updates", self)
        updates_action.triggered.connect(self.check_updates.emit)
        help_menu.addAction(updates_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about.emit)
        help_menu.addAction(about_action)