import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.uic import loadUi  # Sửa từ 'ui' thành 'uic'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load file UI - đảm bảo tên file đúng
        loadUi('Khutrungbay.ui', self)  # Sửa tên file cho đúng

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())