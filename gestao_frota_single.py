import os, json, base64, re
from pathlib import Path
import pandas as pd



import os, json
from pathlib import Path
from PyQt6.QtGui import QColor


USERS_FILE = "users.csv"

BASE_DIR = os.path.expanduser("~")
APP_DIR  = os.path.join(BASE_DIR, "Documentos", "GestaoFrotas")

MULTAS_ROOT      = os.path.join(APP_DIR, "Multas")
GERAL_MULTAS_CSV = os.path.join(MULTAS_ROOT, "geral_multas.csv")
PASTORES_DIR     = os.path.join(APP_DIR, "Pastores")


DATE_FORMAT = "dd/MM/yyyy"                         # padrão do Qt
DATE_COLS   = ["DATA INDICAÇÃO", "BOLETO", "SGU"]  # 3 colunas oficiais

PORTUGUESE_MONTHS = {
    1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho",
    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro",
}

STATUS_OPS = ["", "Pendente", "Pago", "Vencido"]
STATUS_COLOR = {
    "Pago": QColor("#2ecc71"),
    "Pendente": QColor("#ffd166"),
    "Vencido": QColor("#ef5350"),
    "": QColor("#BDBDBD"),
}

# Órgãos (faltava e gerava erro em multas.py)
ORGAOS = ["DETRAN","DEMUTRAM","STTU","DNIT","PRF","SEMUTRAM","DMUT"]

# Módulos para a guia Início (se você usa um launcher em abas)
MODULES = ["Início","Base","Alertas","Infrações e Multas","Relatórios","Combustível"]

# ---- Persistência (antigo config.py) ----
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
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except:
        pass
    return {}

def _cfg_save(data: dict) -> None:
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def cfg_get(key: str, default: str = "") -> str:
    data = _cfg_load()
    if key in data and str(data[key]).strip():
        return data[key]
    return DEFAULTS.get(key, default)

def cfg_set(key: str, value: str) -> None:
    data = _cfg_load()
    data[key] = value
    _cfg_save(data)

def cfg_all() -> dict:
    data = _cfg_load()
    out = DEFAULTS.copy()
    out.update(data)
    return out

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QPushButton, QFrame, QFileDialog, QWidget, QMainWindow, QTabWidget, QMessageBox,
    QGridLayout, QScrollArea, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
)


import os, json
from pathlib import Path
from PyQt6.QtGui import QColor


USERS_FILE = "users.csv"

BASE_DIR = os.path.expanduser("~")
APP_DIR  = os.path.join(BASE_DIR, "Documentos", "GestaoFrotas")

MULTAS_ROOT      = os.path.join(APP_DIR, "Multas")
GERAL_MULTAS_CSV = os.path.join(MULTAS_ROOT, "geral_multas.csv")
PASTORES_DIR     = os.path.join(APP_DIR, "Pastores")

# -------- Datas (padrão pt-BR) --------
DATE_FORMAT = "dd/MM/yyyy"              # Qt display format
DATE_COLS   = ["DATA INDICAÇÃO", "BOLETO", "SGU"]  # 3 colunas oficiais

PORTUGUESE_MONTHS = {
    1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho",
    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro",
}

STATUS_OPS = ["", "Pendente", "Pago", "Vencido"]
STATUS_COLOR = {
    "Pago": QColor("#2ecc71"),
    "Pendente": QColor("#ffd166"),
    "Vencido": QColor("#ef5350"),
    "": QColor("#BDBDBD"),
}

MODULES = [
    "Início",
    "Base",
    "Alertas",
    "Infrações e Multas",
    "Relatórios",
    "Combustível",
]

# -------- Persistência de configuração (antigo config.py) --------
CFG_PATH = str(Path(__file__).resolve().parent / "base.json")
DEFAULTS = {
    "geral_multas_csv": GERAL_MULTAS_CSV,
    "multas_root": MULTAS_ROOT,
    "detalhamento_path": os.path.join(APP_DIR, "CPO-VEÍCULOS", "Notificações de Multas - Detalhamento.xlsx"),
    "pastores_file": os.path.join(APP_DIR, "CPO-VEÍCULOS", "Notificações de Multas - Fase Pastores.xlsx"),
    "condutor_identificado_path": os.path.join(APP_DIR, "CPO-VEÍCULOS", "Notificações de Multas - Condutor Identificado.xlsx"),
    "pastores_dir": PASTORES_DIR,
    "users_file": USERS_FILE,
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
    # garante defaults
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
    return data.get(key, default if default is not None else DEFAULTS.get(key))

def cfg_set(key: str, value):
    data = _cfg_load()
    data[key] = value
    _cfg_save(data)

def cfg_all() -> dict:
    return _cfg_load()


USERS_FILE = "users.csv"

BASE_DIR = os.path.expanduser("~")
APP_DIR  = os.path.join(BASE_DIR, "Documentos", "GestaoFrotas")

MULTAS_ROOT      = os.path.join(APP_DIR, "Multas")
GERAL_MULTAS_CSV = os.path.join(MULTAS_ROOT, "geral_multas.csv")

PASTORES_DIR = os.path.join(APP_DIR, "Pastores")

DATE_FORMAT = "dd/MM/yyyy"

# Somente estas 3 datas são oficiais
DATE_COLS = ["DATA INDICAÇÃO", "BOLETO", "SGU"]  # <- atende seu pedido

PORTUGUESE_MONTHS = {
    1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
    7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro",
}


STATUS_OPS = ["", "Pendente", "Pago", "Vencido"]

STATUS_COLOR = {
    "Pago": QColor("#2ecc71"),
    "Pendente": QColor("#ffd166"),
    "Vencido": QColor("#ef5350"),
    "": QColor("#BDBDBD"),
}

MODULES = [
    "Base",
    "Alertas",
    # você pode adicionar outras guias depois (Multas, Relatórios, Combustível)
]

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

BASE_JSON = str(Path(__file__).resolve().parent / "base.json")

DEFAULTS = {
    "geral_multas_csv": GERAL_MULTAS_CSV,
    "multas_root": MULTAS_ROOT,
    "pastores_dir": PASTORES_DIR,
    "detalhamento_path": "",
    "pastores_file": "",
    "condutor_identificado_path": "",
    "extrato_geral_path": "",
    "extrato_simplificado_path": "",
    "users_file": USERS_FILE,
    "remember_user": "",
    "remember_pwd": "",
    "remember_flag": "0",
}

def _load_cfg():
    if os.path.exists(BASE_JSON):
        try:
            with open(BASE_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except:
            pass
    return {}

def _save_cfg(data):
    try:
        with open(BASE_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def cfg_get(key):
    data = _load_cfg()
    if key in data and str(data[key]).strip():
        return data[key]
    return DEFAULTS.get(key, "")

def cfg_set(key, value):
    data = _load_cfg()
    data[key] = value
    _save_cfg(data)

def cfg_all():
    data = _load_cfg()
    out = DEFAULTS.copy()
    out.update(data)
    return out

from PyQt6.QtWidgets import QGraphicsDropShadowEffect

def apply_shadow(widget, radius=18, blur=40, color=QColor(0, 0, 0, 80)):
    eff = QGraphicsDropShadowEffect()
    eff.setOffset(0, 8)
    eff.setBlurRadius(blur)
    eff.setColor(color)
    widget.setGraphicsEffect(eff)

def _paint_status(item: QTableWidgetItem, status: str):
    st = (status or "").strip()
    if st in STATUS_COLOR:
        bg = STATUS_COLOR[st]
        item.setBackground(bg)
        # contraste do texto
        yiq = (bg.red()*299 + bg.green()*587 + bg.blue()*114)/1000
        item.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))

def ensure_status_cols(df: pd.DataFrame, csv_path: str | None = None) -> pd.DataFrame:
    """
    Garante colunas *_STATUS para cada data oficial em DATE_COLS.
    Se csv_path for fornecido, persiste de volta (sem perder colunas).
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["FLUIG"] + DATE_COLS + [f"{c}_STATUS" for c in DATE_COLS])
    df = df.copy()
    for c in DATE_COLS:
        st = f"{c}_STATUS"
        if c not in df.columns:
            df[c] = ""
        if st not in df.columns:
            df[st] = ""
    if csv_path:
        try:
            df.to_csv(csv_path, index=False)
        except:
            pass
    return df

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
    except:
        pass
    return QDate()

def df_apply_global_texts(df: pd.DataFrame, texts: list[str]) -> pd.DataFrame:
    """
    Aplica filtro 'contém' em TODAS as colunas (case-insensitive).
    Cada caixa tem seus tokens (separados por espaço) combinados com AND,
    e a verificação é OR entre colunas.
    """
    if df is None or df.empty:
        return df
    s_df = df.fillna("").astype(str).apply(lambda col: col.str.lower())
    mask_total = pd.Series(True, index=df.index)
    for text in texts:
        q = (text or "").strip().lower()
        if not q:
            continue
        tokens = [t for t in re.split(r"\s+", q) if t]
        if not tokens:
            continue
        mask_box = pd.Series(True, index=df.index)
        for tok in tokens:
            m_tok = pd.Series(False, index=df.index)
            pat = re.escape(tok)
            for c in s_df.columns:
                m_tok |= s_df[c].str.contains(pat, na=False)
            mask_box &= m_tok
        mask_total &= mask_box
    return df[mask_total].copy()

def _enc(txt: str) -> str:
    return base64.b64encode((txt or "").encode("utf-8")).decode("ascii")

def _dec(txt: str) -> str:
    try:
        return base64.b64decode((txt or "").encode("ascii")).decode("utf-8")
    except Exception:
        return ""

class AuthService:
    """
    Versão simples: se tem usuário/senha, entra. Integra com o remember em base.json.
    """
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

        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=18)
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

        # eventos
        btn_login.clicked.connect(self.do_login)
        btn_cancel.clicked.connect(self.reject)
        self.ed_pass.returnPressed.connect(self.do_login)

        # pré-preenchimento lembrado (base.json)
        remembered_user = cfg_get("remember_user") or ""
        remembered_pwd  = _dec(cfg_get("remember_pwd") or "")
        remembered_flag = cfg_get("remember_flag") == "1"
        self.ed_user.setText(remembered_user)
        self.ed_pass.setText(remembered_pwd)
        self.ck_rem.setChecked(remembered_flag)

    def do_login(self):
        ok, msg = self.auth.login(self.ed_user.text(), self.ed_pass.text())
        if not ok:
            QMessageBox.warning(self, "Login", msg); return
        # persistir lembrar
        if self.ck_rem.isChecked():
            cfg_set("remember_user", self.ed_user.text().strip())
            cfg_set("remember_pwd",  _enc(self.ed_pass.text()))
            cfg_set("remember_flag", "1")
        else:
            cfg_set("remember_user", "")
            cfg_set("remember_pwd",  "")
            cfg_set("remember_flag", "0")
        self.accept()

# =========================================================
# =================== BASE (paths/cfg) ====================
# =========================================================
class _PathRow(QWidget):
    def __init__(self, label, key, mode="file"):
        super().__init__()
        self.key = key
        self.mode = mode
        h = QHBoxLayout(self)
        self.lab = QLabel(label)
        self.ed = QLineEdit(cfg_get(key))
        self.btn = QPushButton("..."); self.btn.setFixedWidth(36)

        # Correção: clicked envia bool; assinamos o parâmetro e ignoramos
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
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=18)
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

# =========================================================
# ===================== ALERTAS (tab) =====================
# =========================================================
class CheckableComboBox(QComboBox):
    """
    Combo multi-seleção com checkboxes embutidos.
    """
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
    """
    Tabela bem organizada, seguindo o padrão:
    - 1 (ou mais) campo(s) de texto global(is) com botão +
    - Por coluna: modo (Todos/Excluir vazios/Somente vazios) + multiseleção
    - Datas oficiais: DATA INDICAÇÃO, BOLETO, SGU
    - Cores de STATUS
    """
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
        self.filters_grid.setContentsMargins(0,0,0,0); self.filters_grid.setHorizontalSpacing(12); self.filters_grid.setVerticalSpacing(8)
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
        use_cols = [c for c in DATE_COLS if c in base.columns]  # DATA INDICAÇÃO / BOLETO / SGU
        for _, r in base.iterrows():
            fluig = str(r.get("FLUIG", "")).strip()
            infr  = str(r.get("INFRATOR", "") or r.get("NOME", "")).strip()
            placa = str(r.get("PLACA", "")).strip()
            for col in use_cols:
                dt = str(r.get(col, "")).strip()
                st = str(r.get(f"{col}_STATUS", "")).strip()
                if dt or st:
                    rows.append([fluig, infr, placa, col, dt, st])
        return pd.DataFrame(rows, columns=["FLUIG","INFRATOR","PLACA","ETAPA","DATA","STATUS"])

    def recarregar(self):
        self.df_original = self._load_df()
        self.df_filtrado = self.df_original.copy()
        self._montar_filtros()
        self._fill_table(self.df_filtrado)

    def _montar_filtros(self):
        while self.filters_grid.count():
            it = self.filters_grid.takeAt(0)
            if it.widget(): it.widget().setParent(None)
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

# =========================================================
# ===================== MAIN WINDOW =======================
# =========================================================
class DependenciesDialog(QDialog):
    """
    Pede/valida os caminhos antes de abrir o sistema.
    (Corrigido: clicked envia bool; assinamos e ignoramos. Implementado _save_and_accept)
    """
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
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=18)
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



# --- gestao_frota_single.py (adicione/substitua esta classe inteira) ---
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox
)

# Imports internos do seu projeto
from gestao_frota_single import cfg_get, MODULES  # já existem neste arquivo
from utils import apply_shadow  # sombra padrão do seu tema
from relatorios import RelatorioWindow
from multas import InfraMultasWindow
from combustivel import CombustivelWindow

# Tentamos obter a AlertsTab onde ela estiver (normalmente em main_window.py)
try:
    from main_window import AlertsTab
except Exception:
    try:
        from .main_window import AlertsTab
    except Exception:
        AlertsTab = None  # se não existir, mostramos aviso ao clicar

class MainWindow(QMainWindow):
    """
    Janela principal em abas:
      - Aba 'Início' com botões grandes
      - Cada módulo abre em uma nova aba (sem duplicar)
    Botões: Base, Infrações e Multas, Combustível, Relatórios, Alertas
    """
    def __init__(self, user_email: str | None = None):
        super().__init__()
        self.setWindowTitle("GESTÃO DE FROTAS")
        self.resize(1280, 860)

        # Abas
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # ==== ABA INÍCIO ====
        home = QWidget()
        hv = QVBoxLayout(home)

        # Cabeçalho
        title_card = QFrame(); title_card.setObjectName("glass")
        apply_shadow(title_card, radius=20, blur=60, color=QColor(0, 0, 0, 60))
        tv = QVBoxLayout(title_card); tv.setContentsMargins(24, 24, 24, 24)

        t = QLabel("Gestão de Frota")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        tv.addWidget(t)

        if user_email:
            tv.addWidget(QLabel(f"Logado como: {user_email}"),
                         alignment=Qt.AlignmentFlag.AlignCenter)
        hv.addWidget(title_card)

        # Cartão com botões
        grid_card = QFrame(); grid_card.setObjectName("card"); apply_shadow(grid_card, radius=18)
        gv = QGridLayout(grid_card); gv.setContentsMargins(18, 18, 18, 18)

        buttons = [
            ("Base", self.open_base),
            ("Infrações e Multas", self.open_multas),
            ("Combustível", self.open_combustivel),
            ("Relatórios", self.open_relatorios),
            ("Alertas", self.open_alertas),
        ]

        for i, (label, slot) in enumerate(buttons):
            b = QPushButton(label)
            b.setMinimumHeight(64)
            b.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            b.clicked.connect(slot)
            gv.addWidget(b, i // 2, i % 2)

        hv.addWidget(grid_card)

        # Barra inferior
        bar = QHBoxLayout()
        out = QPushButton("Sair"); out.setObjectName("danger")
        out.setMinimumHeight(44)
        out.clicked.connect(self.close)
        bar.addStretch(1); bar.addWidget(out)
        hv.addLayout(bar)

        # Coloca a Home
        self.tab_widget.addTab(home, "Início")

    # ===== Helpers =====
    def add_or_focus(self, title, factory):
        """Se a aba já existe, foca; senão cria."""
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx).strip().lower() == str(title).strip().lower():
                self.tab_widget.setCurrentIndex(idx)
                return
        w = factory()
        self.tab_widget.addTab(w, title)
        self.tab_widget.setCurrentWidget(w)

    def close_tab(self, index: int):
        """Não permite fechar a Home (índice 0)."""
        if index == 0:
            return
        w = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        w.deleteLater()

    # ===== Ações dos botões =====
    def open_base(self):
        try:
            # BaseTab já existe no mesmo arquivo (gestao_frota_single)
            from gestao_frota_single import BaseTab
            self.add_or_focus("Base", lambda: BaseTab())
        except Exception as e:
            QMessageBox.warning(self, "Base", f"Não foi possível abrir a Base.\n{e}")

    def open_multas(self):
        # Janela de Infrações/Multas já pronta
        self.add_or_focus("Infrações e Multas", lambda: InfraMultasWindow())

    def open_combustivel(self):
        # Usa seus paths configuráveis (aplique sua correção de cfg_get no módulo)
        try:
            self.add_or_focus("Combustível", lambda: CombustivelWindow())
        except Exception as e:
            QMessageBox.warning(self, "Combustível", str(e))

    def open_relatorios(self):
        # Pede um arquivo e abre o Relatório
        p, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", "", "Planilhas (*.xlsx *.xls *.csv)")
        if not p:
            return
        self.add_or_focus("Relatórios", lambda: RelatorioWindow(p))

    def open_alertas(self):
        # Aba Alertas mostrando as 3 datas oficiais + *_STATUS
        if AlertsTab is None:
            QMessageBox.warning(self, "Alertas", "Classe AlertsTab não encontrada.")
            return
        self.add_or_focus("Alertas", lambda: AlertsTab())



def run():
    app = QApplication([])
    app.setStyleSheet(STYLE)

    # 1) Login
    auth = AuthService()
    dlg = LoginView(auth)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    # 2) Dependências antes de abrir
    deps = DependenciesDialog()
    if deps.exec() != QDialog.DialogCode.Accepted:
        return

    # 3) Main em guias
    email = getattr(auth, "current_user", None)
    win = MainWindow(email)
    win.show()
    app.exec()

if __name__ == "__main__":
    run()
