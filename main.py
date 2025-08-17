import sys
from PyQt6.QtWidgets import QApplication
from utils import ensure_base_csv
from main_window import LoginWindow

STYLE = """
QWidget { background: #FFFFFF; color: #0B2A4A; font-size: 14px; }
QFrame#card { background: #ffffff; border: 1px solid #214D80; border-radius: 18px; }
QFrame#glass { background: rgba(255,255,255,0.85); border: 1px solid rgba(11,42,74,0.25); border-radius: 18px; }
QLabel#headline { font-weight: 800; font-size: 16px; color: #0B2A4A; }
QLabel#colTitle { font-weight: 600; color: #214D80; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0B2A4A, stop:1 #123C69); color:#ffffff; border:none; border-radius:12px; padding:10px 16px; font-weight:700; }
QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #123C69, stop:1 #1B4E7A); }
QPushButton:pressed { background: #081A34; }
QPushButton#danger { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #C62828, stop:1 #B71C1C); color:#ffffff; }
QPushButton#danger:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #D32F2F, stop:1 #C62828); }
QPushButton#danger:pressed { background: #8E1B1B; }
QLineEdit, QComboBox, QDateEdit { background: #ffffff; color:#0B2A4A; border:2px solid #123C69; border-radius:10px; padding:6px 8px; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color:#1F5B8F; }
QTableWidget { background: #ffffff; color:#0B2A4A; alternate-background-color: #F3F6FA; gridline-color:#D5DFEC; border-radius:10px; }
QHeaderView::section { background: #0B2A4A; color:#fff; padding:8px 10px; border:none; font-weight:700; }
QTableCornerButton:section { background: #0B2A4A; }
QTabBar::tab { background: rgba(11,42,74,0.10); padding: 10px 16px; margin: 2px; border-top-left-radius: 14px; border-top-right-radius: 14px; color:#0B2A4A; }
QTabBar::tab:selected { background: rgba(11,42,74,0.18); }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; border-radius: 5px; }
QScrollBar::handle:vertical { background: #123C69; min-height: 20px; border-radius: 5px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""

def main():
    ensure_base_csv()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()