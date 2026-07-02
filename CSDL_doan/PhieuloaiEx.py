# PhieuloaiEx.py
import sys
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.uic import loadUi

class MainWindow(QDialog):  # Đổi từ QMainWindow thành QDialog
    def __init__(self):
        super().__init__()
        # Load file UI
        loadUi('Phieuloai.ui', self)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())