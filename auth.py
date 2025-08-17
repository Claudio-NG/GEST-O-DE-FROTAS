import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton, QScrollArea, QFormLayout, QMessageBox
from utils import parse_permissions
from constants import USERS_FILE, MODULES

class CadastroUsuarioDialog(QDialog):
    def __init__(self, parent, email_existentes):
        super().__init__(parent)
        self.setWindowTitle("Cadastro de Usuário")
        self.resize(520, 460)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.email = QLineEdit(); form.addRow("E-mail", self.email)
        self.senha = QLineEdit(); self.senha.setEchoMode(QLineEdit.EchoMode.Password); form.addRow("Senha", self.senha)
        area = QScrollArea(); area.setWidgetResizable(True)
        inner = QWidget(); lv = QVBoxLayout(inner)
        self.checks = []
        for m in MODULES:
            cb = QCheckBox(m); lv.addWidget(cb); self.checks.append(cb)
        area.setWidget(inner)
        v.addLayout(form)
        v.addWidget(QLabel("Permissões"))
        v.addWidget(area)
        bar = QHBoxLayout()
        self.btn_save = QPushButton("Salvar"); self.btn_close = QPushButton("Fechar")
        bar.addWidget(self.btn_save); bar.addStretch(1); bar.addWidget(self.btn_close)
        v.addLayout(bar)
        self.email_existentes = set(email_existentes)
        self.btn_close.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.try_accept)

    def try_accept(self):
        email = self.email.text().strip().lower()
        pwd = self.senha.text().strip()
        if not email or not pwd:
            QMessageBox.warning(self,"Aviso","Preencha e-mail e senha"); return
        if email in self.email_existentes:
            QMessageBox.warning(self,"Aviso","E-mail já cadastrado"); return
        self.email_value = email
        self.password_value = pwd
        self.perms_value = [cb.text() for cb in self.checks if cb.isChecked()]
        self.accept()

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        from PyQt6.QtGui import QFont
        from utils import apply_shadow
        flags = Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setFixedSize(self.size())
        wrap = QWidget(self); wrap.setObjectName("glass"); wrap.setGeometry(0,0,480,340); apply_shadow(wrap, radius=20, blur=60)
        v = QVBoxLayout(wrap); v.setContentsMargins(20,20,20,20)
        title = QLabel("Gestão de Frota"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 22, weight=QFont.Weight.Bold)); v.addWidget(title)
        v.addSpacing(6)
        email_lbl = QLabel("E-mail"); v.addWidget(email_lbl)
        self.email_combo = QComboBox(); self.email_combo.setEditable(True)
        self.email_combo.addItems(self.load_users()['email'].astype(str).tolist())
        self.email_combo.currentTextChanged.connect(self.prefill)
        v.addWidget(self.email_combo)
        pass_lbl = QLabel("Senha"); v.addWidget(pass_lbl)
        self.password_input = QLineEdit(); self.password_input.setEchoMode(QLineEdit.EchoMode.Password); v.addWidget(self.password_input)
        show = QCheckBox("Mostrar senha"); show.stateChanged.connect(lambda s: self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password)); v.addWidget(show)
        self.remember_cb = QCheckBox("Lembrar acesso por 30 dias"); v.addWidget(self.remember_cb)
        bar = QHBoxLayout()
        login_btn = QPushButton("Entrar"); login_btn.clicked.connect(self.tentar_login); bar.addWidget(login_btn)
        req_btn = QPushButton("Solicitar Acesso"); req_btn.clicked.connect(self.solicitar_acesso); bar.addWidget(req_btn)
        v.addLayout(bar)
        self.prefill()

    def showEvent(self, e):
        self.setWindowOpacity(1.0)
        super().showEvent(e)

    def load_users(self):
        import os
        if os.path.exists(USERS_FILE):
            return pd.read_csv(USERS_FILE, parse_dates=['last_login'])
        df = pd.DataFrame(columns=['email','password','last_login','permissions','remember'])
        df.to_csv(USERS_FILE, index=False)
        return df

    def save_users(self):
        self.users.to_csv(USERS_FILE, index=False)

    def prefill(self):
        self.users = self.load_users()
        email = str(self.email_combo.currentText()).strip().lower()
        row = self.users[self.users['email']==email]
        now = pd.Timestamp.now()
        if not row.empty and bool(row.iloc[0].get('remember', False)) and pd.notna(row.iloc[0].get('last_login')) and now - row.iloc[0]['last_login'] <= pd.Timedelta(days=30):
            self.password_input.setText(str(row.iloc[0]['password']))
            self.remember_cb.setChecked(True)
        else:
            self.password_input.clear()
            self.remember_cb.setChecked(False)

    def tentar_login(self):
        email = str(self.email_combo.currentText()).strip().lower()
        senha = self.password_input.text().strip()
        idxs = self.users.index[self.users['email']==email].tolist()
        if idxs:
            i = idxs[0]
            if str(self.users.at[i, 'password']).strip() == senha:
                self.users.at[i, 'last_login'] = pd.Timestamp.now()
                self.users.at[i, 'remember'] = self.remember_cb.isChecked()
                self.save_users()
                perms = parse_permissions(self.users.at[i, 'permissions'])
                self.open_main(perms)
                return
        QMessageBox.warning(self,"Acesso Negado","E-mail ou senha incorretos")

    def solicitar_acesso(self):
        users = self.load_users()
        dlg = CadastroUsuarioDialog(self, users['email'].astype(str).tolist())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            email = dlg.email_value
            pwd = dlg.password_value
            perms = dlg.perms_value
            now = pd.Timestamp.now()
            self.users.loc[len(self.users)] = {'email':email,'password':pwd,'last_login':now,'permissions':perms,'remember':False}
            self.save_users()
            self.email_combo.addItem(email)
            QMessageBox.information(self,"Sucesso","Usuário cadastrado")

    def open_main(self, perms):
        from main_window import MainWindow
        self.main = MainWindow(perms if perms!='todos' else 'todos')
        self.main.show()
        self.close()
