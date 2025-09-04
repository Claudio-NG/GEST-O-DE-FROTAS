from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Tuple
from utils import df_apply_global_texts

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QSizePolicy, QGridLayout, QTabWidget, QSpacerItem, QProgressBar
)

# --- infra compartilhada ---
from utils import (
    # tema / ui
    THEME, apply_shadow, STATUS_COLOR,
    # dados / filtros
    load_df, ensure_datetime, apply_period, prepare_status_hex, quick_search,
    # eventos / threads
    run_tasks, EVENT_BUS,
    # widgets auxiliares
    GlobalFilterBar, CheckableComboBox,
    # helpers de pintura
    # (_paint_status é usado para colorir células/linhas via QColor)
)
from utils import _paint_status  # import separado para manter compat com seu util antigo

# --- constantes do projeto (com fallbacks definidos no utils.py) ---
try:
    from gestao_frota_single import (
        GERAL_MULTAS_CSV,  # CSV consolidado
        DATE_COLS,         # colunas de data relevantes para multas
    )
except Exception:
    GERAL_MULTAS_CSV = "data/geral_multas.csv"
    DATE_COLS = ["DATA", "VALIDACAO NFF", "CONCLUSAO"]

# =========================
# Widgets locais (chips)
# =========================

class Chip(QPushButton):
    def __init__(self, text: str, color_hex: str):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color = color_hex
        self._apply_style()

    def _apply_style(self):
        base = f"""
        QPushButton {{
            background: rgba(0,0,0,0);
            color: {THEME['text']};
            border: 1px solid {self._color};
            border-radius: 10px;
            padding: 2px 8px;
        }}
        QPushButton:checked {{
            background: {self._color};
            color: #FFFFFF;
        }}
        """
        self.setStyleSheet(base)

# =========================
# MultasView (BaseView-like)
# =========================

from main_window import BaseView

class MultasView(BaseView):
    def __init__(self):
        super().__init__("Infrações e Multas")
        self._df_base: pd.DataFrame = pd.DataFrame()
        self._df_work: pd.DataFrame = pd.DataFrame()
        self._status_chips: Dict[str, Chip] = {}
        self._search = GlobalFilterBar("Filtro global:")
        self._status_combo = CheckableComboBox(["ABERTA","VENCIDA","PAGA","CANCELADA","EM ANALISE","EM RECURSO"])

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setRange(0, 0)
        self._progress.hide()

        self._build_advanced()
        self._build_tabs()

        self.periodChanged.connect(lambda *_: self._refresh())
        self.generateRequested.connect(self._refresh)

        QTimer.singleShot(50, self._refresh)

    # ------------- UI -------------

    def _build_advanced(self):
        wrap = QFrame()
        g = QGridLayout(wrap); g.setContentsMargins(0, 0, 0, 0); g.setHorizontalSpacing(8)
        r = 0

        # chips de status (cores do STATUS_COLOR / tema)
        chip_bar = QHBoxLayout()
        for key in ["ABERTA","VENCIDA","PAGA","CANCELADA","EM ANALISE","EM RECURSO"]:
            qcolor = STATUS_COLOR.get(key)
            hex_color = qcolor.name() if qcolor is not None else "#9E9E9E"
            chip = Chip(key, hex_color)
            chip.setChecked(key in ("ABERTA","VENCIDA"))
            chip.toggled.connect(lambda *_: self._apply_filters_to_work())
            self._status_chips[key] = chip
            chip_bar.addWidget(chip)
        chip_bar.addStretch(1)

        g.addWidget(QLabel("Status:"), r, 0, 1, 1); g.addLayout(chip_bar, r, 1, 1, 3); r += 1
        g.addWidget(QLabel("Seleção rápida de status:"), r, 0, 1, 1); g.addWidget(self._status_combo, r, 1, 1, 1); r += 1
        g.addWidget(QLabel("Busca:"), r, 0, 1, 1); g.addWidget(self._search, r, 1, 1, 3); r += 1
        g.addItem(QSpacerItem(8, 8, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), r, 0, 1, 1)

        self._status_combo.changed.connect(self._sync_chips_from_combo)
        self._search.changed.connect(lambda *_: self._apply_filters_to_work())

        self.set_advanced_widget(wrap)

    def _build_tabs(self):
        self.add_unique_tab("cenario", "Cenário Geral", self._build_tab_cenario())
        self.add_unique_tab("abertas", "Abertas", self._build_tab_abertas())
        self.add_unique_tab("historico", "Histórico", self._build_tab_historico())

    def _build_tab_cenario(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4); v.setSpacing(6)
        self._progress_cenario = QProgressBar(); self._progress_cenario.setTextVisible(False); self._progress_cenario.setFixedHeight(3); self._progress_cenario.hide()
        v.addWidget(self._progress_cenario)

        self._cards = QHBoxLayout()
        v.addLayout(self._cards)

        self._tbl_cenario = self._make_table()
        v.addWidget(self._tbl_cenario, 1)
        return w

    def _build_tab_abertas(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4); v.setSpacing(6)
        self._tbl_abertas = self._make_table()
        v.addWidget(self._tbl_abertas, 1)
        return w

    def _build_tab_historico(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4); v.setSpacing(6)
        self._tbl_hist = self._make_table()
        v.addWidget(self._tbl_hist, 1)
        return w

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.horizontalHeader().setSortIndicatorShown(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        return t

    # ------------- dados -------------

    def _refresh(self):
        self._progress.show()
        self._progress_cenario.show()
        self.set_footer_stats("Carregando…", "", "")
        key, d1, d2 = self.get_period()

        def load_base():
            df = load_df(GERAL_MULTAS_CSV, dtype=str, keep_default_na=False, normalize_cols=False)
            for c in list(df.columns):
                if "DATA" in str(c).upper():
                    try:
                        df[c] = ensure_datetime(df[c])
                    except Exception:
                        pass
            return df

        results = {}
        def on_result(name, res):
            results[name] = res

        run_tasks({"base": load_base}, max_workers=4, on_result=on_result)

        df = results.get("base", pd.DataFrame())
        if isinstance(df, Exception):
            df = pd.DataFrame()

        # normalização e período
        df = prepare_status_hex(df, status_col="STATUS")
        # escolhe melhor coluna de data disponível
        date_col = self._pick_best_date_col(df)
        if date_col:
            df = apply_period(df, date_col, d1, d2)

        self._df_base = df.reset_index(drop=True)
        self._apply_filters_to_work()
        self._progress.hide()
        self._progress_cenario.hide()

    def _pick_best_date_col(self, df: pd.DataFrame) -> Optional[str]:
        if df is None or df.empty:
            return None
        cand = [c for c in DATE_COLS if c in df.columns]
        if cand:
            return cand[0]
        # fallback heurístico
        for c in df.columns:
            cu = str(c).upper()
            if "DATA" in cu or "EMISSAO" in cu or "LANÇAMENTO" in cu or "LANCAMENTO" in cu:
                return c
        return None

    def _apply_filters_to_work(self):
        if self._df_base is None:
            return

        df = self._df_base.copy()

        # status pelos chips
        on = [k for k, chip in self._status_chips.items() if chip.isChecked()]
        if on:
            if "STATUS" in df.columns:
                df = df[df["STATUS"].astype(str).str.upper().isin(on)]

        # busca global
        terms = self._search.values()
        if terms:
            df = df_apply_global_texts(df, terms)

        self._df_work = df.reset_index(drop=True)

        # atualizar telas
        self._render_cenario()
        self._render_abertas()
        self._render_historico()

    # ------------- render -------------

    def _render_cenario(self):
        df = self._df_work

        # cards
        for i in reversed(range(self._cards.count())):
            item = self._cards.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        total = len(df)
        abertas = (df["STATUS"].str.upper() == "ABERTA").sum() if "STATUS" in df.columns else 0
        vencidas = (df["STATUS"].str.upper() == "VENCIDA").sum() if "STATUS" in df.columns else 0
        pagas = (df["STATUS"].str.upper() == "PAGA").sum() if "STATUS" in df.columns else 0

        self._cards.addWidget(self._make_card("Total", str(total)))
        self._cards.addWidget(self._make_card("Abertas", str(int(abertas)), STATUS_COLOR.get("ABERTA")))
        self._cards.addWidget(self._make_card("Vencidas", str(int(vencidas)), STATUS_COLOR.get("VENCIDA")))
        self._cards.addWidget(self._make_card("Pagas", str(int(pagas)), STATUS_COLOR.get("PAGA")))
        self._cards.addStretch(1)

        self.set_footer_stats(
            f"Total: {total}",
            f"Abertas: {int(abertas)} | Vencidas: {int(vencidas)} | Pagas: {int(pagas)}",
            ""
        )

        # tabela
        self._fill_table(self._tbl_cenario, df)

    def _render_abertas(self):
        df = self._df_work
        if "STATUS" in df.columns:
            df = df[df["STATUS"].str.upper().isin(["ABERTA", "VENCIDA"])].reset_index(drop=True)
        self._fill_table(self._tbl_abertas, df)

    def _render_historico(self):
        df = self._df_work
        if "STATUS" in df.columns:
            df = df[~df["STATUS"].str.upper().isin(["ABERTA", "VENCIDA"])].reset_index(drop=True)
        self._fill_table(self._tbl_hist, df)

    # ------------- util ui -------------

    def _make_card(self, title: str, value: str, color=None) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        apply_shadow(card, radius=12)
        v = QVBoxLayout(card); v.setContentsMargins(12, 10, 12, 10); v.setSpacing(2)
        lab1 = QLabel(title); lab1.setStyleSheet(f"color:{THEME['muted']}; font-weight:600;")
        lab2 = QLabel(value); lab2.setStyleSheet("font-size: 20px; font-weight: 700;")
        v.addWidget(lab1); v.addWidget(lab2)
        if color is not None:
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
            card.setStyleSheet(card.styleSheet() + f"QFrame#card{{border:1px solid rgba({r},{g},{b},80);}}")
        return card

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

    def _sync_chips_from_combo(self):
        vals = set(self._status_combo.selected_values())
        for k, chip in self._status_chips.items():
            chip.setChecked(k in vals)
        self._apply_filters_to_work()


# =========================
# Função de fábrica (entry)
# =========================

def build_multas_view() -> MultasView:
    return MultasView()