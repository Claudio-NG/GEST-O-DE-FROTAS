import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame, QLineEdit, QSplitter, QGroupBox, QWidget
from constants import STATUS_COLOR
from utils import apply_shadow, _paint_status

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
                from PyQt6.QtWidgets import QTableWidgetItem
                it = QTableWidgetItem(val)
                if c==6 and val in STATUS_COLOR:
                    _paint_status(it, val)
                t.setItem(r,c,it)
        t.resizeColumnsToContents(); t.resizeRowsToContents()
        cv.addWidget(t)
        v.addWidget(card)
        close = QPushButton("Fechar"); close.clicked.connect(self.accept)
        v.addWidget(close)
