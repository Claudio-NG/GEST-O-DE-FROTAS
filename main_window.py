import os, sys, pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QTabWidget, QVBoxLayout, QFrame, QHBoxLayout,
    QLabel, QPushButton, QGridLayout, QLineEdit, QCheckBox, QComboBox, QMessageBox,
    QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from utils import apply_shadow, parse_permissions, ensure_status_cols
from constants import MODULES
from multas import InfraMultasWindow
from relatorios import RelatorioWindow
from base import BaseWindow
from config import cfg_get
from combustivel import CombustivelWindow

class CenarioGeralWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cenário Geral")
        v = QVBoxLayout(self)
        card = QFrame()
        card.setObjectName("card")
        apply_shadow(card, radius=18)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Cenário Geral")
        title.setObjectName("headline")
        cv.addWidget(title)
        v.addWidget(card)

class MultasMenu(QWidget):
    def __init__(self, open_cb):
        super().__init__()
        v = QVBoxLayout(self)
        card = QFrame()
        card.setObjectName("card")
        apply_shadow(card, radius=18)
        gv = QGridLayout(card)
        gv.setContentsMargins(18, 18, 18, 18)
        b1 = QPushButton("Multas em Aberto")
        b2 = QPushButton("Cenário Geral")
        b1.setMinimumHeight(64)
        b2.setMinimumHeight(64)
        b1.setFont(QFont("Arial", 16, weight=QFont.Weight.Bold))
        b2.setFont(QFont("Arial", 16, weight=QFont.Weight.Bold))
        b1.clicked.connect(lambda: open_cb("Multas em Aberto", lambda: InfraMultasWindow()))
        b2.clicked.connect(lambda: open_cb("Cenário Geral", lambda: CenarioGeralWindow()))
        gv.addWidget(b1, 0, 0)
        gv.addWidget(b2, 0, 1)
        v.addWidget(card)

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        flags = Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Login | Gestão de Frota")
        self.resize(480, 340)
        self.setFixedSize(self.size())
        self.wrap = QFrame(self)
        self.wrap.setObjectName("glass")
        self.wrap.setGeometry(self.rect())
        apply_shadow(self.wrap, radius=20, blur=60, color=QColor(0, 0, 0, 60))
        v = QVBoxLayout(self.wrap)
        v.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Gestão de Frota")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 22, weight=QFont.Weight.Bold))
        v.addWidget(title)
        v.addSpacing(6)
        email_lbl = QLabel("E-mail")
        v.addWidget(email_lbl)
        self.email_combo = QComboBox()
        self.email_combo.setEditable(True)
        self.users = self.load_users()
        self.email_combo.addItems(self.users["email"].astype(str).tolist() if not self.users.empty else [])
        self.email_combo.currentTextChanged.connect(self.prefill)
        v.addWidget(self.email_combo)
        pass_lbl = QLabel("Senha")
        v.addWidget(pass_lbl)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        v.addWidget(self.password_input)
        show = QCheckBox("Mostrar senha")
        show.stateChanged.connect(lambda s: self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password))
        v.addWidget(show)
        self.remember_cb = QCheckBox("Lembrar acesso por 30 dias")
        v.addWidget(self.remember_cb)
        bar = QHBoxLayout()
        login_btn = QPushButton("Entrar")
        req_btn = QPushButton("Solicitar Acesso")
        login_btn.clicked.connect(self.tentar_login)
        req_btn.clicked.connect(self.solicitar_acesso)
        bar.addWidget(login_btn)
        bar.addWidget(req_btn)
        v.addLayout(bar)
        self.prefill()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "wrap"):
            self.wrap.setGeometry(self.rect())

    def load_users(self):
        p = cfg_get("users_file") or "users.csv"
        if os.path.exists(p):
            try:
                return pd.read_csv(p, dtype={"email": str, "password": str, "permissions": str}, parse_dates=["last_login"])
            except:
                pass
        return pd.DataFrame(columns=["email", "password", "last_login", "permissions", "remember"])

    def save_users(self):
        p = cfg_get("users_file") or "users.csv"
        try:
            self.users.to_csv(p, index=False)
        except:
            pass

    def prefill(self):
        if self.users is None or self.users.empty:
            self.password_input.clear()
            self.remember_cb.setChecked(False)
            return
        email = str(self.email_combo.currentText()).strip().lower()
        row = self.users[self.users["email"].astype(str).str.lower() == email]
        now = pd.Timestamp.now()
        if not row.empty and bool(row.iloc[0].get("remember", False)) and pd.notna(row.iloc[0].get("last_login")) and now - row.iloc[0]["last_login"] <= pd.Timedelta(days=30):
            self.password_input.setText(str(row.iloc[0].get("password", "")))
            self.remember_cb.setChecked(True)
        else:
            self.password_input.clear()
            self.remember_cb.setChecked(False)

    def tentar_login(self):
        email = str(self.email_combo.currentText()).strip().lower()
        senha = self.password_input.text().strip()
        if self.users is None or self.users.empty:
            QMessageBox.warning(self, "Acesso Negado", "Arquivo de usuários não encontrado.")
            return
        idxs = self.users.index[self.users["email"].astype(str).str.lower() == email].tolist()
        if idxs:
            i = idxs[0]
            if str(self.users.at[i, "password"]).strip() == senha:
                self.users.at[i, "last_login"] = pd.Timestamp.now()
                self.users.at[i, "remember"] = self.remember_cb.isChecked()
                self.save_users()
                perms = parse_permissions(self.users.at[i, "permissions"])
                self.open_main(perms if perms != "todos" else "todos")
                return
        QMessageBox.warning(self, "Acesso Negado", "E-mail ou senha incorretos")

    def solicitar_acesso(self):
        QMessageBox.information(self, "Acesso", "Cadastro simplificado desativado.")

    def open_main(self, perms):
        self.main = MainWindow(perms)
        self.main.show()
        self.close()

class MainWindow(QMainWindow):
    def __init__(self, perms):
        super().__init__()
        self.setWindowTitle("Sistema de Gestão de Frota")
        self.resize(1280, 860)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setDocumentMode(True)
        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(18, 18, 18, 18)
        cv.addWidget(self.tab_widget)
        self.setCentralWidget(central)
        home = QWidget()
        hv = QVBoxLayout(home)
        title_card = QFrame()
        title_card.setObjectName("glass")
        apply_shadow(title_card, radius=20, blur=60, color=QColor(0, 0, 0, 60))
        tv = QVBoxLayout(title_card)
        tv.setContentsMargins(24, 24, 24, 24)
        t = QLabel("Gestão de Frota")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setFont(QFont("Arial", 28, weight=QFont.Weight.Bold))
        tv.addWidget(t)
        hv.addWidget(title_card)
        grid_card = QFrame()
        grid_card.setObjectName("card")
        apply_shadow(grid_card, radius=18)
        gv = QGridLayout(grid_card)
        gv.setContentsMargins(18, 18, 18, 18)
        modules = MODULES + ["Base"]
        if perms != "todos":
            modules = [m for m in modules if (m == "Base") or (m in perms)]
        for i, mod in enumerate(modules):
            b = QPushButton(mod)
            b.setMinimumHeight(64)
            b.setFont(QFont("Arial", 16, weight=QFont.Weight.Bold))
            b.clicked.connect(lambda _, m=mod: self.open_module(m))
            gv.addWidget(b, i // 2, i % 2)
        hv.addWidget(grid_card)
        bar = QHBoxLayout()
        out = QPushButton("Sair")
        out.setObjectName("danger")
        out.setMinimumHeight(44)
        out.clicked.connect(self.logout)
        bar.addStretch(1)
        bar.addWidget(out)
        hv.addLayout(bar)
        self.tab_widget.addTab(home, "Início")

    def close_tab(self, index):
        if index == 0:
            return
        w = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        w.deleteLater()

    def add_or_focus(self, title, factory):
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx) == title:
                self.tab_widget.setCurrentIndex(idx)
                return
        w = factory()
        self.tab_widget.addTab(w, title)
        self.tab_widget.setCurrentWidget(w)

    def open_module(self, module):
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx)==module:
                self.tab_widget.setCurrentIndex(idx); return
        if module == "Infrações e Multas":
            w = MultasMenu(self.add_or_focus)
            self.tab_widget.addTab(w, "Infrações e Multas")
            self.tab_widget.setCurrentWidget(w)
            return
        if module == "Relatórios":
            file, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", "", "Planilhas (*.xlsx *.xls *.csv)")
            if not file:
                return
            w = RelatorioWindow(file)
        elif module == "Base":
            w = BaseWindow()
        elif module == "Combustível":
            w = CombustivelWindow()
        else:
            w = QWidget(); v = QVBoxLayout(w); v.addWidget(QLabel(module))
        self.tab_widget.addTab(w, module)
        self.tab_widget.setCurrentWidget(w)

    def logout(self):
        self.close()
        self.login = LoginWindow()
        self.login.show()

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
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
    """)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
