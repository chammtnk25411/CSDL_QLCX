import sys
from PyQt6.QtWidgets import QApplication

from CSDL_doan.loginEX import LoginWindow



app = QApplication(sys.argv)

window = LoginWindow()
window.show()

sys.exit(app.exec())