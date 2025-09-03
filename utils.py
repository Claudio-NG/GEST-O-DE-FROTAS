import os, ast, re, shutil, unicodedata
from glob import glob
import pandas as pd

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect, QMessageBox, QComboBox, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame, QLineEdit,
    QSplitter, QGroupBox, QWidget
)


import re
import pandas as pd
from gestao_frota_single import DATE_COLS, STATUS_COLOR, GERAL_MULTAS_CSV, MULTAS_ROOT, PASTORES_DIR, cfg_get, cfg_set

def df_apply_global_texts(df: pd.DataFrame, texts: list[str]) -> pd.DataFrame:
    """
    Aplica filtro 'contém' em TODAS as colunas (case-insensitive).
    - texts: lista com 1+ caixas (no seu caso, só 1). Cada caixa pode ter vários tokens separados por espaço.
    - Para cada caixa: TODOS os tokens precisam aparecer (AND) em ALGUMA coluna (OR entre colunas).
    - Se texts estiver vazio, retorna df sem alterações.
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

        # Para esta caixa, todos tokens (AND) devem ser verdadeiros em OR de colunas
        mask_box = pd.Series(True, index=df.index)
        for tok in tokens:
            m_tok = pd.Series(False, index=df.index)
            pat = re.escape(tok)
            for c in s_df.columns:
                m_tok |= s_df[c].str.contains(pat, na=False)
            mask_box &= m_tok

        mask_total &= mask_box

    return df[mask_total].copy()



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

# =============================================================================
# Helpers de data / parsing
# =============================================================================
def _parse_dt_any(s):
    s = str(s).strip()
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

def _norm(s):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(ch)).lower()

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
    out["FLUIG"] = out["FLUIG"].astype(str).str.strip()
    out["DATA_PASTORES"] = out["DATA_PASTORES"].astype(str).str.strip()
    out["TIPO"] = out["TIPO"].astype(str).str.strip()
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
    out["FLUIG"] = out["FLUIG"].astype(str).str.strip()
    out["DATA_PASTORES"] = out["DATA_PASTORES"].astype(str).str.strip()
    out["TIPO"] = out["TIPO"].astype(str).str.strip()
    return out

# =============================================================================
# UI helpers
# =============================================================================
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
        except:
            return [p.strip() for p in s.split(",") if p.strip()] 
    return 'todos'

def apply_shadow(w, radius=20, blur=40, color=QColor(0,0,0,100)):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(8)
    eff.setColor(color)
    w.setGraphicsEffect(eff)
    w.setStyleSheet(f"border-radius:{radius}px;")

# =============================================================================
# CSV / Multas helpers
# =============================================================================
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
        except:
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
    sub = f"{placa}_{notificacao}_FLUIG({fluig})"
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
                            fluig = parts[2].split('(')[1].split(')')[0]
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
        os.makedirs(os.path.dirname(GERAL_MULTAS_CSV), exist_ok=True)
        gerar_geral_multas_csv()

# =============================================================================
# DIÁLOGOS (antes em dialogs.py)
# =============================================================================
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
            except:
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
        if tbl.rowCount()==0:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText("")
            return
        col = None
        for j in range(tbl.columnCount()):
            name = tbl.horizontalHeaderItem(j).text().lower()
            if name.startswith("nº fluig") or name=="fluig":
                col = j; break
        if col is None:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText("")
            return
        rows = tbl.selectionModel().selectedRows()
        vals = [tbl.item(r.row(), col).text() for r in rows] if rows else [tbl.item(r, col).text() for r in range(tbl.rowCount())]
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(vals))

    def _insert_one(self, code):
        if not code:
            return
        try:
            self.parent().inserir(code)
        except:
            pass
        try:
            fcol = next((c for c in self.df_left.columns if str(c).lower().startswith("nº fluig") or str(c).lower()=="fluig"), None)
            if fcol:
                self.df_left = self.df_left[self.df_left[fcol].astype(str).str.strip()!=str(code).strip()].reset_index(drop=True)
                self._fill(self.tbl_left, self.df_left, actions_col=True)
        except:
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
