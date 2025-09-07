# multas.py — versão com ações clássicas (Inserir, Editar, Fase Pastores, Conferir FLUIG)
from __future__ import annotations

import os
import pandas as pd
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QSizePolicy, QGridLayout, QSpacerItem, QProgressBar, QComboBox,
    QInputDialog, QMessageBox, QFileDialog, QDialog, QFormLayout, QLineEdit
)

# --- infra compartilhada ---
from utils import (
    THEME, apply_shadow, STATUS_COLOR,
    load_df, ensure_datetime, apply_period, df_apply_global_texts, _paint_status,
    ensure_status_cols, load_fase_pastores, load_fase_pastores_from,
    export_to_csv, export_to_excel, normalize_text, EVENT_BUS
)

# --- constantes ---
try:
    from gestao_frota_single import (
        GERAL_MULTAS_CSV, DATE_COLS, DETALHAMENTO_PATH, cfg_get, cfg_set
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
# Diálogo de Edição Rápida
# =========================
class EditMultaDialog(QDialog):
    def __init__(self, row: dict, status_cols: List[str]):
        super().__init__()
        self.setWindowTitle("Editar Multa")
        self._row = dict(row)
        self._status_cols = status_cols

        form = QFormLayout(self)
        self._eds: Dict[str, QLineEdit] = {}

        key_fields = ["FLUIG", "INFRATOR", "PLACA", "ORGÃO", "ORGAO", "ÓRGÃO",
                      "NOTIFICACAO", "NOTIFICAÇÃO", "TIPO INFRACAO", "TIPO INFRAÇÃO", "VALOR"]
        keys_present = [k for k in key_fields if k in self._row]

        for k in keys_present:
            ed = QLineEdit(str(self._row.get(k, "")))
            form.addRow(QLabel(k + ":"), ed)
            self._eds[k] = ed

        for c in self._status_cols:
            eds = QLineEdit(str(self._row.get(c, "")))
            form.addRow(QLabel(c + ":"), eds)
            self._eds[c] = eds

        btns = QHBoxLayout()
        bt_ok = QPushButton("Salvar"); bt_cancel = QPushButton("Cancelar")
        bt_ok.clicked.connect(self.accept); bt_cancel.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(bt_cancel); btns.addWidget(bt_ok)
        form.addRow(btns)

    def data(self) -> dict:
        out = dict(self._row)
        for k, ed in self._eds.items():
            out[k] = ed.text()
        return out


# =========================
# MultasView
# =========================
from main_window import BaseView

class MultasView(BaseView):
    def __init__(self):
        super().__init__("Infrações e Multas")

        self._df_base: pd.DataFrame = pd.DataFrame()
        self._df_work: pd.DataFrame = pd.DataFrame()

        # status dinâmico
        self._status_cols_available: List[str] = []
        self._status_col: Optional[str] = None
        self._status_chips: Dict[str, Chip] = {}

        # filtro global
        self._search = GlobalFilterBar("Filtro global:")

        # seleção coluna de status
        self._status_col_combo = QComboBox()
        self._status_col_combo.currentIndexChanged.connect(self._on_status_col_changed)

        # multi-valor de status
        self._status_values_combo = CheckableComboBox([])
        self._status_values_combo.changed.connect(self._sync_chips_from_combo)

        # AÇÕES clássicas
        self._btn_inserir = QPushButton("Inserir")
        self._btn_editar = QPushButton("Editar")
        self._btn_fase_pastores = QPushButton("Fase Pastores")
        self._btn_conferir_fluig = QPushButton("Conferir FLUIG")
        self._btn_inserir.clicked.connect(self._on_inserir)
        self._btn_editar.clicked.connect(self._on_editar)
        self._btn_fase_pastores.clicked.connect(self._on_fase_pastores)
        self._btn_conferir_fluig.clicked.connect(self._on_conferir_fluig)

        # progresso
        self._progress = QProgressBar(); self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4); self._progress.setRange(0,0); self._progress.hide()

        self._build_advanced()
        self._build_tabs()

        self.periodChanged.connect(lambda *_: self._refresh())
        self.generateRequested.connect(self._refresh)
        QTimer.singleShot(50, self._refresh)

    # UI
    def _build_advanced(self):
        wrap = QFrame()
        g = QGridLayout(wrap); g.setContentsMargins(0,0,0,0); g.setHorizontalSpacing(8)
        r = 0

        g.addWidget(QLabel("Coluna de status:"), r, 0); g.addWidget(self._status_col_combo, r, 1); r += 1

        self._chip_bar = QHBoxLayout(); self._chip_bar.addStretch(1)
        g.addWidget(QLabel("Status:"), r, 0); g.addLayout(self._chip_bar, r, 1, 1, 3); r += 1

        g.addWidget(QLabel("Seleção rápida de status:"), r, 0); g.addWidget(self._status_values_combo, r, 1); r += 1

        g.addWidget(QLabel("Busca:"), r, 0); g.addWidget(self._search, r, 1, 1, 3); r += 1

        bar = QHBoxLayout()
        for b in (self._btn_inserir, self._btn_editar, self._btn_fase_pastores, self._btn_conferir_fluig):
            b.setMinimumHeight(32); bar.addWidget(b)
        bar.addStretch(1)
        g.addLayout(bar, r, 0, 1, 4); r += 1

        g.addItem(QSpacerItem(8, 8, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), r, 0)
        self._search.changed.connect(lambda *_: self._apply_filters_to_work())
        self.set_advanced_widget(wrap)

    def _build_tabs(self):
        self.add_unique_tab("cenario", "Cenário Geral", self._build_tab_cenario())
        self.add_unique_tab("abertas", "Filtradas", self._build_tab_abertas())
        self.add_unique_tab("historico", "Outras", self._build_tab_historico())

    def _build_tab_cenario(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4); v.setSpacing(6)
        self._progress_cenario = QProgressBar(); self._progress_cenario.setTextVisible(False)
        self._progress_cenario.setFixedHeight(3); self._progress_cenario.hide()
        v.addWidget(self._progress_cenario)
        self._cards = QHBoxLayout(); v.addLayout(self._cards)
        self._tbl_cenario = self._make_table(); v.addWidget(self._tbl_cenario, 1)
        return w

    def _build_tab_abertas(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4)
        self._tbl_abertas = self._make_table(); v.addWidget(self._tbl_abertas, 1)
        return w

    def _build_tab_historico(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4)
        self._tbl_hist = self._make_table(); v.addWidget(self._tbl_hist, 1)
        return w

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.horizontalHeader().setSortIndicatorShown(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        return t

    # dados
    def _refresh(self):
        self._progress.show(); self._progress_cenario.show()
        self.set_footer_stats("Carregando…", "", "")
        key, d1, d2 = self.get_period()

        def load_base():
            df = load_df(GERAL_MULTAS_CSV, dtype=str, keep_default_na=False, normalize_cols=False)
            # normaliza datas
            for c in list(df.columns):
                if "DATA" in str(c).upper():
                    try: df[c] = ensure_datetime(df[c])
                    except Exception: pass
            # normaliza *_STATUS
            for c in df.columns:
                if str(c).upper().endswith("_STATUS"):
                    df[c] = df[c].astype(str).str.strip().str.upper()
            df = ensure_status_cols(df, csv_path=GERAL_MULTAS_CSV)
            return df

        results = {}
        def on_result(name, res): results[name] = res

        from utils import run_tasks
        run_tasks({"base": load_base}, max_workers=2, on_result=on_result)

        df = results.get("base", pd.DataFrame())
        if isinstance(df, Exception): df = pd.DataFrame()

        date_col = self._pick_best_date_col(df)
        if date_col: df = apply_period(df, date_col, d1, d2)

        self._status_cols_available = [c for c in df.columns if str(c).upper().endswith("_STATUS")]
        self._status_cols_available.sort()
        if self._status_col not in self._status_cols_available:
            self._status_col = self._status_cols_available[0] if self._status_cols_available else None

        self._status_col_combo.blockSignals(True)
        self._status_col_combo.clear()
        for c in self._status_cols_available: self._status_col_combo.addItem(c)
        if self._status_col:
            self._status_col_combo.setCurrentIndex(self._status_cols_available.index(self._status_col))
        self._status_col_combo.blockSignals(False)

        self._df_base = df.reset_index(drop=True)
        self._rebuild_status_controls()
        self._apply_filters_to_work()
        self._progress.hide(); self._progress_cenario.hide()

    def _pick_best_date_col(self, df: pd.DataFrame) -> Optional[str]:
        if df is None or df.empty: return None
        cand = [c for c in DATE_COLS if c in df.columns]
        if cand: return cand[0]
        for c in df.columns:
            cu = str(c).upper()
            if "DATA" in cu or "EMISSAO" in cu or "LANÇAMENTO" in cu or "LANCAMENTO" in cu:
                return c
        return None

    # status
    def _on_status_col_changed(self, *_):
        idx = self._status_col_combo.currentIndex()
        if 0 <= idx < len(self._status_cols_available):
            self._status_col = self._status_cols_available[idx]
            self._rebuild_status_controls()
            self._apply_filters_to_work()

    def _rebuild_status_controls(self):
        for i in reversed(range(self._chip_bar.count())):
            item = self._chip_bar.takeAt(i)
            if item and item.widget(): item.widget().deleteLater()
        self._status_chips.clear()

        if not self._status_col or self._df_base.empty or self._status_col not in self._df_base.columns:
            self._status_values_combo.set_items([]); self._chip_bar.addStretch(1); return

        col = self._status_col
        vals = (self._df_base[col].fillna("").astype(str).str.strip().str.upper().replace({"": "(SEM STATUS)"}).unique().tolist())
        vals = sorted(vals)

        self._status_values_combo.set_items(vals)
        self._status_values_combo.set_all_checked(True)

        for v in vals:
            qcolor = STATUS_COLOR.get(v) or STATUS_COLOR.get(v.capitalize())
            hex_color = qcolor.name() if qcolor is not None else "#9E9E9E"
            chip = Chip(v, hex_color); chip.setChecked(True)
            chip.toggled.connect(lambda *_: self._apply_filters_to_work())
            self._status_chips[v] = chip
            self._chip_bar.addWidget(chip)
        self._chip_bar.addStretch(1)

    # filtros
    def _apply_filters_to_work(self):
        if self._df_base is None: return
        df = self._df_base.copy()

        if self._status_col and self._status_col in df.columns:
            on = [k for k, chip in self._status_chips.items() if chip.isChecked()]
            if on:
                series = (df[self._status_col].fillna("").astype(str).str.strip().str.upper().replace({"": "(SEM STATUS)"}))
                df = df[series.isin(on)]

        terms = self._search.values()
        if terms:
            df = df_apply_global_texts(df, terms)

        self._df_work = df.reset_index(drop=True)
        self._render_cenario(); self._render_abertas(); self._render_historico()

    # render
    def _render_cenario(self):
        df = self._df_work
        for i in reversed(range(self._cards.count())):
            item = self._cards.takeAt(i)
            if item and item.widget(): item.widget().deleteLater()

        total = len(df)
        self._cards.addWidget(self._make_card("Total", str(total)))

        if self._status_col and self._status_col in df.columns:
            series = (df[self._status_col].fillna("").astype(str).str.strip().str.upper().replace({"": "(SEM STATUS)"}))
            counts = series.value_counts(dropna=False)
            for val, qty in counts.items():
                qcolor = STATUS_COLOR.get(val) or STATUS_COLOR.get(str(val).capitalize())
                self._cards.addWidget(self._make_card(str(val).title() if val != "(SEM STATUS)" else "(Sem status)", str(int(qty)), qcolor))

        self._cards.addStretch(1)
        self.set_footer_stats(f"Total: {total}", f"Coluna de status: {self._status_col or '—'}", "")
        self._fill_table(self._tbl_cenario, df)

    def _render_abertas(self):
        self._fill_table(self._tbl_abertas, self._df_work)

    def _render_historico(self):
        df = self._df_base
        if self._status_col and self._status_col in self._df_base.columns:
            on = [k for k, chip in self._status_chips.items() if chip.isChecked()]
            series = (self._df_base[self._status_col].fillna("").astype(str).str.strip().str.upper().replace({"": "(SEM STATUS)"}))
            if on: df = self._df_base[~series.isin(on)]
        self._fill_table(self._tbl_hist, df.reset_index(drop=True))

    def _make_card(self, title: str, value: str, color=None) -> QWidget:
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=12)
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
            tbl.setRowCount(0); tbl.setColumnCount(0); return
        cols = [str(c) for c in df.columns]
        tbl.setColumnCount(len(cols)); tbl.setHorizontalHeaderLabels(cols); tbl.setRowCount(len(df))

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
                    if not row_status: row_status = "(SEM STATUS)"
                    _paint_status(it, row_status)
            if row_status and status_idx is not None:
                for j in range(len(cols)):
                    if j == status_idx: continue
                    it2 = tbl.item(i, j)
                    if it2: _paint_status(it2, row_status)

        tbl.resizeColumnsToContents(); tbl.resizeRowsToContents()

    def _sync_chips_from_combo(self):
        vals = set(self._status_values_combo.selected_values())
        for k, chip in self._status_chips.items():
            chip.setChecked(k in vals)
        self._apply_filters_to_work()

    # ============== AÇÕES ==============

    def inserir(self, fluig_code: str):
        """Insere um novo registro no CSV, somente se o FLUIG existir no Detalhamento; pré-preenche campos quando possível."""
        code = (fluig_code or "").strip()
        if not code: return

        # Checa no Detalhamento
        det = None
        try:
            det = load_df(DETALHAMENTO_PATH, dtype=str, normalize_cols=False)
        except Exception:
            det = None

        if isinstance(det, dict):
            # torna DataFrame se load_df eventualmente devolver dict
            det = pd.DataFrame(det)
        if det is None or not isinstance(det, pd.DataFrame) or det.empty:
            QMessageBox.warning(self, "Inserir", "Não foi possível ler o Detalhamento para validar o FLUIG.")
            return

        fcol = next((c for c in det.columns if "fluig" in str(c).lower() or "nº fluig" in str(c).lower() or "no fluig" in str(c).lower()), None)
        if not fcol:
            QMessageBox.warning(self, "Inserir", "Coluna FLUIG não identificada no Detalhamento.")
            return

        det[fcol] = det[fcol].astype(str).str.strip()
        row_det = det[det[fcol] == code]
        if row_det.empty:
            QMessageBox.information(self, "Inserir", "FLUIG não encontrado no Detalhamento. Inserção bloqueada.")
            return

        # Carrega CSV
        try:
            df = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            df = pd.DataFrame([{"FLUIG": code}])
        else:
            if "FLUIG" not in df.columns: df["FLUIG"] = ""
            if code in set(df["FLUIG"].astype(str).str.strip()):
                QMessageBox.information(self, "Inserir", "Este FLUIG já existe no CSV.")
                return
            df = pd.concat([df, pd.DataFrame([{"FLUIG": code}])], ignore_index=True)

        # Pré-preenche campos compatíveis a partir do Detalhamento (colunas que existirem em comum)
        # Pega a primeira ocorrência
        r = row_det.iloc[0].to_dict()
        # campos sugeridos comuns
        sugestao_keys = ["PLACA","INFRATOR","NOME","CONDUTOR","ORGÃO","ÓRGÃO","ORGAO","TIPO INFRAÇÃO","TIPO INFRACAO",
                         "DATA","DATA DA INFRACAO","DATA INFRAÇÃO","VALOR","VALOR MULTA","VALOR DA MULTA"]
        for k in sugestao_keys:
            if k in df.columns and k in r:
                df.at[df.index[-1], k] = str(r.get(k, ""))

        df = ensure_status_cols(df, csv_path=None)
        try:
            df.to_csv(GERAL_MULTAS_CSV, index=False)
            QMessageBox.information(self, "Inserir", "Registro inserido e pré-preenchido com sucesso.")
        except Exception as e:
            QMessageBox.warning(self, "Inserir", f"Falha ao salvar: {e}")
        self._refresh()

    def _on_inserir(self):
        code, ok = QInputDialog.getText(self, "Inserir", "Informe o Nº FLUIG:")
        if ok and code.strip(): self.inserir(code.strip())

    def _on_editar(self):
        tbl = self._current_table()
        if tbl is None: return
        sel = tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Editar", "Selecione uma linha para editar."); return
        row = sel[0].row()

        row_dict = {}
        for j in range(tbl.columnCount()):
            k = tbl.horizontalHeaderItem(j).text()
            v = tbl.item(row, j).text() if tbl.item(row, j) else ""
            row_dict[k] = v

        status_cols = [c for c in self._df_base.columns if str(c).upper().endswith("_STATUS")]
        dlg = EditMultaDialog(row_dict, status_cols)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        new_row = dlg.data()

        try:
            base = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            base = pd.DataFrame()
        if base.empty:
            QMessageBox.warning(self, "Editar", "Base vazia. Não foi possível atualizar."); return

        if "FLUIG" in new_row and str(new_row["FLUIG"]).strip():
            mask = base.get("FLUIG","").astype(str).str.strip() == str(new_row["FLUIG"]).strip()
            if not mask.any():
                QMessageBox.warning(self, "Editar", "FLUIG não localizado no CSV."); return
            idx = mask[mask].index[0]
        else:
            QMessageBox.warning(self, "Editar", "A linha não possui FLUIG para localizar no CSV."); return

        for k, v in new_row.items():
            if k in base.columns:
                base.at[idx, k] = v
            else:
                base[k] = ""
                base.at[idx, k] = v

        base = ensure_status_cols(base)
        try:
            base.to_csv(GERAL_MULTAS_CSV, index=False)
            QMessageBox.information(self, "Editar", "Registro atualizado com sucesso.")
        except Exception as e:
            QMessageBox.warning(self, "Editar", f"Falha ao salvar: {e}")
        self._refresh()

    def _on_fase_pastores(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar planilha de Fase Pastores", "", "Excel (*.xlsx *.xls)")
        dfp = load_fase_pastores_from(path) if path else load_fase_pastores()
        if dfp is None or dfp.empty:
            QMessageBox.information(self, "Fase Pastores", "Planilha não encontrada ou sem dados.")
            return

        dfp["FLUIG"] = dfp["FLUIG"].astype(str).str.strip()
        try:
            base = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            base = pd.DataFrame()
        if base.empty:
            QMessageBox.warning(self, "Fase Pastores", "Base de multas vazia."); return

        if "FLUIG" not in base.columns: base["FLUIG"] = ""
        base["FLUIG"] = base["FLUIG"].astype(str).str.strip()
        for c in ("PASTORES_DATA", "PASTORES_TIPO"):
            if c not in base.columns: base[c] = ""

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
        """Compara FLUIG do Detalhamento x CSV, com correção para quando o Detalhamento vier como dict."""
        try:
            det = load_df(DETALHAMENTO_PATH, dtype=str, normalize_cols=False)
        except Exception as e:
            QMessageBox.warning(self, "Conferir FLUIG", f"Não foi possível ler o Detalhamento.\n{e}")
            return

        if isinstance(det, dict):
            det = pd.DataFrame(det)
        if det is None or not isinstance(det, pd.DataFrame) or det.empty:
            QMessageBox.information(self, "Conferir FLUIG", "Detalhamento vazio ou inválido."); return

        fcol = next((c for c in det.columns if "fluig" in str(c).lower() or "nº fluig" in str(c).lower() or "no fluig" in str(c).lower()), None)
        if not fcol:
            QMessageBox.information(self, "Conferir FLUIG", "Coluna FLUIG não identificada no Detalhamento.")
            return

        det_f = det.copy()
        det_f[fcol] = det_f[fcol].astype(str).str.strip()
        set_det = set(det_f[fcol].astype(str).str.strip())

        try:
            base = pd.read_csv(GERAL_MULTAS_CSV, dtype=str).fillna("") if os.path.exists(GERAL_MULTAS_CSV) else pd.DataFrame()
        except Exception:
            base = pd.DataFrame()

        if base.empty:
            QMessageBox.information(self, "Conferir FLUIG", "Base de multas vazia."); return
        if "FLUIG" not in base.columns: base["FLUIG"] = ""
        base["FLUIG"] = base["FLUIG"].astype(str).str.strip()
        set_csv = set(base["FLUIG"].astype(str).str.strip())

        df_left  = det_f[~det_f[fcol].isin(set_csv)].copy()   # no Detalhamento e faltando no CSV
        df_right = base[~base["FLUIG"].isin(set_det)].copy()  # no CSV e não no Detalhamento

        from utils import ConferirFluigDialog
        dlg = ConferirFluigDialog(self, df_left, df_right)  # parent precisa ter self.inserir()
        dlg.exec()

    # helpers
    def _current_table(self) -> Optional[QTableWidget]:
        idx = self.tabs.currentIndex()
        w = self.tabs.widget(idx)
        if w is None: return None
        for child in w.findChildren(QTableWidget):
            return child
        return None
