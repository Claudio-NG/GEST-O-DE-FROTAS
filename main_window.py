import os, re
import pandas as pd

from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QTabWidget, QVBoxLayout, QFrame, QHBoxLayout,
    QLabel, QPushButton, QGridLayout, QLineEdit, QComboBox, QMessageBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QScrollArea,
    QDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from gestao_frota_single import (
    BaseTab, MODULES, DATE_FORMAT, DATE_COLS, STATUS_COLOR,
    cfg_get, cfg_set, cfg_all
)
from utils import apply_shadow, CheckableComboBox, ensure_status_cols, df_apply_global_texts
from multas import InfraMultasWindow
from relatorios import RelatorioWindow
from combustivel import CombustivelMenu, CombustivelWindow


def _collect_alertas(df):
    """
    Monta as linhas (FLUIG, INFRATOR, PLACA, ETAPA, DATA, STATUS)
    usando SOMENTE as colunas listadas em constants.DATE_COLS.
    """
    linhas = []
    if df.empty:
        return linhas
    use_cols = [c for c in DATE_COLS if c in df.columns]  # garante só as 3
    for _, row in df.iterrows():
        fluig = str(row.get("FLUIG", "")).strip()
        infr = str(row.get("INFRATOR", "") or row.get("NOME", "")).strip()
        placa = str(row.get("PLACA", "")).strip()
        for col in use_cols:
            dt = str(row.get(col, "")).strip()
            st = str(row.get(f"{col}_STATUS", "")).strip()
            if dt or st:
                linhas.append([fluig, infr, placa, col, dt, st])
    return linhas


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
        use_cols = [c for c in DATE_COLS if c in base.columns]  # só DATA INDICAÇÃO / BOLETO / SGU
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
                    st = val.strip()
                    if st in STATUS_COLOR:
                        bg = STATUS_COLOR[st]
                        it.setBackground(bg)
                        yiq = (bg.red()*299 + bg.green()*587 + bg.blue()*114)/1000
                        it.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))
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


class _AlertasDialog(QDialog):
    """
    Dialog de Alertas com tabela organizada e o padrão de filtros:
    - 1 campo de texto global (com botão +) que filtra em TODAS as colunas
    - por coluna: modo (Todos/Excluir vazios/Somente vazios) + multiseleção
    - cores de STATUS preservadas
    """
    def __init__(self, parent, df):
        super().__init__(parent)
        self.setWindowTitle("Alertas de Datas")
        self.resize(1100, 640)

        self.df_original = df.copy()
        # Reduz às colunas de interesse do alerta
        cols_fixas = ["FLUIG", "INFRATOR", "PLACA", "ETAPA", "DATA", "STATUS"]
        if not set(cols_fixas).issubset(self.df_original.columns):
            # Se vier a planilha bruta, montamos as linhas a partir de DATE_COLS
            rows = []
            use_cols = [c for c in DATE_COLS if c in self.df_original.columns]
            for _, row in self.df_original.iterrows():
                fluig = str(row.get("FLUIG", "")).strip()
                infr  = str(row.get("INFRATOR", "") or row.get("NOME", "")).strip()
                placa = str(row.get("PLACA", "")).strip()
                for col in use_cols:
                    dt = str(row.get(col, "")).strip()
                    st = str(row.get(f"{col}_STATUS", "")).strip()
                    if dt or st:
                        rows.append([fluig, infr, placa, col, dt, st])
            self.df_original = pd.DataFrame(rows, columns=cols_fixas)

        self.df_filtrado = self.df_original.copy()

        # ===== UI =====
        root = QVBoxLayout(self)

        # Card dos filtros (padrão)
        header = QFrame(); header.setObjectName("card"); apply_shadow(header, radius=18)
        hv = QVBoxLayout(header)

        # Filtro global com "+"
        row_global = QHBoxLayout()
        row_global.addWidget(QLabel("Filtro global:"))
        self.global_boxes = []
        def add_box():
            le = QLineEdit()
            le.setPlaceholderText("Digite para filtrar em todas as colunas…")
            le.textChanged.connect(self._apply_filters)
            row_global.addWidget(le, 1)
            self.global_boxes.append(le)
        add_box()
        btn_plus = QPushButton("+"); btn_plus.setFixedWidth(28); btn_plus.clicked.connect(add_box)
        row_global.addWidget(btn_plus)
        hv.addLayout(row_global)

        # Filtros por coluna (modo + multiseleção)
        from utils import CheckableComboBox  # já existe
        self.mode_filtros = {}
        self.multi_filtros = {}

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner = QWidget(); gl = QGridLayout(inner); gl.setContentsMargins(0,0,0,0); gl.setHorizontalSpacing(12); gl.setVerticalSpacing(8)
        cols = list(self.df_original.columns)

        for i, col in enumerate(cols):
            wrap = QFrame(); wv = QVBoxLayout(wrap)
            lab = QLabel(col); lab.setObjectName("colTitle"); wv.addWidget(lab)

            line = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos","Excluir vazios","Somente vazios"])
            mode.currentTextChanged.connect(self._apply_filters)
            ms = CheckableComboBox(self.df_original[col].dropna().astype(str).unique())
            ms.changed.connect(self._apply_filters)
            line.addWidget(mode); line.addWidget(ms)
            wv.addLayout(line)

            self.mode_filtros[col] = mode
            self.multi_filtros[col] = ms
            gl.addWidget(wrap, i//3, i%3)

        host = QWidget(); host.setLayout(gl)
        scroll.setWidget(host)
        hv.addWidget(scroll)
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

        # Botões
        bar = QHBoxLayout()
        btn_limpar = QPushButton("Limpar filtros"); btn_limpar.clicked.connect(self._limpar_filtros)
        btn_fechar = QPushButton("Fechar"); btn_fechar.clicked.connect(self.accept)
        bar.addWidget(btn_limpar); bar.addStretch(1); bar.addWidget(btn_fechar)
        tv.addLayout(bar)

        root.addWidget(table_card)

        self._apply_filters()

    def _limpar_filtros(self):
        for le in self.global_boxes:
            le.blockSignals(True); le.clear(); le.blockSignals(False)
        for mode in self.mode_filtros.values():
            mode.blockSignals(True); mode.setCurrentIndex(0); mode.blockSignals(False)
        for ms in self.multi_filtros.values():
            vals = [ms.itemText(i) for i in range(ms.count())]
            ms.set_values(vals)
        self._apply_filters()

    def _apply_filters(self):
        from utils import df_apply_global_texts
        df = self.df_original.copy()

        # Global (todas as colunas) — suporta múltiplas caixas se clicar +
        texts = [le.text() for le in self.global_boxes if le.text().strip()]
        df = df_apply_global_texts(df, texts)

        # Por coluna: modo + multiseleção
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
        self._fill_table()

    def _fill_table(self):
        headers = list(self.df_filtrado.columns)
        self.tabela.clear()
        self.tabela.setColumnCount(len(headers))
        self.tabela.setHorizontalHeaderLabels(headers)
        self.tabela.setRowCount(len(self.df_filtrado))

        for i, (_, r) in enumerate(self.df_filtrado.iterrows()):
            for j, col in enumerate(headers):
                val = "" if pd.isna(r[col]) else str(r[col])
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Pintar STATUS
                if col.upper() == "STATUS":
                    st = val.strip()
                    if st in STATUS_COLOR:
                        bg = STATUS_COLOR[st]
                        it.setBackground(bg)
                        yiq = (bg.red()*299 + bg.green()*587 + bg.blue()*114)/1000
                        it.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))
                self.tabela.setItem(i, j, it)

        self.tabela.resizeColumnsToContents()
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.resizeRowsToContents()



def _parse_dt(val):
    s = str(val).strip()
    if not s:
        return pd.NaT
    for fmt in ("%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%Y/%m/%d"):
        try:
            return pd.to_datetime(s, format=fmt, dayfirst=True, errors="raise")
        except:
            pass
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


def _parse_money(s):
    """
    Converte números em pt-BR para float:
    - "R$ 1.234,56" -> 1234.56
    - "6,590" -> 6.59
    - "1,234.56" (se vier assim) -> 1234.56
    """
    if s is None:
        return 0.0
    txt = str(s).strip()
    if not txt:
        return 0.0
    import re
    txt = re.sub(r"[^\d.,-]", "", txt)  # remove tudo menos dígito, vírgula, ponto, sinal

    # Sem separadores -> só número inteiro
    if ("," not in txt) and ("." not in txt):
        try:
            return float(txt)
        except:
            return 0.0

    if "," in txt and "." in txt:
        # Heurística: o último símbolo define o separador decimal
        last_comma = txt.rfind(",")
        last_dot = txt.rfind(".")
        if last_comma > last_dot:
            # vírgula é decimal; ponto é milhar
            txt = txt.replace(".", "").replace(",", ".")
        else:
            # ponto é decimal; vírgula é milhar
            txt = txt.replace(",", "")
    else:
        # só vírgula -> decimal BR
        if "," in txt:
            txt = txt.replace(",", ".")
        # só ponto -> já é decimal internacional

    try:
        return float(txt)
    except:
        return 0.0

# --- Cenário Geral de Multas (classe completa) ---
class CenarioGeralWindow(QWidget):
    """
    Cenário Geral de Multas:
      - Filtro TEXTO GLOBAL único (padronizado, + para mais caixas; vazias somem)
      - KPIs + abas (GERAL / MOTORISTA / PLACA)
      - Pontuação do motorista baseada no VALOR da multa (regra escalonada)
    Abre como QWidget (para ser usado dentro de uma aba).
    """
    # ========================= Helpers locais / fallback =========================
    @staticmethod
    def _to_num_brl(s):
        import re
        s = str(s)
        s = re.sub(r"[^\d,.-]","", s)
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):  # 1.234,56 -> 1234.56
                s = s.replace(".","").replace(",",".")
            else:                             # 1,234.56 -> 1234.56
                s = s.replace(",","")
        else:
            s = s.replace(",",".")
        try: return float(s)
        except: return 0.0

    @staticmethod
    def _first_col(df, *names):
        for n in names:
            if n in df.columns:
                return n
        return None

    # ========================= Construtor =========================
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cenário Geral de Multas")
        self.setMinimumSize(1024, 680)  # responsivo: base segura

        # imports tardios
        from gestao_frota_single import cfg_get
        from utils import apply_shadow, GlobalFilterBar, df_apply_global_texts
        self.cfg_get = cfg_get
        self.apply_shadow = apply_shadow
        self.GlobalFilterBar = GlobalFilterBar
        self.df_apply_global_texts = df_apply_global_texts

        # DATE_COLS (fallback se não existir)
        try:
            from gestao_frota_single import DATE_COLS  # ["DATA INDICAÇÃO","BOLETO","SGU"]
            self.DATE_COLS = DATE_COLS
        except Exception:
            self.DATE_COLS = ["DATA INDICAÇÃO", "BOLETO", "SGU"]

        self._load()
        self._build_ui()
        self._refresh_all()

    # ========================= Carga =========================
    def _load(self):
        import pandas as pd, os
        csv = self.cfg_get("geral_multas_csv")
        if not csv or not os.path.exists(csv):
            self.base = pd.DataFrame()
            return
        df = pd.read_csv(csv, dtype=str).fillna("")

        # garante colunas das 3 datas e *_STATUS
        for c in self.DATE_COLS:
            st = f"{c}_STATUS"
            if c not in df.columns: df[c] = ""
            if st not in df.columns: df[st] = ""

        # VALOR_NUM
        if "VALOR" not in df.columns:
            # tenta mapear "VALOR MULTA"
            vcands = [c for c in df.columns if c.upper().strip() in ("VALOR MULTA","VALOR_MULTA","VALOR DA MULTA")]
            if vcands:
                df["VALOR"] = df[vcands[0]]
            else:
                df["VALOR"] = ""
        df["VALOR_NUM"] = df["VALOR"].map(self._to_num_brl)

        # INFRATOR/NOME
        name_col = "INFRATOR" if "INFRATOR" in df.columns else ("NOME" if "NOME" in df.columns else None)
        if not name_col:
            df["INFRATOR"] = ""
            name_col = "INFRATOR"
        self.name_col = name_col

        self.base = df

    # ========================= UI =========================
    def _build_ui(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QColor
        from PyQt6.QtWidgets import (
            QVBoxLayout, QFrame, QLabel, QWidget, QHBoxLayout, QTableWidget,
            QHeaderView, QComboBox
        )

        root = QVBoxLayout(self)

        # header
        top = QFrame(); top.setObjectName("glass"); self.apply_shadow(top, radius=18, blur=60, color=QColor(0,0,0,60))
        tv = QVBoxLayout(top)
        t = QLabel("Cenário Geral de Multas"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setFont(QFont("Arial", 22, weight=QFont.Weight.Bold))
        tv.addWidget(t)
        root.addWidget(top)

        # filtro GLOBAL único
        self.global_bar = self.GlobalFilterBar("Filtro global:")
        self.global_bar.changed.connect(self._refresh_all)
        root.addWidget(self.global_bar)

        # Tabs
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)

        # GERAL (Top Motoristas)
        self.tab_geral = QWidget(); vg = QVBoxLayout(self.tab_geral)
        self.tbl_top_mot = QTableWidget(); self._prep(self.tbl_top_mot, ["Motorista","Qtd Multas","Valor Total (R$)","Pontuação"])
        vg.addWidget(QLabel("TOP Motoristas (por Valor e Pontuação)"))
        vg.addWidget(self.tbl_top_mot)
        self.tabs.addTab(self.tab_geral, "GERAL")

        # POR MOTORISTA (detalhe)
        self.tab_mot = QWidget(); vm = QVBoxLayout(self.tab_mot)
        row = QHBoxLayout()
        row.addWidget(QLabel("Motorista:"))
        self.cb_mot = QComboBox(); self.cb_mot.currentTextChanged.connect(self._refresh_motorista)
        row.addWidget(self.cb_mot); row.addStretch(1); vm.addLayout(row)
        self.tbl_mot = QTableWidget(); self._prep(self.tbl_mot, ["FLUIG","Placa","Órgão","Infração","Valor (R$)","Data"])
        vm.addWidget(self.tbl_mot)
        self.tabs.addTab(self.tab_mot, "MOTORISTA")

        # POR PLACA
        self.tab_placa = QWidget(); vp = QVBoxLayout(self.tab_placa)
        self.tbl_placa = QTableWidget(); self._prep(self.tbl_placa, ["Placa","Qtd Multas","Valor (R$)"])
        vp.addWidget(self.tbl_placa)
        self.tabs.addTab(self.tab_placa, "PLACA")

    def _prep(self, tbl, headers):
        from PyQt6.QtWidgets import QHeaderView
        tbl.setAlternatingRowColors(True)
        tbl.setSortingEnabled(True)
        tbl.horizontalHeader().setSortIndicatorShown(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)

    # ========================= Pontuação =========================
    @staticmethod
    def _score(valor):
        """
        Regra simples (ajuste se quiser):
          - R$ 0  ~ 199  -> 1 ponto
          - R$ 200 ~ 499 -> 2 pontos
          - R$ 500 ~ 999 -> 3 pontos
          - R$ 1000+     -> 5 pontos
        """
        v = float(valor or 0)
        if v >= 1000: return 5
        if v >= 500: return 3
        if v >= 200: return 2
        return 1

    # ========================= Refresh =========================
    def _refresh_all(self):
        if self.base is None or self.base.empty:
            return
        # filtro GLOBAL único
        texts = self.global_bar.values()
        df = self.df_apply_global_texts(self.base.copy(), texts)

        # TOP motoristas
        import pandas as pd
        g = df.groupby(self.name_col, dropna=False).agg(QT=("FLUIG","count"), VAL=("VALOR_NUM","sum")).reset_index()
        g["SCORE"] = g["VAL"].map(self._score)
        g = g.sort_values(["VAL","SCORE","QT"], ascending=False)
        rows = [[r[self.name_col], int(r["QT"]), f"{r['VAL']:.2f}", int(r["SCORE"])] for _, r in g.head(25).iterrows()]
        self._fill(self.tbl_top_mot, rows)

        # combo motoristas
        opts = [x for x in g[self.name_col].astype(str).tolist() if x]
        self.cb_mot.blockSignals(True); self.cb_mot.clear(); self.cb_mot.addItems(opts); self.cb_mot.blockSignals(False)
        self.df_f = df

        # placas
        p = df.groupby("PLACA", dropna=False).agg(QT=("FLUIG","count"), VAL=("VALOR_NUM","sum")).reset_index().sort_values(["VAL","QT"], ascending=False)
        self._fill(self.tbl_placa, [[r["PLACA"], int(r["QT"]), f"{r['VAL']:.2f}"] for _, r in p.iterrows()])

        # detalhe motorista (inicial)
        self._refresh_motorista()

    def _refresh_motorista(self):
        sel = (self.cb_mot.currentText() or "").strip()
        d = self.df_f if not sel else self.df_f[self.df_f[self.name_col].astype(str) == sel]
        if d is None or d.empty:
            self._fill(self.tbl_mot, []); return

        org = self._first_col(d, "ORGÃO","ORGAO","ÓRGÃO")
        inf = self._first_col(d, "TIPO INFRACAO","TIPO INFRAÇÃO","INFRACAO","INFRAÇÃO","NOTIFICACAO","NOTIFICAÇÃO")
        dtc = self._first_col(d, "DATA DA INFRACAO","DATA INFRAÇÃO","DATA","DATA INDICAÇÃO")
        if org is None: org = "ORGÃO" if "ORGÃO" in d.columns else (list(d.columns)[0] if len(d.columns) else "")
        if inf is None: inf = "INFRACAO" if "INFRACAO" in d.columns else (list(d.columns)[0] if len(d.columns) else "")
        if dtc is None: dtc = "DATA" if "DATA" in d.columns else (list(d.columns)[0] if len(d.columns) else "")

        rows = []
        for _, r in d.sort_values("VALOR_NUM", ascending=False).iterrows():
            rows.append([
                r.get("FLUIG",""), r.get("PLACA",""), r.get(org,""), r.get(inf,""),
                f"{float(r.get('VALOR_NUM',0)):.2f}", r.get(dtc,"")
            ])
        self._fill(self.tbl_mot, rows)

    def _fill(self, tbl, rows):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QTableWidgetItem
        tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem(str(v))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents()
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.resizeRowsToContents()



class MultasMenu(QWidget):
    def __init__(self, open_cb):
        super().__init__()
        v = QVBoxLayout(self)
        card = QFrame()
        card.setObjectName("card")
        apply_shadow(card, radius=18)
        gv = QGridLayout(card)
        gv.setContentsMargins(18, 18, 18, 18)
        b1 = QPushButton("Multas em Aberto")
        b2 = QPushButton("Cenário Geral")
        b1.setMinimumHeight(64)
        b2.setMinimumHeight(64)
        b1.setFont(QFont("Arial", 16, weight=QFont.Weight.Bold))
        b2.setFont(QFont("Arial", 16, weight=QFont.Weight.Bold))
        b1.clicked.connect(lambda: open_cb("Multas em Aberto", lambda: InfraMultasWindow()))
        b2.clicked.connect(lambda: open_cb("Cenário Geral", lambda: CenarioGeralWindow()))
        gv.addWidget(b1, 0, 0)
        gv.addWidget(b2, 0, 1)
        v.addWidget(card)

try:
    from main_window import AlertsTab  # quando AlertsTab está neste arquivo
except Exception:
    try:
        from .main_window import AlertsTab
    except Exception:
        pass


class MainWindow(QMainWindow):
    """
    Janela principal com:
    - Aba 'Início' contendo os botões grandes (Base, Infrações e Multas, Combustível, Relatórios, Alertas)
    - Abertura de cada módulo em novas abas (sem duplicar se já estiver aberto)
    """
    def __init__(self, user_email: str | None = None):
        super().__init__()
        self.setWindowTitle("GESTÃO DE FROTAS")
        self.resize(1280, 860)

        # ---- Área de abas ----
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # ---- Home / Início ----
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

        # Cartão com os botões grandes
        grid_card = QFrame(); grid_card.setObjectName("card"); apply_shadow(grid_card, radius=18)
        gv = QGridLayout(grid_card); gv.setContentsMargins(18, 18, 18, 18)

        buttons = [
            ("Base", self.open_base),
            ("Infrações e Multas", self.open_multas),
            ("Combustível", self.open_combustivel),
            ("Relatórios", self.open_relatorios),
            ("Alertas", self.mostrar_alertas),
        ]

        for i, (label, slot) in enumerate(buttons):
            b = QPushButton(label)
            b.setMinimumHeight(64)
            b.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            b.clicked.connect(slot)
            gv.addWidget(b, i // 2, i % 2)

        hv.addWidget(grid_card)

        # Barra inferior (logout)
        bar = QHBoxLayout()
        out = QPushButton("Sair"); out.setObjectName("danger")
        out.setMinimumHeight(44)
        out.clicked.connect(self.logout)
        bar.addStretch(1); bar.addWidget(out)
        hv.addLayout(bar)

        # Coloca a Home como primeira aba
        self.tab_widget.addTab(home, "Início")

    # ===== Helpers de abas =====
    def add_or_focus(self, title, factory):
        """Evita duplicar abas: foca se já existir; senão cria."""
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx) == title:
                self.tab_widget.setCurrentIndex(idx)
                return
        w = factory()
        self.tab_widget.addTab(w, title)
        self.tab_widget.setCurrentWidget(w)

    def close_tab(self, index):
        """Impede fechar a Home (índice 0); fecha as demais."""
        if index == 0:
            return
        w = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        w.deleteLater()

    # ===== Ações dos botões =====
    def open_base(self):
        # BaseTab costuma estar definido no seu projeto; ajuste o import se necessário
        try:
            from gestao_frota_single import BaseTab
            self.add_or_focus("Base", lambda: BaseTab())
        except Exception as e:
            QMessageBox.warning(self, "Base", f"Não foi possível abrir a Base.\n{e}")

    def open_multas(self):
        # Abre a janela principal de Multas (filtros + inserir/editar etc.)
        self.add_or_focus("Infrações e Multas", lambda: InfraMultasWindow())

    def open_combustivel(self):
        # Abre o módulo Combustível (agora com caminhos configuráveis)
        try:
            self.add_or_focus("Combustível", lambda: CombustivelWindow())
        except Exception as e:
            QMessageBox.warning(self, "Combustível", str(e))

    def open_relatorios(self):
        # Pede um arquivo (xlsx/xls/csv) e abre a janela de relatórios
        p, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", "", "Planilhas (*.xlsx *.xls *.csv)")
        if not p:
            return
        self.add_or_focus("Relatórios", lambda: RelatorioWindow(p))

    def mostrar_alertas(self):
        # Mostra a aba de Alertas (focada nas 3 datas oficiais)
        try:
            self.add_or_focus("Alertas", lambda: AlertsTab())
        except Exception as e:
            QMessageBox.warning(self, "Alertas", f"Não foi possível abrir Alertas.\n{e}")

    def logout(self):
        self.close()
