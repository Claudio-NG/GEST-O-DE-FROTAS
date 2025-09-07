# multas.py — versão com ações clássicas (Inserir, Editar, Fase Pastores, Conferir FLUIG)

from __future__ import annotations

import os
import datetime as dt
from typing import Dict, List, Optional, Tuple
import pandas as pd

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QSizePolicy, QGridLayout, QSpacerItem, QProgressBar, QComboBox,
    QInputDialog, QMessageBox, QFileDialog, QDialog, QFormLayout, QLineEdit
)

# --- infra compartilhada ---
from utils import (
    # tema / ui
    THEME, apply_shadow, STATUS_COLOR,
    # dados / filtros
    load_df, ensure_datetime, apply_period,
    # eventos / threads
    run_tasks,
    # widgets auxiliares
    GlobalFilterBar, CheckableComboBox,
)
from utils import df_apply_global_texts, _paint_status  # compat
from utils import (
    ensure_status_cols, load_fase_pastores, load_fase_pastores_from,
    export_to_csv, export_to_excel, normalize_text, EVENT_BUS
)

# --- constantes do projeto (com fallbacks definidos no utils.py) ---
try:
    from gestao_frota_single import (
        GERAL_MULTAS_CSV,      # CSV consolidado
        DATE_COLS,             # colunas de data relevantes para multas
        DETALHAMENTO_PATH,     # planilha “Detalhamento” (para conferir FLUIG)
        cfg_get, cfg_set,
    )
except Exception:
    GERAL_MULTAS_CSV = "data/geral_multas.csv"
    DATE_COLS = ["DATA", "VALIDACAO NFF", "CONCLUSAO"]
    DETALHAMENTO_PATH = "Notificações de Multas - Detalhamento.xlsx"
    def cfg_get(*a, **kw): return None
    def cfg_set(*a, **kw): return None


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
# Dialogo de Edição Simples
# =========================

class EditMultaDialog(QDialog):
    """
    Editor rápido para uma multa (focado em FLUIG + campos principais + *_STATUS).
    Recebe o dicionário da linha e permite alterar valores; devolve dict atualizado.
    """
    def __init__(self, row: dict, status_cols: List[str]):
        super().__init__()
        self.setWindowTitle("Editar Multa")
        self._row = dict(row)  # cópia
        self._status_cols = status_cols

        form = QFormLayout(self)
        self._eds: Dict[str, QLineEdit] = {}

        # Campos-chave mais comuns (se existirem)
        key_fields = ["FLUIG", "INFRATOR", "PLACA", "ORGÃO", "ORGAO", "ÓRGÃO",
                      "NOTIFICACAO", "NOTIFICAÇÃO", "TIPO INFRACAO", "TIPO INFRAÇÃO", "VALOR"]
        # mantém os que realmente existem
        keys_present = [k for k in key_fields if k in self._row]

        for k in keys_present:
            ed = QLineEdit(str(self._row.get(k, "")))
            form.addRow(QLabel(k + ":"), ed)
            self._eds[k] = ed

        # Campos de status (dinâmicos)
        for c in self._status_cols:
            eds = QLineEdit(str(self._row.get(c, "")))
            form.addRow(QLabel(c + ":"), eds)
            self._eds[c] = eds

        # Ações
        btns = QHBoxLayout()
        btn_salvar = QPushButton("Salvar")
        btn_cancel = QPushButton("Cancelar")
        btn_salvar.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_salvar)
        form.addRow(btns)

    def data(self) -> dict:
        out = dict(self._row)
        for k, ed in self._eds.items():
            out[k] = ed.text()
        return out


# =========================
# MultasView (BaseView-like)
# =========================

from main_window import BaseView

class MultasView(BaseView):
    def __init__(self):
        super().__init__("Infrações e Multas")

        # dados
        self._df_base: pd.DataFrame = pd.DataFrame()
        self._df_work: pd.DataFrame = pd.DataFrame()

        # status dyn
        self._status_cols_available: List[str] = []  # detectadas por *_STATUS
        self._status_col: Optional[str] = None       # coluna atualmente selecionada
        self._status_chips: Dict[str, Chip] = {}     # chips por valor do status

        # filtros globais
        self._search = GlobalFilterBar("Filtro global:")

        # seleção de coluna de status (dinâmica)
        self._status_col_combo = QComboBox()
        self._status_col_combo.currentIndexChanged.connect(self._on_status_col_changed)

        # seleção rápida de valores (multi)
        self._status_values_combo = CheckableComboBox([])  # preenchido ao escolher coluna
        self._status_values_combo.changed.connect(self._sync_chips_from_combo)

        # AÇÕES “CLÁSSICAS”
        self._btn_inserir = QPushButton("Inserir")
        self._btn_editar = QPushButton("Editar")
        self._btn_fase_pastores = QPushButton("Fase Pastores")
        self._btn_conferir_fluig = QPushButton("Conferir FLUIG")

        self._btn_inserir.clicked.connect(self._on_inserir)
        self._btn_editar.clicked.connect(self._on_editar)
        self._btn_fase_pastores.clicked.connect(self._on_fase_pastores)
        self._btn_conferir_fluig.clicked.connect(self._on_conferir_fluig)

        # progresso
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setRange(0, 0)
        self._progress.hide()

        self._build_advanced()
        self._build_tabs()

        # sinais de período / geração
        self.periodChanged.connect(lambda *_: self._refresh())
        self.generateRequested.connect(self._refresh)

        QTimer.singleShot(50, self._refresh)

    # ------------- UI -------------

    def _build_advanced(self):
        wrap = QFrame()
        g = QGridLayout(wrap); g.setContentsMargins(0, 0, 0, 0); g.setHorizontalSpacing(8)
        r = 0

        # linha 1: seleção da coluna de status
        g.addWidget(QLabel("Coluna de status:"), r, 0, 1, 1)
        g.addWidget(self._status_col_combo, r, 1, 1, 1)
        r += 1

        # linha 2: chips de status (dinâmicos)
        self._chip_bar = QHBoxLayout()
        self._chip_bar.addStretch(1)
        g.addWidget(QLabel("Status:"), r, 0, 1, 1)
        g.addLayout(self._chip_bar, r, 1, 1, 3)
        r += 1

        # linha 3: combo multi de valores (atalho para selecionar/desselecionar chips)
        g.addWidget(QLabel("Seleção rápida de status:"), r, 0, 1, 1)
        g.addWidget(self._status_values_combo, r, 1, 1, 1)
        r += 1

        # linha 4: busca global
        g.addWidget(QLabel("Busca:"), r, 0, 1, 1)
        g.addWidget(self._search, r, 1, 1, 3)
        r += 1

        # linha 5: AÇÕES clássicas
        bar = QHBoxLayout()
        for b in (self._btn_inserir, self._btn_editar, self._btn_fase_pastores, self._btn_conferir_fluig):
            b.setMinimumHeight(32)
            bar.addWidget(b)
        bar.addStretch(1)
        g.addLayout(bar, r, 0, 1, 4)
        r += 1

        g.addItem(QSpacerItem(8, 8, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), r, 0, 1, 1)

        self._search.changed.connect(lambda *_: self._apply_filters_to_work())

        self.set_advanced_widget(wrap)

    def _build_tabs(self):
        self.add_unique_tab("cenario", "Cenário Geral", self._build_tab_cenario())
        self.add_unique_tab("abertas", "Filtradas", self._build_tab_abertas())
        self.add_unique_tab("historico", "Outras", self._build_tab_historico())

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
            # normaliza datas
            for c in list(df.columns):
                if "DATA" in str(c).upper():
                    try:
                        df[c] = ensure_datetime(df[c])
                    except Exception:
                        pass
            # normaliza textos (caixa/trim) nas colunas *_STATUS
            for c in df.columns:
                cu = str(c).upper()
                if cu.endswith("_STATUS"):
                    df[c] = df[c].astype(str).str.strip().str.upper()
            # garante colunas *_STATUS básicas, se necessário
            df = ensure_status_cols(df, csv_path=GERAL_MULTAS_CSV)
            return df

        results = {}
        def on_result(name, res):
            results[name] = res

        run_tasks({"base": load_base}, max_workers=2, on_result=on_result)

        df = results.get("base", pd.DataFrame())
        if isinstance(df, Exception):
            df = pd.DataFrame()

        # escolhe melhor coluna de data disponível para o período
        date_col = self._pick_best_date_col(df)
        if date_col:
            df = apply_period(df, date_col, d1, d2)

        # detecta colunas *_STATUS
        self._status_cols_available = [c for c in df.columns if str(c).upper().endswith("_STATUS")]
        self._status_cols_available.sort()

        # define coluna padrão (se já havia uma selecionada e ainda existe, mantém)
        if self._status_col in self._status_cols_available:
            pass
        else:
            self._status_col = self._status_cols_available[0] if self._status_cols_available else None

        # popula combo de coluna de status
        self._status_col_combo.blockSignals(True)
        self._status_col_combo.clear()
        for c in self._status_cols_available:
            self._status_col_combo.addItem(c)
        if self._status_col:
            self._status_col_combo.setCurrentIndex(self._status_cols_available.index(self._status_col))
        self._status_col_combo.blockSignals(False)

        self._df_base = df.reset_index(drop=True)

        # preparar chips/valores para a coluna atual
        self._rebuild_status_controls()

        self._apply_filters_to_work()
        self._progress.hide()
        self._progress_cenario.hide()

    def _pick_best_date_col(self, df: pd.DataFrame) -> Optional[str]:
        if df is None or df.empty:
            return None
        cand = [c for c in DATE_COLS if c in df.columns]
        if cand:
            return cand[0]
        for c in df.columns:
            cu = str(c).upper()
            if "DATA" in cu or "EMISSAO" in cu or "LANÇAMENTO" in cu or "LANCAMENTO" in cu:
                return c
        return None

    # ----- dinâmica de coluna de status -----

    def _on_status_col_changed(self, *_):
        idx = self._status_col_combo.currentIndex()
        if 0 <= idx < len(self._status_cols_available):
            self._status_col = self._status_cols_available[idx]
            self._rebuild_status_controls()
            self._apply_filters_to_work()

    def _rebuild_status_controls(self):
        """Reconstrói chips e combo de valores para a coluna de status escolhida."""
        # limpa chips antigos
        for i in reversed(range(self._chip_bar.count())):
            item = self._chip_bar.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._status_chips.clear()

        if not self._status_col or self._df_base.empty or self._status_col not in self._df_base.columns:
            self._status_values_combo.set_items([])
            self._chip_bar.addStretch(1)
            return

        col = self._status_col
        vals = (
            self._df_base[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .replace({"": "(SEM STATUS)"})
            .unique()
            .tolist()
        )
        vals = sorted(vals)

        # combo multi
        self._status_values_combo.set_items(vals)
        # por UX: marcar todos inicialmente
        self._status_values_combo.set_all_checked(True)

        # chips
        for v in vals:
            # cor baseada nos STATUS_COLOR conhecidos; senão, tom neutro
            qcolor = STATUS_COLOR.get(v) or STATUS_COLOR.get(v.capitalize())
            hex_color = qcolor.name() if qcolor is not None else "#9E9E9E"
            chip = Chip(v, hex_color)
            chip.setChecked(True)
            chip.toggled.connect(lambda *_: self._apply_filters_to_work())
            self._status_chips[v] = chip
            self._chip_bar.addWidget(chip)

        self._chip_bar.addStretch(1)

    # ------------- aplicação de filtros -------------

    def _apply_filters_to_work(self):
        if self._df_base is None:
            return

        df = self._df_base.copy()

        # status pelos chips (usando a coluna selecionada)
        if self._status_col and self._status_col in df.columns:
            on = [k for k, chip in self._status_chips.items() if chip.isChecked()]
            if on:
                series = (
                    df[self._status_col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .replace({"": "(SEM STATUS)"})
                )
                df = df[series.isin(on)]

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

        # cards dinâmicos por valor da coluna de status
        for i in reversed(range(self._cards.count())):
            item = self._cards.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        total = len(df)
        self._cards.addWidget(self._make_card("Total", str(total)))

        if self._status_col and self._status_col in df.columns:
            # value_counts sobre a coluna selecionada (normalizada)
            series = (
                df[self._status_col]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"": "(SEM STATUS)"})
            )
            counts = series.value_counts(dropna=False)
            for val, qty in counts.items():
                qcolor = STATUS_COLOR.get(val) or STATUS_COLOR.get(str(val).capitalize())
                self._cards.addWidget(self._make_card(str(val).title() if val != "(SEM STATUS)" else "(Sem status)", str(int(qty)), qcolor))

        self._cards.addStretch(1)

        # footer simplificado
        self.set_footer_stats(
            f"Total: {total}",
            f"Coluna de status: {self._status_col or '—'}",
            ""
        )

        # tabela
        self._fill_table(self._tbl_cenario, df)

    def _render_abertas(self):
        """Nesta versão, 'Filtradas' = exatamente o que está selecionado nos chips."""
        df = self._df_work
        self._fill_table(self._tbl_abertas, df)

    def _render_historico(self):
        """'Outras' = complemento dos selecionados (apenas para ter uma visão do que ficou de fora)."""
        df = self._df_base
        if self._status_col and self._status_col in self._df_base.columns:
            on = [k for k, chip in self._status_chips.items() if chip.isChecked()]
            series = (
                self._df_base[self._status_col]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"": "(SEM STATUS)"})
            )
            if on:
                df = self._df_base[~series.isin(on)]
        self._fill_table(self._tbl_hist, df.reset_index(drop=True))

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

        # índice da coluna atualmente escolhida para status (para colorir)
        status_idx = None
        if self._status_col and self._status_col in df.columns:
            status_idx = cols.index(self._status_col)

        for i in range(len(df)):
            row_status = None
            for j, c in enumerate(cols):
                val = df.iat[i, j]
                it = QTableWidgetItem("" if pd.isna(val) else str(val))
                it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                tbl.setItem(i, j, it)
                if status_idx is not None and j == status_idx:
                    row_status = str(val).upper().strip() if val is not None else ""
                    if not row_status:
                        row_status = "(SEM STATUS)"
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
        """Marcar/desmarcar chips conforme seleção múltipla do combo."""
        vals = set(self._status_values_combo.selected_values())
        for k, chip in self._status_chips.items():
            chip.setChecked(k in vals)
        self._apply_filters_to_work()

    # ------------- AÇÕES CLÁSSICAS -------------

    def inserir(self, fluig_code: str):
        """Insere um novo registro no CSV de multas com o FLUIG informado (se ainda não existir)."""
        code = (fluig_code or "").strip()
        if not code:
            return
        try:
            df = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            df = pd.DataFrame([{"FLUIG": code}])
        else:
            if "FLUIG" not in df.columns:
                df["FLUIG"] = ""
            if code in set(df["FLUIG"].astype(str).str.strip()):
                QMessageBox.information(self, "Inserir", "Este FLUIG já existe no CSV.")
                return
            df = pd.concat([df, pd.DataFrame([{"FLUIG": code}])], ignore_index=True)

        df = ensure_status_cols(df, csv_path=None)
        try:
            df.to_csv(GERAL_MULTAS_CSV, index=False)
            QMessageBox.information(self, "Inserir", "Registro inserido com sucesso.")
        except Exception as e:
            QMessageBox.warning(self, "Inserir", f"Falha ao salvar: {e}")

        self._refresh()

    def _on_inserir(self):
        code, ok = QInputDialog.getText(self, "Inserir", "Informe o Nº FLUIG:")
        if ok and code.strip():
            self.inserir(code.strip())

    def _on_editar(self):
        """Abre editor para a primeira linha selecionada na aba atual (se houver FLUIG)."""
        tbl = self._current_table()
        if tbl is None:
            return
        sel = tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Editar", "Selecione uma linha para editar.")
            return
        row = sel[0].row()
        row_dict = {}
        for j in range(tbl.columnCount()):
            k = tbl.horizontalHeaderItem(j).text()
            v = tbl.item(row, j).text() if tbl.item(row, j) else ""
            row_dict[k] = v

        status_cols = [c for c in self._df_base.columns if str(c).upper().endswith("_STATUS")]
        dlg = EditMultaDialog(row_dict, status_cols)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_row = dlg.data()

        # Persiste no CSV (por FLUIG, se existir; senão, por índice relativo na base filtrada)
        try:
            df = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            QMessageBox.warning(self, "Editar", "Base vazia. Não foi possível atualizar.")
            return

        if "FLUIG" in new_row and str(new_row["FLUIG"]).strip():
            mask = df["FLUIG"].astype(str).str.strip() == str(new_row["FLUIG"]).strip()
            if mask.any():
                idxs = df[mask].index.tolist()
                idx = idxs[0]
            else:
                QMessageBox.warning(self, "Editar", "FLUIG não localizado no CSV.")
                return
        else:
            QMessageBox.warning(self, "Editar", "A linha não possui FLUIG para localizar no CSV.")
            return

        # aplica campos editados
        for k, v in new_row.items():
            if k in df.columns:
                df.at[idx, k] = v
            else:
                # cria coluna nova se preciso (ex.: um *_STATUS que não existia)
                df[k] = ""
                df.at[idx, k] = v

        df = ensure_status_cols(df)
        try:
            df.to_csv(GERAL_MULTAS_CSV, index=False)
            QMessageBox.information(self, "Editar", "Registro atualizado com sucesso.")
        except Exception as e:
            QMessageBox.warning(self, "Editar", f"Falha ao salvar: {e}")

        self._refresh()

    def _on_fase_pastores(self):
        """
        Lê a planilha de Fase Pastores escolhida pelo usuário (ou a padrão) e anota no CSV
        as colunas PASTORES_DATA e PASTORES_TIPO por FLUIG.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar planilha de Fase Pastores", "", "Excel (*.xlsx *.xls)")
        dfp = load_fase_pastores_from(path) if path else load_fase_pastores()
        if dfp is None or dfp.empty:
            QMessageBox.information(self, "Fase Pastores", "Planilha não encontrada ou sem dados.")
            return

        # normaliza
        dfp["FLUIG"] = dfp["FLUIG"].astype(str).str.strip()
        try:
            base = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            base = pd.DataFrame()

        if base.empty:
            QMessageBox.warning(self, "Fase Pastores", "Base de multas vazia.")
            return

        if "FLUIG" not in base.columns:
            base["FLUIG"] = ""

        base["FLUIG"] = base["FLUIG"].astype(str).str.strip()
        # cria/garante colunas de saída
        for c in ("PASTORES_DATA", "PASTORES_TIPO"):
            if c not in base.columns:
                base[c] = ""

        # aplica merge
        mp = dfp.set_index("FLUIG")
        hits = 0
        for i in base.index:
            code = base.at[i, "FLUIG"]
            if code in mp.index:
                base.at[i, "PASTORES_DATA"] = str(mp.at[code, "DATA_PASTORES"])
                base.at[i, "PASTORES_TIPO"] = str(mp.at[code, "TIPO"])
                hits += 1

        try:
            base.to_csv(GERAL_MULTAS_CSV, index=False)
            QMessageBox.information(self, "Fase Pastores", f"Atualização concluída. {hits} vínculo(s) aplicado(s).")
        except Exception as e:
            QMessageBox.warning(self, "Fase Pastores", f"Falha ao salvar: {e}")

        self._refresh()

    def _on_conferir_fluig(self):
        """
        Compara FLUIG presentes no Detalhamento x CSV e abre a janela de conferência.
        - Esquerda: no Detalhamento e faltando no CSV
        - Direita:  no CSV e não no Detalhamento
        """
        # carrega detalhamento
        try:
            det = load_df(DETALHAMENTO_PATH, dtype=str, normalize_cols=False)
        except Exception as e:
            QMessageBox.warning(self, "Conferir FLUIG", f"Não foi possível ler o Detalhamento.\n{e}")
            return

        # identifica coluna do FLUIG no detalhamento
        fcol = next((c for c in det.columns if "fluig" in str(c).lower() or "nº fluig" in str(c).lower() or "no fluig" in str(c).lower()), None)
        if not fcol:
            QMessageBox.information(self, "Conferir FLUIG", "Coluna FLUIG não identificada no Detalhamento.")
            return

        det_f = det.copy()
        det_f[fcol] = det_f[fcol].astype(str).str.strip()
        set_det = set(det_f[fcol].astype(str).str.strip())

        # carrega CSV base
        try:
            base = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            base = pd.DataFrame()

        if base.empty:
            QMessageBox.information(self, "Conferir FLUIG", "Base de multas vazia.")
            return
        if "FLUIG" not in base.columns:
            base["FLUIG"] = ""
        base["FLUIG"] = base["FLUIG"].astype(str).str.strip()
        set_csv = set(base["FLUIG"].astype(str).str.strip())

        # monta dataframes para o diálogo
        df_left = det_f[~det_f[fcol].isin(set_csv)].copy()   # no Detalhamento e faltando no CSV
        df_right = base[~base["FLUIG"].isin(set_det)].copy() # no CSV e não no Detalhamento

        # abre o diálogo (usa o da utils)
        from utils import ConferirFluigDialog
        dlg = ConferirFluigDialog(self, df_left, df_right)  # parent PRECISA ter self.inserir()
        dlg.exec()

    # ------------- helpers -------------

    def _current_table(self) -> Optional[QTableWidget]:
        # devolve a tabela da aba ativa (cenário/filtradas/outras)
        idx = self.tabs.currentIndex()
        w = self.tabs.widget(idx)
        if w is None:
            return None
        # varre por QTableWidget
        for child in w.findChildren(QTableWidget):
            return child
        return None