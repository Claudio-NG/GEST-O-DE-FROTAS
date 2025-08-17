import os, re
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFontMetrics
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton, QScrollArea, QGridLayout, QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSizePolicy
from constants import DATE_COLS
from utils import apply_shadow, ensure_status_cols, _paint_status
from dialogs import SummaryDialog

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
        self.carregar_dados(self.path)
        self.showMaximized()

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
