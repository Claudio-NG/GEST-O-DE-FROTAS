import os, re
from decimal import Decimal
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton, QComboBox, QLabel, QGridLayout, QMessageBox
from constants import PORTUGUESE_MONTHS
from utils import apply_shadow

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDateEdit, QPushButton, QGridLayout, QScrollArea, QLineEdit
)
from utils import apply_shadow, CheckableComboBox


class CombustivelWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combustível")
        self.resize(1280, 900)
        self.path_geral = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\ExtratoGeral.xlsx"
        self.path_simplificado = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\ExtratoSimplificado.xlsx"
        self.cat_cols = ["DATA TRANSACAO","PLACA","MODELO VEICULO","NOME MOTORISTA","TIPO COMBUSTIVEL","NOME ESTABELECIMENTO","RESPONSAVEL"]
        self.num_cols = ["LITROS","VL/LITRO","HODOMETRO OU HORIMETRO","KM RODADOS OU HORAS TRABALHADAS","KM/LITRO OU LITROS/HORA","VALOR EMISSAO"]
        self.df_original = pd.DataFrame(columns=self.cat_cols + self.num_cols)
        self.df_filtrado = self.df_original.copy()
        self.df_limites = pd.DataFrame()
        self.tot_limites = {"LIMITE ATUAL":0.0,"COMPRAS (UTILIZADO)":0.0,"SALDO":0.0,"LIMITE PRÓXIMO PERÍODO":0.0}
        self.filters = {}
        self.kpi_vals = {}
        self.kpi_dual = {}
        self.fit_targets = []
        root = QVBoxLayout(self)
        header = QFrame(); header.setObjectName("card"); apply_shadow(header, radius=18)
        hv = QVBoxLayout(header)
        tools = QHBoxLayout()
        self.btn_reload = QPushButton("Recarregar"); self.btn_reload.clicked.connect(self.recarregar)
        self.btn_clear = QPushButton("Limpar Filtros"); self.btn_clear.clicked.connect(self.limpar_filtros)
        tools.addWidget(self.btn_reload); tools.addStretch(1); tools.addWidget(self.btn_clear)
        hv.addLayout(tools)
        timebar = QHBoxLayout()
        self.cb_periodo = QComboBox(); self.cb_periodo.addItem("Todos"); self.cb_periodo.currentTextChanged.connect(lambda _: self._on_time_combo("periodo"))
        self.cb_mes = QComboBox(); self.cb_mes.addItem("Todos"); self.cb_mes.currentTextChanged.connect(lambda _: self._on_time_combo("mes"))
        self.cb_ano = QComboBox(); self.cb_ano.addItem("Todos"); self.cb_ano.currentTextChanged.connect(lambda _: self._on_time_combo("ano"))
        timebar.addWidget(QLabel("Período")); timebar.addWidget(self.cb_periodo)
        timebar.addSpacing(16)
        timebar.addWidget(QLabel("Mês")); timebar.addWidget(self.cb_mes)
        timebar.addSpacing(16)
        timebar.addWidget(QLabel("Ano")); timebar.addWidget(self.cb_ano)
        hv.addLayout(timebar)
        self.filters_layout = QGridLayout()
        for i,col in enumerate(self.cat_cols):
            box = QVBoxLayout()
            lab = QLabel(col); lab.setObjectName("colTitle")
            cb = QComboBox(); cb.addItem("Todos"); cb.currentTextChanged.connect(self.atualizar_filtro)
            self.filters[col] = cb
            box.addWidget(lab); box.addWidget(cb)
            self.filters_layout.addLayout(box, i//4, i%4)
        hv.addLayout(self.filters_layout)
        root.addWidget(header)
        grid_top = QFrame(); grid_top.setObjectName("glass"); apply_shadow(grid_top, radius=18, blur=60, color=QColor(0,0,0,80))
        gv1 = QGridLayout(grid_top)
        k1 = self._make_kpi("LITROS"); self.kpi_vals["LITROS"] = k1.findChild(QLabel, "val")
        k2 = self._make_kpi("VL/LITRO"); self.kpi_vals["VL/LITRO"] = k2.findChild(QLabel, "val")
        k3 = self._make_kpi("HODOMETRO OU HORIMETRO"); self.kpi_vals["HODOMETRO OU HORIMETRO"] = k3.findChild(QLabel, "val")
        k4 = self._make_kpi("KM RODADOS OU HORAS TRABALHADAS"); self.kpi_vals["KM RODADOS OU HORAS TRABALHADAS"] = k4.findChild(QLabel, "val")
        k5 = self._make_kpi("KM/LITRO OU LITROS/HORA"); self.kpi_vals["KM/LITRO OU LITROS/HORA"] = k5.findChild(QLabel, "val")
        k6 = self._make_kpi("VALOR EMISSAO"); self.kpi_vals["VALOR EMISSAO"] = k6.findChild(QLabel, "val")
        for i,c in enumerate([k1,k2,k3,k4,k5,k6]):
            gv1.addWidget(c, i//3, i%3)
        root.addWidget(grid_top)
        grid_bottom = QFrame(); grid_bottom.setObjectName("glass"); apply_shadow(grid_bottom, radius=18, blur=60, color=QColor(0,0,0,80))
        gv2 = QGridLayout(grid_bottom)
        d1 = self._make_kpi_dual("LIMITE ATUAL", True); self.kpi_dual["LIMITE ATUAL"] = d1
        d2 = self._make_kpi_dual("COMPRAS (UTILIZADO)", True); self.kpi_dual["COMPRAS (UTILIZADO)"] = d2
        d3 = self._make_kpi_dual("SALDO", True); self.kpi_dual["SALDO"] = d3
        d4 = self._make_kpi_dual("LIMITE PRÓXIMO PERÍODO", True); self.kpi_dual["LIMITE PRÓXIMO PERÍODO"] = d4
        for i,c in enumerate([d1,d2,d3,d4]):
            gv2.addWidget(c["frame"], i//2, i%2)
        root.addWidget(grid_bottom)
        self.recarregar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for lab in self.fit_targets:
            self._fit_font(lab)

    def _make_kpi(self, title):
        f = QFrame(); f.setObjectName("card"); apply_shadow(f, radius=14)
        v = QVBoxLayout(f)
        t = QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val = QLabel("0"); val.setObjectName("val"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t); v.addWidget(val)
        val.setFont(QFont("Arial", 30, QFont.Weight.Bold))
        self.fit_targets.append(val)
        return f

    def _make_kpi_dual(self, title, currency=False):
        f = QFrame(); f.setObjectName("card"); apply_shadow(f, radius=14)
        v = QVBoxLayout(f)
        t = QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main = QLabel("0"); main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("TOTAL: 0"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.setProperty("currency", currency)
        sub.setProperty("currency", currency)
        main.setFont(QFont("Arial", 34, QFont.Weight.Bold))
        sub.setFont(QFont("Arial", 12))
        v.addWidget(t); v.addWidget(main); v.addWidget(sub)
        self.fit_targets.append(main)
        return {"frame": f, "main": main, "sub": sub}

    def _parse_dt(self, s):
        s = str(s).strip()
        if not s:
            return pd.NaT
        for fmt in ["%d/%m/%Y %H:%M:%S","%d/%m/%Y","%Y-%m-%d %H:%M:%S","%Y-%m-%d"]:
            try:
                return pd.to_datetime(s, format=fmt, dayfirst=True)
            except:
                continue
        try:
            return pd.to_datetime(s, dayfirst=True, errors="coerce")
        except:
            return pd.NaT

    def _period_start(self, d):
        if d.day >= 15:
            return pd.Timestamp(d.year, d.month, 15)
        prev = d - pd.offsets.MonthBegin(1)
        prev = prev - pd.offsets.Day(1)
        return pd.Timestamp(prev.year, prev.month, 15)

    def _period_end(self, start):
        nm = start + pd.offsets.MonthBegin(1)
        return pd.Timestamp(nm.year, nm.month, 14)

    def _month_label(self, d):
        return f"{PORTUGUESE_MONTHS.get(d.month,'').upper()}/{str(d.year)[-2:]}"

    def recarregar(self):
        try:
            df = pd.read_excel(self.path_geral, dtype=str).fillna("")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e)); df = pd.DataFrame()
        try:
            df2 = pd.read_excel(self.path_simplificado, dtype=str).fillna("")
        except Exception as e:
            QMessageBox.critical(self,"Erro",str(e)); df2 = pd.DataFrame()
        df.columns = [str(c).strip().upper() for c in df.columns]
        df2.columns = [str(c).strip().upper() for c in df2.columns]
        for c in self.cat_cols + self.num_cols:
            if c not in df.columns:
                df[c] = ""
        if "DATA TRANSACAO" in df.columns:
            dt_series = df["DATA TRANSACAO"].apply(self._parse_dt)
        else:
            dt_series = pd.to_datetime(pd.Series([], dtype=str))
        df["__DT__"] = dt_series
        df["DATA TRANSACAO"] = df["__DT__"].dt.strftime("%d-%m-%Y").fillna("")
        self.df_original = df[self.cat_cols + self.num_cols + ["__DT__"]].copy()
        self.df_filtrado = self.df_original.copy()
        cr = None
        for cand in ["NOME RESPONSÁVEL","NOME RESPONSAVEL","RESPONSAVEL","RESPONSÁVEL"]:
            if cand in df2.columns:
                cr = cand; break
        if cr is None:
            df2["RESPONSAVEL"] = ""
        else:
            df2 = df2.rename(columns={cr:"RESPONSAVEL"})
        map_cols = {
            "LIMITE ATUAL":["LIMITE ATUAL","LIMITE ATUAL "],
            "COMPRAS (UTILIZADO)":["COMPRAS (UTILIZADO)","COMPRAS","COMPRAS UTILIZADO"],
            "SALDO":["SALDO"],
            "LIMITE PRÓXIMO PERÍODO":["LIMITE PRÓXIMO PERÍODO","LIMITE PROXIMO PERIODO"]
        }
        for std, alts in map_cols.items():
            if std not in df2.columns:
                for a in alts:
                    if a in df2.columns:
                        df2.rename(columns={a:std}, inplace=True)
                        break
        for need in ["PLACA","LIMITE ATUAL","COMPRAS (UTILIZADO)","SALDO","LIMITE PRÓXIMO PERÍODO"]:
            if need not in df2.columns:
                df2[need] = ""
        self.df_limites = df2[["PLACA","RESPONSAVEL","LIMITE ATUAL","COMPRAS (UTILIZADO)","SALDO","LIMITE PRÓXIMO PERÍODO"]].copy()
        self.tot_limites = {
            "LIMITE ATUAL": float(self._col_sum(self.df_limites, "LIMITE ATUAL")),
            "COMPRAS (UTILIZADO)": float(self._col_sum(self.df_limites, "COMPRAS (UTILIZADO)")),
            "SALDO": float(self._col_sum(self.df_limites, "SALDO")),
            "LIMITE PRÓXIMO PERÍODO": float(self._col_sum(self.df_limites, "LIMITE PRÓXIMO PERÍODO"))
        }
        self._rebuild_filters()
        self._build_time_combos()
        self._update_all()

    def _build_time_combos(self):
        dts = self.df_original["__DT__"].dropna()
        periods = []
        months = []
        years = []
        if not dts.empty:
            dmin = dts.min().normalize()
            dmax = dts.max().normalize()
            start = self._period_start(dmin)
            idx = 1
            while start <= dmax:
                end = self._period_end(start)
                periods.append((f"P{idx}: {start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}", start, end))
                idx += 1
                start = end + pd.Timedelta(days=1)
            uniq = sorted({(int(d.month), int(d.year)) for d in dts})
            for m,y in uniq:
                months.append((self._month_label(pd.Timestamp(y, m, 1)), m, y))
            years = sorted({int(d.year) for d in dts})
        self.cb_periodo.blockSignals(True); self.cb_periodo.clear(); self.cb_periodo.addItem("Todos")
        for label, s, e in periods:
            self.cb_periodo.addItem(label, (s, e))
        self.cb_periodo.blockSignals(False)
        self.cb_mes.blockSignals(True); self.cb_mes.clear(); self.cb_mes.addItem("Todos")
        for label, m, y in months:
            self.cb_mes.addItem(label, (m, y))
        self.cb_mes.blockSignals(False)
        self.cb_ano.blockSignals(True); self.cb_ano.clear(); self.cb_ano.addItem("Todos")
        for y in years:
            self.cb_ano.addItem(str(y), y)
        self.cb_ano.blockSignals(False)

    def _on_time_combo(self, who):
        if who=="periodo" and self.cb_periodo.currentText()!="Todos":
            self.cb_mes.blockSignals(True); self.cb_mes.setCurrentIndex(0); self.cb_mes.blockSignals(False)
            self.cb_ano.blockSignals(True); self.cb_ano.setCurrentIndex(0); self.cb_ano.blockSignals(False)
        elif who=="mes" and self.cb_mes.currentText()!="Todos":
            self.cb_periodo.blockSignals(True); self.cb_periodo.setCurrentIndex(0); self.cb_periodo.blockSignals(False)
            self.cb_ano.blockSignals(True); self.cb_ano.setCurrentIndex(0); self.cb_ano.blockSignals(False)
        elif who=="ano" and self.cb_ano.currentText()!="Todos":
            self.cb_periodo.blockSignals(True); self.cb_periodo.setCurrentIndex(0); self.cb_periodo.blockSignals(False)
            self.cb_mes.blockSignals(True); self.cb_mes.setCurrentIndex(0); self.cb_mes.blockSignals(False)
        self.atualizar_filtro()

    def limpar_filtros(self):
        for cb in self.filters.values():
            cb.blockSignals(True); cb.setCurrentIndex(0); cb.blockSignals(False)
        self.cb_periodo.blockSignals(True); self.cb_periodo.setCurrentIndex(0); self.cb_periodo.blockSignals(False)
        self.cb_mes.blockSignals(True); self.cb_mes.setCurrentIndex(0); self.cb_mes.blockSignals(False)
        self.cb_ano.blockSignals(True); self.cb_ano.setCurrentIndex(0); self.cb_ano.blockSignals(False)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()
        mask = pd.Series([True]*len(df))
        if self.cb_periodo.currentText()!="Todos":
            s,e = self.cb_periodo.currentData()
            mask &= df["__DT__"].between(s, e)
        elif self.cb_mes.currentText()!="Todos":
            m,y = self.cb_mes.currentData()
            mask &= (df["__DT__"].dt.month==m) & (df["__DT__"].dt.year==y)
        elif self.cb_ano.currentText()!="Todos":
            y = self.cb_ano.currentData()
            mask &= (df["__DT__"].dt.year==y)
        df = df[mask]
        for col,cb in self.filters.items():
            sel = cb.currentText()
            if sel and sel!="Todos":
                df = df[df[col].astype(str)==sel]
        self.df_filtrado = df
        for col,cb in self.filters.items():
            current = cb.currentText()
            items = ["Todos"] + sorted(self.df_filtrado[col].dropna().astype(str).unique())
            cb.blockSignals(True); cb.clear(); cb.addItems(items); cb.setCurrentText(current if current in items else "Todos"); cb.blockSignals(False)
        self._update_all()

    def _rebuild_filters(self):
        for col,cb in self.filters.items():
            cb.blockSignals(True)
            cb.clear()
            items = ["Todos"] + sorted(self.df_original[col].dropna().astype(str).unique())
            cb.addItems(items)
            cb.blockSignals(False)

    def _num_brl(self, x):
        s = str(x).strip()
        if not s:
            return Decimal("0")
        s = re.sub(r"[^\d,.\-]", "", s)
        if "," in s and "." in s:
            dec = "," if s.rfind(",") > s.rfind(".") else "."
            mil = "." if dec == "," else ","
            s = s.replace(mil, "")
            if dec == ",":
                s = s.replace(",", ".")
        elif "," in s and "." not in s:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        elif "." in s and "," not in s:
            pass
        try:
            return Decimal(s)
        except:
            return Decimal("0")

    def _col_sum(self, df, col):
        return sum(self._num_brl(v) for v in df[col].tolist())

    def _to_float(self, x):
        return float(self._num_brl(x))

    def _fmt_num(self, v):
        s = f"{v:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_brl(self, v):
        return "R$ " + self._fmt_num(v)

    def _fit_font(self, label, max_pt=40, min_pt=10):
        text = label.text()
        if not text:
            return
        w = max(10, label.width()-8)
        h = max(10, label.height()-8)
        f = label.font()
        size = max_pt
        while size >= min_pt:
            f.setPointSize(size)
            fm = QFontMetrics(f)
            if fm.horizontalAdvance(text) <= w and fm.height() <= h:
                break
            size -= 1
        label.setFont(f)

    def _update_all(self):
        vals = {c: float(self.df_filtrado[c].apply(self._num_brl).sum()) for c in self.num_cols}
        self.kpi_vals["LITROS"].setText(self._fmt_num(vals["LITROS"]))
        self.kpi_vals["VL/LITRO"].setText(self._fmt_brl(vals["VL/LITRO"]))
        self.kpi_vals["HODOMETRO OU HORIMETRO"].setText(self._fmt_num(vals["HODOMETRO OU HORIMETRO"]))
        self.kpi_vals["KM RODADOS OU HORAS TRABALHADAS"].setText(self._fmt_num(vals["KM RODADOS OU HORAS TRABALHADAS"]))
        self.kpi_vals["KM/LITRO OU LITROS/HORA"].setText(self._fmt_num(vals["KM/LITRO OU LITROS/HORA"]))
        self.kpi_vals["VALOR EMISSAO"].setText(self._fmt_brl(vals["VALOR EMISSAO"]))
        for lab in self.kpi_vals.values():
            self._fit_font(lab)
        placa_sel = self.filters["PLACA"].currentText() if "PLACA" in self.filters else "Todos"
        if placa_sel != "Todos":
            p = str(placa_sel).strip().upper()
            dfp = self.df_limites[self.df_limites["PLACA"].astype(str).str.strip().str.upper().eq(p)]
        else:
            dfp = self.df_limites.iloc[0:0]
        for key, card in self.kpi_dual.items():
            main_val = float(self._col_sum(dfp, key)) if placa_sel != "Todos" else 0.0
            total_val = float(self._col_sum(self.df_limites, key))
            card["main"].setText(self._fmt_brl(main_val))
            card["sub"].setText("TOTAL: " + self._fmt_brl(total_val))
            self._fit_font(card["main"])
<<<<<<< HEAD
# ==========================
# VISÃO DETALHADA DE COMBUSTÍVEL (mini-BI)
# ==========================
import re
import pandas as pd
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDateEdit, QPushButton, QGridLayout
)
from utils import apply_shadow
from constants import DATE_FORMAT
from config import cfg_get

def _dt_parse_any(s):
    s = str(s).strip()
    if not s:
        return pd.NaT
    # tenta com hora
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return pd.to_datetime(s, format=fmt, dayfirst=True, errors="raise")
        except:
            pass
    # sem hora
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return pd.to_datetime(s, format=fmt, dayfirst=True, errors="raise")
        except:
            pass
    return pd.to_datetime(s, dayfirst=True, errors="coerce")



def _num_from_text(s):
    """
    Suporta formatos BR e US:
    - "R$ 1.234,56" -> 1234.56
    - "6,590" -> 6.59
    - "1,234.56" -> 1234.56
    """
    if s is None:
        return 0.0
    txt = str(s).strip()
    if not txt:
        return 0.0
    import re
    txt = re.sub(r"[^\d.,-]", "", txt)

    if ("," not in txt) and ("." not in txt):
        try:
            return float(txt)
        except:
            return 0.0

    if "," in txt and "." in txt:
        last_comma = txt.rfind(",")
        last_dot = txt.rfind(".")
        if last_comma > last_dot:
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    else:
        if "," in txt:
            txt = txt.replace(",", ".")
    try:
        return float(txt)
    except:
        return 0.0



class CombustivelDetalhadoWindow(QWidget):
    """
    Painel detalhado:
    - Base = ExtratoGeral (principal)
    - Complemento = ExtratoSimplificado (por PLACA)
    - Filtro por DATA TRANSACAO (régua de tempo)
    - Cenários: GERAL, DATA, PLACA, MOTORISTA, COMBUSTÍVEL, CIDADE/UF, ESTABELECIMENTO, RESPONSÁVEL
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combustível - Visão Detalhada")
        self.resize(1280, 860)
        self.path_geral = cfg_get("extrato_geral_path")
        self.path_simpl = cfg_get("extrato_simplificado_path")
        self._load_data()
        self._build_ui()
        self._apply_filters_and_refresh()

    # ------- carga
    def _read_xls(self, path):
        if not path:
            return pd.DataFrame()
        try:
            return pd.read_excel(path, dtype=str).fillna("")
        except Exception as e:
            QMessageBox.warning(self, "Combustível", f"Erro ao abrir '{path}': {e}")
            return pd.DataFrame()

    def _load_data(self):
        geral = self._read_xls(self.path_geral)
        simpl = self._read_xls(self.path_simpl)

        # Normaliza nomes mínimos
        # ExtratoGeral
        m1 = {
            "DATA TRANSACAO":"DATA_TRANSACAO",
            "PLACA":"PLACA",
            "NOME MOTORISTA":"MOTORISTA",
            "TIPO COMBUSTIVEL":"COMBUSTIVEL",
            "LITROS":"LITROS",
            "VL/LITRO":"VL_LITRO",
            "VALOR EMISSAO":"VALOR",
            "NOME ESTABELECIMENTO":"ESTABELECIMENTO",
            "CIDADE":"CIDADE",
            "UF":"UF",
            "CIDADE/UF":"CIDADE_UF",
            "SERVICO":"SERVICO",
            "FORMA DE PAGAMENTO":"PAGAMENTO",
            "RESPONSAVEL":"RESPONSAVEL",
            "MODELO VEICULO":"MODELO",
            "FAMILIA VEICULO":"FAMILIA",
            "TIPO FROTA":"TIPO_FROTA",
            "KM RODADOS OU HORAS TRABALHADAS":"KM_RODADOS",
            "KM/LITRO OU LITROS/HORA":"KM_POR_L"
        }
        use1 = {src: dst for src, dst in m1.items() if src in geral.columns}
        geral = geral.rename(columns=use1)

        # ExtratoSimplificado
        m2 = {
            "Placa":"PLACA",
            "Família":"FAMILIA",
            "Tipo Frota":"TIPO_FROTA",
            "Modelo":"MODELO",
            "Fabricante":"FABRICANTE",
            "Cidade/UF":"CIDADE_UF",
            "Nome Responsável":"RESPONSAVEL",
            "Limite":"LIMITE",
            "Valor Reservado":"RESERVADO",
            "Limite Atual":"LIMITE_ATUAL",
            "Compras (utilizado)":"UTILIZADO",
            "Saldo":"SALDO",
            "Limite Próximo Período":"LIMITE_PROX"
        }
        use2 = {src: dst for src, dst in m2.items() if src in simpl.columns}
        simpl = simpl.rename(columns=use2)

        # Deriva cidade/uf se não houver
        if "CIDADE_UF" not in geral.columns:
            cu = []
            for _, r in geral.iterrows():
                cidade = str(r.get("CIDADE", "")).strip()
                uf = str(r.get("UF", "")).strip()
                cu.append(f"{cidade}/{uf}" if cidade or uf else "")
            geral["CIDADE_UF"] = cu

        # Tipos e números
        geral["DT"] = geral.get("DATA_TRANSACAO", "").map(_dt_parse_any)
        geral["LITROS_NUM"] = geral.get("LITROS", "").map(_num_from_text)
        geral["VL_LITRO_NUM"] = geral.get("VL_LITRO", "").map(_num_from_text)
        geral["VALOR_NUM"] = geral.get("VALOR", "").map(_num_from_text)
        geral["KM_RODADOS_NUM"] = geral.get("KM_RODADOS", "").map(_num_from_text)
        geral["KM_POR_L_NUM"] = geral.get("KM_POR_L", "").map(_num_from_text)

        # Merge do simplificado por PLACA
        if not simpl.empty and "PLACA" in simpl.columns:
            # números do simplificado
            for c in ["LIMITE","RESERVADO","LIMITE_ATUAL","UTILIZADO","SALDO","LIMITE_PROX"]:
                if c in simpl.columns:
                    simpl[c+"_NUM"] = simpl[c].map(_num_from_text)
            self.df_base = geral.merge(
                simpl[[c for c in simpl.columns if c]], on="PLACA", how="left", suffixes=("", "_S")
            )
        else:
            self.df_base = geral.copy()

        # Datas para régua
        dates = sorted(list(self.df_base["DT"].dropna().dt.normalize().unique()))
        self._dates = dates if dates else []
        self._dmin = min(dates) if dates else pd.Timestamp.today().normalize()
        self._dmax = max(dates) if dates else pd.Timestamp.today().normalize()


    def _build_ui(self):
        root = QVBoxLayout(self)

    
        title = QFrame(); title.setObjectName("glass"); apply_shadow(title, radius=18, blur=60, color=QColor(0,0,0,60))
        tv = QVBoxLayout(title); tv.setContentsMargins(18,18,18,18)
        h = QLabel("Combustível — Visão Detalhada"); h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.setFont(QFont("Arial", 22, weight=QFont.Weight.Bold))
        tv.addWidget(h)
        root.addWidget(title)

        # KPIs + Régua de tempo
        top = QFrame(); top.setObjectName("card"); apply_shadow(top, radius=18)
        tl = QVBoxLayout(top); tl.setContentsMargins(16,16,16,16)

        # KPIs
        krow = QGridLayout()
        self.kpi_abast = QLabel(); self.kpi_litros = QLabel(); self.kpi_valor = QLabel()
        for lbl in (self.kpi_abast, self.kpi_litros, self.kpi_valor):
            lbl.setFont(QFont("Arial", 12, weight=QFont.Weight.Bold))
        krow.addWidget(QLabel("Abastecimentos:"), 0, 0); krow.addWidget(self.kpi_abast, 0, 1)
        krow.addWidget(QLabel("Litros:"), 0, 2); krow.addWidget(self.kpi_litros, 0, 3)
        krow.addWidget(QLabel("Valor (R$):"), 0, 4); krow.addWidget(self.kpi_valor, 0, 5)
        tl.addLayout(krow)

        # Régua de tempo
        self.de_ini = QDateEdit(); self.de_fim = QDateEdit()
        for de in (self.de_ini, self.de_fim):
            de.setCalendarPopup(True); de.setDisplayFormat(DATE_FORMAT)
            de.setMinimumDate(QDate(1752,9,14)); de.setSpecialValueText("")
        self.de_ini.setDate(QDate(self._dmin.year, self._dmin.month, self._dmin.day))
        self.de_fim.setDate(QDate(self._dmax.year, self._dmax.month, self._dmax.day))

        from PyQt6.QtWidgets import QSlider
        self.sl_ini = QSlider(Qt.Orientation.Horizontal); self.sl_fim = QSlider(Qt.Orientation.Horizontal)
        n = max(0, len(self._dates)-1)
        for s in (self.sl_ini, self.sl_fim):
            s.setMinimum(0); s.setMaximum(n); s.setTickInterval(1); s.setSingleStep(1); s.setPageStep(1)
        self.sl_ini.setValue(0); self.sl_fim.setValue(n)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Início:")); r1.addWidget(self.de_ini); r1.addSpacing(10)
        r1.addWidget(QLabel("Fim:")); r1.addWidget(self.de_fim); r1.addStretch(1)
        r2 = QHBoxLayout(); r2.addWidget(self.sl_ini); r2.addSpacing(8); r2.addWidget(self.sl_fim)

        tl.addLayout(r1); tl.addLayout(r2)
        root.addWidget(top)

        # ===== Filtros por coluna (modelo igual às outras telas) =====
        filt = QFrame(); filt.setObjectName("card"); apply_shadow(filt, radius=18)
        fl = QVBoxLayout(filt); fl.setContentsMargins(12,12,12,12)
        self.f_scroll = QScrollArea(); self.f_scroll.setWidgetResizable(True)
        self.f_host = QWidget(); self.f_grid = QGridLayout(self.f_host)
        self.f_grid.setHorizontalSpacing(14); self.f_grid.setVerticalSpacing(8)
        self.f_scroll.setWidget(self.f_host); fl.addWidget(self.f_scroll)
        root.addWidget(filt)

        # campos filtráveis (por placa e atributos relevantes)
        self.fcols = [
            ("PLACA","Placa"),
            ("MOTORISTA","Motorista"),
            ("COMBUSTIVEL","Combustível"),
            ("CIDADE_UF","Cidade/UF"),
            ("ESTABELECIMENTO","Estabelecimento"),
            ("RESPONSAVEL","Responsável"),
            ("SERVICO","Serviço"),
            ("PAGAMENTO","Pagamento"),
            ("MODELO","Modelo"),
            ("FAMILIA","Família"),
            ("TIPO_FROTA","Tipo Frota"),
        ]
        self.f_mode = {}; self.f_ms = {}; self.f_texts = {}
        self._mount_col_filters()

        # Abas
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)

        # GERAL
        self.tab_geral = QWidget(); vg = QVBoxLayout(self.tab_geral)
        self.tbl_geral = QTableWidget(); self._prep(self.tbl_geral, ["Placa","Abastecimentos","Litros","Valor (R$)","Km Rodados"])
        vg.addWidget(self.tbl_geral)
        self.tabs.addTab(self.tab_geral, "GERAL")

        # DATA
        self.tab_data = QWidget(); vd = QVBoxLayout(self.tab_data)
        self.tbl_data = QTableWidget(); self._prep(self.tbl_data, ["Ano-Mês","Abastecimentos","Litros","Valor (R$)"])
        vd.addWidget(self.tbl_data)
        self.tabs.addTab(self.tab_data, "DATA")

        # PLACA
        self.tab_placa = QWidget(); vp = QVBoxLayout(self.tab_placa)
        rowp = QHBoxLayout(); rowp.addWidget(QLabel("Placa:"))
        self.cb_placa = QComboBox(); self.cb_placa.currentTextChanged.connect(self._refresh_placa)
        rowp.addWidget(self.cb_placa); rowp.addStretch(1); vp.addLayout(rowp)
        self.lbl_placa_metrics = QLabel(""); vp.addWidget(self.lbl_placa_metrics)
        self.tbl_placa = QTableWidget(); self._prep(self.tbl_placa, ["Data","Motorista","Combustível","Litros","Vl/Litro","Valor (R$)","Estabelecimento","Cidade/UF"])
        vp.addWidget(self.tbl_placa)
        self.tabs.addTab(self.tab_placa, "PLACA")

        # MOTORISTA
        self.tab_motor = QWidget(); vm = QVBoxLayout(self.tab_motor)
        rowm = QHBoxLayout(); rowm.addWidget(QLabel("Motorista:"))
        self.cb_motor = QComboBox(); self.cb_motor.currentTextChanged.connect(self._refresh_motorista)
        rowm.addWidget(self.cb_motor); rowm.addStretch(1); vm.addLayout(rowm)
        self.lbl_motor_metrics = QLabel(""); vm.addWidget(self.lbl_motor_metrics)
        self.tbl_motor = QTableWidget(); self._prep(self.tbl_motor, ["Placa","Abastecimentos","Litros","Valor (R$)"])
        vm.addWidget(self.tbl_motor)
        self.tabs.addTab(self.tab_motor, "MOTORISTA")

        # COMBUSTÍVEL
        self.tab_comb = QWidget(); vc = QVBoxLayout(self.tab_comb)
        self.tbl_comb = QTableWidget(); self._prep(self.tbl_comb, ["Combustível","Abastecimentos","Litros","Preço Médio (R$/L)","Valor (R$)"])
        vc.addWidget(self.tbl_comb)
        self.tabs.addTab(self.tab_comb, "COMBUSTÍVEL")

        # CIDADE/UF
        self.tab_cid = QWidget(); vci = QVBoxLayout(self.tab_cid)
        self.tbl_cid = QTableWidget(); self._prep(self.tbl_cid, ["Cidade/UF","Abastecimentos","Litros","Valor (R$)"])
        vci.addWidget(self.tbl_cid)
        self.tabs.addTab(self.tab_cid, "CIDADE/UF")

        # ESTABELECIMENTO
        self.tab_est = QWidget(); ve = QVBoxLayout(self.tab_est)
        self.tbl_est = QTableWidget(); self._prep(self.tbl_est, ["Estabelecimento","Abastecimentos","Litros","Valor (R$)"])
        ve.addWidget(self.tbl_est)
        self.tabs.addTab(self.tab_est, "ESTABELECIMENTO")

        # RESPONSÁVEL
        self.tab_resp = QWidget(); vr = QVBoxLayout(self.tab_resp)
        self.tbl_resp = QTableWidget(); self._prep(self.tbl_resp, ["Responsável","Abastecimentos","Litros","Valor (R$)"])
        vr.addWidget(self.tbl_resp)
        self.tabs.addTab(self.tab_resp, "RESPONSÁVEL")

        # sinais de tempo
        self.de_ini.dateChanged.connect(self._dates_changed)
        self.de_fim.dateChanged.connect(self._dates_changed)
        self.sl_ini.valueChanged.connect(self._sliders_changed)
        self.sl_fim.valueChanged.connect(self._sliders_changed)

    def _mount_col_filters(self):
        while self.f_grid.count():
            item = self.f_grid.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)

        for i, (col, label) in enumerate(self.fcols):
            box = QFrame(); vb = QVBoxLayout(box)
            vb.addWidget(QLabel(label))
            h1 = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos","Excluir vazios","Somente vazios"])
            ms = CheckableComboBox(self.df_base.get(col, pd.Series([], dtype=str)).astype(str).dropna().unique())
            mode.currentTextChanged.connect(self._apply_filters_and_refresh)
            ms.changed.connect(self._apply_filters_and_refresh)
            h1.addWidget(mode); h1.addWidget(ms)
            vb.addLayout(h1)

            h2 = QHBoxLayout()
            le = QLineEdit(); le.setPlaceholderText(f"Filtrar {label}..."); le.textChanged.connect(self._apply_filters_and_refresh)
            add = QPushButton("+"); add.setFixedWidth(28)
            h2.addWidget(le); h2.addWidget(add); vb.addLayout(h2)

            def _add_more(_=None, col_=col, vb_=vb):
                le2 = QLineEdit(); le2.setPlaceholderText(f"Filtrar {label}..."); le2.textChanged.connect(self._apply_filters_and_refresh)
                vb_.addWidget(le2)
                self.f_texts[col_].append(le2)
            add.clicked.connect(_add_more)

            self.f_grid.addWidget(box, i//3, i%3)
            self.f_mode[col] = mode
            self.f_ms[col] = ms
            self.f_texts[col] = [le]


    def _prep(self, tbl, headers):
        tbl.setAlternatingRowColors(True)
        tbl.setSortingEnabled(True)
        tbl.horizontalHeader().setSortIndicatorShown(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)

    # ------- tempo
    def _sliders_changed(self):
        if not self._dates:
            return
        a = min(self.sl_ini.value(), self.sl_fim.value())
        b = max(self.sl_ini.value(), self.sl_fim.value())
        da = self._dates[a]; db = self._dates[b]
        self.de_ini.blockSignals(True); self.de_fim.blockSignals(True)
        self.de_ini.setDate(QDate(da.year, da.month, da.day))
        self.de_fim.setDate(QDate(db.year, db.month, db.day))
        self.de_ini.blockSignals(False); self.de_fim.blockSignals(False)
        self._apply_filters_and_refresh()

    def _dates_changed(self):
        if not self._dates:
            self._apply_filters_and_refresh()
            return
        def near_idx(qd):
            ts = pd.Timestamp(qd.year(), qd.month(), qd.day())
            arr = pd.Series(self._dates)
            return int((arr - ts).abs().argmin())
        i0 = near_idx(self.de_ini.date())
        i1 = near_idx(self.de_fim.date())
        self.sl_ini.blockSignals(True); self.sl_fim.blockSignals(True)
        self.sl_ini.setValue(min(i0, i1)); self.sl_fim.setValue(max(i0, i1))
        self.sl_ini.blockSignals(False); self.sl_fim.blockSignals(False)
        self._apply_filters_and_refresh()


    def _apply_filters_and_refresh(self):
        q0, q1 = self.de_ini.date(), self.de_fim.date()
        t0 = pd.Timestamp(q0.year(), q0.month(), q0.day())
        t1 = pd.Timestamp(q1.year(), q1.month(), q1.day())
        a, b = (t0, t1) if t0 <= t1 else (t1, t0)

        df = self.df_base.copy()
        mask = (df["DT"].notna()) & (df["DT"] >= a) & (df["DT"] <= b)
        df = df[mask].reset_index(drop=True)

        # Filtros por coluna
        for col, _label in self.fcols:
            if col not in df.columns: 
                continue
            mode = self.f_mode[col].currentText()
            if mode == "Excluir vazios":
                df = df[df[col].astype(str).str.strip()!=""]
            elif mode == "Somente vazios":
                df = df[df[col].astype(str).str.strip()==""]

            sels = [s for s in self.f_ms[col].selected_values() if s]
            if sels:
                df = df[df[col].astype(str).isin(sels)]

            termos = [le.text().strip().lower() for le in self.f_texts[col] if le.text().strip()]
            if termos:
                s = df[col].astype(str).str.lower()
                import re as _re
                rgx = "|".join(map(_re.escape, termos))
                df = df[s.str.contains(rgx, na=False)]

        for col, _label in self.fcols:
            ms = self.f_ms[col]
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

        # KPIs
        self.kpi_abast.setText(str(len(self.df_f)))
        self.kpi_litros.setText(f"{self.df_f['LITROS_NUM'].sum():.2f}")
        self.kpi_valor.setText(f"{self.df_f['VALOR_NUM'].sum():.2f}")

        # combos dependentes
        placas = sorted([x for x in self.df_f["PLACA"].astype(str).unique() if x])
        motors = sorted([x for x in self.df_f.get("MOTORISTA", pd.Series([], dtype=str)).astype(str).unique() if x])
        self.cb_placa.blockSignals(True); self.cb_placa.clear(); self.cb_placa.addItems(placas); self.cb_placa.blockSignals(False)
        self.cb_motor.blockSignals(True); self.cb_motor.clear(); self.cb_motor.addItems(motors); self.cb_motor.blockSignals(False)

        # cenários (mesmos métodos que você já tem)
        self._refresh_geral()
        self._refresh_data()
        self._refresh_placa()
        self._refresh_motorista()
        self._refresh_combustivel()
        self._refresh_cidade()
        self._refresh_estab()
        self._refresh_resp()





    def _fill(self, tbl, rows):
        tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem(str(v))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents(); tbl.resizeRowsToContents()

    # ------- cenários
    def _refresh_geral(self):
        d = self.df_f.copy()
        if d.empty:
            self._fill(self.tbl_geral, []); return
        g = d.groupby("PLACA", dropna=False).agg(
            QT=("PLACA", "count"),
            LT=("LITROS_NUM", "sum"),
            VL=("VALOR_NUM", "sum"),
            KM=("KM_RODADOS_NUM","sum")
        ).reset_index().sort_values(["VL","LT","QT"], ascending=False).head(10)
        rows = [[r["PLACA"], int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}", f"{r['KM']:.0f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_geral, rows)

    def _refresh_data(self):
        d = self.df_f.copy()
        if d.empty:
            self._fill(self.tbl_data, []); return
        d["YM"] = d["DT"].dt.to_period("M").astype(str)
        g = d.groupby("YM").agg(
            QT=("PLACA","count"),
            LT=("LITROS_NUM","sum"),
            VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("YM")
        rows = [[r["YM"], int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_data, rows)

    def _refresh_placa(self):
        placa = self.cb_placa.currentText().strip()
        d = self.df_f if not placa else self.df_f[self.df_f["PLACA"].astype(str)==placa]
        if d.empty:
            self.lbl_placa_metrics.setText(""); self._fill(self.tbl_placa, []); return
        total_l = d["LITROS_NUM"].sum()
        total_v = d["VALOR_NUM"].sum()
        media_preco = (d["VALOR_NUM"].sum() / d["LITROS_NUM"].sum()) if d["LITROS_NUM"].sum() > 0 else 0.0
        km = d["KM_RODADOS_NUM"].sum()
        kml = (d["KM_RODADOS_NUM"].sum() / d["LITROS_NUM"].sum()) if d["LITROS_NUM"].sum() > 0 else 0.0
        self.lbl_placa_metrics.setText(f"Abastecimentos: {len(d)} | Litros: {total_l:.2f} | Valor: R$ {total_v:.2f} | Preço médio: R$ {media_preco:.2f}/L | Km: {km:.0f} | Média: {kml:.2f} km/L")
        rows = []
        for _, r in d.sort_values("DT").iterrows():
            rows.append([
                r["DT"].strftime("%d/%m/%Y %H:%M") if pd.notna(r["DT"]) else "",
                r.get("MOTORISTA",""),
                r.get("COMBUSTIVEL",""),
                f"{float(r.get('LITROS_NUM',0)):.2f}",
                f"{float(r.get('VL_LITRO_NUM',0)):.2f}",
                f"{float(r.get('VALOR_NUM',0)):.2f}",
                r.get("ESTABELECIMENTO",""),
                r.get("CIDADE_UF","")
            ])
        self._fill(self.tbl_placa, rows)

    def _refresh_motorista(self):
        nome = self.cb_motor.currentText().strip()
        d = self.df_f if not nome else self.df_f[self.df_f.get("MOTORISTA","").astype(str)==nome]
        if d.empty:
            self.lbl_motor_metrics.setText(""); self._fill(self.tbl_motor, []); return
        total_l = d["LITROS_NUM"].sum()
        total_v = d["VALOR_NUM"].sum()
        self.lbl_motor_metrics.setText(f"Abastecimentos: {len(d)} | Litros: {total_l:.2f} | Valor: R$ {total_v:.2f}")
        g = d.groupby("PLACA", dropna=False).agg(
            QT=("PLACA","count"),
            LT=("LITROS_NUM","sum"),
            VL=("VALOR_NUM","sum")
        ).reset_index().sort_values(["VL","LT","QT"], ascending=False)
        rows = [[r["PLACA"], int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_motor, rows)

    def _refresh_combustivel(self):
        d = self.df_f.copy()
        if d.empty:
            self._fill(self.tbl_comb, []); return
        g = d.groupby("COMBUSTIVEL", dropna=False).agg(
            QT=("PLACA","count"),
            LT=("LITROS_NUM","sum"),
            VL_MED=("VL_LITRO_NUM","mean"),
            VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False)
        rows = [[r.get("COMBUSTIVEL",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL_MED']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_comb, rows)

    def _refresh_cidade(self):
        d = self.df_f.copy()
        if d.empty:
            self._fill(self.tbl_cid, []); return
        g = d.groupby("CIDADE_UF", dropna=False).agg(
            QT=("PLACA","count"),
            LT=("LITROS_NUM","sum"),
            VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False)
        rows = [[r.get("CIDADE_UF",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_cid, rows)

    def _refresh_estab(self):
        d = self.df_f.copy()
        if d.empty:
            self._fill(self.tbl_est, []); return
        g = d.groupby("ESTABELECIMENTO", dropna=False).agg(
            QT=("PLACA","count"),
            LT=("LITROS_NUM","sum"),
            VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False).head(50)
        rows = [[r.get("ESTABELECIMENTO",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_est, rows)

    def _refresh_resp(self):
        d = self.df_f.copy()
        # prioridade: RESPONSAVEL do simplificado (merge) > RESPONSAVEL do geral
        if "RESPONSAVEL_S" in d.columns:
            d["RESP_X"] = d["RESPONSAVEL_S"].where(d["RESPONSAVEL_S"].astype(str).str.strip()!="", d.get("RESPONSAVEL",""))
        else:
            d["RESP_X"] = d.get("RESPONSAVEL","")
        if d.empty:
            self._fill(self.tbl_resp, []); return
        g = d.groupby("RESP_X", dropna=False).agg(
            QT=("PLACA","count"),
            LT=("LITROS_NUM","sum"),
            VL=("VALOR_NUM","sum")
        ).reset_index().sort_values("VL", ascending=False)
        rows = [[r.get("RESP_X",""), int(r["QT"]), f"{r['LT']:.2f}", f"{r['VL']:.2f}"] for _, r in g.iterrows()]
        self._fill(self.tbl_resp, rows)


class CombustivelMenu(QWidget):
    def __init__(self, open_cb):
        super().__init__()
        self.open_cb = open_cb
        v = QVBoxLayout(self)
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=18)
        gv = QGridLayout(card); gv.setContentsMargins(18,18,18,18)
        b1 = QPushButton("Visão Geral")
        b2 = QPushButton("Visão Detalhada")
        for b in (b1, b2):
            b.setMinimumHeight(64); b.setFont(QFont("Arial", 16, weight=QFont.Weight.Bold))
        # Visão Geral = sua tela atual (classe CombustivelWindow que já existe)
        b1.clicked.connect(lambda: self.open_cb("Combustível - Visão Geral", lambda: CombustivelWindow()))
        # Visão Detalhada = nova
        b2.clicked.connect(lambda: self.open_cb("Combustível - Visão Detalhada", lambda: CombustivelDetalhadoWindow()))
        gv.addWidget(b1, 0, 0); gv.addWidget(b2, 0, 1)
        v.addWidget(card)
=======
>>>>>>> parent of f7f355c (ATUALIZAÇÃO DE COMBUSTÍVEL)
