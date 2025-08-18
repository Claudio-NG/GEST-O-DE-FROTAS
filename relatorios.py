import os, re
import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget as QW, QGridLayout, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QColor, QFontMetrics
from utils import ensure_status_cols, apply_shadow, _paint_status, CheckableComboBox, SummaryDialog
from constants import DATE_COLS
from config import cfg_get

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
        self.mode_filtros = {}
        self.multi_filtros = {}
        self.text_filtros = {}

        root = QVBoxLayout(self)
        header_card = QFrame(); header_card.setObjectName("card"); apply_shadow(header_card, radius=18)
        top = QVBoxLayout(header_card)
        actions = QHBoxLayout()
        btn_recarregar = QPushButton("Recarregar"); btn_recarregar.clicked.connect(self.recarregar)
        btn_visao = QPushButton("Visão Geral"); btn_visao.clicked.connect(self.mostrar_visao)
        btn_limpar = QPushButton("Limpar filtros"); btn_limpar.clicked.connect(self.limpar_filtros)
        btn_export = QPushButton("Exportar Excel"); btn_export.clicked.connect(self.exportar_excel)
        actions.addWidget(btn_recarregar); actions.addWidget(btn_visao); actions.addWidget(btn_limpar); actions.addStretch(1); actions.addWidget(btn_export)
        top.addLayout(actions)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.filters_host = QW()
        self.filters_grid = QGridLayout(self.filters_host)
        self.filters_grid.setContentsMargins(12,12,12,12)
        self.filters_grid.setHorizontalSpacing(14)
        self.filters_grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.filters_host)
        top.addWidget(self.scroll)
        root.addWidget(header_card)

        table_card = QFrame(); table_card.setObjectName("glass"); apply_shadow(table_card, radius=18, blur=60, color=QColor(0,0,0,80))
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

    def _add_text_row(self, col, where):
        le = QLineEdit(); le.setPlaceholderText(f"Filtrar {col}..."); le.setMaximumWidth(self.max_pix)
        le.textChanged.connect(self.atualizar_filtro)
        self.text_filtros[col].append(le)
        where.addWidget(le)

    def _montar_filtros(self):
        while self.filters_grid.count():
            item = self.filters_grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.mode_filtros.clear()
        self.multi_filtros.clear()
        self.text_filtros.clear()

        cols = list(self.df_original.columns)
        for i, coluna in enumerate(cols):
            wrap = QFrame()
            v = QVBoxLayout(wrap)
            label = QLabel(coluna); label.setObjectName("colTitle"); label.setWordWrap(True); label.setMaximumWidth(self.max_pix)

            line1 = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos","Excluir vazios","Somente vazios"])
            ms = CheckableComboBox(self.df_original[coluna].dropna().astype(str).unique())
            mode.currentTextChanged.connect(self.atualizar_filtro)
            ms.changed.connect(self.atualizar_filtro)
            line1.addWidget(mode); line1.addWidget(ms)

            v.addWidget(label); v.addLayout(line1)

            line2 = QVBoxLayout()
            btn_plus = QPushButton("+"); btn_plus.setFixedWidth(28)
            row = QHBoxLayout(); row.addLayout(line2, 1); row.addWidget(btn_plus)
            v.addLayout(row)

            self.mode_filtros[coluna] = mode
            self.multi_filtros[coluna] = ms
            self.text_filtros[coluna] = []
            self._add_text_row(coluna, line2)
            btn_plus.clicked.connect(lambda _, c=coluna, l=line2: self._add_text_row(c, l))

            self.filters_grid.addWidget(wrap, i//3, i%3)

        spacer = QFrame(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.filters_grid.addWidget(spacer, (len(cols)+2)//3, 0, 1, 3)

    def mostrar_visao(self):
        dlg = SummaryDialog(self.df_filtrado)
        dlg.exec()

    def limpar_filtros(self):
        for mode in self.mode_filtros.values():
            mode.blockSignals(True); mode.setCurrentIndex(0); mode.blockSignals(False)
        for ms in self.multi_filtros.values():
            vals = [ms.itemText(i) for i in range(ms.count())]
            ms.set_values(vals)
        for col, arr in self.text_filtros.items():
            for i, le in enumerate(arr):
                le.blockSignals(True)
                if i == 0:
                    le.clear()
                else:
                    le.setParent(None)
            self.text_filtros[col] = [arr[0]]
            arr[0].blockSignals(False)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()
        for coluna in self.df_original.columns:
            mode = self.mode_filtros[coluna].currentText()
            if mode == "Excluir vazios":
                df = df[df[coluna].astype(str)!=""]
            elif mode == "Somente vazios":
                df = df[df[coluna].astype(str)==""] 
            sels = [s for s in self.multi_filtros[coluna].selected_values() if s]
            if sels:
                df = df[df[coluna].astype(str).isin(sels)]
            termos = []
            for le in self.text_filtros[coluna]:
                t = le.text().strip()
                if t:
                    termos.append(t)
            if termos:
                s = df[coluna].astype(str).str.lower()
                rgx = "|".join(re.escape(t.lower()) for t in termos)
                df = df[s.str.contains(rgx, na=False)]
        self.df_filtrado = df
        for col in self.df_original.columns:
            ms = self.multi_filtros[col]
            current_sel = ms.selected_values()
            ms.set_values(self.df_filtrado[col].dropna().astype(str).unique())
            if current_sel:
                for i in range(ms.count()):
                    if ms.itemText(i) in current_sel:
                        idx = ms.model().index(i, 0)
                        ms.model().setData(idx, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
                ms._update_text()
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
            QMessageBox.information(self, "Exportado", "relatorio_filtrado.xlsx criado.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def recarregar(self):
        if not self.path or not os.path.exists(self.path):
            QMessageBox.warning(self, "Aviso", "Arquivo não encontrado.")
            return
        self.carregar_dados(self.path)
