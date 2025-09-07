<<<<<<< HEAD
from __future__ import annotations
=======
# main_window.py
import os, re
import pandas as pd
from pathlib import Path
>>>>>>> f9b717829de913f73d13717fa914335134ff238d

import datetime as dt
from typing import Callable, Dict, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QToolButton, QTabWidget, QSpacerItem, QSizePolicy
)

from utils import THEME, apply_shadow, period_presets, EventBus, EVENT_BUS


class FilterBarCompact(QFrame):
    changed = pyqtSignal()

    def __init__(self, title: str = "Período"):
        super().__init__()
        self.setObjectName("card")
        apply_shadow(self, radius=14)
        self._presets = period_presets()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lab = QLabel(title)
        self.cmb_preset = QComboBox()
        self.cmb_preset.addItem("Mês atual", "MES_ATUAL")
        self.cmb_preset.addItem("Últimos 3 meses", "ULTIMOS_3_MESES")
        self.cmb_preset.addItem("Ano atual", "ANO_ATUAL")
        self.cmb_preset.addItem("Personalizado", "PERSONALIZADO")

        self.dt_ini = QDateEdit()
        self.dt_fim = QDateEdit()
        for ed in (self.dt_ini, self.dt_fim):
            ed.setCalendarPopup(True)
            ed.setDisplayFormat("dd/MM/yyyy")
            ed.setDate(QDate.currentDate())

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_limpar = QToolButton()
        self.btn_limpar.setText("Limpar")
        self.btn_avancado = QToolButton()
        self.btn_avancado.setText("Avançado")
        self.btn_avancado.setCheckable(True)

        row1.addWidget(self.lab)
        row1.addWidget(self.cmb_preset)
        row1.addWidget(self.dt_ini)
        row1.addWidget(self.dt_fim)
        row1.addItem(QSpacerItem(16, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        row1.addWidget(self.btn_avancado)
        row1.addWidget(self.btn_limpar)
        row1.addWidget(self.btn_aplicar)

        self.adv = QFrame()
        self.adv.setVisible(False)
        adv_layout = QHBoxLayout(self.adv)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        self._adv_placeholder = QLabel("Filtros avançados (use por tela)")
        adv_layout.addWidget(self._adv_placeholder)
        adv_layout.addItem(QSpacerItem(16, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        root.addLayout(row1)
        root.addWidget(self.adv)

<<<<<<< HEAD
        self._wire()
        self._apply_preset("MES_ATUAL")
        self._apply_theme()
=======
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
            orgao = str(r.get("ORGÃO", "") or r.get("ORG", "") or r.get("ORGAO", "")).strip()  # 👈 novo

            for col in use_cols:
                dt = str(r.get(col, "")).strip()
                st = str(r.get(f"{col}_STATUS", "")).strip()
                if dt or st:
                    rows.append([fluig, infr, placa, orgao, col, dt, st])

        return pd.DataFrame(rows, columns=["FLUIG","INFRATOR","PLACA","ORGÃO","ETAPA","DATA","STATUS"])
>>>>>>> f9b717829de913f73d13717fa914335134ff238d

    def _apply_theme(self):
        self.setStyleSheet(f"""
        QFrame#card {{
            background: {THEME['surface']};
        }}
        QLabel {{
            color: {THEME['text']};
            font-weight: 600;
        }}
        QComboBox, QDateEdit {{
            min-height: 28px;
        }}
        QPushButton, QToolButton {{
            min-height: 28px;
            padding: 4px 10px;
        }}
        """)

    def _wire(self):
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_change)
        self.btn_aplicar.clicked.connect(lambda: self.changed.emit())
        self.btn_limpar.clicked.connect(self._on_clear)
        self.btn_avancado.toggled.connect(self.adv.setVisible)

    def _on_clear(self):
        self.cmb_preset.setCurrentIndex(0)
        self._apply_preset("MES_ATUAL")
        self.changed.emit()

    def _on_preset_change(self):
        key = self.cmb_preset.currentData()
        self._apply_preset(key)

    def _apply_preset(self, key: str):
        if key != "PERSONALIZADO":
            self.dt_ini.setEnabled(False)
            self.dt_fim.setEnabled(False)
            ini, fim = self._presets.get(key, (None, None))
            if ini:
                self.dt_ini.setDate(QDate(ini.year, ini.month, ini.day))
            if fim:
                self.dt_fim.setDate(QDate(fim.year, fim.month, fim.day))
        else:
            self.dt_ini.setEnabled(True)
            self.dt_fim.setEnabled(True)

    def get_period(self) -> Tuple[str, Optional[dt.date], Optional[dt.date]]:
        key = self.cmb_preset.currentData()
        d1 = self.dt_ini.date()
        d2 = self.dt_fim.date()
        ini = dt.date(d1.year(), d1.month(), d1.day())
        fim = dt.date(d2.year(), d2.month(), d2.day())
        return (
            key,
            ini if key == "PERSONALIZADO" else self._presets[key][0],
            fim if key == "PERSONALIZADO" else self._presets[key][1],
        )

<<<<<<< HEAD
    def set_period(self, start: dt.date, end: dt.date):
        self.cmb_preset.setCurrentIndex(self.cmb_preset.findData("PERSONALIZADO"))
        self._apply_preset("PERSONALIZADO")
        self.dt_ini.setDate(QDate(start.year, start.month, start.day))
        self.dt_fim.setDate(QDate(end.year, end.month, end.day))

    def set_preset(self, key: str):
        idx = max(0, self.cmb_preset.findData(key))
        self.cmb_preset.setCurrentIndex(idx)

    def set_advanced_widget(self, w: QWidget | None):
        lay = self.adv.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        if w is None:
            lay.addWidget(self._adv_placeholder)
        else:
            lay.addWidget(w)
        lay.addItem(QSpacerItem(16, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))


class TabManager:
    def __init__(self, tabs: QTabWidget):
        self.tabs = tabs
        self._keys: Dict[str, int] = {}

    def open_or_activate(self, key: str, builder: Callable[[], Tuple[str, QWidget]]):
        if key in self._keys:
            self.tabs.setCurrentIndex(self._keys[key])
            return
        title, widget = builder()
        idx = self.tabs.addTab(widget, title)
        self._keys[key] = idx
        self.tabs.setCurrentIndex(idx)

    def add_unique(self, key: str, title: str, widget: QWidget):
        if key in self._keys:
            self.tabs.setCurrentIndex(self._keys[key])
            return self._keys[key]
        idx = self.tabs.addTab(widget, title)
        self._keys[key] = idx
        return idx

    def has(self, key: str) -> bool:
        return key in self._keys

    def index(self, key: str) -> int:
        return self._keys.get(key, -1)


class BaseView(QWidget):
    periodChanged = pyqtSignal(tuple)
    generateRequested = pyqtSignal()

    def __init__(self, title: str):
=======

class CenarioGeralWindow(QWidget):
    """
    Painel consolidado (mini-BI):
    - Base: Fase Pastores, complementada por Detalhamento e Condutor Identificado
    - Filtro de tempo por Data de Infração
    - Filtros por coluna (modelo igual ao das outras telas): texto ao digitar, multiseleção, modo vazio/cheio
    - Abas: GERAL, FLUIG, DATA, NOME, TIPO, PLACA, REGIÃO/IGREJA
    """
    def __init__(self):
>>>>>>> f9b717829de913f73d13717fa914335134ff238d
        super().__init__()
        self.title = title

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.header = FilterBarCompact()
        self.header.changed.connect(self._emit_period)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(False)

        self.footer = QFrame()
        self.footer.setObjectName("footer")
        fl = QHBoxLayout(self.footer)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(16)
        self.stat_left = QLabel("")
        self.stat_mid = QLabel("")
        self.stat_right = QLabel("")
        fl.addWidget(self.stat_left)
        fl.addWidget(self.stat_mid)
        fl.addStretch(1)
        fl.addWidget(self.stat_right)

        root.addWidget(self.header)
        root.addWidget(self.tabs, 1)
<<<<<<< HEAD
        root.addWidget(self.footer)

        self.tabman = TabManager(self.tabs)
        self._apply_theme()

        self.header.btn_aplicar.clicked.connect(self.generateRequested.emit)

    def _apply_theme(self):
        self.setStyleSheet(f"""
        QTabWidget::pane {{
            border: 1px solid rgba(0,0,0,0.06);
            background: {THEME['surface']};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            padding: 6px 10px;
        }}
        QFrame#footer {{
            background: {THEME['surface']};
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 10px;
        }}
        QLabel {{
            color: {THEME['text']};
        }}
        """)

    def set_advanced_widget(self, w: QWidget | None):
        self.header.set_advanced_widget(w)

    def get_period(self) -> Tuple[str, Optional[dt.date], Optional[dt.date]]:
        return self.header.get_period()

    def open_or_activate(self, key: str, builder: Callable[[], Tuple[str, QWidget]]):
        self.tabman.open_or_activate(key, builder)

    def add_unique_tab(self, key: str, title: str, widget: QWidget):
        return self.tabman.add_unique(key, title, widget)

    def set_footer_stats(self, left: str = "", mid: str = "", right: str = ""):
        self.stat_left.setText(left or "")
        self.stat_mid.setText(mid or "")
        self.stat_right.setText(right or "")

    def _emit_period(self):
        self.periodChanged.emit(self.get_period())
=======

        # GERAL
        self.tab_geral = QWidget(); vg = QVBoxLayout(self.tab_geral)
        self.tbl_geral = QTableWidget(); self._prep_table(self.tbl_geral, ["Nome","Qtde Multas","Placas distintas","Valor Total (R$)"])
        vg.addWidget(self.tbl_geral)

        # FLUIG
        self.tab_fluig = QWidget(); vf = QVBoxLayout(self.tab_fluig)
        self.tbl_fluig = QTableWidget(); self._prep_table(self.tbl_fluig, ["Status","Quantidade"])
        vf.addWidget(self.tbl_fluig)

        # DATA
        self.tab_data = QWidget(); vd = QVBoxLayout(self.tab_data)
        self.tbl_data = QTableWidget(); self._prep_table(self.tbl_data, ["Ano-Mês","Total no mês","Abertas (se houver status)"])
        vd.addWidget(self.tbl_data)

        # NOME
        self.tab_nome = QWidget(); vn = QVBoxLayout(self.tab_nome)
        row_nome = QHBoxLayout()
        row_nome.addWidget(QLabel("Nome:"))
        self.cb_nome = QComboBox(); self.cb_nome.currentTextChanged.connect(self._refresh_nome)
        row_nome.addWidget(self.cb_nome); row_nome.addStretch(1)
        vn.addLayout(row_nome)
        self.lbl_nome_metrics = QLabel(""); vn.addWidget(self.lbl_nome_metrics)
        self.tbl_nome = QTableWidget(); self._prep_table(self.tbl_nome, ["FLUIG","Placa","Infração","Data Infração","Status","AIT","Valor (R$)"])
        vn.addWidget(self.tbl_nome)

        # TIPO
        self.tab_tipo = QWidget(); vt = QVBoxLayout(self.tab_tipo)
        row_tipo = QHBoxLayout()
        row_tipo.addWidget(QLabel("Infração:"))
        self.cb_tipo = QComboBox(); self.cb_tipo.currentTextChanged.connect(self._refresh_tipo)
        row_tipo.addWidget(self.cb_tipo); row_tipo.addStretch(1)
        vt.addLayout(row_tipo)
        self.tbl_tipo_top = QTableWidget(); self._prep_table(self.tbl_tipo_top, ["Infração","Quantidade"])
        vt.addWidget(self.tbl_tipo_top)
        self.tbl_tipo_nomes = QTableWidget(); self._prep_table(self.tbl_tipo_nomes, ["Nome","Quantidade"])
        vt.addWidget(self.tbl_tipo_nomes)

        # PLACA
        self.tab_placa = QWidget(); vp = QVBoxLayout(self.tab_placa)
        row_placa = QHBoxLayout()
        row_placa.addWidget(QLabel("Placa:"))
        self.cb_placa = QComboBox(); self.cb_placa.currentTextChanged.connect(self._refresh_placa)
        row_placa.addWidget(self.cb_placa); row_placa.addStretch(1)
        vp.addLayout(row_placa)
        self.tbl_placa_top = QTableWidget(); self._prep_table(self.tbl_placa_top, ["Placa","Quantidade"])
        vp.addWidget(self.tbl_placa_top)
        self.tbl_placa_det = QTableWidget(); self._prep_table(self.tbl_placa_det, ["Nome","Infração","Qtde","Valor Total (R$)"])
        vp.addWidget(self.tbl_placa_det)

        # REGIÃO/IGREJA
        self.tab_reg = QWidget(); vr = QVBoxLayout(self.tab_reg)
        self.tbl_reg = QTableWidget(); self._prep_table(self.tbl_reg, ["Região","Igreja","Quantidade"])
        vr.addWidget(self.tbl_reg)

        self.tabs.addTab(self.tab_geral, "GERAL")
        self.tabs.addTab(self.tab_fluig, "FLUIG")
        self.tabs.addTab(self.tab_data, "DATA")
        self.tabs.addTab(self.tab_nome, "NOME")
        self.tabs.addTab(self.tab_tipo, "TIPO DE INFRAÇÃO")
        self.tabs.addTab(self.tab_placa, "PLACA")
        self.tabs.addTab(self.tab_reg, "REGIÃO/IGREJA")

    def _mount_filters(self):
        # limpa grid
        while self.filters_grid.count():
            item = self.filters_grid.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)

        for i, (col, label) in enumerate(self.filter_cols):
            box = QFrame(); vb = QVBoxLayout(box)
            t = QLabel(label); vb.addWidget(t)
            h1 = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos","Excluir vazios","Somente vazios"])
            ms = CheckableComboBox(self.df_base.get(col, pd.Series([], dtype=str)).astype(str).dropna().unique())
            mode.currentTextChanged.connect(self._apply_filters_and_refresh)
            ms.changed.connect(self._apply_filters_and_refresh)
            h1.addWidget(mode); h1.addWidget(ms)
            vb.addLayout(h1)

            # linha de texto + botão +
            h2 = QHBoxLayout()
            le = QLineEdit(); le.setPlaceholderText(f"Filtrar {label}..."); le.textChanged.connect(self._apply_filters_and_refresh)
            btn = QPushButton("+"); btn.setFixedWidth(28)
            vb.addLayout(h2)
            h2.addWidget(le); h2.addWidget(btn)

            # se clicar +, adiciona outra caixa de texto
            def _add_more(_=None, col_=col, vb_=vb):
                le2 = QLineEdit(); le2.setPlaceholderText(f"Filtrar {label}..."); le2.textChanged.connect(self._apply_filters_and_refresh)
                vb_.addWidget(le2)
                self.text_filtros[col_].append(le2)
            btn.clicked.connect(_add_more)

            self.filters_grid.addWidget(box, i//3, i%3)
            self.mode_filtros[col] = mode
            self.multi_filtros[col] = ms
            self.text_filtros[col] = [le]

    def _prep_table(self, tbl, headers):
        tbl.setAlternatingRowColors(True)
        tbl.setSortingEnabled(True)
        tbl.horizontalHeader().setSortIndicatorShown(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)

    # ----- filtros tempo <-> sliders
    def _on_slider_changed(self):
        if not self._date_index:
            return
        a = min(self.sl_start.value(), self.sl_end.value())
        b = max(self.sl_start.value(), self.sl_end.value())
        da = self._date_index[a]; db = self._date_index[b]
        self.de_start.blockSignals(True); self.de_end.blockSignals(True)
        self.de_start.setDate(QDate(da.year, da.month, da.day))
        self.de_end.setDate(QDate(db.year, db.month, db.day))
        self.de_start.blockSignals(False); self.de_end.blockSignals(False)
        self._apply_filters_and_refresh()

    def _on_dateedit_changed(self):
        if not self._date_index:
            self._apply_filters_and_refresh()
            return
        def _nearest_idx(dt):
            ts = pd.Timestamp(dt.year(), dt.month(), dt.day())
            arr = pd.Series(self._date_index)
            return int((arr - ts).abs().argmin())
        i0 = _nearest_idx(self.de_start.date())
        i1 = _nearest_idx(self.de_end.date())
        self.sl_start.blockSignals(True); self.sl_end.blockSignals(True)
        self.sl_start.setValue(min(i0, i1))
        self.sl_end.setValue(max(i0, i1))
        self.sl_start.blockSignals(False); self.sl_end.blockSignals(False)
        self._apply_filters_and_refresh()

    # ----- refresh + aplicação dos filtros
    def _apply_filters_and_refresh(self):
        # contadores brutos (sem filtro)
        self.lbl_count_det.setText(str(len(self.df_det)))
        self.lbl_count_past.setText(str(len(self.df_past)))
        self.lbl_count_cond.setText(str(len(self.df_cond)))

        # período
        q0, q1 = self.de_start.date(), self.de_end.date()
        t0 = pd.Timestamp(q0.year(), q0.month(), q0.day())
        t1 = pd.Timestamp(q1.year(), q1.month(), q1.day())
        a, b = (t0, t1) if t0 <= t1 else (t1, t0)

        df = self.df_base.copy()
        mask = (df["DT_INF"].notna()) & (df["DT_INF"] >= a) & (df["DT_INF"] <= b)
        df = df[mask].reset_index(drop=True)

        # filtros por coluna
        for col, _label in self.filter_cols:
            if col not in df.columns:
                continue
            mode = self.mode_filtros[col].currentText()
            if mode == "Excluir vazios":
                df = df[df[col].astype(str).str.strip()!=""]
            elif mode == "Somente vazios":
                df = df[df[col].astype(str).str.strip()==""]
            sels = [s for s in self.multi_filtros[col].selected_values() if s]
            if sels:
                df = df[df[col].astype(str).isin(sels)]
            # textos (OR entre caixas do mesmo campo)
            termos = [le.text().strip().lower() for le in self.text_filtros[col] if le.text().strip()]
            if termos:
                s = df[col].astype(str).str.lower()
                rgx = "|".join(map(re.escape, termos))
                df = df[s.str.contains(rgx, na=False)]

        # atualiza opções dos combos com o recorte atual (mantendo seleção)
        for col, _label in self.filter_cols:
            ms = self.multi_filtros[col]
            if col not in df.columns: 
                continue
            current_sel = ms.selected_values()
            ms.set_values(sorted([x for x in df[col].astype(str).dropna().unique() if x]))
            if current_sel:
                for i in range(ms.count()):
                    if ms.itemText(i) in current_sel:
                        idx = ms.model().index(i, 0)
                        ms.model().setData(idx, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
                ms._update_text()

        self.df_f = df

        # combos dependentes das abas
        nomes = sorted([x for x in self.df_f["U_NOME"].astype(str).unique() if x])
        self.cb_nome.blockSignals(True); self.cb_nome.clear(); self.cb_nome.addItems(nomes); self.cb_nome.blockSignals(False)

        tipos = sorted([x for x in self.df_f["U_INFRACAO"].astype(str).unique() if x])
        self.cb_tipo.blockSignals(True); self.cb_tipo.clear(); self.cb_tipo.addItems(tipos); self.cb_tipo.blockSignals(False)

        placas = sorted([x for x in self.df_f["U_PLACA"].astype(str).unique() if x])
        self.cb_placa.blockSignals(True); self.cb_placa.clear(); self.cb_placa.addItems(placas); self.cb_placa.blockSignals(False)

        # render das abas
        self._refresh_geral()
        self._refresh_fluig()
        self._refresh_data()
        self._refresh_nome()
        self._refresh_tipo()
        self._refresh_placa()
        self._refresh_reg()

    def _refresh_geral(self):
        df = self.df_f.copy()
        if df.empty:
            self._fill_table(self.tbl_geral, [])
            return
        g = df.groupby("U_NOME", dropna=False).agg(
            QT=("FLUIG","count"),
            PLACAS=("U_PLACA", lambda s: len(set([x for x in s if str(x).strip()]))),
            VAL=("VALOR_NUM","sum")
        ).reset_index().rename(columns={"U_NOME":"Nome","QT":"Qtde Multas","PLACAS":"Placas distintas","VAL":"Valor Total (R$)"})
        g = g.sort_values(["Qtde Multas","Valor Total (R$)"], ascending=[False, False]).head(10)
        rows = [[str(r["Nome"]), str(int(r["Qtde Multas"])), str(int(r["Placas distintas"])), f"{r['Valor Total (R$)']:.2f}"] for _, r in g.iterrows()]
        self._fill_table(self.tbl_geral, rows)

    def _refresh_fluig(self):
        df = self.df_f.copy()
        if df.empty or "U_STATUS" not in df.columns:
            self._fill_table(self.tbl_fluig, [])
            return
        g = df["U_STATUS"].fillna("").replace("", "Sem Status").str.upper().value_counts().reset_index()
        g.columns = ["Status","Quantidade"]
        rows = [[str(r["Status"]), str(int(r["Quantidade"]))] for _, r in g.iterrows()]
        self._fill_table(self.tbl_fluig, rows)

    def _refresh_data(self):
        df = self.df_f.copy()
        if df.empty:
            self._fill_table(self.tbl_data, [])
            return
        df["YM"] = df["DT_INF"].dt.to_period("M").astype(str)
        total = df.groupby("YM").size().reset_index(name="Total no mês")
        if "U_STATUS" in df.columns:
            ab = df["U_STATUS"].fillna("").str.upper().eq("ABERTA")
            ab_count = df[ab].groupby("YM").size().reindex(total["YM"]).fillna(0).astype(int).reset_index(drop=True)
            total["Abertas (se houver status)"] = ab_count
        rows = [[r["YM"], str(int(r["Total no mês"])), str(int(r.get("Abertas (se houver status)", 0)))] for _, r in total.iterrows()]
        self._fill_table(self.tbl_data, rows)

    def _refresh_nome(self):
        df = self.df_f.copy()
        nome = self.cb_nome.currentText().strip()
        if not nome:
            self.lbl_nome_metrics.setText("")
            self._fill_table(self.tbl_nome, [])
            return
        d = df[df["U_NOME"].astype(str)==nome]
        qt = len(d)
        valor = d["VALOR_NUM"].sum()
        placas = len(set([x for x in d["U_PLACA"].astype(str) if x]))
        self.lbl_nome_metrics.setText(f"Qtde: {qt} | Valor Total: R$ {valor:.2f} | Placas distintas: {placas}")
        rows = []
        for _, r in d.iterrows():
            rows.append([
                str(r.get("FLUIG","")),
                str(r.get("U_PLACA","")),
                str(r.get("U_INFRACAO","")),
                r["DT_INF"].strftime("%d/%m/%Y") if pd.notna(r["DT_INF"]) else "",
                str(r.get("U_STATUS","")),
                str(r.get("U_AIT","")),
                f"{float(r.get('VALOR_NUM',0.0)):.2f}"
            ])
        self._fill_table(self.tbl_nome, rows)

    def _refresh_tipo(self):
        df = self.df_f.copy()
        if df.empty:
            self._fill_table(self.tbl_tipo_top, [])
            self._fill_table(self.tbl_tipo_nomes, [])
            return
        g = df["U_INFRACAO"].astype(str).replace("", pd.NA).dropna().value_counts().reset_index()
        g.columns = ["Infração","Quantidade"]
        rows = [[str(r["Infração"]), str(int(r["Quantidade"]))] for _, r in g.iterrows()]
        self._fill_table(self.tbl_tipo_top, rows)

        tipo = self.cb_tipo.currentText().strip()
        if not tipo:
            self._fill_table(self.tbl_tipo_nomes, [])
        else:
            dn = df[df["U_INFRACAO"].astype(str)==tipo]
            g2 = dn.groupby("U_NOME").size().reset_index(name="Qtde").sort_values("Qtde", ascending=False)
            rows2 = [[str(r["U_NOME"]), str(int(r["Qtde"]))] for _, r in g2.iterrows()]
            self._fill_table(self.tbl_tipo_nomes, rows2)

    def _refresh_placa(self):
        df = self.df_f.copy()
        if df.empty:
            self._fill_table(self.tbl_placa_top, [])
            self._fill_table(self.tbl_placa_det, [])
            return
        g = df["U_PLACA"].astype(str).replace("", pd.NA).dropna().value_counts().reset_index()
        g.columns = ["Placa","Quantidade"]
        rows = [[str(r["Placa"]), str(int(r["Quantidade"]))] for _, r in g.iterrows()]
        self._fill_table(self.tbl_placa_top, rows)

        placa = self.cb_placa.currentText().strip()
        if not placa:
            self._fill_table(self.tbl_placa_det, [])
        else:
            dp = df[df["U_PLACA"].astype(str)==placa]
            g2 = dp.groupby(["U_NOME","U_INFRACAO"], dropna=False).agg(
                QT=("FLUIG","count"), VAL=("VALOR_NUM","sum")
            ).reset_index().sort_values("QT", ascending=False)
            rows2 = [[str(r["U_NOME"]), str(r["U_INFRACAO"]), str(int(r["QT"])), f"{r['VAL']:.2f}"] for _, r in g2.iterrows()]
            self._fill_table(self.tbl_placa_det, rows2)

    def _refresh_reg(self):
        df = self.df_f.copy()
        if df.empty or ("REGIAO" not in df.columns and "IGREJA" not in df.columns):
            self._fill_table(self.tbl_reg, [])
            return
        reg = df.get("REGIAO", pd.Series([""]*len(df)))
        igr = df.get("IGREJA", pd.Series([""]*len(df)))
        g = pd.DataFrame({"REGIAO":reg.astype(str),"IGREJA":igr.astype(str)})
        g["K"]=1
        g = g.groupby(["REGIAO","IGREJA"]).size().reset_index(name="Quantidade").sort_values("Quantidade", ascending=False)
        rows = [[str(r["REGIAO"]), str(r["IGREJA"]), str(int(r["Quantidade"]))] for _, r in g.iterrows()]
        self._fill_table(self.tbl_reg, rows)

    def _fill_table(self, tbl, rows):
        tbl.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents()
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


class MainWindow(QMainWindow):
    """
    Janela principal com:
    - Aba 'Início' contendo os botões grandes (Base, Infrações e Multas, Combustível, Relatórios, Alertas, Condutor)
    - Abertura de cada módulo em novas abas
    - Relatórios EXPANSIVOS: cada planilha abre em sua própria aba "Relatório — <nome>"
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
            ("Relatórios", self.open_relatorios),      # agora abre múltiplos arquivos em abas separadas
            ("Alertas", self.open_alertas),            # método corrigido
            ("Condutor", self.open_condutor),          # botão ativo
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

    # ===== Utilidades de abas =====
    def _find_tab_index_by_title(self, title: str) -> int:
        for idx in range(self.tab_widget.count()):
            if self.tab_widget.tabText(idx) == title:
                return idx
        return -1

    def add_or_focus(self, title, factory):
        """Evita duplicar abas com o mesmo título: foca se já existir; senão cria."""
        idx = self._find_tab_index_by_title(title)
        if idx >= 0:
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
        try:
            from gestao_frota_single import BaseTab
            self.add_or_focus("Base", lambda: BaseTab())
        except Exception as e:
            QMessageBox.warning(self, "Base", f"Não foi possível abrir a Base.\n{e}")

    def open_multas(self):
        self.add_or_focus("Infrações e Multas", lambda: InfraMultasWindow())

    def open_combustivel(self):
        try:
            self.add_or_focus("Combustível", lambda: CombustivelWindow())
        except Exception as e:
            QMessageBox.warning(self, "Combustível", str(e))

    def open_relatorios(self):
        """
        Permite selecionar UMA OU VÁRIAS planilhas e abre cada uma em sua própria aba:
        'Relatório — <nome_da_planilha>'.
        Se a aba já existir, apenas foca.
        """
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Abrir arquivo(s) de relatório", "",
            "Planilhas (*.xlsx *.xls *.csv)"
        )
        if not paths:
            return

        for p in paths:
            try:
                stem = Path(p).stem
                title = f"Relatório — {stem}"
                self.add_or_focus(title, lambda p_=p: RelatorioWindow(p_))
            except Exception as e:
                QMessageBox.warning(self, "Relatórios", f"Não foi possível abrir '{p}'.\n{e}")

    def open_alertas(self):
        """Abre a aba de Alertas (corrigido; antes o método não existia)."""
        try:
            self.add_or_focus("Alertas", lambda: AlertsTab())
        except Exception as e:
            QMessageBox.warning(self, "Alertas", f"Não foi possível abrir Alertas.\n{e}")

    def open_condutor(self):
        """Abre a tela de Condutor em uma nova aba."""
        try:
            from condutor import CondutorWindow
            self.add_or_focus("Condutor — Busca Integrada", lambda: CondutorWindow())
        except Exception as e:
            QMessageBox.warning(self, "Condutor", f"Não foi possível abrir a tela de Condutor.\n{e}")

    def logout(self):
        self.close()
>>>>>>> f9b717829de913f73d13717fa914335134ff238d
