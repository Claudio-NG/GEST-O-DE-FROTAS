import os
import re
import io
import ast
import math
import json
import time
import queue
import shutil
import unicodedata
import threading
import datetime as dt
from glob import glob
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===============================
# TEMA / CORES (HEX) DO SISTEMA
# ===============================

THEME = {
    "primary": "#0B1E3B",
    "accent": "#D72638",
    "background": "#F7F9FC",
    "surface": "#FFFFFF",
    "text": "#101828",
    "muted": "#6B7280",
}

STATUS_COLORS_HEX = {
    "ABERTA": "#F59E0B",
    "VENCIDA": "#EF4444",
    "PAGA": "#10B981",
    "CANCELADA": "#6B7280",
    "EM ANALISE": "#3B82F6",
    "EM ANÁLISE": "#3B82F6",
    "EM RECURSO": "#9333EA",
}

PERIOD_LABELS = {
    "MES_ATUAL": "Mês atual",
    "ULTIMOS_3_MESES": "Últimos 3 meses",
    "ANO_ATUAL": "Ano atual",
    "PERSONALIZADO": "Personalizado",
}

# =========================================================
# IMPORTAÇÕES DE CONSTANTES DO PROJETO (com defaults seguros)
# =========================================================
try:
    from gestao_frota_single import (
        DATE_COLS,
        STATUS_COLOR,          # dict[str, QColor]
        GERAL_MULTAS_CSV,
        MULTAS_ROOT,
        PASTORES_DIR,
        cfg_get,
        cfg_set,
    )
except Exception:
    DATE_COLS = []
    GERAL_MULTAS_CSV = str(Path("data/geral_multas.csv"))
    MULTAS_ROOT = str(Path("data/MULTAS"))
    PASTORES_DIR = str(Path("data/PASTORES"))

    def cfg_get(*args, **kwargs):  # fallback
        return None

    def cfg_set(*args, **kwargs):  # fallback
        return None

    # STATUS_COLOR (QColor) será criado mais abaixo se PyQt estiver disponível

# ======================
# NORMALIZAÇÕES DE TEXTO
# ======================

def _to_str(x: Any) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return str(x)

def normalize_text(s: Any) -> str:
    s = _to_str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_status(s: Any) -> str:
    t = normalize_text(s).upper()
    if not t:
        return ""
    aliases = {
        "ABERTO": "ABERTA",
        "ABERTAS": "ABERTA",
        "VENCIDO": "VENCIDA",
        "VENCIDAS": "VENCIDA",
        "PAGAS": "PAGA",
        "CANCELADO": "CANCELADA",
        "CANCELADOS": "CANCELADA",
        "EM ANALISE": "EM ANALISE",
        "EM ANÁLISE": "EM ANALISE",
        "RECURSO": "EM RECURSO",
        "RECORRIDA": "EM RECURSO",
    }
    return aliases.get(t, t)

def get_status_hex(status: Any) -> str:
    s = normalize_status(status)
    return STATUS_COLORS_HEX.get(s, "#9E9E9E")

def normalize_columns_upper(df: pd.DataFrame) -> pd.DataFrame:
    cols = [normalize_text(c).upper() for c in df.columns]
    out = df.copy()
    out.columns = cols
    return out

def ensure_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)

# ===========
# PERÍODOS
# ===========

def _today() -> dt.date:
    return dt.date.today()

def period_presets(today: Optional[dt.date] = None) -> Dict[str, Tuple[dt.date, dt.date]]:
    d = today or _today()
    first_month = d.replace(day=1)
    next_month = (first_month + dt.timedelta(days=32)).replace(day=1)
    mes_atual = (first_month, next_month - dt.timedelta(days=1))

    start_3 = (first_month - dt.timedelta(days=92)).replace(day=1)
    ult_3 = (start_3, d)

    ano_inicio = d.replace(month=1, day=1)
    ano_atual = (ano_inicio, d)

    return {
        "MES_ATUAL": mes_atual,
        "ULTIMOS_3_MESES": ult_3,
        "ANO_ATUAL": ano_atual,
        "PERSONALIZADO": (None, None),
    }

# ==================
# CACHE DE DATAFRAME
# ==================

class DataCache:
    def __init__(self):
        self._lock = threading.RLock()
        self._store: Dict[str, Tuple[float, pd.DataFrame]] = {}

    def _key(self, path: str, sheet_name: Optional[str]) -> str:
        return f"{Path(path).resolve()}::{sheet_name or ''}"

    def load_df_cached(
        self,
        path: str,
        sheet_name: Optional[str] = None,
        dtype: Optional[Dict[str, Any]] = None,
        parse_dates: Optional[List[str]] = None,
        keep_default_na: bool = True,
        normalize_cols: bool = False,
    ) -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        mtime = p.stat().st_mtime
        key = self._key(path, sheet_name)

        with self._lock:
            if key in self._store:
                cached_mtime, cached_df = self._store[key]
                if abs(cached_mtime - mtime) < 1e-6:
                    return cached_df.copy()

        ext = p.suffix.lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(p, sheet_name=sheet_name, dtype=dtype, engine="openpyxl")
        elif ext in (".csv",):
            df = pd.read_csv(p, dtype=dtype, keep_default_na=keep_default_na)
        else:
            raise ValueError(f"Extensão não suportada: {ext}")

        if parse_dates:
            for col in parse_dates:
                if col in df.columns:
                    df[col] = ensure_datetime(df[col])

        if normalize_cols:
            df = normalize_columns_upper(df)

        with self._lock:
            self._store[key] = (mtime, df.copy())

        return df.copy()

DATA_CACHE = DataCache()

def load_df(path: str, **kwargs) -> pd.DataFrame:
    return DATA_CACHE.load_df_cached(path, **kwargs)

# ==============
# EXECUTOR (IO)
# ==============

def run_tasks(
    tasks: Dict[str, Callable[[], Any]],
    max_workers: int = 8,
    on_result: Optional[Callable[[str, Any], None]] = None,
    on_error: Optional[Callable[[str, BaseException], None]] = None,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    if not tasks:
        return results
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="GF-IO") as ex:
        fut_map = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(fut_map):
            name = fut_map[fut]
            try:
                res = fut.result()
                results[name] = res
                if on_result:
                    on_result(name, res)
            except BaseException as e:
                if on_error:
                    on_error(name, e)
                else:
                    results[name] = e
    return results

# =========
# EVENT BUS
# =========

class EventBus:
    def __init__(self):
        self._sub: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()
        self._q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._started = False

    def _loop(self):
        while True:
            topic, data = self._q.get()
            with self._lock:
                handlers = list(self._sub.get(topic, []))
            for h in handlers:
                try:
                    h(data)
                except Exception:
                    pass

    def start(self):
        with self._lock:
            if not self._started:
                self._worker.start()
                self._started = True

    def subscribe(self, topic: str, handler: Callable[[Any], None]):
        with self._lock:
            self._sub.setdefault(topic, []).append(handler)

    def publish(self, topic: str, data: Any):
        self._q.put((topic, data))

EVENT_BUS = EventBus()
EVENT_BUS.start()

# ======================
# HELPERS PARA RELATÓRIO
# ======================

def apply_period(df: pd.DataFrame, col_data: str, start: Optional[dt.date], end: Optional[dt.date]) -> pd.DataFrame:
    if df is None or df.empty or col_data not in df.columns:
        return df
    s = ensure_datetime(df[col_data]).dt.date
    if start:
        df = df[s >= start]
    if end:
        df = df[s <= end]
    return df

def prepare_status_hex(df: pd.DataFrame, status_col: str = "STATUS") -> pd.DataFrame:
    if df is None or df.empty or status_col not in df.columns:
        return df
    out = df.copy()
    out[status_col] = out[status_col].map(normalize_status)
    out["_STATUS_COLOR_HEX_"] = out[status_col].map(get_status_hex)
    return out

def quick_search(df: pd.DataFrame, term: str, cols: Optional[List[str]] = None) -> pd.DataFrame:
    t = normalize_text(term)
    if not t or df is None or df.empty:
        return df
    cols = cols or list(df.columns)
    mask = pd.Series(False, index=df.index)
    for c in cols:
        try:
            mask |= df[c].astype(str).str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.contains(t, case=False, na=False)
        except Exception:
            pass
    return df[mask]

def export_to_csv(df: pd.DataFrame, path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8")
    return str(p)

def export_to_excel(df: pd.DataFrame, path: str, sheet_name: str = "Dados") -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(p, engine="xlsxwriter") as xw:
        df.to_excel(xw, index=False, sheet_name=sheet_name)
    return str(p)

# ==========================
# PYQT6 UI HELPERS E CORES
# ==========================
try:
    from PyQt6.QtCore import QDate, Qt, pyqtSignal
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (
        QGraphicsDropShadowEffect, QMessageBox, QComboBox, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame, QLineEdit,
        QSplitter, QGroupBox, QWidget
    )

    # STATUS_COLOR (QColor) fallback, caso não tenha vindo do gestao_frota_single
    try:
        STATUS_COLOR  # noqa
    except NameError:
        STATUS_COLOR = {k: QColor(v) for k, v in STATUS_COLORS_HEX.items()}

    class CheckableComboBox(QComboBox):
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
            self._update_text()
            self.changed.emit()
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
            self.setEditable(True)
            self.lineEdit().setReadOnly(True)
            self.lineEdit().setText("Todos" if n == 0 else f"{n} selecionados")
            self.setEditable(False)

    def _paint_status(item, status):
        if status:
            bg = STATUS_COLOR.get(status)
            if bg:
                item.setBackground(bg)
                yiq = (bg.red()*299 + bg.green()*587 + bg.blue()*114) / 1000
                item.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))

    def parse_permissions(perms):
        if isinstance(perms, list):
            return perms
        if isinstance(perms, str):
            s = perms.strip()
            if s.lower() in ("todos","all","*",""):
                return 'todos'
            try:
                return ast.literal_eval(s)
            except Exception:
                return [p.strip() for p in s.split(",") if p.strip()]
        return 'todos'

    def apply_shadow(w, radius=20, blur=40, color=None):
        if color is None:
            color = QColor(0,0,0,100)
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(blur)
        eff.setXOffset(0)
        eff.setYOffset(8)
        eff.setColor(color)
        w.setGraphicsEffect(eff)
        try:
            w.setStyleSheet(f"border-radius:{radius}px;")
        except Exception:
            pass

    # -----------------------
    # Data helpers (QDate etc)
    # -----------------------
    def _parse_dt_any(s):
        s = str(s).strip()
        if not s:
            return QDate()
        for fmt in ["dd/MM/yyyy","dd-MM-yyyy","yyyy-MM-dd","yyyy/MM/dd"]:
            q = QDate.fromString(s, fmt)
            if q.isValid():
                return q
        try:
            dtv = pd.to_datetime(s, dayfirst=True, errors="coerce")
            if pd.notna(dtv):
                return QDate(int(dtv.year), int(dtv.month), int(dtv.day))
        except Exception:
            pass
        return QDate()

    def _norm(s):
        return ''.join(ch for ch in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(ch)).lower()

    # -----------------------
    # Pastores / Multas (I/O)
    # -----------------------
    def _pick_fase_pastores():
        base = os.path.join(PASTORES_DIR, "Notificações de Multas - Fase Pastores.xlsx")
        if os.path.exists(base):
            return base
        cands = []
        for p in ("*Fase*Pastor*.xls*", "*fase*pastor*.xls*"):
            cands += glob(os.path.join(PASTORES_DIR, p))
        cands = [p for p in cands if os.path.isfile(p)]
        if not cands:
            return ""
        return max(cands, key=lambda p: os.path.getmtime(p))

    def load_fase_pastores():
        path = _pick_fase_pastores()
        if not path:
            return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
        try:
            df = pd.read_excel(path, dtype=str, engine="openpyxl").fillna("")
        except Exception as e:
            QMessageBox.critical(None, "Erro", str(e))
            return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
        fcol = next((c for c in df.columns if "fluig" in c.lower()), None)
        dcol = next((c for c in df.columns if "data pastores" in c.lower() or ("pastores" in c.lower() and "data" in c.lower())), None)
        tcol = next((c for c in df.columns if "tipo" in c.lower()), None)
        if not fcol or not dcol or not tcol:
            return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
        out = df[[fcol, dcol, tcol]].copy()
        out.columns = ["FLUIG","DATA_PASTORES","TIPO"]
        for c in out.columns:
            out[c] = out[c].astype(str).str.strip()
        return out

    def load_fase_pastores_from(path):
        if not path or not os.path.exists(path):
            return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
        try:
            df = pd.read_excel(path, dtype=str, engine="openpyxl").fillna("")
        except Exception as e:
            QMessageBox.critical(None, "Erro", str(e))
            return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
        fcol = next((c for c in df.columns if "fluig" in c.lower()), None)
        dcol = next((c for c in df.columns if "data pastores" in c.lower() or ("pastores" in c.lower() and "data" in c.lower())), None)
        tcol = next((c for c in df.columns if "tipo" in c.lower()), None)
        if not fcol or not dcol or not tcol:
            return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
        out = df[[fcol, dcol, tcol]].copy()
        out.columns = ["FLUIG","DATA_PASTORES","TIPO"]
        for c in out.columns:
            out[c] = out[c].astype(str).str.strip()
        return out

    # -----------------------
    # CSV / Multas helpers
    # -----------------------
    def ensure_status_cols(df, csv_path=None):
        changed = False
        for c in DATE_COLS:
            sc = f"{c}_STATUS"
            if sc not in df.columns:
                df[sc] = ""
                changed = True
        if changed and csv_path:
            try:
                df.to_csv(csv_path, index=False)
            except Exception:
                pass
        return df

    def to_qdate_flexible(val):
        if not isinstance(val, str) or not val.strip():
            return QDate()
        for fmt in ["dd-MM-yyyy","dd/MM/yyyy","yyyy-MM-dd","yyyy/MM/dd"]:
            qd = QDate.fromString(val.strip(), fmt)
            if qd.isValid():
                return qd
        return QDate()

    def build_multa_dir(infrator, ano, mes, placa, notificacao, fluig):
        sub = f"{placa}_{notificao}_FLUIG({fluig})" if (notificao:=str(notificacao).strip()) else f"{placa}_FLUIG({fluig})"
        return os.path.join(MULTAS_ROOT, str(infrator).strip(), str(ano).strip(), str(mes).strip(), sub)

    def gerar_geral_multas_csv(root=MULTAS_ROOT, output=GERAL_MULTAS_CSV):
        rows = []
        if os.path.isdir(root):
            for infrator in os.listdir(root):
                infrator_dir = os.path.join(root, infrator)
                if not os.path.isdir(infrator_dir):
                    continue
                for ano in os.listdir(infrator_dir):
                    ano_dir = os.path.join(infrator_dir, ano)
                    if not os.path.isdir(ano_dir):
                        continue
                    for mes in os.listdir(ano_dir):
                        mes_dir = os.path.join(ano_dir, mes)
                        if not os.path.isdir(mes_dir):
                            continue
                        for folder in os.listdir(mes_dir):
                            fdir = os.path.join(mes_dir, folder)
                            if not os.path.isdir(fdir):
                                continue
                            parts = folder.split('_')
                            placa = parts[0] if len(parts)>0 else ""
                            notificacao = parts[1] if len(parts)>1 else ""
                            fluig = ""
                            if len(parts)>2 and '(' in parts[2] and ')' in parts[2]:
                                try:
                                    fluig = parts[2].split('(')[1].split(')')[0]
                                except Exception:
                                    fluig = ""
                            rows.append({
                                "INFRATOR": infrator,
                                "ANO": ano,
                                "MES": mes,
                                "PLACA": placa,
                                "NOTIFICACAO": notificacao,
                                "FLUIG": fluig,
                                "ORGÃO": "",
                                "DATA INDITACAO": "",
                                "BOLETO": "",
                                "LANÇAMENTO NFF": "",
                                "VALIDACAO NFF": "",
                                "CONCLUSAO": "",
                                "SGU": ""
                            })
        df = pd.DataFrame(rows)
        df = ensure_status_cols(df)
        df.to_csv(output, index=False)

    def ensure_base_csv():
        if not os.path.exists(GERAL_MULTAS_CSV):
            dir_path = os.path.dirname(GERAL_MULTAS_CSV)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            gerar_geral_multas_csv()

    # -----------------------
    # Diálogos
    # -----------------------
    class SummaryDialog(QDialog):
        def __init__(self, df):
            super().__init__()
            self.setWindowTitle("Visão Geral")
            self.resize(640, 480)
            v = QVBoxLayout(self)
            card = QFrame()
            card.setObjectName("card")
            apply_shadow(card, radius=16)
            cv = QVBoxLayout(card)
            t = QTableWidget()
            t.setColumnCount(2)
            t.setHorizontalHeaderLabels(["Coluna","Resumo"])
            resumo = []
            for col in df.columns:
                try:
                    s = pd.to_numeric(df[col], errors="coerce").sum()
                    resumo.append((col, str(s)))
                except Exception:
                    resumo.append((col, str(df[col].nunique())))
            t.setRowCount(len(resumo))
            for i,(c,val) in enumerate(resumo):
                t.setItem(i,0,QTableWidgetItem(c))
                t.setItem(i,1,QTableWidgetItem(val))
            t.resizeColumnsToContents()
            cv.addWidget(t)
            v.addWidget(card)
            close = QPushButton("Fechar")
            v.addWidget(close)
            close.clicked.connect(self.accept)

    class ConferirFluigDialog(QDialog):
        def __init__(self, parent, df_left, df_right):
            super().__init__(parent)
            self.setWindowTitle("Conferir Fluig")
            self.resize(1200, 680)
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
            wrap = QVBoxLayout(self)
            top = QHBoxLayout()
            l = QLabel(f"Abertas no Detalhamento e faltando no CSV: {len(df_left)}")
            r = QLabel(f"No CSV e não no Detalhamento (abertas): {len(df_right)}")
            l.setObjectName("headline"); r.setObjectName("headline")
            top.addWidget(l); top.addStretch(1); top.addWidget(r)
            wrap.addLayout(top)
            tools = QHBoxLayout()
            self.left_search = QLineEdit(); self.left_search.setPlaceholderText("Filtrar esquerda...")
            self.right_search = QLineEdit(); self.right_search.setPlaceholderText("Filtrar direita...")
            tools.addWidget(self.left_search); tools.addStretch(1); tools.addWidget(self.right_search)
            wrap.addLayout(tools)
            split = QSplitter()
            gb_l = QGroupBox("Detalhamento → faltando no CSV")
            gb_r = QGroupBox("CSV → faltando no Detalhamento")
            apply_shadow(gb_l, radius=14); apply_shadow(gb_r, radius=14)
            lv = QVBoxLayout(gb_l); rv = QVBoxLayout(gb_r)
            self.tbl_left = QTableWidget(); self.tbl_right = QTableWidget()
            for tbl in (self.tbl_left, self.tbl_right):
                tbl.setAlternatingRowColors(True)
                tbl.setSortingEnabled(True)
                tbl.horizontalHeader().setSortIndicatorShown(True)
                tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
                tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
            lv.addWidget(self.tbl_left); rv.addWidget(self.tbl_right)
            split.addWidget(gb_l); split.addWidget(gb_r)
            wrap.addWidget(split)
            actions = QHBoxLayout()
            self.btn_copy_left = QPushButton("Copiar FLUIG (esquerda)")
            self.btn_insert_left = QPushButton("Inserir selecionados")
            self.btn_copy_right = QPushButton("Copiar FLUIG (direita)")
            actions.addWidget(self.btn_copy_left)
            actions.addWidget(self.btn_insert_left)
            actions.addStretch(1)
            actions.addWidget(self.btn_copy_right)
            wrap.addLayout(actions)
            self.df_left = df_left.reset_index(drop=True)
            self.df_right = df_right.reset_index(drop=True)
            self._fill(self.tbl_left, self.df_left, actions_col=True)
            self._fill(self.tbl_right, self.df_right, actions_col=False)
            self.left_search.textChanged.connect(lambda: self._filter(self.tbl_left, self.df_left, self.left_search.text(), actions_col=True))
            self.right_search.textChanged.connect(lambda: self._filter(self.tbl_right, self.df_right, self.right_search.text(), actions_col=False))
            self.btn_copy_left.clicked.connect(lambda: self._copy(self.tbl_left))
            self.btn_copy_right.clicked.connect(lambda: self._copy(self.tbl_right))
            self.btn_insert_left.clicked.connect(self._insert_selected)

        def _fill(self, tbl, df, actions_col=False):
            tbl.clear()
            cols = [str(c) for c in df.columns]
            if actions_col:
                cols = cols + ["Ações"]
            tbl.setColumnCount(len(cols))
            tbl.setRowCount(len(df))
            tbl.setHorizontalHeaderLabels(cols)
            fcol = None
            for c in df.columns:
                if str(c).lower().startswith("nº fluig") or str(c).lower()=="fluig":
                    fcol = c
                    break
            for i in range(len(df)):
                for j,c in enumerate(df.columns):
                    it = QTableWidgetItem(str(df.iat[i, j]))
                    it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                    tbl.setItem(i, j, it)
                if actions_col and fcol is not None:
                    code = str(df.at[i, fcol]).strip()
                    btn = QPushButton("INSERIR")
                    btn.clicked.connect(lambda _, k=code: self._insert_one(k))
                    tbl.setCellWidget(i, len(cols)-1, btn)
            tbl.resizeColumnsToContents()
            tbl.resizeRowsToContents()

        def _filter(self, tbl, base, text, actions_col=False):
            tx = text.strip().lower()
            if not tx:
                df = base
            else:
                mask = base.apply(lambda r: any(tx in str(x).lower() for x in r.values), axis=1)
                df = base[mask]
            self._fill(tbl, df.reset_index(drop=True), actions_col=actions_col)

        def _copy(self, tbl):
            from PyQt6.QtWidgets import QApplication
            if tbl.rowCount()==0:
                QApplication.clipboard().setText("")
                return
            col = None
            for j in range(tbl.columnCount()):
                name = tbl.horizontalHeaderItem(j).text().lower()
                if name.startswith("nº fluig") or name=="fluig":
                    col = j; break
            if col is None:
                QApplication.clipboard().setText("")
                return
            rows = tbl.selectionModel().selectedRows()
            vals = [tbl.item(r.row(), col).text() for r in rows] if rows else [tbl.item(r, col).text() for r in range(tbl.rowCount())]
            QApplication.clipboard().setText("\n".join(vals))

        def _insert_one(self, code):
            if not code:
                return
            try:
                self.parent().inserir(code)
            except Exception:
                pass
            try:
                fcol = next((c for c in self.df_left.columns if str(c).lower().startswith("nº fluig") or str(c).lower()=="fluig"), None)
                if fcol:
                    self.df_left = self.df_left[self.df_left[fcol].astype(str).str.strip()!=str(code).strip()].reset_index(drop=True)
                    self._fill(self.tbl_left, self.df_left, actions_col=True)
            except Exception:
                pass

        def _insert_selected(self):
            col = None
            for j in range(self.tbl_left.columnCount()):
                name = self.tbl_left.horizontalHeaderItem(j).text().lower()
                if name.startswith("nº fluig") or name=="fluig":
                    col = j; break
            if col is None:
                return
            rows = self.tbl_left.selectionModel().selectedRows()
            if not rows:
                return
            codes = [self.tbl_left.item(r.row(), col).text() for r in rows]
            for code in codes:
                self._insert_one(code)

    class AlertasDialog(QDialog):
        def __init__(self, parent, df_alertas):
            super().__init__(parent)
            self.setWindowTitle("Alertas de Datas")
            self.resize(960,560)
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
            v = QVBoxLayout(self)
            card = QFrame(); card.setObjectName("glass"); apply_shadow(card, radius=18, blur=60, color=QColor(0,0,0,60))
            cv = QVBoxLayout(card)
            t = QTableWidget(); t.setAlternatingRowColors(True); t.setSortingEnabled(True); t.horizontalHeader().setSortIndicatorShown(True)
            t.setColumnCount(7)
            t.setHorizontalHeaderLabels(["FLUIG","INFRATOR","PLACA","ORGÃO","ETAPA","DATA","STATUS"])
            t.setRowCount(len(df_alertas))
            for r,row in enumerate(df_alertas):
                for c,val in enumerate(row):
                    it = QTableWidgetItem(val)
                    if c==6 and val in STATUS_COLOR:
                        _paint_status(it, val)
                    t.setItem(r,c,it)
            t.resizeColumnsToContents(); t.resizeRowsToContents()
            cv.addWidget(t)
            v.addWidget(card)
            close = QPushButton("Fechar"); close.clicked.connect(self.accept)
            v.addWidget(close)

    # -----------
    # GlobalFilter
    # -----------
    from PyQt6.QtWidgets import QFrame as _QFrame, QHBoxLayout as _QHBoxLayout, QLineEdit as _QLineEdit, QPushButton as _QPushButton, QLabel as _QLabel
    from PyQt6.QtCore import pyqtSignal as _pyqtSignal

    class GlobalFilterBar(_QFrame):
        changed = _pyqtSignal(list)
        def __init__(self, title: str = "Filtro global:"):
            super().__init__()
            self.setObjectName("card")
            apply_shadow(self, radius=14)
            self._edits: List[_QLineEdit] = []
            root = _QHBoxLayout(self)
            self._lab = _QLabel(title)
            root.addWidget(self._lab)
            self._add_box(fixed=True)
            self._btn_add = _QPushButton("+")
            self._btn_add.setFixedWidth(28)
            self._btn_add.clicked.connect(self._handle_add)
            root.addWidget(self._btn_add)
            root.addStretch(1)
        def _handle_add(self):
            self._add_box(fixed=False)
        def _add_box(self, fixed: bool):
            ed = _QLineEdit()
            ed.setPlaceholderText("Digite para filtrar em TODAS as colunas…")
            ed.textChanged.connect(lambda _=None, ed_=ed, fixed_=fixed: self._on_change(ed_, fixed_))
            self.layout().insertWidget(self.layout().count()-2, ed, 1)
            self._edits.append(ed)
        def _on_change(self, ed: _QLineEdit, fixed: bool):
            if not fixed and ed.text().strip() == "":
                try:
                    self._edits.remove(ed)
                except ValueError:
                    pass
                ed.setParent(None)
                ed.deleteLater()
            self.changed.emit(self.values())
        def values(self) -> List[str]:
            return [e.text().strip() for e in self._edits if e.text().strip()]

    def df_apply_global_texts(df: pd.DataFrame, texts: List[str]) -> pd.DataFrame:
        if df is None or df.empty or not texts:
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

except Exception:
    # Sem PyQt: mantemos apenas funções não-UI
    pass
