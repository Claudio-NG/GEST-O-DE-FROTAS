from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout
)
from PyQt6.QtGui import QIcon, QAction   # QAction vem do QtGui
from PyQt6.QtCore import Qt

class LoginView(QDialog):
    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("Entrar — GESTÃO DE FROTAS")
        self.setModal(True)
        self.setFixedSize(420, 320)

        self.user = QLineEdit(placeholderText="Usuário")
        self.pwd  = QLineEdit(placeholderText="Senha"); self.pwd.setEchoMode(QLineEdit.EchoMode.Password)

        toggle = QAction("👁", self); toggle.triggered.connect(self._toggle_pwd)
        self.pwd.addAction(toggle, QLineEdit.ActionPosition.TrailingPosition)

        self.btn = QPushButton("Entrar"); self.btn.clicked.connect(self._do_login)

        form = QFormLayout(); form.addRow("Usuário", self.user); form.addRow("Senha", self.pwd)
        root = QVBoxLayout(); root.addLayout(form); root.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(root)

        self.user.returnPressed.connect(self._do_login)
        self.pwd.returnPressed.connect(self._do_login)

    def _toggle_pwd(self):
        mode = self.pwd.echoMode()
        self.pwd.setEchoMode(QLineEdit.EchoMode.Normal if mode==QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password)

    def _do_login(self):
        ok, msg = self.auth.login(self.user.text().strip(), self.pwd.text())
        if ok: self.accept()
        else:  self._show_error(msg)

    def _show_error(self, msg):
        self.pwd.setStyleSheet("border:1px solid #e11;")
        self.pwd.setToolTip(msg or "Usuário ou senha inválidos")
