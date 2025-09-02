import sys, os
import pandas as pd

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox
)

from config import cfg_get, cfg_set, cfg_all
from utils import ensure_status_cols, _parse_dt_any, apply_shadow
from constants import DATE_COLS

from auth import AuthService           # (arquivo do usuário)
from login_view import LoginView       # (arquivo do usuário)
from base import BaseWindow            # (arquivo do usuário)
from multas import InfraMultasWindow   # (arquivo do usuário)
from relatorios import RelatorioWindow # (arquivo do usuário)

try:
    from combustivel import CombustivelWindow  # preferencial
except Exception:
    class CombustivelWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Combustível")
            v = QVBoxLayout(self)
            v.addWidget(QLabel("Módulo de Combustível não disponível."))



STYLE = """
QWidget { background: #FFFFFF; color: #0B2A4A; font-size: 14px; }
QFrame#card { background: #ffffff; border: 1px solid #214D80; border-radius: 18px; }
QFrame#glass { background: rgba(255,255,255,0.85); border: 1px solid rgba(11,42,74,0.25); border-radius: 18px; }
QLabel#headline { font-weight: 800; font-size: 20px; color: #0B2A4A; }
QPushButton { background: #0B2A4A; color:#ffffff; border:none; border-radius:12px; padding:10px 16px; font-weight:700; }
QPushButton:hover { background: #123C69; }
QPushButton#danger { background: #C62828; }
QHeaderView::section { background: #0B2A4A; color:#fff; padding:8px 10px; border:none; font-weight:700; }
"""


# =========================================================
# Janela principal
# =========================================================
class MainWindow(QMainWindow):
    def __init__(self, user_email: str | None = None):
        super().__init__()
        self.setWindowTitle("GESTÃO DE FROTAS")
        self.resize(1100, 760)

        # Conteúdo central
        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(18, 18, 18, 18)

        # Cabeçalho
        header = QWidget()
        header.setObjectName("glass")
        apply_shadow(header, radius=20)
        hv = QVBoxLayout(header)
        title = QLabel("Gestão de Frotas")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("headline")
        hv.addWidget(title)
        if user_email:
            hv.addWidget(QLabel(f"Logado como: {user_email}"), alignment=Qt.AlignmentFlag.AlignCenter)
        v.addWidget(header)

        # Grade de botões
        buttons = QWidget()
        buttons.setObjectName("card")
        apply_shadow(buttons, radius=18)
        bv = QHBoxLayout(buttons)
        bv.setSpacing(12)

        btn_base = QPushButton("Base")
        btn_multas = QPushButton("Infrações e Multas")
        btn_comb = QPushButton("Combustível")
        btn_rel = QPushButton("Relatórios")
        btn_alertas = QPushButton("Alertas")

        for b in (btn_base, btn_multas, btn_comb, btn_rel, btn_alertas):
            b.setMinimumHeight(56)
            bv.addWidget(b)

        v.addWidget(buttons)

        # Conexões
        btn_base.clicked.connect(self.open_base)
        btn_multas.clicked.connect(self.open_multas)
        btn_comb.clicked.connect(self.open_combustivel)
        btn_rel.clicked.connect(self.open_relatorios)
        btn_alertas.clicked.connect(self.show_alertas)

        # Barra inferior
        foot = QHBoxLayout()
        out = QPushButton("Sair")
        out.setObjectName("danger")
        out.clicked.connect(self.logout)
        foot.addStretch(1)
        foot.addWidget(out)
        v.addLayout(foot)

        # Para manter referências das janelas abertas
        self._child_windows = []

    # --------- Ações dos botões ---------
    def open_base(self):
        w = BaseWindow()
        w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        w.show()
        self._child_windows.append(w)

    def open_multas(self):
        w = InfraMultasWindow()
        w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        w.show()
        self._child_windows.append(w)

    def open_combustivel(self):
        w = CombustivelWindow()
        w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        w.show()
        self._child_windows.append(w)

    def open_relatorios(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", "", "Planilhas (*.xlsx *.xls *.csv)")
        if not path:
            return
        w = RelatorioWindow(path)
        w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        w.show()
        self._child_windows.append(w)

    # --------- Alertas (usa GERAL_MULTAS.csv + DATE_COLS) ---------
    def show_alertas(self):
        try:
            csv_path = cfg_get("geral_multas_csv")
            if not csv_path or not os.path.exists(csv_path):
                QMessageBox.information(self, "Alertas", "Configure o caminho do GERAL_MULTAS.csv na tela Base.")
                return

            df = pd.read_csv(csv_path, dtype=str).fillna("")
            df = ensure_status_cols(df, csv_path=None)

            now_q = QDate.currentDate()
            pend = []  # lista de tuplas (FLUIG, INFRATOR, PLACA, ETAPA, DATA, STATUS)

            for _, r in df.iterrows():
                for col in DATE_COLS:
                    st = str(r.get(f"{col}_STATUS", "")).strip()
                    if not st:
                        continue
                    # QDate (suporta dd/MM/yyyy, dd-MM-yyyy, yyyy-MM-dd, etc. via _parse_dt_any)
                    qd = _parse_dt_any(r.get(col, ""))
                    is_empty_date = not (isinstance(qd, QDate) and qd.isValid())

                    if st in ("Pendente", "Vencido"):
                        # Sem data => pendência
                        if is_empty_date:
                            pend.append((
                                str(r.get("FLUIG", "")),
                                str(r.get("INFRATOR", "")),
                                str(r.get("PLACA", "")),
                                col,
                                str(r.get(col, "")),
                                st
                            ))
                        else:
                            # Com data no passado e ainda aberto => Vencido
                            if qd < now_q and st in ("Pendente",):
                                pend.append((
                                    str(r.get("FLUIG", "")),
                                    str(r.get("INFRATOR", "")),
                                    str(r.get("PLACA", "")),
                                    col,
                                    qd.toString("dd/MM/yyyy"),
                                    "Vencido"
                                ))

            if not pend:
                QMessageBox.information(self, "Alertas", "Sem pendências.")
                return

            # Formata
            txt = "\n".join([f"FLUIG {a} • {b} • {c} • {d} • {e} • {f}" for a, b, c, d, e, f in pend[:400]])
            if len(pend) > 400:
                txt += f"\n... e mais {len(pend) - 400} itens."
            QMessageBox.information(self, "Alertas", txt)

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    # --------- Logout (volta ao LoginView) ---------
    def logout(self):
        self.hide()
        try:
            auth = AuthService()
            dlg = LoginView(auth_service=auth)
            if dlg.exec():
                # Se você quiser permissões por usuário, pode ler aqui do CSV (auth.list_users())
                email = getattr(auth, "current_user", None) if hasattr(auth, "current_user") else None
                nova = MainWindow(email)
                nova.show()
        finally:
            self.close()

def main():
    # Inicializa app
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    # Login
    auth = AuthService()
    dlg = LoginView(auth_service=auth)
    if dlg.exec():
        email = getattr(auth, "current_user", None) if hasattr(auth, "current_user") else None
        win = MainWindow(email)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()