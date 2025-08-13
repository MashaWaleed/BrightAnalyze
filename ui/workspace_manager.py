"""
Workspace Manager for Professional CAN Analyzer
Manages multiple analysis workspaces and layouts
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QDialog, QLineEdit, QPushButton, QLabel, QFormLayout,
                               QMessageBox, QInputDialog, QFileDialog)
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtGui import QIcon
import json
import os

class WorkspaceManager(QWidget):
    """Manages multiple workspaces for different analysis tasks"""
    
    # Signals
    workspace_created = Signal(str)  # workspace_name
    workspace_switched = Signal(str)  # workspace_name
    workspace_deleted = Signal(str)  # workspace_name
    workspace_saved = Signal(str)    # workspace_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workspaces = {}
        self.current_workspace = "Default"
        self.workspace_dir = "workspaces"
        
        # Create workspace directory if it doesn't exist
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        self.setup_default_workspace()
        
    def setup_default_workspace(self):
        """Setup the default workspace"""
        default_config = {
            'name': 'Default',
            'description': 'Default workspace for general analysis',
            'layout': {
                'left_sidebar_width': 350,
                'right_sidebar_width': 350,
                'message_log_height': 600,
                'bottom_panel_height': 300
            },
            'filters': {
                'id_filter': '',
                'data_filter': '',
                'direction_filter': 'All'
            },
            'dbc_files': [],
            'connection_config': {
                'interface': 'can0',
                'bitrate': 500000,
                'driver': 'socketcan'
            }
        }
        
        self.workspaces['Default'] = default_config
        
    def create_workspace(self, name, description="", clone_current=False):
        """Create a new workspace"""
        if name in self.workspaces:
            return False, f"Workspace '{name}' already exists"
            
        if clone_current and self.current_workspace in self.workspaces:
            # Clone current workspace configuration
            current_config = self.workspaces[self.current_workspace].copy()
            new_config = current_config.copy()
            new_config['name'] = name
            new_config['description'] = description
        else:
            # Create new workspace with default configuration
            new_config = {
                'name': name,
                'description': description,
                'layout': {
                    'left_sidebar_width': 350,
                    'right_sidebar_width': 350,
                    'message_log_height': 600,
                    'bottom_panel_height': 300
                },
                'filters': {
                    'id_filter': '',
                    'data_filter': '',
                    'direction_filter': 'All'
                },
                'dbc_files': [],
                'connection_config': {
                    'interface': 'can0',
                    'bitrate': 500000,
                    'driver': 'socketcan'
                },
                'message_templates': [],
                'custom_scripts': []
            }
            
        self.workspaces[name] = new_config
        self.workspace_created.emit(name)
        return True, f"Workspace '{name}' created successfully"
        
    def switch_workspace(self, name):
        """Switch to a different workspace"""
        if name not in self.workspaces:
            return False, f"Workspace '{name}' does not exist"
            
        self.current_workspace = name
        self.workspace_switched.emit(name)
        return True, f"Switched to workspace '{name}'"
        
    def delete_workspace(self, name):
        """Delete a workspace"""
        if name == "Default":
            return False, "Cannot delete the default workspace"
            
        if name not in self.workspaces:
            return False, f"Workspace '{name}' does not exist"
            
        if name == self.current_workspace:
            # Switch to default before deleting
            self.switch_workspace("Default")
            
        del self.workspaces[name]
        
        # Delete workspace file if it exists
        workspace_file = os.path.join(self.workspace_dir, f"{name}.json")
        if os.path.exists(workspace_file):
            os.remove(workspace_file)
            
        self.workspace_deleted.emit(name)
        return True, f"Workspace '{name}' deleted successfully"
        
    def rename_workspace(self, old_name, new_name):
        """Rename a workspace"""
        if old_name not in self.workspaces:
            return False, f"Workspace '{old_name}' does not exist"
            
        if new_name in self.workspaces:
            return False, f"Workspace '{new_name}' already exists"
            
        if old_name == "Default":
            return False, "Cannot rename the default workspace"
            
        # Copy workspace with new name
        workspace_config = self.workspaces[old_name].copy()
        workspace_config['name'] = new_name
        self.workspaces[new_name] = workspace_config
        
        # Remove old workspace
        del self.workspaces[old_name]
        
        # Update current workspace if needed
        if self.current_workspace == old_name:
            self.current_workspace = new_name
            
        return True, f"Workspace renamed from '{old_name}' to '{new_name}'"
        
    def save_workspace(self, name=None):
        """Save workspace configuration to file"""
        if name is None:
            name = self.current_workspace
            
        if name not in self.workspaces:
            return False, f"Workspace '{name}' does not exist"
            
        workspace_file = os.path.join(self.workspace_dir, f"{name}.json")
        
        try:
            with open(workspace_file, 'w') as f:
                json.dump(self.workspaces[name], f, indent=2)
            self.workspace_saved.emit(name)
            return True, f"Workspace '{name}' saved successfully"
        except Exception as e:
            return False, f"Failed to save workspace: {str(e)}"
            
    def load_workspace(self, filename):
        """Load workspace from file"""
        try:
            with open(filename, 'r') as f:
                workspace_config = json.load(f)
                
            name = workspace_config.get('name', os.path.basename(filename).replace('.json', ''))
            
            # Ensure required fields exist
            required_fields = ['layout', 'filters', 'connection_config']
            for field in required_fields:
                if field not in workspace_config:
                    workspace_config[field] = {}
                    
            self.workspaces[name] = workspace_config
            return True, f"Workspace '{name}' loaded successfully"
            
        except Exception as e:
            return False, f"Failed to load workspace: {str(e)}"
            
    def get_workspace_config(self, name=None):
        """Get workspace configuration"""
        if name is None:
            name = self.current_workspace
            
        return self.workspaces.get(name, {})
        
    def update_workspace_config(self, config, name=None):
        """Update workspace configuration"""
        if name is None:
            name = self.current_workspace
            
        if name in self.workspaces:
            self.workspaces[name].update(config)
            return True
        return False
        
    def get_workspace_list(self):
        """Get list of all workspace names"""
        return list(self.workspaces.keys())
        
    def export_workspace(self, name, filename):
        """Export workspace to file"""
        if name not in self.workspaces:
            return False, f"Workspace '{name}' does not exist"
            
        try:
            with open(filename, 'w') as f:
                json.dump(self.workspaces[name], f, indent=2)
            return True, f"Workspace '{name}' exported to '{filename}'"
        except Exception as e:
            return False, f"Failed to export workspace: {str(e)}"
            
    def import_workspace(self, filename):
        """Import workspace from file"""
        return self.load_workspace(filename)
        
    def save_all_workspaces(self):
        """Save all workspaces to files"""
        success_count = 0
        errors = []
        
        for name in self.workspaces:
            if name != "Default":  # Don't save default to file
                success, message = self.save_workspace(name)
                if success:
                    success_count += 1
                else:
                    errors.append(message)
                    
        return success_count, errors
        
    def load_all_workspaces(self):
        """Load all workspaces from workspace directory"""
        loaded_count = 0
        errors = []
        
        if not os.path.exists(self.workspace_dir):
            return loaded_count, errors
            
        for filename in os.listdir(self.workspace_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.workspace_dir, filename)
                success, message = self.load_workspace(filepath)
                if success:
                    loaded_count += 1
                else:
                    errors.append(message)
                    
        return loaded_count, errors

class WorkspaceDialog(QDialog):
    """Dialog for creating/editing workspaces"""
    
    def __init__(self, parent=None, workspace_manager=None, edit_workspace=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.edit_workspace = edit_workspace
        
        self.setWindowTitle("Workspace Configuration")
        self.setModal(True)
        self.resize(400, 300)
        
        self.setup_ui()
        
        if edit_workspace:
            self.load_workspace_data()
            
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Form layout for workspace details
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter workspace name...")
        form_layout.addRow("Name:", self.name_edit)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Enter description...")
        form_layout.addRow("Description:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.clone_button = QPushButton("Clone Current")
        self.clone_button.clicked.connect(self.set_clone_mode)
        button_layout.addWidget(self.clone_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("Create" if not self.edit_workspace else "Update")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        self.clone_current = False
        
    def set_clone_mode(self):
        """Set clone mode"""
        self.clone_current = True
        self.clone_button.setText("✓ Clone Current")
        self.clone_button.setEnabled(False)
        
    def load_workspace_data(self):
        """Load existing workspace data for editing"""
        if self.workspace_manager and self.edit_workspace:
            config = self.workspace_manager.get_workspace_config(self.edit_workspace)
            self.name_edit.setText(config.get('name', ''))
            self.description_edit.setText(config.get('description', ''))
            self.name_edit.setEnabled(False)  # Don't allow name changes when editing
            
    def get_workspace_data(self):
        """Get workspace data from dialog"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.text().strip(),
            'clone_current': self.clone_current
        }
        
    def accept(self):
        """Handle dialog acceptance"""
        data = self.get_workspace_data()
        
        if not data['name']:
            QMessageBox.warning(self, "Invalid Input", "Please enter a workspace name.")
            return
            
        if self.workspace_manager:
            if self.edit_workspace:
                # Update existing workspace
                config = self.workspace_manager.get_workspace_config(self.edit_workspace)
                config['description'] = data['description']
                success = self.workspace_manager.update_workspace_config(config, self.edit_workspace)
                if not success:
                    QMessageBox.warning(self, "Error", "Failed to update workspace.")
                    return
            else:
                # Create new workspace
                success, message = self.workspace_manager.create_workspace(
                    data['name'], 
                    data['description'], 
                    data['clone_current']
                )
                if not success:
                    QMessageBox.warning(self, "Error", message)
                    return
                    
        super().accept()