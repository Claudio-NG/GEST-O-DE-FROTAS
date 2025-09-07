from __future__ import annotations

import os
import datetime as dt
from typing import Dict, List, Optional, Tuple

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QSizePolicy, QGridLayout, QSpacerItem, QProgressBar, QFileDialog,
    QInputDialog
)

from utils import (
    THEME, apply_shadow, load_df, ensure_datetime, apply_period, prepare_status_hex,
    run_tasks, EVENT_BUS, quick_search, export_to_csv, export_to_excel,
    GlobalFilterBar, CheckableComboBox, normalize_text, _paint_status
)
from main_window import BaseView


class RelatoriosView(BaseView):
    def __init__(self):
        super().__init__("Relatórios")
        self._tab_data: Dict[int, Dict[str, object]] = {}
        self._search = GlobalFilterBar("Busca global:")
        self._cmb_cols_filter = CheckableComboBox([])
        self._cmb_status = CheckableComboBox(["ABERTA","VENCIDA","PAGA","CANCELADA","EM ANALISE","EM RECURSO"])
        self._btn_export_csv = QPushButton("Exportar CSV")
        self._btn_export_xlsx = QPushButton("Exportar XLSX")
        self._btn_novo = QPushButton("Novo Relatório")
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()
        self._build_advanced()
        self._build_tabs()
        self.header.btn_aplicar.setText("Novo Relatório")
        self.header.btn_aplicar.clicked.disconnect()
        self.header.btn_aplicar.clicked.connect(self._novo_relatorio)
        self._btn_novo.clicked.connect(self._novo_relatorio)
        self._search.changed.connect(lambda *_: self._apply_filters_current())
        self._cmb_cols_filter.changed.connect(lambda *_: self._apply_filters_current())
        self._cmb_status.changed.connect(lambda *_: self._apply_filters_current())
        self._btn_export_csv.clicked.connect(self._export_csv_current)
        self._btn_export_xlsx.clicked.connect(self._export_xlsx_current)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _build_advanced(self):
        wrap = QFrame()
        g = QGridLayout(wrap); g.setContentsMargins(0,0,0,0); g.setHorizontalSpacing(8)
        r = 0
        g.addWidget(QLabel("Status:"), r, 0, 1, 1); g.addWidget(self._cmb_status, r, 1, 1, 1); r += 1
        g.addWidget(QLabel("Filtrar por colunas (texto contém):"), r, 0, 1, 1); g.addWidget(self._cmb_cols_filter, r, 1, 1, 2); r += 1
        g.addWidget(QLabel("Busca:"), r, 0, 1, 1); g.addWidget(self._search, r, 1, 1, 2); r += 1
        actions = QHBoxLayout()
        actions.addWidget(self._btn_novo)
        actions.addStretch(1)
        actions.addWidget(self._btn_export_csv)
        actions.addWidget(self._btn_export_xlsx)
        g.addLayout(actions, r, 0, 1, 3); r += 1
        self.set_advanced_widget(wrap)

    def _build_tabs(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4)
        v.addWidget(self._progress)
        self.tabs.addTab(w, "Consolidado")
        self.tabs.setTabEnabled(0, False)

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.horizontalHeader().setSortIndicatorShown(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        return t

    def _novo_relatorio(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Escolher planilha", "", "Excel (*.xlsx *.xls);;CSV (*.csv)")
        if not paths:
            return
        for path in paths:
            self._load_and_add_tab(path)

    def _load_and_add_tab(self, path: str):
        self._progress.show()
        self.set_footer_stats("Carregando…", "", "")
        sheet_name = None
        ext = os.path.splitext(path)[1].lower()
        if ext in (".xlsx", ".xls"):
            try:
                xl = pd.ExcelFile(path)
                if len(xl.sheet_names) > 1:
                    sheet_name, ok = QInputDialog.getItem(self, "Selecionar aba", "Aba:", xl.sheet_names, 0, False)
                    if not ok:
                        self._progress.hide(); return
                else:
                    sheet_name = xl.sheet_names[0]
            except Exception:
                sheet_name = None
        def _load():
            df = load_df(path, dtype=str, normalize_cols=False, sheet_name=sheet_name) if sheet_name else load_df(path, dtype=str, normalize_cols=False)
            for c in list(df.columns):
                if "DATA" in str(c).upper():
                    try:
                        df[c] = ensure_datetime(df[c])
                    except Exception:
                        pass
            df = prepare_status_hex(df, status_col="STATUS")
            return df
        res = run_tasks({"df": _load}, max_workers=1)
        df = res.get("df", pd.DataFrame())
        if isinstance(df, Exception) or df is None:
            self._progress.hide(); return
        title = os.path.basename(path)
        if sheet_name:
            title = f"{title} • {sheet_name}"
        key = f"{path}::{sheet_name or ''}"
        tbl = self._make_table()
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4)
        v.addWidget(tbl, 1)
        idx = self.tabs.addTab(w, title)
        self._tab_data[idx] = {"path": path, "sheet": sheet_name, "df": df, "df_view": pd.DataFrame(), "tbl": tbl}
        self.tabs.setCurrentIndex(idx)
        self._feed_filters_from_df(df)
        self._apply_filters_to_df(idx)
        self._progress.hide()

    def _on_tab_changed(self, idx: int):
        if idx in self._tab_data:
            df = self._tab_data[idx]["df"]
            self._feed_filters_from_df(df)
            self._apply_filters_to_df(idx)

    def _pick_date_col(self, cols: List[str]) -> Optional[str]:
        pref = ["DATA", "EMISSAO", "LANÇAMENTO", "LANCAMENTO", "DATA REFERENCIA", "DATA REFERÊNCIA"]
        candidates = [c for c in cols if any(k in str(c).upper() for k in pref)]
        return candidates[0] if candidates else None

    def _feed_filters_from_df(self, df: pd.DataFrame):
        if df is None or df.empty:
            self._cmb_cols_filter.set_values([])
            return
        cols = [c for c in df.columns if df[c].dtype == object and str(c).upper() not in ("_STATUS_COLOR_HEX_")]
        self._cmb_cols_filter.set_values(cols)

    def _apply_filters_current(self):
        idx = self.tabs.currentIndex()
        if idx not in self._tab_data:
            return
        self._apply_filters_to_df(idx)

    def _apply_filters_to_df(self, idx: int):
        key, d1, d2 = self.get_period()
        info = self._tab_data[idx]
        df = info["df"].copy()
        date_col = self._pick_date_col([str(c) for c in df.columns])
        if date_col:
            df = apply_period(df, date_col, d1, d2)
        sel_status = set(s.upper() for s in self._cmb_status.selected_values())
        if sel_status and "STATUS" in df.columns:
            df = df[df["STATUS"].astype(str).str.upper().isin(sel_status)]
        terms = self._search.values()
        if terms:
            df = self._search_all_cols(df, terms)
        info["df_view"] = df.reset_index(drop=True)
        self._fill_table(info["tbl"], info["df_view"])
        total = len(info["df"])
        vis = len(info["df_view"])
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

    def _fill_table(self, tbl: QTableWidget, df: pd.DataFrame):
        tbl.clear()
        if df is None or df.empty:
            tbl.setRowCount(0); tbl.setColumnCount(0)
            return
        cols = [str(c) for c in df.columns]
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setRowCount(len(df))
        status_idx = None
        for j, c in enumerate(cols):
            if c.upper() == "STATUS":
                status_idx = j
                break
        for i in range(len(df)):
            row_status = None
            for j, c in enumerate(cols):
                val = df.iat[i, j]
                it = QTableWidgetItem("" if pd.isna(val) else str(val))
                it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                tbl.setItem(i, j, it)
                if status_idx is not None and j == status_idx:
                    row_status = str(val).upper().strip()
                    _paint_status(it, row_status)
            if row_status and status_idx is not None:
                for j in range(len(cols)):
                    if j == status_idx:
                        continue
                    it2 = tbl.item(i, j)
                    if it2:
                        _paint_status(it2, row_status)
        tbl.resizeColumnsToContents()
        tbl.resizeRowsToContents()

    def _export_csv_current(self):
        idx = self.tabs.currentIndex()
        if idx not in self._tab_data:
            return
        df = self._tab_data[idx]["df_view"]
        if df is None or len(df) == 0:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", "relatorio.csv", "CSV (*.csv)")
        if not path:
            return
        export_to_csv(df, path)

    def _export_xlsx_current(self):
        idx = self.tabs.currentIndex()
        if idx not in self._tab_data:
            return
        df = self._tab_data[idx]["df_view"]
        if df is None or len(df) == 0:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Excel", "relatorio.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        export_to_excel(df, path, sheet_name="Relatorio")


def build_relatorios_view() -> RelatoriosView:
    return RelatoriosView()