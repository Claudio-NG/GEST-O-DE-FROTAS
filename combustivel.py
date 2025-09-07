from __future__ import annotations

import os, re
import datetime as dt
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QComboBox, QTabWidget, QDateEdit,
    QSlider, QProgressBar
)

from main_window import BaseView
from utils import (
    THEME, apply_shadow, load_df, ensure_datetime, apply_period, run_tasks,
    export_to_csv, export_to_excel, GlobalFilterBar, CheckableComboBox,
    normalize_text, df_apply_global_texts
)

# ==================== Config / paths ====================
try:
    from gestao_frota_single import (
        cfg_get, cfg_set, DATE_FORMAT
    )
except Exception:
    def cfg_get(k): return None
    def cfg_set(k, v): pass
    DATE_FORMAT = "dd/MM/yyyy"

DEFAULT_GERAL_PATH = cfg_get("extrato_geral_path") or ""
DEFAULT_SIMPL_PATH = cfg_get("extrato_simplificado_path") or ""
DEFAULT_DIR = cfg_get("combustivel_dir") or ""


# ==================== Helpers num/str ====================
def _num_from_text(s) -> float:
    if s is None: return 0.0
    txt = str(s).strip()
    if not txt: return 0.0
    txt = re.sub(r"[^\d.,-]", "", txt)
    if ("," not in txt) and ("." not in txt):
        try: return float(txt)
        except: return 0.0
    if "," in txt and "." in txt:
        last_comma = txt.rfind(","); last_dot = txt.rfind(".")
        if last_comma > last_dot:
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    else:
        if "," in txt:
            txt = txt.replace(",", ".")
    try: return float(txt)
    except: return 0.0

def _fmt_num(v: float) -> str:
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_brl(v: float) -> str:
    return "R$ " + _fmt_num(v)

# ==================== View ====================

class CombustivelView(BaseView):
    def __init__(self):
        super().__init__("Combustível")

        # estado
        self.path_geral = DEFAULT_GERAL_PATH
        self.path_simpl = DEFAULT_SIMPL_PATH
        self.dir_many  = DEFAULT_DIR

        self._df_base: pd.DataFrame = pd.DataFrame()          # extrato geral (normalizado + merge)
        self._df_simpl: pd.DataFrame = pd.DataFrame()         # extrato simplificado (limites)
        self._df_work: pd.DataFrame = pd.DataFrame()          # filtrado/tab lançamentos
        self._df_analitico: pd.DataFrame = pd.DataFrame()     # filtrado/tab analítico
        self._df_limites: pd.DataFrame = pd.DataFrame()       # limites por placa

        # filtros avançados
        self._search = GlobalFilterBar("Busca global:")
        self._cmb_veiculo = CheckableComboBox([])
        self._cmb_condutor = CheckableComboBox([])

        # botões
        self._btn_paths = QPushButton("Definir Arquivos…")
        self._btn_paths.clicked.connect(self._definir_arquivos)
        self._btn_export_csv = QPushButton("Exportar CSV")
        self._btn_export_xlsx = QPushButton("Exportar XLSX")
        self._btn_export_csv.clicked.connect(self._export_csv)
        self._btn_export_xlsx.clicked.connect(self._export_xlsx)

        # progresso
        self._progress = QProgressBar(); self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4); self._progress.hide()

        # avançado
        self._build_advanced()

        # abas
        self._build_tabs()

        # sinais
        self.header.btn_aplicar.clicked.connect(self._reload)
        self._search.changed.connect(lambda *_: self._apply_filters())
        self._cmb_veiculo.changed.connect(lambda *_: self._apply_filters())
        self._cmb_condutor.changed.connect(lambda *_: self._apply_filters())

        QTimer.singleShot(60, self._reload)

    # ------------- Advanced panel -------------
    def _build_advanced(self):
        wrap = QFrame()
        g = QGridLayout(wrap); g.setContentsMargins(0,0,0,0); g.setHorizontalSpacing(8)
        r = 0
        g.addWidget(QLabel("Veículo/Placa:"), r, 0, 1, 1); g.addWidget(self._cmb_veiculo, r, 1, 1, 1); r += 1
        g.addWidget(QLabel("Condutor:"), r, 0, 1, 1); g.addWidget(self._cmb_condutor, r, 1, 1, 1); r += 1
        g.addWidget(QLabel("Busca:"), r, 0, 1, 1); g.addWidget(self._search, r, 1, 1, 2); r += 1
        actions = QHBoxLayout(); actions.addWidget(self._btn_paths); actions.addStretch(1)
        actions.addWidget(self._btn_export_csv); actions.addWidget(self._btn_export_xlsx)
        g.addLayout(actions, r, 0, 1, 3)
        self.set_advanced_widget(wrap)

    # ------------- Tabs -------------
    def _build_tabs(self):
        # Cenário Geral
        self._tab_cenario = QWidget(); vc = QVBoxLayout(self._tab_cenario); vc.setContentsMargins(4,4,4,4)
        vc.addWidget(self._progress)
        self._cards_top = QHBoxLayout()
        self._cards_bottom = QHBoxLayout()
        vc.addLayout(self._cards_top)
        vc.addLayout(self._cards_bottom)
        self.add_unique_tab("cenario", "Cenário Geral", self._tab_cenario)

        # Lançamentos
        self._tab_lanc = QWidget(); vl = QVBoxLayout(self._tab_lanc); vl.setContentsMargins(4,4,4,4)
        self._tbl_lanc = self._make_table()
        vl.addWidget(self._tbl_lanc, 1)
        self.add_unique_tab("lanc", "Lançamentos", self._tab_lanc)

        # Analítico (Visão Detalhada)
        self._tab_ana = self._build_analitico_tab()
        self.add_unique_tab("ana", "Analítico", self._tab_ana)

        # Limites
        self._tab_lim = QWidget(); vlm = QVBoxLayout(self._tab_lim); vlm.setContentsMargins(4,4,4,4)
        self._cards_lim = QHBoxLayout()
        vlm.addLayout(self._cards_lim)
        self.add_unique_tab("lim", "Limites", self._tab_lim)

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.horizontalHeader().setSortIndicatorShown(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        return t

    # ------------- Load / Threads -------------
    def _reload(self):
        self._progress.show()
        self.set_footer_stats("Carregando…", "", "")
        key, d1, d2 = self.get_period()

        def load_geral():
            if self.path_geral and os.path.isfile(self.path_geral):
                df = load_df(self.path_geral, dtype=str, normalize_cols=False)
            elif self.dir_many and os.path.isdir(self.dir_many):
                dfs = []
                for n in os.listdir(self.dir_many):
                    if n.lower().endswith((".xlsx",".xls",".csv")):
                        p = os.path.join(self.dir_many, n)
                        try:
                            dfs.append(load_df(p, dtype=str, normalize_cols=False))
                        except Exception:
                            pass
                df = pd.concat(dfs, ignore_index=True, sort=False) if dfs else pd.DataFrame()
            else:
                df = pd.DataFrame()
            # normalizações de data
            for c in df.columns:
                if "DATA" in str(c).upper():
                    try: df[c] = ensure_datetime(df[c])
                    except Exception: pass
            return df

        def load_simpl():
            if self.path_simpl and os.path.isfile(self.path_simpl):
                df = load_df(self.path_simpl, dtype=str, normalize_cols=False)
            else:
                df = pd.DataFrame()
            for c in df.columns:
                if "DATA" in str(c).upper():
                    try: df[c] = ensure_datetime(df[c])
                    except Exception: pass
            return df

        results: Dict[str, pd.DataFrame] = {}
        def on_result(name, res):
            results[name] = res

        run_tasks({"GERAL": load_geral, "SIMPL": load_simpl}, max_workers=2, on_result=on_result)

        geral = results.get("GERAL", pd.DataFrame()).fillna("")
        simpl = results.get("SIMPL", pd.DataFrame()).fillna("")

        # Normalizações mínimas (mapa do seu código antigo)
        m1 = {
            "DATA TRANSACAO":"DATA_TRANSACAO","PLACA":"PLACA","NOME MOTORISTA":"MOTORISTA",
            "TIPO COMBUSTIVEL":"COMBUSTIVEL","LITROS":"LITROS","VL/LITRO":"VL_LITRO",
            "VALOR EMISSAO":"VALOR","NOME ESTABELECIMENTO":"ESTABELECIMENTO","CIDADE":"CIDADE",
            "UF":"UF","CIDADE/UF":"CIDADE_UF","RESPONSAVEL":"RESPONSAVEL",
            "KM RODADOS OU HORAS TRABALHADAS":"KM_RODADOS","KM/LITRO OU LITROS/HORA":"KM_POR_L",
            "MODELO VEICULO":"MODELO","FAMILIA VEICULO":"FAMILIA","TIPO FROTA":"TIPO_FROTA"
        }
        use1 = {src: dst for src, dst in m1.items() if src in geral.columns}
        geral = geral.rename(columns=use1)

        m2 = {
            "Placa":"PLACA","Família":"FAMILIA","Tipo Frota":"TIPO_FROTA","Modelo":"MODELO",
            "Cidade/UF":"CIDADE_UF","Nome Responsável":"RESPONSAVEL",
            "Limite Atual":"LIMITE_ATUAL","Compras (utilizado)":"UTILIZADO","Saldo":"SALDO","Limite Próximo Período":"LIMITE_PROX"
        }
        use2 = {src: dst for src, dst in m2.items() if src in simpl.columns}
        simpl = simpl.rename(columns=use2)

        if "CIDADE_UF" not in geral.columns:
            geral["CIDADE_UF"] = geral.get("CIDADE","").astype(str).str.strip()+"/"+geral.get("UF","").astype(str).str.strip()

        geral["DT"] = geral.get("DATA_TRANSACAO", "").apply(lambda x: pd.to_datetime(str(x), dayfirst=True, errors="coerce"))
        for c_src, c_num in [("LITROS","LITROS_NUM"),("VL_LITRO","VL_LITRO_NUM"),("VALOR","VALOR_NUM"),
                             ("KM_RODADOS","KM_RODADOS_NUM"),("KM_POR_L","KM_POR_L_NUM")]:
            geral[c_num] = geral.get(c_src, "").map(_num_from_text)

        if not simpl.empty and "PLACA" in simpl.columns:
            for c in ["LIMITE_ATUAL","UTILIZADO","SALDO","LIMITE_PROX"]:
                if c in simpl.columns:
                    simpl[c+"_NUM"] = simpl[c].map(_num_from_text)
            merged = geral.merge(simpl, on="PLACA", how="left", suffixes=("", "_S"))
        else:
            merged = geral.copy()

        # período do cabeçalho
        date_col = "DT" if "DT" in merged.columns else None
        if date_col:
            merged = apply_period(merged, date_col, d1, d2)

        self._df_base = merged.reset_index(drop=True)
        self._df_simpl = simpl.reset_index(drop=True)
        self._df_limites = simpl[["PLACA","RESPONSAVEL","LIMITE_ATUAL","UTILIZADO","SALDO","LIMITE_PROX"]].copy() if not simpl.empty else pd.DataFrame()

        self._feed_filters_from_df(self._df_base)
        self._apply_filters()

        self._progress.hide()

    # ------------- Filtros -------------
    def _feed_filters_from_df(self, df: pd.DataFrame):
        if df is None or df.empty:
            self._cmb_veiculo.set_values([]); self._cmb_condutor.set_values([]); return
        veic_col = next((c for c in df.columns if "VEIC" in c.upper() or "PLACA" in c.upper()), None)
        cond_col = next((c for c in df.columns if "MOTORISTA" in c.upper() or "CONDUTOR" in c.upper() or "RESPONS" in c.upper()), None)
        self._cmb_veiculo.set_values(sorted(df[veic_col].dropna().astype(str).unique())) if veic_col else self._cmb_veiculo.set_values([])
        self._cmb_condutor.set_values(sorted(df[cond_col].dropna().astype(str).unique())) if cond_col else self._cmb_condutor.set_values([])

    def _apply_filters(self):
        df = self._df_base.copy()
        if df is None or df.empty:
            self._render_cards(pd.DataFrame(), pd.DataFrame())
            self._fill_table(self._tbl_lanc, pd.DataFrame())
            self._render_limites(None, None)
            return

        veic_col = next((c for c in df.columns if "VEIC" in c.upper() or "PLACA" in c.upper()), None)
        cond_col = next((c for c in df.columns if "MOTORISTA" in c.upper() or "CONDUTOR" in c.upper() or "RESPONS" in c.upper()), None)

        sel_veic = set(self._cmb_veiculo.selected_values())
        if sel_veic and veic_col:
            df = df[df[veic_col].astype(str).isin(sel_veic)]

        sel_cond = set(self._cmb_condutor.selected_values())
        if sel_cond and cond_col:
            df = df[df[cond_col].astype(str).isin(sel_cond)]

        terms = self._search.values()
        if terms:
            df = df_apply_global_texts(df, terms)

        self._df_work = df.reset_index(drop=True)
        self._render_cards(self._df_work, self._df_limites)
        self._fill_table(self._tbl_lanc, self._df_work)
        self._update_analitico_source(self._df_work)
        placa_sel = next(iter(sel_veic)) if sel_veic else None
        self._render_limites(self._df_limites, placa_sel)

        total = len(self._df_base)
        vis = len(self._df_work)
        self.set_footer_stats(f"Total: {total}", f"Visíveis: {vis}", "")

    # ------------- Cenário Geral + Limites -------------
    def _render_cards(self, df: pd.DataFrame, df_lim: pd.DataFrame):
        # limpar
        for layout in (self._cards_top, self._cards_bottom):
            for i in reversed(range(layout.count())):
                item = layout.takeAt(i)
                if item and item.widget(): item.widget().deleteLater()

        if df is None or df.empty:
            self._cards_top.addWidget(self._make_card("Registros", "0"))
            self._cards_bottom.addWidget(self._make_card("—", "—"))
            self._cards_top.addStretch(1); self._cards_bottom.addStretch(1)
            return

        total_reg = len(df)
        total_litros = float(df.get("LITROS_NUM", pd.Series(dtype=float)).sum())
        total_valor  = float(df.get("VALOR_NUM", pd.Series(dtype=float)).sum())
        km_rodado    = float(df.get("KM_RODADOS_NUM", pd.Series(dtype=float)).sum())
        custo_km     = (total_valor / km_rodado) if km_rodado > 0 else 0.0
        consumo_med  = (km_rodado / total_litros) if total_litros > 0 else 0.0
        preco_med    = (total_valor / total_litros) if total_litros > 0 else 0.0

        self._cards_top.addWidget(self._make_card("Registros", f"{total_reg}"))
        self._cards_top.addWidget(self._make_card("Litros", _fmt_num(total_litros)))
        self._cards_top.addWidget(self._make_card("Valor (R$)", _fmt_brl(total_valor)))
        self._cards_top.addWidget(self._make_card("Km rodado", _fmt_num(km_rodado)))
        self._cards_top.addWidget(self._make_card("Custo/km (R$)", _fmt_brl(custo_km)))
        self._cards_top.addWidget(self._make_card("Média (km/L)", _fmt_num(consumo_med)))
        self._cards_top.addStretch(1)

        self._cards_bottom.addWidget(self._make_card("Preço médio (R$/L)", _fmt_brl(preco_med)))
        self._cards_bottom.addStretch(1)

    def _render_limites(self, df_lim: Optional[pd.DataFrame], placa_sel: Optional[str]):
        for i in reversed(range(self._cards_lim.count())):
            item = self._cards_lim.takeAt(i)
            if item and item.widget(): item.widget().deleteLater()

        if df_lim is None or df_lim.empty:
            self._cards_lim.addWidget(self._make_card("Limite Atual", "—"))
            self._cards_lim.addWidget(self._make_card("Utilizado", "—"))
            self._cards_lim.addWidget(self._make_card("Saldo", "—"))
            self._cards_lim.addWidget(self._make_card("Limite Próx. Período", "—"))
            self._cards_lim.addStretch(1)
            return

        def col_sum(col):
            return float(pd.to_numeric(df_lim.get(col, 0), errors="coerce").fillna(0).sum()) if col in df_lim.columns else 0.0

        total_lim   = col_sum("LIMITE_ATUAL_NUM") if "LIMITE_ATUAL_NUM" in df_lim.columns else col_sum("LIMITE_ATUAL")
        total_util  = col_sum("UTILIZADO_NUM")    if "UTILIZADO_NUM" in df_lim.columns else col_sum("UTILIZADO")
        total_saldo = col_sum("SALDO_NUM")        if "SALDO_NUM" in df_lim.columns else col_sum("SALDO")
        total_prox  = col_sum("LIMITE_PROX_NUM")  if "LIMITE_PROX_NUM" in df_lim.columns else col_sum("LIMITE_PROX")

        if placa_sel:
            dfx = df_lim[df_lim["PLACA"].astype(str).str.strip().str.upper() == str(placa_sel).strip().upper()]
            pl_lim   = col_sum("LIMITE_ATUAL_NUM") if not dfx.empty and "LIMITE_ATUAL_NUM" in dfx.columns else float(pd.to_numeric(dfx.get("LIMITE_ATUAL",0), errors="coerce").fillna(0).sum())
            pl_util  = col_sum("UTILIZADO_NUM")    if not dfx.empty and "UTILIZADO_NUM" in dfx.columns else float(pd.to_numeric(dfx.get("UTILIZADO",0), errors="coerce").fillna(0).sum())
            pl_saldo = col_sum("SALDO_NUM")        if not dfx.empty and "SALDO_NUM" in dfx.columns else float(pd.to_numeric(dfx.get("SALDO",0), errors="coerce").fillna(0).sum())
            pl_prox  = col_sum("LIMITE_PROX_NUM")  if not dfx.empty and "LIMITE_PROX_NUM" in dfx.columns else float(pd.to_numeric(dfx.get("LIMITE_PROX",0), errors="coerce").fillna(0).sum())
        else:
            pl_lim = pl_util = pl_saldo = pl_prox = 0.0

        # placa (à esquerda) vs total (sub)
        self._cards_lim.addWidget(self._make_card_dual("Limite Atual", _fmt_brl(pl_lim), "TOTAL: " + _fmt_brl(total_lim)))
        self._cards_lim.addWidget(self._make_card_dual("Utilizado", _fmt_brl(pl_util), "TOTAL: " + _fmt_brl(total_util)))
        self._cards_lim.addWidget(self._make_card_dual("Saldo", _fmt_brl(pl_saldo), "TOTAL: " + _fmt_brl(total_saldo)))
        self._cards_lim.addWidget(self._make_card_dual("Limite Próx. Período", _fmt_brl(pl_prox), "TOTAL: " + _fmt_brl(total_prox)))
        self._cards_lim.addStretch(1)

    # ------------- Analítico (Visão Detalhada) -------------
    def _build_analitico_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(4,4,4,4)

        # régua de tempo local
        top = QFrame(); top.setObjectName("card"); apply_shadow(top, radius=14)
        tl = QHBoxLayout(top)
        self.de_ini = QDateEdit(); self.de_fim = QDateEdit()
        for de in (self.de_ini, self.de_fim):
            de.setCalendarPopup(True); de.setDisplayFormat(DATE_FORMAT)
        self.sl_ini = QSlider(Qt.Orientation.Horizontal); self.sl_fim = QSlider(Qt.Orientation.Horizontal)
        for s in (self.sl_ini, self.sl_fim):
            s.setMinimum(0); s.setMaximum(0); s.setSingleStep(1); s.setPageStep(1)
        tl.addWidget(QLabel("Início:")); tl.addWidget(self.de_ini)
        tl.addSpacing(12); tl.addWidget(QLabel("Fim:")); tl.addWidget(self.de_fim)
        tl.addSpacing(12); tl.addWidget(self.sl_ini, 1); tl.addWidget(self.sl_fim, 1)
        v.addWidget(top)

        # filtro global analítico
        self.global_bar = GlobalFilterBar("Filtro global (Analítico):")
        self.global_bar.changed.connect(self._refresh_analitico)
        v.addWidget(self.global_bar)

        # abas de cenários
        self.tabs_ana = QTabWidget(); v.addWidget(self.tabs_ana, 1)

        # geral
        self.tbl_geral = self._prep_table(["Placa","Abastecimentos","Litros","Valor (R$)","Km Rodados"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_geral), "GERAL")

        # data
        self.tbl_data = self._prep_table(["Ano-Mês","Abastecimentos","Litros","Valor (R$)"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_data), "DATA")

        # placa
        self.tbl_placa = self._prep_table(["Data","Motorista","Combustível","Litros","Vl/Litro","Valor (R$)","Estabelecimento","Cidade/UF"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_placa), "PLACA")
        self.cb_placa = QComboBox()
        self.tabs_ana.setTabToolTip(2, "Use a caixa PLACA na própria tabela de Lançamentos")
        # combustível
        self.tbl_comb = self._prep_table(["Combustível","Abastecimentos","Litros","Preço Médio (R$/L)","Valor (R$)"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_comb), "COMBUSTÍVEL")

        # cidade/uf
        self.tbl_cid = self._prep_table(["Cidade/UF","Abastecimentos","Litros","Valor (R$)"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_cid), "CIDADE/UF")

        # estabelecimento
        self.tbl_est = self._prep_table(["Estabelecimento","Abastecimentos","Litros","Valor (R$)"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_est), "ESTABELECIMENTO")

        # responsável
        self.tbl_resp = self._prep_table(["Responsável","Abastecimentos","Litros","Valor (R$)"])
        self.tabs_ana.addTab(self._wrap_table(self.tbl_resp), "RESPONSÁVEL")

        # sinais régua
        self.de_ini.dateChanged.connect(self._dates_changed)
        self.de_fim.dateChanged.connect(self._dates_changed)
        self.sl_ini.valueChanged.connect(self._sliders_changed)
        self.sl_fim.valueChanged.connect(self._sliders_changed)

        return w

    def _wrap_table(self, tbl: QTableWidget) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0)
        v.addWidget(tbl, 1); return w

    def _prep_table(self, headers: List[str]) -> QTableWidget:
        t = self._make_table()
        t.setColumnCount(len(headers)); t.setHorizontalHeaderLabels(headers)
        return t

    def _update_analitico_source(self, df: pd.DataFrame):
        # define limites da régua
        dts = df["DT"].dropna().dt.normalize() if "DT" in df.columns else pd.Series([], dtype="datetime64[ns]")
        if dts.empty:
            dmin = dmax = pd.Timestamp.today().normalize()
            dates = [dmin]
        else:
            dmin = dts.min(); dmax = dts.max()
            dates = list(pd.date_range(dmin, dmax, freq="D"))
        self._ana_dates = dates
        self._ana_dmin, self._ana_dmax = dmin, dmax

        self.de_ini.blockSignals(True); self.de_fim.blockSignals(True)
        self.de_ini.setDate(QDate(dmin.year, dmin.month, dmin.day))
        self.de_fim.setDate(QDate(dmax.year, dmax.month, dmax.day))
        self.de_ini.blockSignals(False); self.de_fim.blockSignals(False)

        for s in (self.sl_ini, self.sl_fim):
            s.blockSignals(True); s.setMinimum(0); s.setMaximum(max(0,len(dates)-1)); s.blockSignals(False)
        self.sl_ini.blockSignals(True); self.sl_fim.blockSignals(True)
        self.sl_ini.setValue(0); self.sl_fim.setValue(max(0,len(dates)-1))
        self.sl_ini.blockSignals(False); self.sl_fim.blockSignals(False)

        self._df_analitico = df.copy()
        self._refresh_analitico()

    def _sliders_changed(self):
        if not getattr(self, "_ana_dates", None): return
        a = min(self.sl_ini.value(), self.sl_fim.value()); b = max(self.sl_ini.value(), self.sl_fim.value())
        da = self._ana_dates[a]; db = self._ana_dates[b]
        self.de_ini.blockSignals(True); self.de_fim.blockSignals(True)
        self.de_ini.setDate(QDate(da.year, da.month, da.day)); self.de_fim.setDate(QDate(db.year, db.month, db.day))
        self.de_ini.blockSignals(False); self.de_fim.blockSignals(False)
        self._refresh_analitico()

    def _dates_changed(self):
        if not getattr(self, "_ana_dates", None): 
            self._refresh_analitico(); 
            return
        ts_ini = pd.Timestamp(self.de_ini.date().year(), self.de_ini.date().month(), self.de_ini.date().day())
        ts_fim = pd.Timestamp(self.de_fim.date().year(), self.de_fim.date().month(), self.de_fim.date().day())
        idx = pd.Index(self._ana_dates)
        i0 = int((idx - ts_ini).abs().argmin()); i1 = int((idx - ts_fim).abs().argmin())
        self.sl_ini.blockSignals(True); self.sl_fim.blockSignals(True)
        self.sl_ini.setValue(min(i0,i1)); self.sl_fim.setValue(max(i0,i1))
        self.sl_ini.blockSignals(False); self.sl_fim.blockSignals(False)
        self._refresh_analitico()

    def _refresh_analitico(self):
        df = self._df_analitico.copy()
        if df is None or df.empty:
            for t in (self.tbl_geral,self.tbl_data,self.tbl_placa,self.tbl_comb,self.tbl_cid,self.tbl_est,self.tbl_resp):
                self._fill_table(t, pd.DataFrame(), headers=t.horizontalHeaderItem(0).text() if t.columnCount()==1 else None)
            return

        # período local (régua)
        q0, q1 = self.de_ini.date(), self.de_fim.date()
        t0 = pd.Timestamp(q0.year(), q0.month(), q0.day())
        t1 = pd.Timestamp(q1.year(), q1.month(), q1.day())
        a, b = (t0, t1) if t0 <= t1 else (t1, t0)
        if "DT" in df.columns:
            df = df[(df["DT"].notna()) & (df["DT"]>=a) & (df["DT"]<=b)].copy()

        # filtro global analítico
        texts = self.global_bar.values()
        if texts:
            df = df_apply_global_texts(df, texts)

        # GERAL (top N por valor)
        g = df.groupby("PLACA", dropna=False).agg(
            QT=("PLACA","count"), LT=("LITROS_NUM","sum"), VL=("VALOR_NUM","sum"), KM=("KM_RODADOS_NUM","sum")
        ).reset_index().sort_values(["VL","LT","QT"], ascending=False).head(10)
        rows = [[r["PLACA"], int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}", f"{r['KM']:.0f}"] for _, r in g.iterrows()]
        self._fill_rows(self.tbl_geral, rows)

        # DATA (ano-mês)
        dtmp = df.copy()
        if "DT" in dtmp.columns:
            dtmp["YM"] = dtmp["DT"].dt.to_period("M").astype(str)
        else:
            dtmp["YM"] = ""
        g = dtmp.groupby("YM").agg(QT=("PLACA","count"), LT=("LITROS_NUM","sum"), VL=("VALOR_NUM","sum")).reset_index().sort_values("YM")
        rows = [[r["YM"], int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill_rows(self.tbl_data, rows)

        # PLACA (detalhes ordenados por data)
        rows = []
        for _, r in df.sort_values("DT").iterrows():
            rows.append([
                r["DT"].strftime("%d/%m/%Y %H:%M") if pd.notna(r["DT"]) else "",
                r.get("MOTORISTA",""), r.get("COMBUSTIVEL",""),
                f"{float(r.get('LITROS_NUM',0)):.2f}",
                f"{float(r.get('VL_LITRO_NUM',0)):.2f}",
                f"{float(r.get('VALOR_NUM',0)):.2f}",
                r.get("ESTABELECIMENTO",""), r.get("CIDADE_UF","")
            ])
        self._fill_rows(self.tbl_placa, rows)

        # COMBUSTÍVEL
        g = df.groupby("COMBUSTIVEL", dropna=False).agg(
            QT=("PLACA","count"), LT=("LITROS_NUM","sum"),
            VL_MED=("VL_LITRO_NUM","mean"), VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False)
        rows = [[r.get("COMBUSTIVEL",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL_MED']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill_rows(self.tbl_comb, rows)

        # CIDADE/UF
        g = df.groupby("CIDADE_UF", dropna=False).agg(
            QT=("PLACA","count"), LT=("LITROS_NUM","sum"), VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False)
        rows = [[r.get("CIDADE_UF",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill_rows(self.tbl_cid, rows)

        # ESTABELECIMENTO
        g = df.groupby("ESTABELECIMENTO", dropna=False).agg(
            QT=("PLACA","count"), LT=("LITROS_NUM","sum"), VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False).head(50)
        rows = [[r.get("ESTABELECIMENTO",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill_rows(self.tbl_est, rows)

        # RESPONSÁVEL (preferindo coluna do simplificado se existir)
        d = df.copy()
        if "RESPONSAVEL_S" in d.columns:
            d["RESP_X"] = d["RESPONSAVEL_S"].where(d["RESPONSAVEL_S"].astype(str).str.strip()!="", d.get("RESPONSAVEL",""))
        else:
            d["RESP_X"] = d.get("RESPONSAVEL","")
        g = d.groupby("RESP_X", dropna=False).agg(QT=("PLACA","count"), LT=("LITROS_NUM","sum"), VL=("VALOR_NUM","sum")).reset_index().sort_values("VL", ascending=False)
        rows = [[r.get("RESP_X",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill_rows(self.tbl_resp, rows)

    # ------------- UI utils -------------
    def _make_card(self, title: str, value: str) -> QWidget:
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=12)
        v = QVBoxLayout(card); v.setContentsMargins(12, 10, 12, 10); v.setSpacing(2)
        lab1 = QLabel(title); lab1.setStyleSheet(f"color:{THEME['muted']}; font-weight:600;")
        lab2 = QLabel(value); lab2.setStyleSheet("font-size: 20px; font-weight: 700;")
        v.addWidget(lab1); v.addWidget(lab2)
        return card

    def _make_card_dual(self, title: str, main: str, sub: str) -> QWidget:
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=12)
        v = QVBoxLayout(card); v.setContentsMargins(12, 10, 12, 10); v.setSpacing(2)
        lab1 = QLabel(title); lab1.setStyleSheet(f"color:{THEME['muted']}; font-weight:600;")
        lab2 = QLabel(main); lab2.setStyleSheet("font-size: 22px; font-weight: 700;")
        lab3 = QLabel(sub);  lab3.setStyleSheet(f"color:{THEME['muted']};")
        v.addWidget(lab1); v.addWidget(lab2); v.addWidget(lab3)
        return card

    def _fill_table(self, tbl: QTableWidget, df: pd.DataFrame, headers: Optional[List[str]] = None):
        tbl.clear()
        if df is None or df.empty:
            if headers:
                tbl.setColumnCount(len(headers)); tbl.setHorizontalHeaderLabels(headers)
            else:
                tbl.setColumnCount(0)
            tbl.setRowCount(0)
            return
        cols = headers if headers else [str(c) for c in df.columns]
        tbl.setColumnCount(len(cols)); tbl.setHorizontalHeaderLabels(cols)
        max_rows = min(len(df), 10000)
        tbl.setRowCount(max_rows)
        for i in range(max_rows):
            for j, c in enumerate(cols):
                val = df.iat[i, df.columns.get_loc(c)] if c in df.columns else df.iat[i, j]
                it = QTableWidgetItem("" if pd.isna(val) else str(val))
                it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents(); tbl.resizeRowsToContents()

    def _fill_rows(self, tbl: QTableWidget, rows: List[List[str]]):
        tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem(str(v)); it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents(); tbl.resizeRowsToContents()
        tbl.horizontalHeader().setStretchLastSection(True)

    # ------------- Export -------------
    def _export_csv(self):
        if self._tbl_lanc.rowCount() == 0: return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", "combustivel.csv", "CSV (*.csv)")
        if not path: return
        df = self._grab_df_from_table(self._tbl_lanc)
        export_to_csv(df, path)

    def _export_xlsx(self):
        if self._tbl_lanc.rowCount() == 0: return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Excel", "combustivel.xlsx", "Excel (*.xlsx)")
        if not path: return
        df = self._grab_df_from_table(self._tbl_lanc)
        export_to_excel(df, path, sheet_name="Combustivel")

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

    # ------------- Paths -------------
    def _definir_arquivos(self):
        p1, _ = QFileDialog.getOpenFileName(self, "Selecionar Extrato Geral", "", "Planilhas (*.xlsx *.xls *.csv)")
        if p1:
            self.path_geral = p1; cfg_set("extrato_geral_path", p1)
        p2, _ = QFileDialog.getOpenFileName(self, "Selecionar Extrato Simplificado", "", "Planilhas (*.xlsx *.xls *.csv)")
        if p2:
            self.path_simpl = p2; cfg_set("extrato_simplificado_path", p2)
        p3 = QFileDialog.getExistingDirectory(self, "Selecionar Diretório de Lançamentos (opcional)")
        if p3:
            self.dir_many = p3; cfg_set("combustivel_dir", p3)
        if p1 or p2 or p3:
            self._reload()


def build_combustivel_view() -> CombustivelView:
    return CombustivelView()
