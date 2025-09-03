from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QFormLayout, QScrollArea,
    QTabWidget, QTabBar, QSplitter, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QDateEdit, QCompleter, QFrame,
    QGraphicsDropShadowEffect, QMessageBox
)
from PyQt6.QtGui import QFont, QFontMetrics, QColor, QIcon
from PyQt6.QtCore import Qt, QDate
import os, sys, re, shutil, ast
from decimal import Decimal
import pandas as pd
from PyQt6.QtCore import Qt, QDate, QFileSystemWatcher, QTimer

USERS_FILE = 'users.csv'
MODULES = [
    "Combustível",
    "Condutores",
    "Infrações e Multas",
    "Acidentes",
    "Avarias Corretivas (Acidentes e Mau Uso)",
    "Relatórios"
]
MULTAS_ROOT = r"T:\Veiculos\VEÍCULOS - RN\MULTAS"
GERAL_MULTAS_CSV = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\GERAL_MULTAS.csv"
ORGAOS = ["DETRAN","DEMUTRAM","STTU","DNIT","PRF","SEMUTRAM","DMUT"]
MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
PORTUGUESE_MONTHS = {1:"JANEIRO",2:"FEVEREIRO",3:"MARÇO",4:"ABRIL",5:"MAIO",6:"JUNHO",7:"JULHO",8:"AGOSTO",9:"SETEMBRO",10:"OUTUBRO",11:"NOVEMBRO",12:"DEZEMBRO"}

DATE_FORMAT = "dd-MM-yyyy"
DATE_COLS = ["DATA INDITACAO","BOLETO","LANÇAMENTO NFF","VALIDACAO NFF","CONCLUSAO","SGU"]
STATUS_OPS = ["","Pendente","Pago","Vencido"]
STATUS_COLOR = {"Pago": QColor("#2ecc71"), "Pendente": QColor("#ffd166"), "Vencido": QColor("#ef5350")}
PASTORES_XLSX = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\Notificações de Multas - Fase Pastores.xlsx"


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

from glob import glob

PASTORES_DIR = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS"
PASTORES_XLSX = os.path.join(PASTORES_DIR, "Notificações de Multas - Fase Pastores.xlsx")



from glob import glob
import unicodedata, os
from PyQt6.QtWidgets import QMessageBox

PASTORES_DIR = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS"

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


from pathlib import Path
import sys, os, pandas as pd

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PASTORES_XLSX = str(BASE_DIR / "Notificações de Multas - Fase Pastores.xlsx")

def load_fase_pastores():
    if not os.path.exists(PASTORES_XLSX):
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    try:
        df = pd.read_excel(PASTORES_XLSX, dtype=str, engine="openpyxl").fillna("")
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
            if not os.path.isdir(infrator_dir): continue
            for ano in os.listdir(infrator_dir):
                ano_dir = os.path.join(infrator_dir, ano)
                if not os.path.isdir(ano_dir): continue
                for mes in os.listdir(ano_dir):
                    mes_dir = os.path.join(ano_dir, mes)
                    if not os.path.isdir(mes_dir): continue
                    for folder in os.listdir(mes_dir):
                        fdir = os.path.join(mes_dir, folder)
                        if not os.path.isdir(fdir): continue
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
        t.setColumnCount(6)
        t.setHorizontalHeaderLabels(["FLUIG","INFRATOR","PLACA","ETAPA","DATA","STATUS"])
        t.setRowCount(len(df_alertas))
        for r,row in enumerate(df_alertas):
            for c,val in enumerate(row):
                it = QTableWidgetItem(val)
                if c==5 and val in STATUS_COLOR:
                    _paint_status(it, val)
                t.setItem(r,c,it)
        t.resizeColumnsToContents(); t.resizeRowsToContents()
        cv.addWidget(t)
        v.addWidget(card)
        close = QPushButton("Fechar"); close.clicked.connect(self.accept)
        v.addWidget(close)

class CombustivelWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combustível")
        self.resize(1280, 900)
        self.path_geral = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\ExtratoGeral.xlsx"
        self.path_simplificado = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\ExtratoSimplificado.xlsx"
        self.cat_cols = ["DATA TRANSACAO","PLACA","MODELO VEICULO","NOME MOTORISTA","TIPO COMBUSTIVEL","NOME ESTABELECIMENTO","RESPONSAVEL"]
        self.num_cols = ["LITROS","VL/LITRO","HODOMETRO OU HORIMETRO","KM RODADOS OU HORAS TRABALHADAS","KM/LITRO OU LITROS/HORA","VALOR EMISSAO"]
        self.df_original = pd.DataFrame(columns=self.cat_cols + self.num_cols)
        self.df_filtrado = self.df_original.copy()
        self.df_limites = pd.DataFrame()
        self.tot_limites = {"LIMITE ATUAL":0.0,"COMPRAS (UTILIZADO)":0.0,"SALDO":0.0,"LIMITE PRÓXIMO PERÍODO":0.0}
        self.filters = {}
        self.kpi_vals = {}
        self.kpi_dual = {}
        self.fit_targets = []
        root = QVBoxLayout(self)
        header = QFrame(); header.setObjectName("card"); apply_shadow(header, radius=18)
        hv = QVBoxLayout(header)
        tools = QHBoxLayout()
        self.btn_reload = QPushButton("Recarregar"); self.btn_reload.clicked.connect(self.recarregar)
        self.btn_clear = QPushButton("Limpar Filtros"); self.btn_clear.clicked.connect(self.limpar_filtros)
        tools.addWidget(self.btn_reload); tools.addStretch(1); tools.addWidget(self.btn_clear)
        hv.addLayout(tools)
        timebar = QHBoxLayout()
        self.cb_periodo = QComboBox(); self.cb_periodo.addItem("Todos"); self.cb_periodo.currentTextChanged.connect(lambda _: self._on_time_combo("periodo"))
        self.cb_mes = QComboBox(); self.cb_mes.addItem("Todos"); self.cb_mes.currentTextChanged.connect(lambda _: self._on_time_combo("mes"))
        self.cb_ano = QComboBox(); self.cb_ano.addItem("Todos"); self.cb_ano.currentTextChanged.connect(lambda _: self._on_time_combo("ano"))
        timebar.addWidget(QLabel("Período")); timebar.addWidget(self.cb_periodo)
        timebar.addSpacing(16)
        timebar.addWidget(QLabel("Mês")); timebar.addWidget(self.cb_mes)
        timebar.addSpacing(16)
        timebar.addWidget(QLabel("Ano")); timebar.addWidget(self.cb_ano)
        hv.addLayout(timebar)
        self.filters_layout = QGridLayout()
        for i,col in enumerate(self.cat_cols):
            box = QVBoxLayout()
            lab = QLabel(col); lab.setObjectName("colTitle")
            cb = QComboBox(); cb.addItem("Todos"); cb.currentTextChanged.connect(self.atualizar_filtro)
            self.filters[col] = cb
            box.addWidget(lab); box.addWidget(cb)
            self.filters_layout.addLayout(box, i//4, i%4)
        hv.addLayout(self.filters_layout)
        root.addWidget(header)
        grid_top = QFrame(); grid_top.setObjectName("glass"); apply_shadow(grid_top, radius=18, blur=60, color=QColor(0,0,0,80))
        gv1 = QGridLayout(grid_top)
        k1 = self._make_kpi("LITROS"); self.kpi_vals["LITROS"] = k1.findChild(QLabel, "val")
        k2 = self._make_kpi("VL/LITRO"); self.kpi_vals["VL/LITRO"] = k2.findChild(QLabel, "val")
        k3 = self._make_kpi("HODOMETRO OU HORIMETRO"); self.kpi_vals["HODOMETRO OU HORIMETRO"] = k3.findChild(QLabel, "val")
        k4 = self._make_kpi("KM RODADOS OU HORAS TRABALHADAS"); self.kpi_vals["KM RODADOS OU HORAS TRABALHADAS"] = k4.findChild(QLabel, "val")
        k5 = self._make_kpi("KM/LITRO OU LITROS/HORA"); self.kpi_vals["KM/LITRO OU LITROS/HORA"] = k5.findChild(QLabel, "val")
        k6 = self._make_kpi("VALOR EMISSAO"); self.kpi_vals["VALOR EMISSAO"] = k6.findChild(QLabel, "val")
        for i,c in enumerate([k1,k2,k3,k4,k5,k6]):
            gv1.addWidget(c, i//3, i%3)
        root.addWidget(grid_top)
        grid_bottom = QFrame(); grid_bottom.setObjectName("glass"); apply_shadow(grid_bottom, radius=18, blur=60, color=QColor(0,0,0,80))
        gv2 = QGridLayout(grid_bottom)
        d1 = self._make_kpi_dual("LIMITE ATUAL", True); self.kpi_dual["LIMITE ATUAL"] = d1
        d2 = self._make_kpi_dual("COMPRAS (UTILIZADO)", True); self.kpi_dual["COMPRAS (UTILIZADO)"] = d2
        d3 = self._make_kpi_dual("SALDO", True); self.kpi_dual["SALDO"] = d3
        d4 = self._make_kpi_dual("LIMITE PRÓXIMO PERÍODO", True); self.kpi_dual["LIMITE PRÓXIMO PERÍODO"] = d4
        for i,c in enumerate([d1,d2,d3,d4]):
            gv2.addWidget(c["frame"], i//2, i%2)
        root.addWidget(grid_bottom)
        self.recarregar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for lab in self.fit_targets:
            self._fit_font(lab)

    def _make_kpi(self, title):
        f = QFrame(); f.setObjectName("card"); apply_shadow(f, radius=14)
        v = QVBoxLayout(f)
        t = QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val = QLabel("0"); val.setObjectName("val"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t); v.addWidget(val)
        val.setFont(QFont("Arial", 30, QFont.Weight.Bold))
        self.fit_targets.append(val)
        return f

    def _make_kpi_dual(self, title, currency=False):
        f = QFrame(); f.setObjectName("card"); apply_shadow(f, radius=14)
        v = QVBoxLayout(f)
        t = QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main = QLabel("0"); main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("TOTAL: 0"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.setProperty("currency", currency)
        sub.setProperty("currency", currency)
        main.setFont(QFont("Arial", 34, QFont.Weight.Bold))
        sub.setFont(QFont("Arial", 12))
        v.addWidget(t); v.addWidget(main); v.addWidget(sub)
        self.fit_targets.append(main)
        return {"frame": f, "main": main, "sub": sub}

    def _parse_dt(self, s):
        s = str(s).strip()
        if not s:
            return pd.NaT
        for fmt in ["%d/%m/%Y %H:%M:%S","%d/%m/%Y","%Y-%m-%d %H:%M:%S","%Y-%m-%d"]:
            try:
                return pd.to_datetime(s, format=fmt, dayfirst=True)
            except:
                continue
        try:
            return pd.to_datetime(s, dayfirst=True, errors="coerce")
        except:
            return pd.NaT

    def _period_start(self, d):
        if d.day >= 15:
            return pd.Timestamp(d.year, d.month, 15)
        prev = d - pd.offsets.MonthBegin(1)
        prev = prev - pd.offsets.Day(1)
        return pd.Timestamp(prev.year, prev.month, 15)

    def _period_end(self, start):
        nm = start + pd.offsets.MonthBegin(1)
        return pd.Timestamp(nm.year, nm.month, 14)

    def _month_label(self, d):
        return f"{PORTUGUESE_MONTHS.get(d.month,'').upper()}/{str(d.year)[-2:]}"

    def recarregar(self):
        try:
            df = pd.read_excel(self.path_geral, dtype=str).fillna("")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e)); df = pd.DataFrame()
        try:
            df2 = pd.read_excel(self.path_simplificado, dtype=str).fillna("")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e)); df2 = pd.DataFrame()
        df.columns = [str(c).strip().upper() for c in df.columns]
        df2.columns = [str(c).strip().upper() for c in df2.columns]
        for c in self.cat_cols + self.num_cols:
            if c not in df.columns:
                df[c] = ""
        if "DATA TRANSACAO" in df.columns:
            dt_series = df["DATA TRANSACAO"].apply(self._parse_dt)
        else:
            dt_series = pd.to_datetime(pd.Series([], dtype=str))
        df["__DT__"] = dt_series
        df["DATA TRANSACAO"] = df["__DT__"].dt.strftime("%d-%m-%Y").fillna("")
        self.df_original = df[self.cat_cols + self.num_cols + ["__DT__"]].copy()
        self.df_filtrado = self.df_original.copy()
        cr = None
        for cand in ["NOME RESPONSÁVEL","NOME RESPONSAVEL","RESPONSAVEL","RESPONSÁVEL"]:
            if cand in df2.columns:
                cr = cand; break
        if cr is None:
            df2["RESPONSAVEL"] = ""
        else:
            df2 = df2.rename(columns={cr:"RESPONSAVEL"})
        map_cols = {
            "LIMITE ATUAL":["LIMITE ATUAL","LIMITE ATUAL "],
            "COMPRAS (UTILIZADO)":["COMPRAS (UTILIZADO)","COMPRAS","COMPRAS UTILIZADO"],
            "SALDO":["SALDO"],
            "LIMITE PRÓXIMO PERÍODO":["LIMITE PRÓXIMO PERÍODO","LIMITE PROXIMO PERIODO"]
        }
        for std, alts in map_cols.items():
            if std not in df2.columns:
                for a in alts:
                    if a in df2.columns:
                        df2.rename(columns={a:std}, inplace=True)
                        break
        for need in ["PLACA","LIMITE ATUAL","COMPRAS (UTILIZADO)","SALDO","LIMITE PRÓXIMO PERÍODO"]:
            if need not in df2.columns:
                df2[need] = ""
        self.df_limites = df2[["PLACA","RESPONSAVEL","LIMITE ATUAL","COMPRAS (UTILIZADO)","SALDO","LIMITE PRÓXIMO PERÍODO"]].copy()
        self.tot_limites = {
            "LIMITE ATUAL": float(self._col_sum(self.df_limites, "LIMITE ATUAL")),
            "COMPRAS (UTILIZADO)": float(self._col_sum(self.df_limites, "COMPRAS (UTILIZADO)")),
            "SALDO": float(self._col_sum(self.df_limites, "SALDO")),
            "LIMITE PRÓXIMO PERÍODO": float(self._col_sum(self.df_limites, "LIMITE PRÓXIMO PERÍODO"))
        }
        self._rebuild_filters()
        self._build_time_combos()
        self._update_all()

    def _build_time_combos(self):
        dts = self.df_original["__DT__"].dropna()
        periods = []
        months = []
        years = []
        if not dts.empty:
            dmin = dts.min().normalize()
            dmax = dts.max().normalize()
            start = self._period_start(dmin)
            idx = 1
            while start <= dmax:
                end = self._period_end(start)
                periods.append((f"P{idx}: {start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}", start, end))
                idx += 1
                start = end + pd.Timedelta(days=1)
            uniq = sorted({(int(d.month), int(d.year)) for d in dts})
            for m,y in uniq:
                months.append((self._month_label(pd.Timestamp(y, m, 1)), m, y))
            years = sorted({int(d.year) for d in dts})
        self.cb_periodo.blockSignals(True); self.cb_periodo.clear(); self.cb_periodo.addItem("Todos")
        for label, s, e in periods:
            self.cb_periodo.addItem(label, (s, e))
        self.cb_periodo.blockSignals(False)
        self.cb_mes.blockSignals(True); self.cb_mes.clear(); self.cb_mes.addItem("Todos")
        for label, m, y in months:
            self.cb_mes.addItem(label, (m, y))
        self.cb_mes.blockSignals(False)
        self.cb_ano.blockSignals(True); self.cb_ano.clear(); self.cb_ano.addItem("Todos")
        for y in years:
            self.cb_ano.addItem(str(y), y)
        self.cb_ano.blockSignals(False)

    def _on_time_combo(self, who):
        if who=="periodo" and self.cb_periodo.currentText()!="Todos":
            self.cb_mes.blockSignals(True); self.cb_mes.setCurrentIndex(0); self.cb_mes.blockSignals(False)
            self.cb_ano.blockSignals(True); self.cb_ano.setCurrentIndex(0); self.cb_ano.blockSignals(False)
        elif who=="mes" and self.cb_mes.currentText()!="Todos":
            self.cb_periodo.blockSignals(True); self.cb_periodo.setCurrentIndex(0); self.cb_periodo.blockSignals(False)
            self.cb_ano.blockSignals(True); self.cb_ano.setCurrentIndex(0); self.cb_ano.blockSignals(False)
        elif who=="ano" and self.cb_ano.currentText()!="Todos":
            self.cb_periodo.blockSignals(True); self.cb_periodo.setCurrentIndex(0); self.cb_periodo.blockSignals(False)
            self.cb_mes.blockSignals(True); self.cb_mes.setCurrentIndex(0); self.cb_mes.blockSignals(False)
        self.atualizar_filtro()

    def limpar_filtros(self):
        for cb in self.filters.values():
            cb.blockSignals(True); cb.setCurrentIndex(0); cb.blockSignals(False)
        self.cb_periodo.blockSignals(True); self.cb_periodo.setCurrentIndex(0); self.cb_periodo.blockSignals(False)
        self.cb_mes.blockSignals(True); self.cb_mes.setCurrentIndex(0); self.cb_mes.blockSignals(False)
        self.cb_ano.blockSignals(True); self.cb_ano.setCurrentIndex(0); self.cb_ano.blockSignals(False)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()
        mask = pd.Series([True]*len(df))
        if self.cb_periodo.currentText()!="Todos":
            s,e = self.cb_periodo.currentData()
            mask &= df["__DT__"].between(s, e)
        elif self.cb_mes.currentText()!="Todos":
            m,y = self.cb_mes.currentData()
            mask &= (df["__DT__"].dt.month==m) & (df["__DT__"].dt.year==y)
        elif self.cb_ano.currentText()!="Todos":
            y = self.cb_ano.currentData()
            mask &= (df["__DT__"].dt.year==y)
        df = df[mask]
        for col,cb in self.filters.items():
            sel = cb.currentText()
            if sel and sel!="Todos":
                df = df[df[col].astype(str)==sel]
        self.df_filtrado = df
        for col,cb in self.filters.items():
            current = cb.currentText()
            items = ["Todos"] + sorted(self.df_filtrado[col].dropna().astype(str).unique())
            cb.blockSignals(True); cb.clear(); cb.addItems(items); cb.setCurrentText(current if current in items else "Todos"); cb.blockSignals(False)
        self._update_all()

    def _rebuild_filters(self):
        for col,cb in self.filters.items():
            cb.blockSignals(True)
            cb.clear()
            items = ["Todos"] + sorted(self.df_original[col].dropna().astype(str).unique())
            cb.addItems(items)
            cb.blockSignals(False)

    def _num_brl(self, x):
        s = str(x).strip()
        if not s:
            return Decimal("0")
        s = re.sub(r"[^\d,.\-]", "", s)
        if "," in s and "." in s:
            dec = "," if s.rfind(",") > s.rfind(".") else "."
            mil = "." if dec == "," else ","
            s = s.replace(mil, "")
            if dec == ",":
                s = s.replace(",", ".")
        elif "," in s and "." not in s:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        elif "." in s and "," not in s:
            pass
        try:
            return Decimal(s)
        except:
            return Decimal("0")

    def _col_sum(self, df, col):
        return sum(self._num_brl(v) for v in df[col].tolist())

    def _to_float(self, x):
        return float(self._num_brl(x))

    def _fmt_num(self, v):
        s = f"{v:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_brl(self, v):
        return "R$ " + self._fmt_num(v)

    def _fit_font(self, label, max_pt=40, min_pt=10):
        text = label.text()
        if not text:
            return
        w = max(10, label.width()-8)
        h = max(10, label.height()-8)
        f = label.font()
        size = max_pt
        while size >= min_pt:
            f.setPointSize(size)
            fm = QFontMetrics(f)
            if fm.horizontalAdvance(text) <= w and fm.height() <= h:
                break
            size -= 1
        label.setFont(f)

    def _update_all(self):
        vals = {c: float(self.df_filtrado[c].apply(self._num_brl).sum()) for c in self.num_cols}
        self.kpi_vals["LITROS"].setText(self._fmt_num(vals["LITROS"]))
        self.kpi_vals["VL/LITRO"].setText(self._fmt_brl(vals["VL/LITRO"]))
        self.kpi_vals["HODOMETRO OU HORIMETRO"].setText(self._fmt_num(vals["HODOMETRO OU HORIMETRO"]))
        self.kpi_vals["KM RODADOS OU HORAS TRABALHADAS"].setText(self._fmt_num(vals["KM RODADOS OU HORAS TRABALHADAS"]))
        self.kpi_vals["KM/LITRO OU LITROS/HORA"].setText(self._fmt_num(vals["KM/LITRO OU LITROS/HORA"]))
        self.kpi_vals["VALOR EMISSAO"].setText(self._fmt_brl(vals["VALOR EMISSAO"]))
        for lab in self.kpi_vals.values():
            self._fit_font(lab)
        placa_sel = self.filters["PLACA"].currentText() if "PLACA" in self.filters else "Todos"
        if placa_sel != "Todos":
            p = str(placa_sel).strip().upper()
            dfp = self.df_limites[self.df_limites["PLACA"].astype(str).str.strip().str.upper().eq(p)]
        else:
            dfp = self.df_limites.iloc[0:0]
        for key, card in self.kpi_dual.items():
            main_val = float(self._col_sum(dfp, key)) if placa_sel != "Todos" else 0.0
            total_val = float(self._col_sum(self.df_limites, key))
            card["main"].setText(self._fmt_brl(main_val))
            card["sub"].setText("TOTAL: " + self._fmt_brl(total_val))
            self._fit_font(card["main"])



class InserirDialog(QDialog):
    def __init__(self, parent, prefill_fluig=None):
        super().__init__(parent)
        self.setWindowTitle("Inserir Multa")
        self.resize(720, 560)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
        form = QFormLayout(self)
        self.widgets = {}
        fields = ["FLUIG"] + [c for c in self.df.columns if not c.endswith("_STATUS") and c!="FLUIG"]
        for c in fields:
            if c in DATE_COLS:
                d = QDateEdit(); d.setCalendarPopup(True); d.setDisplayFormat(DATE_FORMAT)
                d.setMinimumDate(QDate(1752,9,14)); d.setSpecialValueText("")
                d.setDate(d.minimumDate())
                s = QComboBox(); s.addItems(STATUS_OPS)
                box = QWidget(); hb = QHBoxLayout(box); hb.setContentsMargins(0,0,0,0); hb.addWidget(d); hb.addWidget(s)
                form.addRow(c, box); self.widgets[c]=(d,s)
            elif c=="ORGÃO":
                cb=QComboBox(); cb.addItems(ORGAOS); form.addRow(c,cb); self.widgets[c]=cb
            else:
                w=QLineEdit()
                if c=="FLUIG":
                    comp=QCompleter(sorted(self.df["FLUIG"].dropna().astype(str).unique()))
                    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                    w.setCompleter(comp)
                    w.editingFinished.connect(lambda le=w: self.on_fluig_leave(le))
                form.addRow(c,w); self.widgets[c]=w
        bar = QHBoxLayout()
        btn_save = QPushButton("Salvar"); btn_pdf = QPushButton("Anexar PDF"); btn_close = QPushButton("Fechar")
        bar.addWidget(btn_save); bar.addStretch(1); bar.addWidget(btn_pdf); bar.addWidget(btn_close)
        form.addRow(bar)
        btn_save.clicked.connect(self.salvar)
        btn_pdf.clicked.connect(self.anexar_pdf)
        btn_close.clicked.connect(self.reject)
        if prefill_fluig:
            self.widgets["FLUIG"].setText(str(prefill_fluig).strip())
            self.on_fluig_leave(self.widgets["FLUIG"])

    def _apply_fase_pastores(self, code):
        dfp = load_fase_pastores()
        if dfp.empty:
            return
        row = dfp[dfp["FLUIG"].eq(str(code).strip())]
        if row.empty:
            return
        r = row.iloc[0]
        tipo = str(r["TIPO"]).upper()
        data = str(r["DATA_PASTORES"]).strip()
        if ("PASTOR" in tipo) and data and "SGU" in self.widgets:
            de, se = self.widgets["SGU"]
            qd = _parse_dt_any(data)
            if qd.isValid():
                de.setDate(qd)
                se.setCurrentText("Pago")

    def on_fluig_leave(self, le):
        code = str(le.text()).strip()
        if code in self.df["FLUIG"].astype(str).tolist():
            QMessageBox.warning(self,"Erro","FLUIG existe"); le.clear(); return
        try:
            x = pd.read_excel(r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\Notificações de Multas - Detalhamento.xlsx",
                              usecols=["Nº Fluig","Placa","Nome","AIT","Data Infração","Data Limite","Status"], dtype=str).fillna("")
        except Exception as e:
            QMessageBox.warning(self,"Aviso",str(e)); return
        row = x[x["Nº Fluig"].astype(str).str.strip()==code]
        if row.empty:
            self._apply_fase_pastores(code)
            return
        self.widgets["PLACA"].setText(row["Placa"].iloc[0])
        self.widgets["INFRATOR"].setText(row["Nome"].iloc[0])
        self.widgets["NOTIFICACAO"].setText(row["AIT"].iloc[0])
        try:
            dt = pd.to_datetime(row["Data Infração"].iloc[0], dayfirst=False)
            self.widgets["MES"].setText(PORTUGUESE_MONTHS.get(dt.month,""))
            self.widgets["ANO"].setText(str(dt.year))
        except:
            pass
        try:
            d2 = pd.to_datetime(row["Data Limite"].iloc[0], dayfirst=False)
            de,_ = self.widgets["DATA INDITACAO"]; de.setDate(QDate(d2.year,d2.month,d2.day))
        except:
            pass
        self._apply_fase_pastores(code)

    def salvar(self):
        new = {}
        for c,w in self.widgets.items():
            if isinstance(w,tuple):
                d,s = w
                new[c] = "" if d.date()==d.minimumDate() else d.date().toString(DATE_FORMAT)
                new[f"{c}_STATUS"] = s.currentText()
            else:
                new[c] = w.currentText() if isinstance(w,QComboBox) else w.text().strip()
        if new.get("FLUIG","") in self.df["FLUIG"].astype(str).tolist():
            QMessageBox.warning(self,"Erro","FLUIG já existe"); return
        self.df.loc[len(self.df)] = new
        os.makedirs(os.path.dirname(GERAL_MULTAS_CSV), exist_ok=True)
        self.df.to_csv(GERAL_MULTAS_CSV, index=False)
        try:
            infr, ano, mes = new.get("INFRATOR",""), new.get("ANO",""), new.get("MES","")
            placa, notificacao, fluig = new.get("PLACA",""), new.get("NOTIFICACAO",""), new.get("FLUIG","")
            dest = build_multa_dir(infr, ano, mes, placa, notificacao, fluig)
            os.makedirs(dest, exist_ok=True)
            if not os.path.isdir(dest):
                QMessageBox.warning(self,"Aviso","Pasta não criada")
        except:
            pass
        self.anexar_pdf()
        QMessageBox.information(self,"Sucesso","Multa inserida.")
        self.accept()

    def anexar_pdf(self):
        try:
            infr, ano, mes = self.widgets["INFRATOR"].text().strip(), self.widgets["ANO"].text().strip(), self.widgets["MES"].text().strip()
            placa, notificacao, fluig = self.widgets["PLACA"].text().strip(), self.widgets["NOTIFICACAO"].text().strip(), self.widgets["FLUIG"].text().strip()
            if not all([infr,ano,mes,placa,notificacao,fluig]): return
            dest = build_multa_dir(infr, ano, mes, placa, notificacao, fluig)
            os.makedirs(dest, exist_ok=True)
            pdf,_ = QFileDialog.getOpenFileName(self,"Selecione PDF","","PDF Files (*.pdf)")
            if pdf:
                shutil.copy(pdf, os.path.join(dest, os.path.basename(pdf)))
        except:
            pass



class EditarDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Editar Multa")
        self.resize(720, 560)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
        self.le_key = QLineEdit(); self.le_key.setPlaceholderText("Digite FLUIG para carregar")
        comp = QCompleter(sorted(self.df["FLUIG"].dropna().astype(str).unique()))
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.le_key.setCompleter(comp)
        btn_load = QPushButton("Carregar")
        top.addWidget(self.le_key); top.addWidget(btn_load)
        v.addLayout(top)
        self.formw = QWidget(); self.form = QFormLayout(self.formw)
        self.widgets = {}
        v.addWidget(self.formw)
        bar = QHBoxLayout()
        btn_save = QPushButton("Salvar"); btn_close = QPushButton("Fechar")
        bar.addWidget(btn_save); bar.addStretch(1); bar.addWidget(btn_close)
        v.addLayout(bar)
        btn_load.clicked.connect(self.load_record)
        btn_save.clicked.connect(self.save_record)
        btn_close.clicked.connect(self.reject)

    def load_record(self):
        key = self.le_key.text().strip()
        if not key: return
        self.df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
        rows = self.df.index[self.df["FLUIG"].astype(str)==key].tolist()
        if not rows:
            QMessageBox.warning(self,"Aviso","FLUIG não encontrado"); return
        i = rows[0]
        for c in [col for col in self.df.columns if not col.endswith("_STATUS")]:
            if c in self.widgets: continue
            if c in DATE_COLS:
                d = QDateEdit(); d.setCalendarPopup(True); d.setDisplayFormat(DATE_FORMAT)
                d.setMinimumDate(QDate(1752,9,14)); d.setSpecialValueText("")
                qd = to_qdate_flexible(self.df.at[i,c])
                d.setDate(qd if qd.isValid() else d.minimumDate())
                s = QComboBox(); s.addItems(STATUS_OPS)
                s.setCurrentText(self.df.at[i, f"{c}_STATUS"] if f"{c}_STATUS" in self.df.columns else "")
                box = QWidget(); hb = QHBoxLayout(box); hb.setContentsMargins(0,0,0,0); hb.addWidget(d); hb.addWidget(s)
                self.form.addRow(c,box); self.widgets[c]=(d,s)
            elif c=="ORGÃO":
                cb=QComboBox(); cb.addItems(ORGAOS); cb.setCurrentText(self.df.at[i,c])
                self.form.addRow(c,cb); self.widgets[c]=cb
            else:
                w=QLineEdit(self.df.at[i,c]); self.form.addRow(c,w); self.widgets[c]=w
        self.current_index = i

    def save_record(self):
        if not hasattr(self, "current_index"): return
        i = self.current_index
        for c,w in self.widgets.items():
            if isinstance(w,tuple):
                d,s = w
                self.df.at[i,c] = "" if d.date()==d.minimumDate() else d.date().toString(DATE_FORMAT)
                self.df.at[i,f"{c}_STATUS"] = s.currentText()
            else:
                self.df.at[i,c] = w.currentText() if isinstance(w,QComboBox) else w.text().strip()
        self.df.to_csv(GERAL_MULTAS_CSV, index=False)
        QMessageBox.information(self,"Sucesso","Multa editada.")
        self.accept()





class ExcluirDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Excluir Multa")
        self.resize(520, 160)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
        self.le_key = QLineEdit(); self.le_key.setPlaceholderText("Digite FLUIG para excluir")
        comp = QCompleter(sorted(self.df["FLUIG"].dropna().astype(str).unique()))
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.le_key.setCompleter(comp)
        btn_delete = QPushButton("Excluir")
        top.addWidget(self.le_key); top.addWidget(btn_delete)
        v.addLayout(top)
        bar = QHBoxLayout()
        btn_close = QPushButton("Fechar"); bar.addStretch(1); bar.addWidget(btn_close)
        v.addLayout(bar)
        btn_delete.clicked.connect(self.do_delete)
        btn_close.clicked.connect(self.reject)

    def do_delete(self):
        key = self.le_key.text().strip()
        if not key: return
        self.df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
        rows = self.df.index[self.df["FLUIG"].astype(str)==key].tolist()
        if not rows:
            QMessageBox.warning(self,"Aviso","FLUIG não encontrado"); return
        i = rows[0]
        try:
            infr = str(self.df.at[i,"INFRATOR"]) if "INFRATOR" in self.df.columns else ""
            ano = str(self.df.at[i,"ANO"]) if "ANO" in self.df.columns else ""
            mes = str(self.df.at[i,"MES"]) if "MES" in self.df.columns else ""
            placa = str(self.df.at[i,"PLACA"]) if "PLACA" in self.df.columns else ""
            notificacao = str(self.df.at[i,"NOTIFICACAO"]) if "NOTIFICACAO" in self.df.columns else ""
            fluig = str(self.df.at[i,"FLUIG"]) if "FLUIG" in self.df.columns else ""
            path = build_multa_dir(infr, ano, mes, placa, notificacao, fluig)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                p = os.path.dirname(path)
                for _ in range(3):
                    if p and os.path.isdir(p) and not os.listdir(p) and os.path.commonpath([p, MULTAS_ROOT])==MULTAS_ROOT:
                        try:
                            os.rmdir(p)
                        except:
                            pass
                        p = os.path.dirname(p)
            if os.path.isdir(path):
                QMessageBox.warning(self,"Aviso","Pasta não removida")
        except:
            pass
        self.df = self.df.drop(i).reset_index(drop=True)
        self.df.to_csv(GERAL_MULTAS_CSV, index=False)
        QMessageBox.information(self,"Sucesso","Multa excluída.")
        self.accept()
     


from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QFormLayout, QScrollArea,
    QTabWidget, QTabBar, QSplitter, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QDateEdit, QCompleter, QFrame,
    QGraphicsDropShadowEffect, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, QFileSystemWatcher, QTimer



class RelatorioWindow(QWidget):
    def __init__(self, caminho_arquivo):
        super().__init__()
        fm = QFontMetrics(self.font())
        self.max_pix = fm.horizontalAdvance("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        self.setWindowTitle("Relatórios")
        self.resize(1280, 820)
        self.path = caminho_arquivo
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.filtros = {}
        self.text_filtros = {}
        root = QVBoxLayout(self)
        header_card = QFrame()
        header_card.setObjectName("card")
        apply_shadow(header_card, radius=18)
        top = QVBoxLayout(header_card)
        actions = QHBoxLayout()
        btn_recarregar = QPushButton("Recarregar")
        btn_recarregar.clicked.connect(self.recarregar)
        btn_visao = QPushButton("Visão Geral")
        btn_visao.clicked.connect(self.mostrar_visao)
        btn_limpar = QPushButton("Limpar filtros")
        btn_limpar.clicked.connect(self.limpar_filtros)
        btn_export = QPushButton("Exportar Excel")
        btn_export.clicked.connect(self.exportar_excel)
        actions.addWidget(btn_recarregar)
        actions.addWidget(btn_visao)
        actions.addWidget(btn_limpar)
        actions.addStretch(1)
        actions.addWidget(btn_export)
        top.addLayout(actions)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.filters_host = QWidget()
        self.filters_grid = QGridLayout(self.filters_host)
        self.filters_grid.setContentsMargins(12,12,12,12)
        self.filters_grid.setHorizontalSpacing(14)
        self.filters_grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.filters_host)
        top.addWidget(self.scroll)
        root.addWidget(header_card)
        table_card = QFrame()
        table_card.setObjectName("glass")
        apply_shadow(table_card, radius=18, blur=60, color=QColor(0,0,0,80))
        tv = QVBoxLayout(table_card)
        self.tabela = QTableWidget()
        self.tabela.setAlternatingRowColors(True)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.setSortingEnabled(True)
        self.tabela.horizontalHeader().setSortIndicatorShown(True)
        tv.addWidget(self.tabela)
        root.addWidget(table_card)
        self.watcher = QFileSystemWatcher()
        if os.path.exists(self.path):
            self.watcher.addPath(self.path)
        self.watcher.fileChanged.connect(self._file_changed)
        self.carregar_dados(self.path)
        self.showMaximized()

    def _file_changed(self, p):
        QTimer.singleShot(500, self.recarregar)

    def carregar_dados(self, caminho):
        ext = os.path.splitext(caminho)[1].lower()
        if ext in ('.xlsx','.xls'):
            df = pd.read_excel(caminho, dtype=str).fillna("")
        elif ext == '.csv':
            try:
                df = pd.read_csv(caminho, dtype=str, encoding='utf-8').fillna("")
            except UnicodeDecodeError:
                df = pd.read_csv(caminho, dtype=str, encoding='latin1').fillna("")
        else:
            QMessageBox.warning(self, "Aviso", "Formato não suportado")
            return
        self.df_original = ensure_status_cols(df)
        self.df_filtrado = self.df_original.copy()
        self._montar_filtros()
        self.preencher_tabela(self.df_filtrado)

    def _montar_filtros(self):
        while self.filters_grid.count():
            item = self.filters_grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.filtros.clear()
        self.text_filtros.clear()
        cols = list(self.df_original.columns)
        for i, coluna in enumerate(cols):
            box = QVBoxLayout()
            wrap = QWidget()
            wrap.setLayout(box)
            label = QLabel(coluna)
            label.setObjectName("colTitle")
            label.setWordWrap(True)
            label.setMaximumWidth(self.max_pix)
            combo = QComboBox()
            combo.addItems(["Todos","Excluir vazios","Somente vazios"] + sorted(self.df_original[coluna].dropna().astype(str).unique()))
            combo.setMaximumWidth(self.max_pix)
            combo.currentTextChanged.connect(self.atualizar_filtro)
            entrada = QLineEdit()
            entrada.setPlaceholderText(f"Filtrar {coluna}...")
            entrada.setMaximumWidth(self.max_pix)
            entrada.textChanged.connect(self.atualizar_filtro)
            box.addWidget(label)
            box.addWidget(combo)
            box.addWidget(entrada)
            self.filtros[coluna] = combo
            self.text_filtros[coluna] = entrada
            self.filters_grid.addWidget(wrap, i//4, i%4)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.filters_grid.addWidget(spacer, (len(cols)+3)//4, 0, 1, 4)

    def mostrar_visao(self):
        dlg = SummaryDialog(self.df_filtrado)
        dlg.exec()

    def limpar_filtros(self):
        for combo in self.filtros.values():
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        for entrada in self.text_filtros.values():
            entrada.blockSignals(True)
            entrada.clear()
            entrada.blockSignals(False)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()
        for coluna in self.df_original.columns:
            sel = self.filtros[coluna].currentText()
            txt = self.text_filtros[coluna].text().strip()
            if sel == "Excluir vazios":
                df = df[df[coluna].astype(str)!=""]
            elif sel == "Somente vazios":
                df = df[df[coluna].astype(str)==""] 
            elif sel != "Todos":
                df = df[df[coluna].astype(str) == sel]
            if txt:
                termos = [t for t in txt.split() if t]
                if termos:
                    s = df[coluna].astype(str).str.lower()
                    for t in termos:
                        df = df[s.str.contains(re.escape(t.lower()), na=False)]
                        s = df[coluna].astype(str).str.lower()
        self.df_filtrado = df
        for col in self.df_original.columns:
            combo = self.filtros[col]
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            items = ["Todos","Excluir vazios","Somente vazios"] + sorted(self.df_filtrado[col].dropna().astype(str).unique())
            combo.addItems(items)
            combo.setCurrentText(current if current in items else "Todos")
            combo.blockSignals(False)
        self.preencher_tabela(self.df_filtrado)

    def preencher_tabela(self, df):
        self.tabela.clear()
        self.tabela.setColumnCount(len(df.columns))
        self.tabela.setRowCount(len(df))
        self.tabela.setHorizontalHeaderLabels([str(c) for c in df.columns])
        df_idx = df.reset_index(drop=True)
        for i in range(len(df_idx)):
            for j, col in enumerate(df_idx.columns):
                val = "" if pd.isna(df_idx.iat[i, j]) else str(df_idx.iat[i, j])
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                if col in DATE_COLS:
                    st = str(df_idx.iloc[i].get(f"{col}_STATUS", ""))
                    _paint_status(it, st)
                self.tabela.setItem(i, j, it)
        self.tabela.resizeColumnsToContents()
        self.tabela.resizeRowsToContents()

    def exportar_excel(self):
        try:
            self.df_filtrado.to_excel("relatorio_filtrado.xlsx", index=False)
            QMessageBox.information(self,"Exportado","relatorio_filtrado.xlsx criado.")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e))

    def recarregar(self):
        if not self.path or not os.path.exists(self.path):
            QMessageBox.warning(self,"Aviso","Arquivo não encontrado.")
            return
        self.carregar_dados(self.path)






class GeralMultasView(QWidget):
    def __init__(self, parent_for_edit=None):
        super().__init__()
        self.parent_for_edit = parent_for_edit
        fm = QFontMetrics(self.font())
        self.max_pix = fm.horizontalAdvance("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        df = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("")
        self.df_original = ensure_status_cols(df, csv_path=GERAL_MULTAS_CSV)
        self.df_filtrado = self.df_original.copy()
        self.cols_show = [c for c in self.df_original.columns if not c.endswith("_STATUS")]
        root = QVBoxLayout(self)
        header_card = QFrame(); header_card.setObjectName("card"); apply_shadow(header_card, radius=18)
        hv = QVBoxLayout(header_card)
        self.filtros_layout = QHBoxLayout()
        self.filtros = {}; self.text_filtros = {}
        for coluna in self.cols_show:
            box = QVBoxLayout()
            label = QLabel(coluna); label.setObjectName("colTitle"); label.setWordWrap(True); label.setMaximumWidth(self.max_pix)
            combo = QComboBox()
            combo.addItems(["Todos","Excluir vazios","Somente vazios"] + sorted(self.df_original[coluna].dropna().astype(str).unique()))
            combo.setMaximumWidth(self.max_pix)
            combo.currentTextChanged.connect(self.atualizar_filtro)
            entrada = QLineEdit(); entrada.setPlaceholderText(f"Filtrar {coluna}..."); entrada.setMaximumWidth(self.max_pix)
            entrada.textChanged.connect(self.atualizar_filtro)
            self.filtros[coluna]=combo; self.text_filtros[coluna]=entrada
            box.addWidget(label); box.addWidget(combo); box.addWidget(entrada)
            self.filtros_layout.addLayout(box)
        hv.addLayout(self.filtros_layout)
        root.addWidget(header_card)
        table_card = QFrame(); table_card.setObjectName("glass"); apply_shadow(table_card, radius=18, blur=60, color=QColor(0,0,0,80))
        tv = QVBoxLayout(table_card)
        self.tabela = QTableWidget()
        self.tabela.setAlternatingRowColors(True)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.setSortingEnabled(True)
        self.tabela.horizontalHeader().setSortIndicatorShown(True)
        self.tabela.cellDoubleClicked.connect(self.on_double_click)
        tv.addWidget(self.tabela)
        buttons = QHBoxLayout()
        btn_visao = QPushButton("Visão Geral"); btn_visao.clicked.connect(self.mostrar_visao)
        btn_limpar = QPushButton("Limpar filtros"); btn_limpar.clicked.connect(self.limpar_filtros)
        btn_inserir = QPushButton("Inserir"); btn_inserir.clicked.connect(lambda: self.parent_for_edit.inserir())
        btn_editar = QPushButton("Editar"); btn_editar.clicked.connect(lambda: self.parent_for_edit.editar())
        btn_excluir = QPushButton("Excluir"); btn_excluir.setObjectName("danger"); btn_excluir.clicked.connect(lambda: self.parent_for_edit.excluir())
        btn_fluig = QPushButton("CONFERIR FLUIG"); btn_fluig.clicked.connect(lambda: self.parent_for_edit.conferir_fluig())
        btn_past = QPushButton("FASE PASTORES"); btn_past.clicked.connect(lambda: self.parent_for_edit.fase_pastores())
        btn_export = QPushButton("Exportar Excel"); btn_export.clicked.connect(self.exportar_excel)
        buttons.addWidget(btn_visao); buttons.addWidget(btn_limpar); buttons.addWidget(btn_inserir); buttons.addWidget(btn_editar); buttons.addWidget(btn_excluir); buttons.addWidget(btn_fluig); buttons.addWidget(btn_past); buttons.addStretch(1); buttons.addWidget(btn_export)
        tv.addLayout(buttons)
        root.addWidget(table_card)
        self.preencher_tabela(self.df_filtrado)

    def recarregar(self):
        df = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("")
        self.df_original = ensure_status_cols(df, csv_path=GERAL_MULTAS_CSV)
        self.df_filtrado = self.df_original.copy()
        self.cols_show = [c for c in self.df_original.columns if not c.endswith("_STATUS")]
        self.atualizar_filtro()

    def mostrar_visao(self):
        dlg = SummaryDialog(self.df_filtrado[self.cols_show])
        dlg.exec()

    def limpar_filtros(self):
        for combo in self.filtros.values():
            combo.blockSignals(True); combo.setCurrentIndex(0); combo.blockSignals(False)
        for entrada in self.text_filtros.values():
            entrada.blockSignals(True); entrada.clear(); entrada.blockSignals(False)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()
        for coluna in self.cols_show:
            sel = self.filtros[coluna].currentText()
            txt = self.text_filtros[coluna].text().strip().lower()
            if sel == "Excluir vazios":
                df = df[df[coluna].astype(str)!=""]
            elif sel == "Somente vazios":
                df = df[df[coluna].astype(str)==""] 
            elif sel != "Todos":
                df = df[df[coluna].astype(str)==sel]
            if txt:
                termos = txt.split()
                df = df[df[coluna].astype(str).str.lower().apply(lambda x: all(re.search(re.escape(t), x) for t in termos))]
        self.df_filtrado = df
        for col in self.cols_show:
            combo = self.filtros[col]; current = combo.currentText()
            combo.blockSignals(True); combo.clear()
            items = ["Todos","Excluir vazios","Somente vazios"] + sorted(self.df_filtrado[col].dropna().astype(str).unique())
            combo.addItems(items); combo.setCurrentText(current if current in items else "Todos"); combo.blockSignals(False)
        self.preencher_tabela(self.df_filtrado)

    def preencher_tabela(self, df):
        show = df[self.cols_show].reset_index(drop=True)
        df_idx = df.reset_index(drop=True)
        self.tabela.clear()
        self.tabela.setColumnCount(len(show.columns))
        self.tabela.setRowCount(len(show))
        self.tabela.setHorizontalHeaderLabels([str(c) for c in show.columns])
        for i in range(len(show)):
            for j,col in enumerate(show.columns):
                val = "" if pd.isna(show.iat[i,j]) else str(show.iat[i,j])
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                if col in DATE_COLS:
                    st = str(df_idx.iloc[i].get(f"{col}_STATUS",""))
                    _paint_status(it, st)
                self.tabela.setItem(i,j,it)
        self.tabela.resizeColumnsToContents()
        self.tabela.resizeRowsToContents()

    def exportar_excel(self):
        try:
            self.df_filtrado[self.cols_show].to_excel("geral_multas_filtrado.xlsx", index=False)
            QMessageBox.information(self,"Exportado","geral_multas_filtrado.xlsx criado.")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e))

    def on_double_click(self, row, col):
        if self.parent_for_edit is None:
            return
        dfv = self.df_filtrado.reset_index(drop=True)
        key = dfv.iloc[row].get("FLUIG","")
        if not key:
            return
        self.parent_for_edit.editar_with_key(key)





class InfraMultasWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Infrações e Multas")
        self.resize(1240, 820)
        lay = QVBoxLayout(self)
        self.view_geral = GeralMultasView(self)
        lay.addWidget(self.view_geral)
        self.watcher = QFileSystemWatcher()
        if os.path.exists(GERAL_MULTAS_CSV):
            self.watcher.addPath(GERAL_MULTAS_CSV)
        self.watcher.fileChanged.connect(self._csv_changed)

    def _csv_changed(self, path):
        if not os.path.exists(path):
            QTimer.singleShot(500, lambda: self._readd_watch(path))
            return
        QTimer.singleShot(500, self.reload_geral)

    def _readd_watch(self, path):
        if os.path.exists(path):
            self.watcher.addPath(path)
        self.reload_geral()

    def reload_geral(self):
        self.view_geral.recarregar()

    def conferir_fluig(self):
        try:
            detalhamento_path = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\Notificações de Multas - Detalhamento.xlsx"
            df_det = pd.read_excel(detalhamento_path, dtype=str).fillna("")
            if df_det.empty or len(df_det.columns)<2:
                QMessageBox.warning(self,"Aviso","Planilha inválida."); return
            status_col = next((c for c in df_det.columns if c.strip().lower()=="status"), df_det.columns[1])
            mask_aberta = df_det[status_col].astype(str).str.strip().str.lower().eq("aberta")
            df_open = df_det[mask_aberta].copy()
            if "Nº Fluig" in df_open.columns:
                fcol = "Nº Fluig"
            else:
                fcol = next((c for c in df_open.columns if "fluig" in c.lower()), None)
            if not fcol:
                QMessageBox.warning(self,"Aviso","Coluna de Fluig não encontrada."); return
            df_csv = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
            fluig_det = set(df_open[fcol].astype(str).str.strip())
            fluig_csv = set(df_csv["FLUIG"].astype(str).str.strip()) if "FLUIG" in df_csv.columns else set()
            no_csv_codes = sorted([c for c in fluig_det if c and c not in fluig_csv])
            no_det_codes = sorted([c for c in fluig_csv if c and c not in fluig_det])
            left_cols = [fcol] + [c for c in ["Placa","Nome","AIT","Data Limite","Data Infração","Status"] if c in df_open.columns]
            df_left = df_open[df_open[fcol].astype(str).str.strip().isin(no_csv_codes)][left_cols].copy()
            df_left.rename(columns={fcol:"Nº Fluig"}, inplace=True)
            right_cols = [c for c in ["FLUIG","PLACA","INFRATOR","NOTIFICACAO","ANO","MES"] if c in df_csv.columns]
            df_right = df_csv[df_csv["FLUIG"].astype(str).str.strip().isin(no_det_codes)][right_cols].copy()
            dlg = ConferirFluigDialog(self, df_left, df_right)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e))

    def inserir(self, prefill_fluig=None):
        dlg = InserirDialog(self, prefill_fluig)
        dlg.exec()
        self.reload_geral()

    def editar(self):
        dlg = EditarDialog(self)
        dlg.exec()
        self.reload_geral()

    def editar_with_key(self, key):
        dlg = EditarDialog(self)
        dlg.le_key.setText(str(key))
        dlg.load_record()
        dlg.exec()
        self.reload_geral()

    def excluir(self):
        dlg = ExcluirDialog(self)
        dlg.exec()
        self.reload_geral()

    def fase_pastores(self):
        try:
            dfp = load_fase_pastores()
            if dfp.empty:
                QMessageBox.warning(self,"Aviso","Planilha Fase Pastores não encontrada ou inválida.")
                return
            df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=None)
            idx = {str(f).strip(): i for i,f in enumerate(df.get("FLUIG", pd.Series([], dtype=str)).astype(str))}
            changed = False
            for _, r in dfp.iterrows():
                f = str(r["FLUIG"]).strip()
                tipo = str(r["TIPO"]).upper()
                data = str(r["DATA_PASTORES"]).strip()
                if not f or f not in idx:
                    continue
                if "PASTOR" not in tipo or not data:
                    continue
                qd = _parse_dt_any(data)
                if not qd.isValid():
                    continue
                i = idx[f]
                df.at[i, "SGU"] = qd.toString(DATE_FORMAT)
                df.at[i, "SGU_STATUS"] = "Pago"
                changed = True
            if changed:
                df.to_csv(GERAL_MULTAS_CSV, index=False)
                QMessageBox.information(self,"Sucesso","Atualizado.")
            else:
                QMessageBox.information(self,"Sucesso","Nada para atualizar.")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e))
        self.reload_geral()




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
        flags = Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Login | Gestão de Frota")
        self.resize(480, 340)
        wrap = QFrame(self); wrap.setObjectName("glass"); wrap.setGeometry(0,0,480,340); apply_shadow(wrap, radius=20, blur=60, color=QColor(0,0,0,60))
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
        self.main = MainWindow(perms if perms!='todos' else 'todos')
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
        central = QWidget(); cv = QVBoxLayout(central); cv.setContentsMargins(18,18,18,18)
        cv.addWidget(self.tab_widget)
        self.setCentralWidget(central)
        home = QWidget()
        hv = QVBoxLayout(home)
        title_card = QFrame(); title_card.setObjectName("glass"); apply_shadow(title_card, radius=20, blur=60, color=QColor(0,0,0,60))
        tv = QVBoxLayout(title_card); tv.setContentsMargins(24,24,24,24)
        t = QLabel("Gestão de Frota"); t.setAlignment(Qt.AlignmentFlag.AlignCenter); t.setFont(QFont("Arial",28, weight=QFont.Weight.Bold))
        tv.addWidget(t)
        hv.addWidget(title_card)
        grid_card = QFrame(); grid_card.setObjectName("card"); apply_shadow(grid_card, radius=18)
        gv = QGridLayout(grid_card); gv.setContentsMargins(18,18,18,18)
        modules = MODULES if perms=='todos' else [m for m in MODULES if m in perms]
        for i,mod in enumerate(modules):
            b = QPushButton(mod)
            b.setMinimumHeight(64)
            b.setFont(QFont("Arial",16, weight=QFont.Weight.Bold))
            b.clicked.connect(lambda _, m=mod: self.open_module(m))
            gv.addWidget(b, i//2, i%2)
        hv.addWidget(grid_card)
        bar = QHBoxLayout()
        out = QPushButton("Sair"); out.setObjectName("danger"); out.setMinimumHeight(44); out.clicked.connect(self.logout)
        bell = QPushButton("Alertas"); bell.clicked.connect(self.show_alertas)
        bar.addWidget(bell); bar.addStretch(1); bar.addWidget(out)
        hv.addLayout(bar)
        self.tab_widget.addTab(home, "Início")

    def show_alertas(self):
        if not os.path.exists(GERAL_MULTAS_CSV):
            QMessageBox.warning(self,"Aviso","GERAL_MULTAS.csv não encontrado."); return
        df = ensure_status_cols(pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna(""), csv_path=GERAL_MULTAS_CSV)
        linhas = []
        for i in range(len(df)):
            for col in DATE_COLS:
                st = str(df.at[i, f"{col}_STATUS"]) if f"{col}_STATUS" in df.columns else ""
                if st in ("Pendente","Vencido"):
                    linhas.append([
                        str(df.at[i,"FLUIG"]) if "FLUIG" in df.columns else "",
                        str(df.at[i,"INFRATOR"]) if "INFRATOR" in df.columns else "",
                        str(df.at[i,"PLACA"]) if "PLACA" in df.columns else "",
                        col,
                        str(df.at[i,col]),
                        st
                    ])
        dlg = AlertasDialog(self, linhas)
        dlg.exec()

    def close_tab(self, index):
        if index==0: return
        w = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        w.deleteLater()

    def open_module(self, module):
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx)==module:
                self.tab_widget.setCurrentIndex(idx); return
        if module=="Infrações e Multas":
            w = InfraMultasWindow()

        elif module=="Relatórios":
            file, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", "", "Planilhas (*.xlsx *.xls *.csv)")
            if not file:
                return
            w = RelatorioWindow(file)

        elif module=="Combustível":
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
    ensure_base_csv()
    app = QApplication(sys.argv)
    app.setStyleSheet("""
    QWidget { background: #FFFFFF; color: #0B2A4A; font-size: 14px; }
    QFrame#card { background: #ffffff; border: 1 x solid #214D80; border-radius: 18px; }
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
    QScrollBar:vertical { background: transparent; width: 10px; margin: 0; border-radius: 5px; }
    QScrollBar::handle:vertical { background: #123C69; min-height: 20px; border-radius: 5px; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
    """)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()