from __future__ import annotations

import os, json, base64
from pathlib import Path
import pandas as pd

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QPushButton, QFrame, QFileDialog, QWidget, QMainWindow, QTabWidget, QMessageBox,
    QGridLayout, QScrollArea, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QSlider
)

<<<<<<< HEAD
=======

>>>>>>> f9b717829de913f73d13717fa914335134ff238d
USERS_FILE = "users.csv"

BASE_DIR = os.path.expanduser("~")
APP_DIR = os.path.join(BASE_DIR, "Documentos", "GestaoFrotas")

MULTAS_ROOT = os.path.join(APP_DIR, "Multas")
GERAL_MULTAS_CSV = os.path.join(MULTAS_ROOT, "geral_multas.csv")
PASTORES_DIR = os.path.join(APP_DIR, "Pastores")

DATE_FORMAT = "dd/MM/yyyy"
DATE_COLS = ["DATA INDICAÇÃO", "BOLETO", "SGU", "VALIDACAO NFF", "CONCLUSAO"]

STATUS_COLOR = {
    "PAGA": QColor("#10B981"),
    "ABERTA": QColor("#F59E0B"),
    "VENCIDA": QColor("#EF4444"),
    "CANCELADA": QColor("#6B7280"),
    "EM ANALISE": QColor("#3B82F6"),
    "EM RECURSO": QColor("#9333EA"),
    "(SEM STATUS)": QColor("#9E9E9E"),
    "Pago": QColor("#2ecc71"),
    "Pendente": QColor("#ffd166"),
    "Vencido": QColor("#ef5350"),
    "": QColor("#BDBDBD"),
}

ORGAOS = ["DETRAN", "DEMUTRAM", "STTU", "DNIT", "PRF", "SEMUTRAM", "DMUT"]

MODULES = ["Início", "Base", "Alertas", "Infrações e Multas", "Relatórios", "Combustível", "Condutor"]

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

CFG_PATH = str(Path(__file__).resolve().parent / "base.json")
DEFAULTS = {
    "geral_multas_csv": GERAL_MULTAS_CSV,
    "multas_root": MULTAS_ROOT,
    "pastores_dir": PASTORES_DIR,
    "detalhamento_path": os.path.join(APP_DIR, "CPO-VEÍCULOS", "Notificações de Multas - Detalhamento.xlsx"),
    "pastores_file": os.path.join(APP_DIR, "CPO-VEÍCULOS", "Notificações de Multas - Fase Pastores.xlsx"),
    "condutor_identificado_path": os.path.join(APP_DIR, "CPO-VEÍCULOS", "Notificações de Multas - Condutor Identificado.xlsx"),
    "extrato_geral_path": "",
    "extrato_simplificado_path": "",
    "users_file": USERS_FILE,
    "remember_user": "",
    "remember_pwd": "",
    "remember_flag": "0",
}

def _cfg_load() -> dict:
    try:
        if os.path.exists(CFG_PATH):
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        else:
            data = {}
    except Exception:
        data = {}
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    return data

def _cfg_save(data: dict) -> None:
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def cfg_get(key: str, default=None):
    data = _cfg_load()
    return data.get(key, DEFAULTS.get(key) if default is None else default)

def cfg_set(key: str, value):
    data = _cfg_load()
    data[key] = value
    _cfg_save(data)

def cfg_all() -> dict:
    return _cfg_load()

DETALHAMENTO_PATH = cfg_get("detalhamento_path")
EXTRATO_GERAL_PATH = cfg_get("extrato_geral_path")
EXTRATO_SIMPLIFICADO_PATH = cfg_get("extrato_simplificado_path")
CONDUTOR_IDENTIFICADO_PATH = cfg_get("condutor_identificado_path")
GERAL_MULTAS_CSV = cfg_get("geral_multas_csv") or GERAL_MULTAS_CSV

def _enc(txt: str) -> str:
    return base64.b64encode((txt or "").encode("utf-8")).decode("ascii")

def _dec(txt: str) -> str:
    try:
        return base64.b64decode((txt or "").encode("ascii")).decode("utf-8")
    except Exception:
        return ""

def _paint_status(item: QTableWidgetItem, status: str):
    st = (status or "").strip()
    bg = STATUS_COLOR.get(st) or STATUS_COLOR.get(st.upper()) or STATUS_COLOR.get("(SEM STATUS)")
    if bg:
        item.setBackground(bg)
        yiq = (bg.red()*299 + bg.green()*587 + bg.blue()*114)/1000
        item.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))

def to_qdate_flexible(s: str) -> QDate:
    s = (s or "").strip()
    if not s:
        return QDate()
    for fmt in ["dd/MM/yyyy","dd-MM-yyyy","yyyy-MM-dd","yyyy/MM/dd"]:
        q = QDate.fromString(s, fmt)
        if q.isValid():
            return q
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return QDate(int(dt.year), int(dt.month), int(dt.day))
    except Exception:
        pass
    return QDate()

class AuthService:
    def __init__(self):
        self.current_user: str | None = None
    def login(self, user: str, password: str) -> tuple[bool, str]:
        email = (user or "").strip().lower()
        pwd = (password or "").strip()
        if not email or not pwd:
            return False, "Informe usuário e senha."
        self.current_user = email
        return True, "OK"

class LoginView(QDialog):
    def __init__(self, auth_service):
        super().__init__()
        self.auth = auth_service
        self.setWindowTitle("Login • Gestão de Frotas")
        self.resize(420, 300)
        self.setModal(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        card = QFrame(); card.setObjectName("card")
        from utils import apply_shadow
        apply_shadow(card, radius=18)
        v = QVBoxLayout(card); v.setSpacing(12)
        title = QLabel("Bem-vindo"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:800;")
        v.addWidget(title)
        self.ed_user = QLineEdit(); self.ed_user.setPlaceholderText("E-mail")
        self.ed_pass = QLineEdit(); self.ed_pass.setPlaceholderText("Senha"); self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ck_rem = QCheckBox("Lembrar-me neste dispositivo")
        v.addWidget(self.ed_user); v.addWidget(self.ed_pass); v.addWidget(self.ck_rem)
        btn_row = QHBoxLayout()
        btn_login = QPushButton("Entrar")
        btn_cancel = QPushButton("Cancelar")
        btn_row.addStretch(1); btn_row.addWidget(btn_cancel); btn_row.addWidget(btn_login)
        v.addLayout(btn_row)
        root.addWidget(card)
        btn_login.clicked.connect(self.do_login)
        btn_cancel.clicked.connect(self.reject)
        self.ed_pass.returnPressed.connect(self.do_login)
        remembered_user = cfg_get("remember_user") or ""
        remembered_pwd = _dec(cfg_get("remember_pwd") or "")
        remembered_flag = cfg_get("remember_flag") == "1"
        self.ed_user.setText(remembered_user)
        self.ed_pass.setText(remembered_pwd)
        self.ck_rem.setChecked(remembered_flag)
    def do_login(self):
        ok, msg = self.auth.login(self.ed_user.text(), self.ed_pass.text())
        if not ok:
            QMessageBox.warning(self, "Login", msg); return
        if self.ck_rem.isChecked():
            cfg_set("remember_user", self.ed_user.text().strip())
            cfg_set("remember_pwd", _enc(self.ed_pass.text()))
            cfg_set("remember_flag", "1")
        else:
            cfg_set("remember_user", "")
            cfg_set("remember_pwd", "")
            cfg_set("remember_flag", "0")
        self.accept()

class _PathRow(QWidget):
    def __init__(self, label, key, mode="file"):
        super().__init__()
        self.key = key
        self.mode = mode
        h = QHBoxLayout(self)
        self.lab = QLabel(label)
        self.ed = QLineEdit(cfg_get(key))
        self.btn = QPushButton("..."); self.btn.setFixedWidth(36)
        def _pick(_checked=False, le_=self.ed, label_=label):
            if self.mode == "dir":
                p = QFileDialog.getExistingDirectory(self, f"Selecionar {label_}", self.ed.text().strip() or os.getcwd())
            else:
                p, _ = QFileDialog.getOpenFileName(self, f"Selecionar {label_}", "", "Todos (*.*)")
            if p:
                le_.setText(p)
        self.btn.clicked.connect(_pick)
        h.addWidget(self.lab); h.addWidget(self.ed, 1); h.addWidget(self.btn)
    def value(self):
        return self.ed.text().strip()

class BaseTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        card = QFrame(); card.setObjectName("card")
        from utils import apply_shadow
        apply_shadow(card, radius=18)
        v = QVBoxLayout(card)
        grid = QGridLayout()
        rows_cfg = [
            ("GERAL_MULTAS.csv", "geral_multas_csv", "file"),
            ("Pasta MULTAS", "multas_root", "dir"),
            ("Detalhamento (planilha)", "detalhamento_path", "file"),
            ("Fase Pastores (planilha)", "pastores_file", "file"),
            ("Condutor Identificado (planilha)", "condutor_identificado_path", "file"),
            ("Diretório Pastores", "pastores_dir", "dir"),
            ("Extrato Geral (Combustível)", "extrato_geral_path", "file"),
            ("Extrato Simplificado (Combustível)", "extrato_simplificado_path", "file"),
            ("Arquivo de usuários", "users_file", "file"),
        ]
        self.rows = []
        for i, (lab, key, mode) in enumerate(rows_cfg):
            r = _PathRow(lab, key, mode)
            grid.addWidget(r, i, 0)
            self.rows.append((key, r))
        v.addLayout(grid)
        bar = QHBoxLayout()
        btn_save = QPushButton("Salvar"); btn_save.clicked.connect(self._save)
        bar.addStretch(1); bar.addWidget(btn_save)
        v.addLayout(bar)
        root.addWidget(card)
    def _save(self):
        for key, row in self.rows:
            cfg_set(key, row.value())
        QMessageBox.information(self, "Base", "Configurações salvas com sucesso.")

<<<<<<< HEAD
=======
# =========================
# Aba “Alertas”
# =========================
class CheckableComboBox(QComboBox):
    from PyQt6.QtCore import pyqtSignal
    changed = pyqtSignal()
    def __init__(self, values):
        super().__init__()
        self.set_values(values)
        self.view().pressed.connect(self._toggle)
        self._update_text()

    def set_values(self, values):
        self.blockSignals(True)
        self.clear()
        vals = sorted({str(v) for v in values if str(v).strip()})
        if not vals:
            self.addItem("(vazio)")
            idx = self.model().index(0, 0)
            self.model().setData(idx, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        else:
            for i, v in enumerate(vals):
                self.addItem(v)
                idx = self.model().index(i, 0)
                self.model().setData(idx, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.blockSignals(False)
        self._update_text()

    def _toggle(self, index):
        st = self.model().data(index, Qt.ItemDataRole.CheckStateRole)
        ns = Qt.CheckState.Unchecked if st == Qt.CheckState.Checked else Qt.CheckState.Checked
        self.model().setData(index, ns, Qt.ItemDataRole.CheckStateRole)
        self._update_text(); self.changed.emit()

    def selected_values(self):
        out = []
        for i in range(self.count()):
            idx = self.model().index(i, 0)
            st = self.model().data(idx, Qt.ItemDataRole.CheckStateRole)
            if st == Qt.CheckState.Checked:
                out.append(self.itemText(i))
        return out

    def _update_text(self):
        n = len(self.selected_values())
        self.setEditable(True); self.lineEdit().setReadOnly(True)
        self.lineEdit().setText("Todos" if n == 0 else f"{n} selecionados")
        self.setEditable(False)

class AlertsTab(QWidget):
 
    def __init__(self):
        super().__init__()
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.mode_filtros = {}
        self.multi_filtros = {}
        self.global_boxes = []

        root = QVBoxLayout(self)

        # Header
        header = QFrame(); header.setObjectName("card"); apply_shadow(header, radius=18)
        hv = QVBoxLayout(header)
        actions = QHBoxLayout()
        btn_reload = QPushButton("Recarregar"); btn_reload.clicked.connect(self.recarregar)
        btn_clear  = QPushButton("Limpar filtros"); btn_clear.clicked.connect(self.limpar_filtros)
        btn_export = QPushButton("Exportar Excel"); btn_export.clicked.connect(self.exportar_excel)
        actions.addWidget(btn_reload); actions.addWidget(btn_clear); actions.addStretch(1); actions.addWidget(btn_export)
        hv.addLayout(actions)

        # Filtro global (+)
        row_global = QHBoxLayout()
        row_global.addWidget(QLabel("Filtro global:"))
        def _add_box():
            le = QLineEdit()
            le.setPlaceholderText("Digite para filtrar em TODAS as colunas…")
            le.textChanged.connect(self._apply_filters)
            self.global_boxes.append(le)
            row_global.addWidget(le, 1)
        _add_box()
        btn_plus = QPushButton("+"); btn_plus.setFixedWidth(28); btn_plus.clicked.connect(_add_box)
        row_global.addWidget(btn_plus)
        hv.addLayout(row_global)

        # filtros por coluna
        self.filters_scroll = QScrollArea(); self.filters_scroll.setWidgetResizable(True)
        self.filters_host = QWidget(); self.filters_grid = QGridLayout(self.filters_host)
        self.filters_grid.setContentsMargins(0,0,0,0)
        self.filters_grid.setHorizontalSpacing(12)
        self.filters_grid.setVerticalSpacing(8)
        self.filters_scroll.setWidget(self.filters_host)
        hv.addWidget(self.filters_scroll)

        root.addWidget(header)

        # Tabela
        table_card = QFrame(); table_card.setObjectName("glass")
        apply_shadow(table_card, radius=18, blur=60, color=QColor(0,0,0,80))
        tv = QVBoxLayout(table_card)
        self.tabela = QTableWidget()
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setSortingEnabled(True)
        self.tabela.horizontalHeader().setSortIndicatorShown(True)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tv.addWidget(self.tabela)
        root.addWidget(table_card)

        self.recarregar()

    def _load_df(self):
        path = cfg_get("geral_multas_csv")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Alertas", "Caminho do GERAL_MULTAS.csv não configurado.")
            return pd.DataFrame()

        base = ensure_status_cols(pd.read_csv(path, dtype=str).fillna(""), csv_path=path)

        rows = []
        use_cols = [c for c in DATE_COLS if c in base.columns]  # só DATA INDICAÇÃO / BOLETO / SGU
        for _, r in base.iterrows():
            fluig = str(r.get("FLUIG", "")).strip()
            infr  = str(r.get("INFRATOR", "") or r.get("NOME", "")).strip()
            placa = str(r.get("PLACA", "")).strip()
            orgao = str(r.get("ORGÃO", "") or r.get("ORG", "") or r.get("ORGAO", "")).strip()  # 👈 novo

            for col in use_cols:
                dt = str(r.get(col, "")).strip()
                st = str(r.get(f"{col}_STATUS", "")).strip()
                if dt or st:
                    rows.append([fluig, infr, placa, orgao, col, dt, st])

        return pd.DataFrame(rows, columns=["FLUIG","INFRATOR","PLACA","ORGÃO","ETAPA","DATA","STATUS"])










    def recarregar(self):
        self.df_original = self._load_df()
        self.df_filtrado = self.df_original.copy()
        self._montar_filtros()
        self._fill_table(self.df_filtrado)

    def _montar_filtros(self):
        while self.filters_grid.count():
            it = self.filters_grid.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        self.mode_filtros.clear(); self.multi_filtros.clear()

        cols = list(self.df_original.columns)
        for i, col in enumerate(cols):
            wrap = QFrame(); v = QVBoxLayout(wrap)
            lab = QLabel(col); lab.setObjectName("colTitle"); v.addWidget(lab)
            line = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos","Excluir vazios","Somente vazios"]); mode.currentTextChanged.connect(self._apply_filters)
            ms = CheckableComboBox(self.df_original[col].dropna().astype(str).unique()); ms.changed.connect(self._apply_filters)
            line.addWidget(mode); line.addWidget(ms); v.addLayout(line)
            self.mode_filtros[col] = mode; self.multi_filtros[col] = ms
            self.filters_grid.addWidget(wrap, i//3, i%3)

    def limpar_filtros(self):
        for le in self.global_boxes:
            le.blockSignals(True); le.clear(); le.blockSignals(False)
        for mode in self.mode_filtros.values():
            mode.blockSignals(True); mode.setCurrentIndex(0); mode.blockSignals(False)
        for ms in self.multi_filtros.values():
            vals = [ms.itemText(i) for i in range(ms.count())]
            ms.set_values(vals)
        self._apply_filters()

    def _apply_filters(self):
        df = self.df_original.copy()
        texts = [le.text() for le in self.global_boxes if le.text().strip()]
        df = df_apply_global_texts(df, texts)
        for col in df.columns:
            mode = self.mode_filtros[col].currentText()
            if mode == "Excluir vazios":
                df = df[df[col].astype(str).str.strip() != ""]
            elif mode == "Somente vazios":
                df = df[df[col].astype(str).str.strip() == ""]
            sels = [s for s in self.multi_filtros[col].selected_values() if s]
            if sels:
                df = df[df[col].astype(str).isin(sels)]
        self.df_filtrado = df
        self._fill_table(self.df_filtrado)

        # atualizar listas mantendo seleção
        for col in self.df_filtrado.columns:
            ms = self.multi_filtros[col]
            current_sel = ms.selected_values()
            ms.set_values(self.df_filtrado[col].dropna().astype(str).unique())
            if current_sel:
                for i in range(ms.count()):
                    if ms.itemText(i) in current_sel:
                        idx = ms.model().index(i, 0)
                        ms.model().setData(idx, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
                ms._update_text()

    def _fill_table(self, df):
        headers = list(df.columns)
        self.tabela.clear()
        self.tabela.setColumnCount(len(headers))
        self.tabela.setHorizontalHeaderLabels(headers)
        self.tabela.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            for j, col in enumerate(headers):
                val = "" if pd.isna(r[col]) else str(r[col])
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col.upper() == "STATUS":
                    _paint_status(it, val)
                self.tabela.setItem(i, j, it)
        self.tabela.resizeColumnsToContents()
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.resizeRowsToContents()

    def exportar_excel(self):
        try:
            self.df_filtrado.to_excel("alertas_filtrado.xlsx", index=False)
            QMessageBox.information(self, "Exportado", "alertas_filtrado.xlsx criado.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

# =========================
# Diálogo de dependências
# =========================
>>>>>>> f9b717829de913f73d13717fa914335134ff238d
class DependenciesDialog(QDialog):
    KEYS = [
        ("geral_multas_csv", "GERAL_MULTAS.csv"),
        ("detalhamento_path", "Detalhamento.xlsx"),
        ("pastores_file", "Fase Pastores.xlsx"),
        ("condutor_identificado_path", "Condutor Identificado.xlsx"),
        ("extrato_geral_path", "ExtratoGeral.xlsx"),
        ("extrato_simplificado_path", "ExtratoSimplificado.xlsx"),
    ]
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dependências do Sistema")
        self.resize(720, 420)
        self.setModal(True)
        root = QVBoxLayout(self)
        card = QFrame(); card.setObjectName("card")
        from utils import apply_shadow
        apply_shadow(card, radius=18)
        cv = QVBoxLayout(card); cv.setSpacing(10)
        self.edits = {}
        cfg = cfg_all()
        for key, label in self.KEYS:
            row = QHBoxLayout()
            lab = QLabel(label + ":"); lab.setMinimumWidth(220)
            le = QLineEdit(cfg.get(key, "")); le.setPlaceholderText("Informe o caminho completo…")
            btn = QPushButton("…"); btn.setFixedWidth(36)
            def _pick(_checked=False, le_=le, label_=label):
                path, _ = QFileDialog.getOpenFileName(self, f"Selecionar {label_}", "", "Todos (*.*)")
                if path:
                    le_.setText(path)
            btn.clicked.connect(_pick)
            row.addWidget(lab); row.addWidget(le, 1); row.addWidget(btn)
            cv.addLayout(row)
            self.edits[key] = le
        bar = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_ok = QPushButton("Confirmar")
        bar.addStretch(1); bar.addWidget(btn_cancel); bar.addWidget(btn_ok)
        cv.addLayout(bar)
        root.addWidget(card)
        btn_ok.clicked.connect(self._save_and_accept)
        btn_cancel.clicked.connect(self.reject)
    def _save_and_accept(self):
        for k, le in self.edits.items():
            cfg_set(k, le.text().strip())
        self.accept()

class CondutorTab(QWidget):
    @staticmethod
    def _to_num_brl(s):
        import re
        s = str(s).strip()
        if not s:
            return 0.0
        s = re.sub(r"[^\d,.-]", "", s)
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0
    @staticmethod
    def _dt_parse_any(s):
        s = str(s).strip()
        if not s:
            return pd.NaT
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return pd.to_datetime(s, format=fmt, dayfirst=True, errors="raise")
            except Exception:
                pass
        return pd.to_datetime(s, dayfirst=True, errors="coerce")
    @staticmethod
    def _score(valor):
        v = float(valor or 0)
        if v >= 1000: return 5
        if v >= 500: return 3
        if v >= 200: return 2
        return 1
    def __init__(self):
        super().__init__()
        self._load_data()
        self._build_ui()
        self._apply_filters_all()
    def _load_data(self):
        multas_csv = cfg_get("geral_multas_csv")
        if multas_csv and os.path.exists(multas_csv):
            dm = pd.read_csv(multas_csv, dtype=str).fillna("")
        else:
            dm = pd.DataFrame()
        if not dm.empty:
            if "VALOR" not in dm.columns:
                cand = [c for c in dm.columns if c.upper().strip() in ("VALOR MULTA","VALOR_MULTA","VALOR DA MULTA")]
                dm["VALOR"] = dm[cand[0]] if cand else ""
            dm["VALOR_NUM"] = dm["VALOR"].map(self._to_num_brl)
            if "INFRATOR" in dm.columns:
                dm["MOTORISTA_X"] = dm["INFRATOR"].astype(str)
            elif "NOME" in dm.columns:
                dm["MOTORISTA_X"] = dm["NOME"].astype(str)
            else:
                dm["MOTORISTA_X"] = ""
            for c in ["DATA DA INFRACAO","DATA INFRAÇÃO","DATA","DATA INDICAÇÃO"]:
                if c in dm.columns:
                    dm["DT_M"] = dm[c].map(self._dt_parse_any); break
            if "DT_M" not in dm.columns:
                dm["DT_M"] = pd.NaT
        self.df_multas = dm
        p_geral = cfg_get("extrato_geral_path")
        p_simpl = cfg_get("extrato_simplificado_path")
        def _read_xls(path):
            try:
                return pd.read_excel(path, dtype=str).fillna("") if path and os.path.exists(path) else pd.DataFrame()
            except Exception:
                return pd.DataFrame()
        dg = _read_xls(p_geral)
        ds = _read_xls(p_simpl)
        if not dg.empty:
            m1 = {
                "DATA TRANSACAO":"DATA_TRANSACAO","PLACA":"PLACA","NOME MOTORISTA":"MOTORISTA",
                "TIPO COMBUSTIVEL":"COMBUSTIVEL","LITROS":"LITROS","VL/LITRO":"VL_LITRO",
                "VALOR EMISSAO":"VALOR","NOME ESTABELECIMENTO":"ESTABELECIMENTO","CIDADE":"CIDADE",
                "UF":"UF","CIDADE/UF":"CIDADE_UF","RESPONSAVEL":"RESPONSAVEL",
                "KM RODADOS OU HORAS TRABALHADAS":"KM_RODADOS","KM/LITRO OU LITROS/HORA":"KM_POR_L",
            }
            use1 = {src: dst for src, dst in m1.items() if src in dg.columns}
            dg = dg.rename(columns=use1)
            if "CIDADE_UF" not in dg.columns:
                dg["CIDADE_UF"] = dg.get("CIDADE","").astype(str).str.strip()+"/"+dg.get("UF","").astype(str).str.strip()
            dg["DT_C"] = dg.get("DATA_TRANSACAO","").map(self._dt_parse_any)
            for c_src, c_num in [("LITROS","LITROS_NUM"),("VL_LITRO","VL_LITRO_NUM"),("VALOR","VALOR_NUM"),
                                 ("KM_RODADOS","KM_RODADOS_NUM"),("KM_POR_L","KM_POR_L_NUM")]:
                dg[c_num] = dg.get(c_src, "").map(self._to_num_brl)
        self.df_comb = dg if not dg.empty else pd.DataFrame()
        if not ds.empty:
            m2 = {"Placa":"PLACA","Nome Responsável":"RESPONSAVEL"}
            ds = ds.rename(columns={k:v for k,v in m2.items() if k in ds.columns})
        self.df_simpl = ds if not ds.empty else pd.DataFrame()
        alls = []
        if not self.df_multas.empty: alls += list(self.df_multas["DT_M"].dropna().dt.normalize().unique())
        if not self.df_comb.empty: alls += list(self.df_comb["DT_C"].dropna().dt.normalize().unique())
        self._dates = sorted(set(alls))
        today = pd.Timestamp.today().normalize()
        self._dmin = min(self._dates) if self._dates else today
        self._dmax = max(self._dates) if self._dates else today
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12)
        title = QFrame(); title.setObjectName("glass")
        from utils import apply_shadow
        apply_shadow(title, radius=18, blur=60, color=QColor(0,0,0,60))
        tv = QVBoxLayout(title); tv.setContentsMargins(18,18,18,18)
        h = QLabel("Condutor — Painel Integrado"); h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        tv.addWidget(h)
        root.addWidget(title)
        bar = QFrame(); bar.setObjectName("card"); apply_shadow(bar, radius=18)
        bv = QVBoxLayout(bar); bv.setSpacing(8)
        from utils import GlobalFilterBar
        self.global_bar = GlobalFilterBar("Filtro global:")
        self.global_bar.changed.connect(self._apply_filters_all)
        bv.addWidget(self.global_bar)
        seg = QHBoxLayout()
        self.cb_resp = QComboBox(); self.cb_resp.setEditable(False)
        self.cb_cond = QComboBox(); self.cb_cond.setEditable(False)
        self.cb_placa = QComboBox(); self.cb_placa.setEditable(False)
        for cb, lab in [(self.cb_resp,"Responsável"),(self.cb_cond,"Condutor"),(self.cb_placa,"Placa")]:
            wrap = QFrame(); wv = QVBoxLayout(wrap); wv.setContentsMargins(0,0,0,0)
            wv.addWidget(QLabel(lab)); wv.addWidget(cb)
            seg.addWidget(wrap)
        seg.addStretch(1)
        for cb in (self.cb_resp, self.cb_cond, self.cb_placa):
            cb.currentTextChanged.connect(self._apply_filters_all)
        bv.addLayout(seg)
        self.de_ini = QDateEdit(); self.de_fim = QDateEdit()
        for de in (self.de_ini, self.de_fim):
            de.setCalendarPopup(True); de.setDisplayFormat(DATE_FORMAT)
        self.de_ini.setDate(self._to_qdate(self._dmin)); self.de_fim.setDate(self._to_qdate(self._dmax))
        self.de_ini.dateChanged.connect(self._period_changed); self.de_fim.dateChanged.connect(self._period_changed)
        self.sl_ini = QSlider(Qt.Orientation.Horizontal); self.sl_fim = QSlider(Qt.Orientation.Horizontal)
        n = max(0, len(self._dates)-1)
        for s in (self.sl_ini, self.sl_fim):
            s.setMinimum(0); s.setMaximum(n); s.setTickInterval(1); s.setSingleStep(1); s.setPageStep(1)
        self.sl_ini.setValue(0); self.sl_fim.setValue(n)
        self.sl_ini.valueChanged.connect(self._sliders_changed); self.sl_fim.valueChanged.connect(self._sliders_changed)
        per1 = QHBoxLayout(); per1.addWidget(QLabel("Início:")); per1.addWidget(self.de_ini); per1.addSpacing(10)
        per1.addWidget(QLabel("Fim:")); per1.addWidget(self.de_fim); per1.addStretch(1)
        per2 = QHBoxLayout(); per2.addWidget(self.sl_ini); per2.addSpacing(8); per2.addWidget(self.sl_fim)
        bv.addLayout(per1); bv.addLayout(per2)
        root.addWidget(bar)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        self.tab_over = QWidget(); ov = QVBoxLayout(self.tab_over)
        kcard = QFrame(); kcard.setObjectName("card"); apply_shadow(kcard, radius=18)
        kl = QGridLayout(kcard)
        self.kpi_multas = QLabel(); self.kpi_valor = QLabel(); self.kpi_score = QLabel()
        self.kpi_litros = QLabel(); self.kpi_custo = QLabel()
        for i, (lbl, val) in enumerate([("Qtd Multas", self.kpi_multas), ("Valor Multas (R$)", self.kpi_valor),
                                        ("Pontuação", self.kpi_score), ("Litros", self.kpi_litros),
                                        ("Custo Combustível (R$)", self.kpi_custo)]):
            kl.addWidget(QLabel(lbl), 0, i)
            v = val; v.setFont(QFont("Arial", 12, QFont.Weight.Bold)); kl.addWidget(v, 1, i)
        ov.addWidget(kcard)
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        self.fig1 = Figure(figsize=(4,2.8), tight_layout=True); self.cv1 = FigureCanvas(self.fig1)
        self.fig2 = Figure(figsize=(4,2.8), tight_layout=True); self.cv2 = FigureCanvas(self.fig2)
        ch = QHBoxLayout(); ch.addWidget(self.cv1, 1); ch.addWidget(self.cv2, 1)
        ov.addLayout(ch)
        self.tbl_top_infracoes = QTableWidget(); self._prep(self.tbl_top_infracoes, ["Infração/Órgão","Qtd","Valor (R$)"])
        self.tbl_top_placas = QTableWidget(); self._prep(self.tbl_top_placas, ["Placa","Abastec.","Litros","Valor (R$)"])
        twrap = QHBoxLayout(); twrap.addWidget(self.tbl_top_infracoes, 1); twrap.addWidget(self.tbl_top_placas, 1)
        ov.addLayout(twrap)
        self.tabs.addTab(self.tab_over, "VISÃO GERAL")
        self.tab_m = QWidget(); vm = QVBoxLayout(self.tab_m)
        self.tbl_multas = QTableWidget(); self._prep(self.tbl_multas, ["FLUIG","Condutor","Placa","Órgão","Infração","Valor (R$)","Data","Score"])
        vm.addWidget(self.tbl_multas)
        self.tabs.addTab(self.tab_m, "MULTAS")
        self.tab_c = QWidget(); vc = QVBoxLayout(self.tab_c)
        self.tbl_abast = QTableWidget(); self._prep(self.tbl_abast, ["Data","Placa","Motorista","Combustível","Litros","R$/L","Valor (R$)","Estabelecimento","Cidade/UF"])
        vc.addWidget(self.tbl_abast)
        self.tabs.addTab(self.tab_c, "COMBUSTÍVEL")
    @staticmethod
    def _to_qdate(ts):
        return QDate(int(ts.year), int(ts.month), int(ts.day))
    def _prep(self, tbl, headers):
        tbl.setAlternatingRowColors(True)
        tbl.setSortingEnabled(True)
        tbl.horizontalHeader().setSortIndicatorShown(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
    def _fill(self, tbl, rows):
        tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem(str(v))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents(); tbl.horizontalHeader().setStretchLastSection(True)
        tbl.resizeRowsToContents()
    def _sliders_changed(self):
        if not self._dates:
            self._apply_filters_all(); return
        a = min(self.sl_ini.value(), self.sl_fim.value())
        b = max(self.sl_ini.value(), self.sl_fim.value())
        da = self._dates[a]; db = self._dates[b]
        self.de_ini.blockSignals(True); self.de_fim.blockSignals(True)
        self.de_ini.setDate(self._to_qdate(da)); self.de_fim.setDate(self._to_qdate(db))
        self.de_ini.blockSignals(False); self.de_fim.blockSignals(False)
        self._apply_filters_all()
    def _period_changed(self):
        if not self._dates:
            self._apply_filters_all(); return
        def near_idx(qd):
            ts = pd.Timestamp(qd.year(), qd.month(), qd.day())
            arr = pd.Series(self._dates)
            return int((arr - ts).abs().argmin())
        i0 = near_idx(self.de_ini.date()); i1 = near_idx(self.de_fim.date())
        self.sl_ini.blockSignals(True); self.sl_fim.blockSignals(True)
        self.sl_ini.setValue(min(i0, i1)); self.sl_fim.setValue(max(i0, i1))
        self.sl_ini.blockSignals(False); self.sl_fim.blockSignals(False)
        self._apply_filters_all()
    def _apply_filters_all(self):
        from utils import df_apply_global_texts
        q0, q1 = self.de_ini.date(), self.de_fim.date()
        t0 = pd.Timestamp(q0.year(), q0.month(), q0.day())
        t1 = pd.Timestamp(q1.year(), q1.month(), q1.day())
        a, b = (t0, t1) if t0 <= t1 else (t1, t0)
        dm = self.df_multas.copy()
        if not dm.empty:
            dm = dm[(dm["DT_M"].notna()) & (dm["DT_M"] >= a) & (dm["DT_M"] <= b)]
            texts = self.global_bar.values()
            dm = df_apply_global_texts(dm, texts)
        dc = self.df_comb.copy()
        if not dc.empty:
            dc = dc[(dc["DT_C"].notna()) & (dc["DT_C"] >= a) & (dc["DT_C"] <= b)]
            texts = self.global_bar.values()
            dc = df_apply_global_texts(dc, texts)
        resp = self.cb_resp.currentText().strip()
        cond = self.cb_cond.currentText().strip()
        pla = self.cb_placa.currentText().strip()
        if resp:
            if not dm.empty and ("RESPONSAVEL" in dm.columns): dm = dm[dm["RESPONSAVEL"].astype(str) == resp]
            if not dc.empty and ("RESPONSAVEL" in dc.columns): dc = dc[dc["RESPONSAVEL"].astype(str) == resp]
        if cond:
            if not dm.empty: dm = dm[dm["MOTORISTA_X"].astype(str) == cond]
            if not dc.empty and ("MOTORISTA" in dc.columns): dc = dc[dc["MOTORISTA"].astype(str) == cond]
        if pla:
            if not dm.empty and ("PLACA" in dm.columns): dm = dm[dm["PLACA"].astype(str) == pla]
            if not dc.empty and ("PLACA" in dc.columns): dc = dc[dc["PLACA"].astype(str) == pla]
        self._repopulate_segmented(dm, dc)
        self.dm_f = dm
        self.dc_f = dc
        self._refresh_overview()
        self._refresh_multas_table()
        self._refresh_comb_table()
    def _repopulate_segmented(self, dm, dc):
        resps = set()
        if not dm.empty and "RESPONSAVEL" in dm.columns: resps |= set(dm["RESPONSAVEL"].astype(str).unique())
        if not dc.empty and "RESPONSAVEL" in dc.columns: resps |= set(dc["RESPONSAVEL"].astype(str).unique())
        conds = set()
        if not dm.empty: conds |= set(dm["MOTORISTA_X"].astype(str).unique())
        if not dc.empty and "MOTORISTA" in dc.columns: conds |= set(dc["MOTORISTA"].astype(str).unique())
        placas = set()
        if not dm.empty and "PLACA" in dm.columns: placas |= set(dm["PLACA"].astype(str).unique())
        if not dc.empty and "PLACA" in dc.columns: placas |= set(dc["PLACA"].astype(str).unique())
        def _reset_combo(cb, values):
            cur = cb.currentText().strip()
            cb.blockSignals(True); cb.clear()
            cb.addItem("")
            for v in sorted([x for x in values if str(x).strip()]):
                cb.addItem(str(v))
            if cur and cur in [cb.itemText(i) for i in range(cb.count())]:
                cb.setCurrentText(cur)
            cb.blockSignals(False)
        _reset_combo(self.cb_resp, resps)
        _reset_combo(self.cb_cond, conds)
        _reset_combo(self.cb_placa, placas)
    def _refresh_overview(self):
        qtd_multas = len(self.dm_f) if not self.dm_f.empty else 0
        val_multas = self.dm_f["VALOR_NUM"].sum() if not self.dm_f.empty else 0.0
        score = int(self.dm_f["VALOR_NUM"].map(self._score).sum()) if not self.dm_f.empty else 0
        litros = self.dc_f["LITROS_NUM"].sum() if not self.dc_f.empty else 0.0
        custo = self.dc_f["VALOR_NUM"].sum() if not self.dc_f.empty else 0.0
        self.kpi_multas.setText(str(qtd_multas))
        self.kpi_valor.setText(f"{val_multas:.2f}")
        self.kpi_score.setText(str(score))
        self.kpi_litros.setText(f"{litros:.2f}")
        self.kpi_custo.setText(f"{custo:.2f}")
        from collections import Counter
        from matplotlib.patches import Circle
        ax1 = self.fig1.clear().add_subplot(111)
        if not self.dm_f.empty:
            org = None
            for c in ("ÓRGÃO","ORGÃO","ORGAO","ORG"):
                if c in self.dm_f.columns: org = c; break
            if org is None: org = "PLACA" if "PLACA" in self.dm_f.columns else None
            labels, values = [], []
            if org:
                cc = Counter(self.dm_f[org].astype(str))
                for k, v in cc.most_common(6):
                    labels.append(k); values.append(v)
            ax1.pie(values or [1], labels=labels or ["Sem dados"], autopct=lambda p: f"{p:.0f}%")
            circ = Circle((0,0), 0.55, facecolor="white"); ax1.add_artist(circ)
            ax1.set_title("Multas por Órgão (top 6)")
        self.cv1.draw()
        ax2 = self.fig2.clear().add_subplot(111)
        if not self.dc_f.empty and "COMBUSTIVEL" in self.dc_f.columns:
            cc = Counter(self.dc_f["COMBUSTIVEL"].astype(str))
            labels, values = zip(*cc.most_common(6)) if cc else (["Sem dados"], [1])
            ax2.pie(values, labels=labels, autopct=lambda p: f"{p:.0f}%")
            circ = Circle((0,0), 0.55, facecolor="white"); ax2.add_artist(circ)
            ax2.set_title("Tipo de Combustível (top 6)")
        self.cv2.draw()
        rows_inf = []
        if not self.dm_f.empty:
            infc = None
            for c in ("TIPO INFRACAO","TIPO INFRAÇÃO","INFRACAO","INFRAÇÃO","NOTIFICACAO","NOTIFICAÇÃO","ÓRGÃO","ORGÃO","ORGAO"):
                if c in self.dm_f.columns: infc = c; break
            g = self.dm_f.groupby(infc if infc else "PLACA", dropna=False).agg(QT=("FLUIG","count"), VAL=("VALOR_NUM","sum")).reset_index().sort_values(["VAL","QT"], ascending=False).head(12)
            rows_inf = [[r[infc] if infc else r["PLACA"], int(r["QT"]), f"{r['VAL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_top_infracoes, rows_inf)
        rows_pl = []
        if not self.dc_f.empty:
            g2 = self.dc_f.groupby("PLACA", dropna=False).agg(QT=("PLACA","count"), LT=("LITROS_NUM","sum"), VL=("VALOR_NUM","sum")).reset_index().sort_values(["VL","LT","QT"], ascending=False).head(12)
            rows_pl = [[r["PLACA"], int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g2.iterrows()]
        self._fill(self.tbl_top_placas, rows_pl)
    def _refresh_multas_table(self):
        d = self.dm_f.copy()
        if d.empty:
            self._fill(self.tbl_multas, []); return
        org = None
        for c in ("ÓRGÃO","ORGÃO","ORGAO","ORG"):
            if c in d.columns: org = c; break
        inf = None
        for c in ("TIPO INFRACAO","TIPO INFRAÇÃO","INFRACAO","INFRAÇÃO","NOTIFICACAO","NOTIFICAÇÃO"):
            if c in d.columns: inf = c; break
        dtc = "DT_M"
        rows = []
        for _, r in d.sort_values("VALOR_NUM", ascending=False).iterrows():
            rows.append([
                r.get("FLUIG",""),
                r.get("MOTORISTA_X",""),
                r.get("PLACA",""),
                r.get(org,"") if org else "",
                r.get(inf,"") if inf else "",
                f"{float(r.get('VALOR_NUM',0)):.2f}",
                r[dtc].strftime("%d/%m/%Y") if pd.notna(r.get(dtc)) else "",
                self._score(r.get("VALOR_NUM",0))
            ])
        self._fill(self.tbl_multas, rows)
    def _refresh_comb_table(self):
        d = self.dc_f.copy()
        if d.empty:
            self._fill(self.tbl_abast, []); return
        rows = []
        for _, r in d.sort_values("DT_C").iterrows():
            rows.append([
                r["DT_C"].strftime("%d/%m/%Y %H:%M") if pd.notna(r["DT_C"]) else "",
                r.get("PLACA",""),
                r.get("MOTORISTA",""),
                r.get("COMBUSTIVEL",""),
                f"{float(r.get('LITROS_NUM',0)):.2f}",
                f"{float(r.get('VL_LITRO_NUM',0)):.2f}",
                f"{float(r.get('VALOR_NUM',0)):.2f}",
                r.get("ESTABELECIMENTO",""),
                r.get("CIDADE_UF",""),
            ])
        self._fill(self.tbl_abast, rows)

class MainWindow(QMainWindow):
    def __init__(self, user_email: str | None = None):
        super().__init__()
        self.setWindowTitle("GESTÃO DE FROTAS")
        self.resize(1280, 860)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)
        home = QWidget()
        hv = QVBoxLayout(home)
        hv.setContentsMargins(18, 18, 18, 18)
        title_card = QFrame(); title_card.setObjectName("glass")
        from utils import apply_shadow
        apply_shadow(title_card, radius=20, blur=60, color=QColor(0, 0, 0, 60))
        tv = QVBoxLayout(title_card); tv.setContentsMargins(24, 24, 24, 24)
        t = QLabel("Gestão de Frotas")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        tv.addWidget(t)
        if user_email:
            lab_user = QLabel(f"Logado como: {user_email}")
            lab_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tv.addWidget(lab_user)
        hv.addWidget(title_card)
        grid_card = QFrame(); grid_card.setObjectName("card"); apply_shadow(grid_card, radius=18)
        gv = QGridLayout(grid_card); gv.setContentsMargins(18, 18, 18, 18); gv.setHorizontalSpacing(12); gv.setVerticalSpacing(12)
        buttons = [
            ("Base", self.open_base),
            ("Infrações e Multas", self.open_multas),
            ("Combustível", self.open_combustivel),
            ("Relatórios", self.open_relatorios),
            ("Alertas", self.open_alertas),
            ("Condutor", self.open_condutor),
        ]
        for i, (label, slot) in enumerate(buttons):
            b = QPushButton(label)
            b.setMinimumHeight(56)
            b.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            b.clicked.connect(slot)
            gv.addWidget(b, i // 2, i % 2)
        hv.addWidget(grid_card)
        bar = QHBoxLayout()
        btn_out = QPushButton("Sair"); btn_out.setObjectName("danger")
        btn_out.setMinimumHeight(44)
        btn_out.clicked.connect(self.close)
        bar.addStretch(1); bar.addWidget(btn_out)
        hv.addLayout(bar)
        self.tab_widget.addTab(home, "Início")
        self.add_or_focus("Base", self._factory_base)
    def add_or_focus(self, title: str, factory):
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx).strip().lower() == str(title).strip().lower():
                self.tab_widget.setCurrentIndex(idx)
                return
        w = factory()
        self.tab_widget.addTab(w, title)
        self.tab_widget.setCurrentWidget(w)
    def close_tab(self, index: int):
        if index == 0:
            return
        w = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        w.deleteLater()
    def _factory_base(self):
        return BaseTab()
    def _factory_multas(self):
        from multas import MultasView as InfraMultasWindow
        return InfraMultasWindow()
    def _factory_combustivel(self):
        from combustivel import CombustivelView
        return CombustivelView()
    def _factory_relatorios(self):
        from relatorios import RelatoriosView
        return RelatoriosView()
    def _factory_alertas(self):
        from utils import AlertasDialog, ensure_datetime
        import pandas as pd, os
        w = QWidget()
        v = QVBoxLayout(w)
        btn = QPushButton("Abrir Alertas de Datas")
        v.addWidget(btn)
        v.addStretch(1)
        def _open():
            path = cfg_get("geral_multas_csv")
            df = pd.read_csv(path, dtype=str).fillna("") if path and os.path.exists(path) else pd.DataFrame()
            rows = []
            if not df.empty:
                cols_date = ["DATA INDICAÇÃO","BOLETO","SGU","VALIDACAO NFF","CONCLUSAO"]
                status_cols = [c for c in df.columns if str(c).upper().endswith("_STATUS")]
                pref = ["CONCLUSAO_STATUS","BOLETO_STATUS","DATA INDICAÇÃO_STATUS","VALIDACAO NFF_STATUS","LANÇAMENTO NFF_STATUS","SGU_STATUS"]
                for col in cols_date:
                    if col in df.columns:
                        dd = ensure_datetime(df[col])
                        for i, r in df.iterrows():
                            d = dd.iat[i]
                            if pd.notna(d):
                                st = ""
                                for c in pref:
                                    if c in df.columns and str(r.get(c,"")).strip():
                                        st = str(r.get(c,"")).strip(); break
                                if not st and status_cols:
                                    for c in status_cols:
                                        if str(r.get(c,"")).strip():
                                            st = str(r.get(c,"")).strip(); break
                                rows.append([
                                    str(r.get("FLUIG","")),
                                    str(r.get("INFRATOR","")),
                                    str(r.get("PLACA","")),
                                    str(r.get("ORGÃO","")),
                                    col,
                                    d.strftime("%d/%m/%Y"),
                                    st
                                ])
            dlg = AlertasDialog(self, rows)
            dlg.exec()
        btn.clicked.connect(_open)
        return w
    def _factory_condutor(self):
        from condutor import CondutorWindow
        return CondutorWindow()
    def open_base(self):
        self.add_or_focus("Base", self._factory_base)
    def open_multas(self):
        self.add_or_focus("Infrações e Multas", self._factory_multas)
    def open_combustivel(self):
        self.add_or_focus("Combustível — Detalhada", self._factory_combustivel)
    def open_relatorios(self):
        self.add_or_focus("Relatórios", self._factory_relatorios)
    def open_alertas(self):
        self.add_or_focus("Alertas", self._factory_alertas)
    def open_condutor(self):
        self.add_or_focus("Condutor", self._factory_condutor)

def run():
    app = QApplication([])
    app.setStyleSheet(STYLE)
    auth = AuthService()
    dlg = LoginView(auth)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    deps = DependenciesDialog()
    if deps.exec() != QDialog.DialogCode.Accepted:
        return
    email = getattr(auth, "current_user", None)
    win = MainWindow(email)
    win.show()
    app.exec()

if __name__ == "__main__":
    run()