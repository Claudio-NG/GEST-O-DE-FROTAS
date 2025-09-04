from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Tuple

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QSizePolicy, QGridLayout, QSpacerItem, QProgressBar, QFileDialog
)

from utils import (
    THEME, apply_shadow, load_df, ensure_datetime, apply_period, prepare_status_hex,
    run_tasks, EVENT_BUS, quick_search, export_to_csv, export_to_excel,
    GlobalFilterBar, CheckableComboBox, normalize_text
)
from main_window import BaseView

try:
    from gestao_frota_single import (
        DETALHAMENTO_PATH,
        EXTRATO_GERAL_PATH,
        EXTRATO_SIMPLIFICADO_PATH,
        CONDUTOR_IDENTIFICADO_PATH,
        GERAL_MULTAS_CSV,
    )
except Exception:
    DETALHAMENTO_PATH = "Notificações de Multas - Detalhamento.xlsx"
    EXTRATO_GERAL_PATH = "ExtratoGeral.xlsx"
    EXTRATO_SIMPLIFICADO_PATH = "ExtratoSimplificado.xlsx"
    CONDUTOR_IDENTIFICADO_PATH = "Notificações de Multas - Condutor Identificado.xlsx"
    GERAL_MULTAS_CSV = "GERAL_MULTAS.csv"


class RelatoriosView(BaseView):
    def __init__(self):
        super().__init__("Relatórios")
        self._df_sources: Dict[str, pd.DataFrame] = {}
        self._df_merged: pd.DataFrame = pd.DataFrame()

        self._search = GlobalFilterBar("Busca global:")
        self._cmb_cols_filter = CheckableComboBox([])
        self._cmb_status = CheckableComboBox(["ABERTA","VENCIDA","PAGA","CANCELADA","EM ANALISE","EM RECURSO"])

        self._btn_export_csv = QPushButton("Exportar CSV")
        self._btn_export_xlsx = QPushButton("Exportar XLSX")

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()

        self._build_advanced()
        self._build_tabs()

        self.header.btn_aplicar.clicked.connect(self._generate)
        self._search.changed.connect(lambda *_: self._apply_filters())
        self._cmb_cols_filter.changed.connect(lambda *_: self._apply_filters())
        self._cmb_status.changed.connect(lambda *_: self._apply_filters())
        self._btn_export_csv.clicked.connect(self._export_csv)
        self._btn_export_xlsx.clicked.connect(self._export_xlsx)

        QTimer.singleShot(60, self._generate)

    # ---------- UI ----------

    def _build_advanced(self):
        wrap = QFrame()
        g = QGridLayout(wrap); g.setContentsMargins(0,0,0,0); g.setHorizontalSpacing(8)
        r = 0

        g.addWidget(QLabel("Status:"), r, 0, 1, 1); g.addWidget(self._cmb_status, r, 1, 1, 1); r += 1
        g.addWidget(QLabel("Filtrar por colunas (texto contém):"), r, 0, 1, 1); g.addWidget(self._cmb_cols_filter, r, 1, 1, 2); r += 1
        g.addWidget(QLabel("Busca:"), r, 0, 1, 1); g.addWidget(self._search, r, 1, 1, 2); r += 1

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self._btn_export_csv)
        actions.addWidget(self._btn_export_xlsx)
        g.addLayout(actions, r, 0, 1, 3); r += 1

        self.set_advanced_widget(wrap)

    def _build_tabs(self):
        self._tab_consolidado = self._make_table()
        self.add_unique_tab("consolidado", "Consolidado", self._wrap_table(self._tab_consolidado))

    def _wrap_table(self, tbl: QTableWidget) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4)
        v.addWidget(self._progress)
        v.addWidget(tbl, 1)
        return w

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.horizontalHeader().setSortIndicatorShown(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        return t

    # ---------- DADOS / THREADS ----------

    def _generate(self):
        self._progress.show()
        self.set_footer_stats("Gerando…", "", "")

        key, d1, d2 = self.get_period()

        def load_det():
            df = load_df(DETALHAMENTO_PATH, dtype=str, normalize_cols=False)
            for c in df.columns:
                if "DATA" in str(c).upper():
                    df[c] = ensure_datetime(df[c])
            return df

        def load_extrato_geral():
            df = load_df(EXTRATO_GERAL_PATH, dtype=str, normalize_cols=False)
            for c in df.columns:
                if "DATA" in str(c).upper():
                    df[c] = ensure_datetime(df[c])
            return df

        def load_extrato_simplificado():
            df = load_df(EXTRATO_SIMPLIFICADO_PATH, dtype=str, normalize_cols=False)
            for c in df.columns:
                if "DATA" in str(c).upper():
                    df[c] = ensure_datetime(df[c])
            return df

        def load_condutor_identificado():
            try:
                df = load_df(CONDUTOR_IDENTIFICADO_PATH, dtype=str, normalize_cols=False)
                for c in df.columns:
                    if "DATA" in str(c).upper():
                        df[c] = ensure_datetime(df[c])
                return df
            except Exception:
                return pd.DataFrame()

        tasks = {
            "DETALHAMENTO": load_det,
            "EXTRATO_GERAL": load_extrato_geral,
            "EXTRATO_SIMPLIFICADO": load_extrato_simplificado,
            "CONDUTOR_IDENTIFICADO": load_condutor_identificado,
        }

        results: Dict[str, pd.DataFrame] = {}
        def on_result(name, res):
            results[name] = res

        run_tasks(tasks, max_workers=4, on_result=on_result)

        # período & status
        merged = []
        for name, df in results.items():
            if isinstance(df, Exception) or df is None or df.empty:
                continue
            cols_upper = [str(c) for c in df.columns]
            date_col = self._pick_date_col(cols_upper)
            if date_col:
                df = apply_period(df, date_col, d1, d2)
            df = prepare_status_hex(df, status_col="STATUS")
            df["FONTE"] = name
            merged.append(df)

        self._df_sources = results
        self._df_merged = pd.concat(merged, ignore_index=True, sort=False) if merged else pd.DataFrame()

        self._feed_filters_from_df(self._df_merged)
        self._apply_filters()
        self._progress.hide()

    def _pick_date_col(self, cols: List[str]) -> Optional[str]:
        pref = ["DATA", "DATA EMISSAO", "EMISSAO", "LANÇAMENTO", "LANCAMENTO", "DATA REFERENCIA", "DATA REFERÊNCIA"]
        candidates = [c for c in cols if any(k in str(c).upper() for k in pref)]
        return candidates[0] if candidates else None

    # ---------- FILTROS ----------

    def _feed_filters_from_df(self, df: pd.DataFrame):
        if df is None or df.empty:
            self._cmb_cols_filter.set_values([])
            return
        cols = [c for c in df.columns if df[c].dtype == object and str(c).upper() not in ("FONTE", "_STATUS_COLOR_HEX_")]
        self._cmb_cols_filter.set_values(cols)

    def _apply_filters(self):
        df = self._df_merged.copy()

        # Status
        sel_status = set(s.upper() for s in self._cmb_status.selected_values())
        if sel_status and "STATUS" in df.columns:
            df = df[df["STATUS"].astype(str).str.upper().isin(sel_status)]

        # Busca global (todas as colunas string)
        terms = self._search.values()
        if terms:
            df = self._search_all_cols(df, terms)

        self._fill_table(self._tab_consolidado, df)

        total = len(self._df_merged)
        vis = len(df)
        self.set_footer_stats(f"Total: {total}", f"Visíveis: {vis}", "")

    def _search_all_cols(self, df: pd.DataFrame, texts: List[str]) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        s_df = df.fillna("").astype(str)
        mask = pd.Series(True, index=s_df.index)
        for text in texts:
            q = normalize_text(text).lower()
            if not q:
                continue
            toks = [t for t in q.split(" ") if t]
            m_box = pd.Series(True, index=s_df.index)
            for tok in toks:
                m_tok = pd.Series(False, index=s_df.index)
                for c in s_df.columns:
                    m_tok |= s_df[c].str.lower().str.contains(tok, na=False)
                m_box &= m_tok
            mask &= m_box
        return df[mask].copy()

    # ---------- RENDER ----------

    def _fill_table(self, tbl: QTableWidget, df: pd.DataFrame):
        tbl.clear()
        if df is None or df.empty:
            tbl.setRowCount(0); tbl.setColumnCount(0)
            return

        cols = [str(c) for c in df.columns]
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setRowCount(len(df))

        for i in range(len(df)):
            for j, c in enumerate(cols):
                val = df.iat[i, j]
                it = QTableWidgetItem("" if pd.isna(val) else str(val))
                it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                tbl.setItem(i, j, it)

        tbl.resizeColumnsToContents()
        tbl.resizeRowsToContents()

    # ---------- EXPORT ----------

    def _export_csv(self):
        if self._tab_consolidado.rowCount() == 0:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", "relatorio.csv", "CSV (*.csv)")
        if not path:
            return
        df = self._grab_df_from_table(self._tab_consolidado)
        export_to_csv(df, path)

    def _export_xlsx(self):
        if self._tab_consolidado.rowCount() == 0:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Excel", "relatorio.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        df = self._grab_df_from_table(self._tab_consolidado)
        export_to_excel(df, path, sheet_name="Relatorio")

    def _grab_df_from_table(self, tbl: QTableWidget) -> pd.DataFrame:
        cols = [tbl.horizontalHeaderItem(j).text() for j in range(tbl.columnCount())]
        data = []
        for i in range(tbl.rowCount()):
            row = []
            for j in range(tbl.columnCount()):
                it = tbl.item(i, j)
                row.append("" if it is None else it.text())
            data.append(row)
        return pd.DataFrame(data, columns=cols)


def build_relatorios_view() -> RelatoriosView:
    return RelatoriosView()