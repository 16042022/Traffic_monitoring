# views/base_view.py
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import pyqtSignal
import logging


class BaseView(QWidget):
    """
    Base view class with common functionality
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def show_error(self, message: str, title: str = "Lỗi"):
        """Show error message"""
        QMessageBox.critical(self, title, message)
        
    def show_info(self, message: str, title: str = "Thông tin"):
        """Show info message"""
        QMessageBox.information(self, title, message)
        
    def show_warning(self, message: str, title: str = "Cảnh báo"):
        """Show warning message"""
        QMessageBox.warning(self, title, message)
        
    def confirm_action(self, message: str, title: str = "Xác nhận") -> bool:
        """Show confirmation dialog"""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes
    
    def set_enabled_recursive(self, enabled: bool):
        """Enable/disable widget and all children"""
        self.setEnabled(enabled)
        for child in self.findChildren(QWidget):
            child.setEnabled(enabled)
    
    def clear_layout(self, layout):
        """Clear all widgets from layout"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())