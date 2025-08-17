import os, re
from decimal import Decimal
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton, QComboBox, QLabel, QGridLayout, QMessageBox
from constants import PORTUGUESE_MONTHS
from utils import apply_shadow

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
