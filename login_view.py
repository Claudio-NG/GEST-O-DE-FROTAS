# login_view.py (SUBSTITUA O ARQUIVO TODO POR ESTA VERSÃO)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QFrame, QMessageBox
)
from utils import apply_shadow

class LoginView(QDialog):
    def __init__(self, auth_service):
        super().__init__()
        self.auth = auth_service
        self.setWindowTitle("Login • Gestão de Frotas")
        self.resize(420, 300)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("card")
        apply_shadow(card, radius=18)
        v = QVBoxLayout(card)
        v.setSpacing(12)

        title = QLabel("Bem-vindo")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:800;")
        v.addWidget(title)

        self.ed_user = QLineEdit(); self.ed_user.setPlaceholderText("E-mail")
        self.ed_pass = QLineEdit(); self.ed_pass.setPlaceholderText("Senha"); self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ck_rem = QCheckBox("Lembrar-me neste dispositivo")

        v.addWidget(self.ed_user)
        v.addWidget(self.ed_pass)
        v.addWidget(self.ck_rem)

        btn_row = QHBoxLayout()
        btn_login = QPushButton("Entrar")
        btn_cancel = QPushButton("Cancelar")
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_login)
        v.addLayout(btn_row)

        root.addWidget(card)

        # eventos
        btn_login.clicked.connect(self.do_login)
        btn_cancel.clicked.connect(self.reject)
        self.ed_pass.returnPressed.connect(self.do_login)   # Enter envia

        # pré-preencher com usuário lembrado, se existir
        remembered = getattr(self.auth, "get_remembered_user", lambda: None)()
        if remembered:
            self.ed_user.setText(remembered)
            self.ck_rem.setChecked(True)

    def do_login(self):
        user = self.ed_user.text().strip()
        pwd = self.ed_pass.text().strip()
        ok, msg = self.auth.login(user, pwd)
        if not ok:
            QMessageBox.warning(self, "Login", msg)
            return
        try:
            self.auth.set_remember(user, self.ck_rem.isChecked())
        except:
            pass
        self.accept()