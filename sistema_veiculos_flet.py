from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QMainWindow, QGridLayout, QLineEdit, QInputDialog, QDialog, QDialogButtonBox, QScrollArea, QCheckBox
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QIcon
from PyQt6.QtCore import Qt, QPropertyAnimation
import pandas as pd
import sys
import os
import re
from datetime import datetime, timedelta

USERS_FILE = 'users.csv'
MODULES = [
    "Combustível",
    "Condutores",
    "Infrações e Multas",
    "Acidentes",
    "Avarias Corretivas (Acidentes e Mau Uso)",
    "Relatórios"
]

class TransparentOverlay(QWidget):
    def __init__(self, parent=None, color=QColor(255,255,255,204)):
        super().__init__(parent)
        self.color = color
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)

class SummaryWindow(QWidget):
    def __init__(self, df):
        super().__init__()
        self.setWindowTitle("Visão Geral")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        tabela = QTableWidget()
        tabela.setColumnCount(2)
        tabela.setHorizontalHeaderLabels(["Coluna", "Resumo"])
        resumo = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                valor = df[col].sum()
            else:
                valor = df[col].nunique()
            resumo.append((col, str(valor)))
        tabela.setRowCount(len(resumo))
        for i, (col, val) in enumerate(resumo):
            tabela.setItem(i, 0, QTableWidgetItem(col))
            tabela.setItem(i, 1, QTableWidgetItem(val))
        tabela.resizeColumnsToContents()
        layout.addWidget(tabela)
        btn = QPushButton("Fechar")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

class RelatorioWindow(QWidget):
    def __init__(self, caminho_arquivo):
        super().__init__()
        self.setWindowTitle("Relatório com Segmentação")
        self.resize(1000, 700)
        ext = os.path.splitext(caminho_arquivo)[1].lower()
        if ext in ('.xlsx', '.xls'):
            self.df_original = pd.read_excel(caminho_arquivo)
        elif ext == '.csv':
            try:
                self.df_original = pd.read_csv(caminho_arquivo, encoding='utf-8')
            except UnicodeDecodeError:
                self.df_original = pd.read_csv(caminho_arquivo, encoding='latin1')
        else:
            QMessageBox.warning(self, "Aviso", "Formato não suportado")
            self.close()
            return
        self.df_filtrado = self.df_original.copy()
        self.layout = QVBoxLayout(self)
        self.filtros_layout = QHBoxLayout()
        self.filtros = {}
        self.text_filtros = {}
        for coluna in self.df_original.columns:
            box = QVBoxLayout()
            label = QLabel(coluna)
            label.setFont(QFont("Arial", 10, weight=QFont.Weight.Bold))
            combo = QComboBox()
            combo.addItem("Todos")
            valores = sorted(self.df_original[coluna].dropna().unique().astype(str))
            combo.addItems(valores)
            combo.currentTextChanged.connect(self.atualizar_filtro)
            entrada = QLineEdit()
            entrada.setPlaceholderText(f"Filtrar {coluna}...")
            entrada.textChanged.connect(self.atualizar_filtro)
            self.filtros[coluna] = combo
            self.text_filtros[coluna] = entrada
            box.addWidget(label)
            box.addWidget(combo)
            box.addWidget(entrada)
            self.filtros_layout.addLayout(box)
        self.layout.addLayout(self.filtros_layout)
        self.tabela = QTableWidget()
        self.layout.addWidget(self.tabela)
        btn_visao = QPushButton("Visão Geral")
        btn_visao.clicked.connect(self.mostrar_visao)
        self.layout.addWidget(btn_visao)
        btn_limpar = QPushButton("Limpar todos os filtros")
        btn_limpar.clicked.connect(self.limpar_filtros)
        self.layout.addWidget(btn_limpar)
        btn_exp = QPushButton("Exportar para Excel")
        btn_exp.clicked.connect(self.exportar_excel)
        self.layout.addWidget(btn_exp)
        self.preencher_tabela(self.df_filtrado)
        self.showMaximized()


    def mostrar_visao(self):
        self.visao = SummaryWindow(self.df_filtrado)
        self.visao.show()
    def limpar_filtros(self):
        for combo in self.filtros.values():
            combo.setCurrentIndex(0)
        for entrada in self.text_filtros.values():
            entrada.clear()
        self.atualizar_filtro()
    def atualizar_filtro(self):
        df = self.df_original.copy()
        for coluna in self.df_original.columns:
            sel = self.filtros[coluna].currentText()
            txt = self.text_filtros[coluna].text().strip().lower()
            if sel != "Todos":
                df = df[df[coluna].astype(str) == sel]
            if txt:
                termos = txt.split()
                df = df[df[coluna].astype(str).str.lower().apply(lambda x: all(re.search(re.escape(t), x) for t in termos))]
        self.df_filtrado = df
        self.preencher_tabela(df)
    def preencher_tabela(self, df):
        self.tabela.clear()
        self.tabela.setColumnCount(len(df.columns))
        self.tabela.setRowCount(len(df))
        self.tabela.setHorizontalHeaderLabels(df.columns)
        for i in range(len(df)):
            for j, col in enumerate(df.columns):
                val = str(df.iloc[i, j])
                txt = self.text_filtros[col].text().strip().lower()
                termos = txt.split()
                item = QTableWidgetItem(val)
                if txt and all(t in val.lower() for t in termos):
                    item.setForeground(QColor("red"))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.tabela.setItem(i, j, item)
        self.tabela.resizeColumnsToContents()
    def exportar_excel(self):
        try:
            self.df_filtrado.to_excel("relatorio_filtrado.xlsx", index=False)
            QMessageBox.information(self, "Exportado", "Relatório exportado para 'relatorio_filtrado.xlsx'.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar: {e}")

class ModuloWindow(QWidget):
    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(parent.size())
        self.setMinimumSize(400, 300)
        self.bg_pix = getattr(parent, 'pixmap_fundo', None)
        bg_label = QLabel(self)
        if self.bg_pix:
            bg_label.setPixmap(self.bg_pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        bg_label.setScaledContents(True)
        bg_label.resize(self.size())
        bg_label.setWindowOpacity(0.2)
        overlay = TransparentOverlay(self, QColor(255,255,255,200))
        overlay.resize(self.size())
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(20,20,20,20)
        title_lbl = QLabel(titulo)
        title_lbl.setFont(QFont("Arial",20,weight=QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)
        back_btn = QPushButton("Início")
        back_btn.setFont(QFont("Arial",16))
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn)
    def resizeEvent(self, event):
        super().resizeEvent(event)

class PermissionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Permissões")
        layout = QVBoxLayout(self)
        area = QScrollArea(self)
        widget = QWidget()
        vlayout = QVBoxLayout(widget)
        self.checks = []
        for m in MODULES:
            cb = QCheckBox(m)
            vlayout.addWidget(cb)
            self.checks.append(cb)
        area.setWidget(widget)
        area.setWidgetResizable(True)
        layout.addWidget(area)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def selected(self):
        return [cb.text() for cb in self.checks if cb.isChecked()]

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.users = self.load_users()
        self.setWindowTitle("Login")
        self.resize(400, 260)
        layout = QVBoxLayout(self)
        title_lbl = QLabel("🚀 Bem-vindo ao Sistema de Gestão de Frota")
        title_lbl.setFont(QFont("Arial", 20, weight=QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)
        email_lbl = QLabel("Selecione seu e-mail")
        email_lbl.setFont(QFont("Arial", 14))
        layout.addWidget(email_lbl)
        self.email_combo = QComboBox()
        self.email_combo.setEditable(True)
        self.email_combo.addItems(self.users['email'].tolist())
        self.email_combo.currentTextChanged.connect(self.prefill)
        layout.addWidget(self.email_combo)
        pass_lbl = QLabel("Senha")
        pass_lbl.setFont(QFont("Arial", 14))
        layout.addWidget(pass_lbl)
        self.password_input = QLineEdit()
        self.password_input.setFont(QFont("Arial", 14))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        toggle_action = self.password_input.addAction(QIcon('eye.png'), QLineEdit.ActionPosition.TrailingPosition)
        toggle_action.triggered.connect(self.toggle_password)
        self.toggle_action = toggle_action
        layout.addWidget(self.password_input)
        self.remember_cb = QCheckBox("Lembrar acesso por 30 dias")
        layout.addWidget(self.remember_cb)
        btn_layout = QHBoxLayout()
        login_btn = QPushButton("Entrar")
        login_btn.setFont(QFont("Arial", 14))
        login_btn.setIcon(QIcon('login_icon.png'))
        login_btn.clicked.connect(self.tentar_login)
        btn_layout.addWidget(login_btn)
        request_btn = QPushButton("Solicitar Acesso")
        request_btn.setFont(QFont("Arial", 14))
        request_btn.setIcon(QIcon('request_icon.png'))
        request_btn.clicked.connect(self.solicitar_acesso)
        btn_layout.addWidget(request_btn)
        close_btn = QPushButton("Fechar")
        close_btn.setFont(QFont("Arial", 14))
        close_btn.setIcon(QIcon('close_icon.png'))
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        self.prefill()
    def showEvent(self, event):
        self.setWindowOpacity(0)
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(500)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        self.anim = anim
        super().showEvent(event)
    def toggle_password(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_action.setIcon(QIcon('eye_off.png'))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_action.setIcon(QIcon('eye.png'))
    def load_users(self):
        if os.path.exists(USERS_FILE):
            return pd.read_csv(USERS_FILE, parse_dates=['last_login'])
        df = pd.DataFrame(columns=['email','password','last_login','permissions','remember'])
        df.to_csv(USERS_FILE, index=False)
        return df
    def save_users(self):
        self.users.to_csv(USERS_FILE, index=False)
    def prefill(self):
        email = self.email_combo.currentText().strip().lower()
        row = self.users[self.users['email'] == email]
        now = datetime.now()
        if not row.empty and row.iloc[0]['remember'] and now - row.iloc[0]['last_login'] <= timedelta(days=30):
            self.password_input.setText(str(row.iloc[0]['password']))
            self.remember_cb.setChecked(True)
        else:
            self.password_input.clear()
            self.remember_cb.setChecked(False)
    def tentar_login(self):
        email = self.email_combo.currentText().strip().lower()
        senha = self.password_input.text().strip()
        idxs = self.users.index[self.users['email'] == email].tolist()
        if idxs:
            i = idxs[0]
            stored_pw = str(self.users.at[i, 'password']).strip()
            if stored_pw == senha:
                self.users.at[i,'last_login'] = datetime.now()
                self.users.at[i,'remember'] = self.remember_cb.isChecked()
                self.save_users()
                perms = self.users.at[i,'permissions']
                self.open_main(perms)
                return
        QMessageBox.warning(self, "Acesso Negado", "E-mail ou senha incorretos")
    def solicitar_acesso(self):
        email, ok = QInputDialog.getText(self, "Novo Usuário", "Digite o e-mail:")
        if not ok or not email:
            return
        email = email.strip().lower()
        if email in self.users['email'].tolist():
            QMessageBox.warning(self, "Erro", "E-mail já cadastrado")
            return
        master, ok2 = QInputDialog.getText(self, "Senha Master", "Senha master:", QLineEdit.EchoMode.Password)
        if not ok2 or master != 'Universal@25':
            QMessageBox.warning(self, "Erro", "Senha master incorreta")
            return
        dlg = PermissionsDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        perms = dlg.selected()
        pwd, ok3 = QInputDialog.getText(self, "Senha Usuário", "Defina a senha:", QLineEdit.EchoMode.Password)
        if not ok3 or not pwd:
            return
        now = datetime.now()
        self.users.loc[len(self.users)] = {
            'email': email,
            'password': pwd,
            'last_login': now,
            'permissions': perms,
            'remember': False
        }
        self.save_users()
        self.email_combo.addItem(email)
        QMessageBox.information(self, "Sucesso", "Usuário cadastrado")
    def open_main(self, perms):
        self.main = MainWindow(perms if isinstance(perms, list) else 'todos')
        self.main.show()
        self.close()

class MainWindow(QMainWindow):
    def __init__(self, perms):
        super().__init__()
        self.setWindowTitle("Sistema de Gestão de Frota")
        self.resize(1024, 768)
        central = QWidget()
        self.setCentralWidget(central)
        self.bg_label = QLabel(central)
        if os.path.exists('fundo1.jpg'):
            pix = QPixmap('fundo1.jpg').scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            self.bg_label.setPixmap(pix)
        self.bg_label.setScaledContents(True)
        self.bg_label.resize(self.size())
        self.bg_label.setWindowOpacity(0.2)
        self.overlay = TransparentOverlay(central, QColor(255,255,255,200))
        self.overlay.resize(self.size())
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(15)
        title = QLabel("🚗 Sistema de Gestão de Frota")
        title.setFont(QFont("Arial",28,weight=QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        modules = MODULES if perms == "todos" else [m for m in MODULES if m in perms]
        grid = QGridLayout()
        grid.setSpacing(15)
        for i, mod in enumerate(modules):
            btn = QPushButton(mod)
            btn.setFont(QFont("Arial",16,weight=QFont.Weight.Bold))
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda _,m=mod: self.open_module(m))
            grid.addWidget(btn, i//2, i%2)
        layout.addLayout(grid)
        sair = QPushButton("Sair")
        sair.setFont(QFont("Arial",16,weight=QFont.Weight.Bold))
        sair.setMinimumHeight(50)
        sair.setStyleSheet(
            "QPushButton{background-color:#ff6666;color:white;border:none;}"
            "QPushButton:hover{background-color:#ff4444;}"
        )
        sair.clicked.connect(self.logout)
        layout.addWidget(sair)
    def open_module(self, module):
        if module == "Relatórios":
            files = [f for f in os.listdir() if f.lower().endswith(('.xlsx', '.csv'))]
            if not files:
                QMessageBox.warning(self, "Aviso", "Não há arquivos .xlsx ou .csv nesta pasta.")
                return
            file, ok = QInputDialog.getItem(self, "Arquivo", "Selecione arquivo:", files, 0, False)
            if ok and file:
                self.rel_window = RelatorioWindow(file)
                self.rel_window.show()
        else:
            self.mod_window = ModuloWindow(module, self)
            self.mod_window.show()
    def logout(self):
        self.close()
        self.login = LoginWindow()
        self.login.show()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_label.resize(self.size())
        self.overlay.resize(self.size())

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
    QWidget {
        background-color: #001f3f;
        color: white;
    }
    QPushButton {
        background-color: #FF4136;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
    }
    QPushButton:hover {
        background-color: #FF6347;
    }
    QLineEdit, QComboBox {
        background-color: white;
        color: #001f3f;
        border: 1px solid #001f3f;
        border-radius: 3px;
        padding: 4px;
    }
    QTableWidget {
        background-color: white;
        color: #001f3f;
        gridline-color: #001f3f;
    }
    QHeaderView::section {
        background-color: #001f3f;
        color: white;
        padding: 4px;
        border: none;
    }
    """)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()