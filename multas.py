# multas.py
import os
import re
import shutil
import pandas as pd

from PyQt6.QtCore import Qt, QDate, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
    QDialog, QFormLayout, QFileDialog, QSizePolicy, QScrollArea, QInputDialog,
    QDateEdit, QCompleter
)

from utils import (
    ensure_status_cols, apply_shadow, _paint_status, to_qdate_flexible,
    build_multa_dir, _parse_dt_any, CheckableComboBox, SummaryDialog, ConferirFluigDialog
)
from constants import ORGAOS, DATE_FORMAT  # Usamos DATE_FORMAT do seu projeto
from config import cfg_get

# ====== MUITO IMPORTANTE ======
# Nesta tela, vamos TRATAR como datas SOMENTE estas três colunas:
DATE_COLS_MUL = ["DATA INDICAÇÃO", "BOLETO", "SGU"]

# E vamos OCULTAR/IGNORAR estas colunas na UI:
IGNORED_COLS = {"LANÇAMENTOS DE NFF", "VALIDAÇÃO", "CONCLUSÃO"}


# ---------------------- DIALOGO: INSERIR ----------------------
class InserirDialog(QDialog):
    def __init__(self, parent, prefill_fluig=None):
        super().__init__(parent)
        self.setWindowTitle("Inserir Multa")
        self.resize(720, 560)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._csv = cfg_get("geral_multas_csv")
        self.df = ensure_status_cols(pd.read_csv(self._csv, dtype=str).fillna(""), csv_path=self._csv)

        # garantir COMENTARIO
        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""
            self.df.to_csv(self._csv, index=False)

        form = QFormLayout(self)
        self.widgets = {}

        # ordem: FLUIG primeiro + demais colunas SEM *_STATUS (e pulando ignoradas)
        base_fields = [c for c in self.df.columns if not c.endswith("_STATUS") and c not in IGNORED_COLS and c != "FLUIG"]
        fields = ["FLUIG"] + base_fields

        for c in fields:
            if c in DATE_COLS_MUL:
                d = QDateEdit(); d.setCalendarPopup(True); d.setDisplayFormat(DATE_FORMAT)
                d.setMinimumDate(QDate(1752, 9, 14)); d.setSpecialValueText("")
                d.setDate(d.minimumDate())
                s = QComboBox(); s.addItems(["", "Pendente", "Pago", "Vencido"])
                box = QWidget(); hb = QHBoxLayout(box); hb.setContentsMargins(0, 0, 0, 0); hb.addWidget(d); hb.addWidget(s)
                form.addRow(c, box); self.widgets[c] = (d, s)
            elif c == "ORGÃO":
                cb = QComboBox(); cb.addItems(ORGAOS); form.addRow(c, cb); self.widgets[c] = cb
            else:
                w = QLineEdit()
                if c == "FLUIG":
                    comp = QCompleter(sorted(self.df["FLUIG"].dropna().astype(str).unique()))
                    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                    w.setCompleter(comp)
                    w.editingFinished.connect(lambda le=w: self.on_fluig_leave(le))
                form.addRow(c, w); self.widgets[c] = w

        bar = QHBoxLayout()
        btn_save = QPushButton("Salvar"); btn_pdf = QPushButton("Anexar PDF"); btn_close = QPushButton("Fechar")
        bar.addWidget(btn_save); bar.addStretch(1); bar.addWidget(btn_pdf); bar.addWidget(btn_close)
        form.addRow(bar)
        btn_save.clicked.connect(self.salvar)
        btn_pdf.clicked.connect(self.anexar_pdf)
        btn_close.clicked.connect(self.reject)

        if prefill_fluig:
            self.widgets["FLUIG"].setText(str(prefill_fluig).strip())
            self.on_fluig_leave(self.widgets["FLUIG"])

    def _apply_fase_pastores(self, code):
        path = cfg_get("pastores_file")
        try:
            dfp = pd.read_excel(path, dtype=str).fillna("")
        except:
            return
        fcol = next((c for c in dfp.columns if "fluig" in c.lower()), None)
        dcol = next((c for c in dfp.columns if "data" in c.lower() and "pastor" in c.lower()), None)
        tcol = next((c for c in dfp.columns if "tipo" in c.lower()), None)
        if not fcol or not dcol or not tcol:
            return
        row = dfp[dfp[fcol].astype(str).str.strip().eq(str(code).strip())]
        if row.empty:
            return
        tipo = str(row[tcol].iloc[0]).upper()
        data = str(row[dcol].iloc[0]).strip()
        if ("PASTOR" in tipo) and data and "SGU" in self.widgets:
            de, se = self.widgets["SGU"]
            qd = _parse_dt_any(data)
            if qd.isValid():
                de.setDate(qd)
                se.setCurrentText("Pago")

    def on_fluig_leave(self, le: QLineEdit):
        code = str(le.text()).strip()
        if code in self.df["FLUIG"].astype(str).tolist():
            QMessageBox.warning(self, "Erro", "FLUIG existe"); le.clear(); return
        try:
            x = pd.read_excel(
                cfg_get("detalhamento_path"),
                usecols=["Nº Fluig", "Placa", "Nome", "AIT", "Data Infração", "Data Limite", "Status"],
                dtype=str
            ).fillna("")
        except Exception as e:
            QMessageBox.warning(self, "Aviso", str(e)); return

        row = x[x["Nº Fluig"].astype(str).str.strip() == code]
        if row.empty:
            self._apply_fase_pastores(code)
            return

        # preencher campos básicos, quando existirem no formulário
        if "PLACA" in self.widgets:
            self.widgets["PLACA"].setText(row["Placa"].iloc[0])
        if "INFRATOR" in self.widgets:
            self.widgets["INFRATOR"].setText(row["Nome"].iloc[0])
        if "NOTIFICACAO" in self.widgets:
            self.widgets["NOTIFICACAO"].setText(row["AIT"].iloc[0])

        # MES/ANO a partir da Data Infração (opcional)
        try:
            dt = pd.to_datetime(row["Data Infração"].iloc[0], dayfirst=False)
            from constants import PORTUGUESE_MONTHS
            if "MES" in self.widgets:
                self.widgets["MES"].setText(PORTUGUESE_MONTHS.get(dt.month, ""))
            if "ANO" in self.widgets:
                self.widgets["ANO"].setText(str(dt.year))
        except:
            pass

        # Preencher DATA INDICAÇÃO a partir de Data Limite, se existir
        try:
            d2 = pd.to_datetime(row["Data Limite"].iloc[0], dayfirst=False)
            if "DATA INDICAÇÃO" in self.widgets and isinstance(self.widgets["DATA INDICAÇÃO"], tuple):
                de, _ = self.widgets["DATA INDICAÇÃO"]
                de.setDate(QDate(d2.year, d2.month, d2.day))
        except:
            pass

        self._apply_fase_pastores(code)

    def salvar(self):
        new = {}
        for c, w in self.widgets.items():
            if isinstance(w, tuple):
                d, s = w
                new[c] = "" if d.date() == d.minimumDate() else d.date().toString(DATE_FORMAT)
                new[f"{c}_STATUS"] = s.currentText()
            else:
                new[c] = w.currentText() if isinstance(w, QComboBox) else w.text().strip()

        if new.get("FLUIG", "") in self.df["FLUIG"].astype(str).tolist():
            QMessageBox.warning(self, "Erro", "FLUIG já existe"); return

        self.df.loc[len(self.df)] = new
        csv = cfg_get("geral_multas_csv")
        os.makedirs(os.path.dirname(csv), exist_ok=True)

        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""
        self.df.to_csv(csv, index=False)

        # criar pasta da multa e anexar PDF
        try:
            infr, ano, mes = new.get("INFRATOR", ""), new.get("ANO", ""), new.get("MES", "")
            placa, notificacao, fluig = new.get("PLACA", ""), new.get("NOTIFICACAO", ""), new.get("FLUIG", "")
            dest = build_multa_dir(infr, ano, mes, placa, notificacao, fluig)
            os.path.isdir(dest) or os.makedirs(dest, exist_ok=True)
            if not os.path.isdir(dest):
                QMessageBox.warning(self, "Aviso", "Pasta não criada")
        except:
            pass

        self.anexar_pdf()
        QMessageBox.information(self, "Sucesso", "Multa inserida.")
        self.accept()

    def anexar_pdf(self):
        try:
            infr = self.widgets.get("INFRATOR")
            ano  = self.widgets.get("ANO")
            mes  = self.widgets.get("MES")
            placa = self.widgets.get("PLACA")
            notif = self.widgets.get("NOTIFICACAO")
            fluig = self.widgets.get("FLUIG")

            if not (infr and ano and mes and placa and notif and fluig):
                return

            infr, ano, mes = infr.text().strip(), ano.text().strip(), mes.text().strip()
            placa, notif, fluig = placa.text().strip(), notif.text().strip(), fluig.text().strip()
            if not all([infr, ano, mes, placa, notif, fluig]):
                return

            dest = build_multa_dir(infr, ano, mes, placa, notif, fluig)
            os.makedirs(dest, exist_ok=True)
            pdf, _ = QFileDialog.getOpenFileName(self, "Selecione PDF", "", "PDF Files (*.pdf)")
            if pdf:
                shutil.copy(pdf, os.path.join(dest, os.path.basename(pdf)))
        except:
            pass


# ---------------------- DIALOGO: EDITAR ----------------------
class EditarDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Editar Multa")
        self.resize(720, 560)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        v = QVBoxLayout(self)
        top = QHBoxLayout()

        csv = cfg_get("geral_multas_csv")
        self.df = ensure_status_cols(pd.read_csv(csv, dtype=str).fillna(""), csv_path=csv)
        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""
            self.df.to_csv(csv, index=False)

        self.le_key = QLineEdit(); self.le_key.setPlaceholderText("Digite FLUIG para carregar")
        comp = QCompleter(sorted(self.df["FLUIG"].dropna().astype(str).unique()))
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.le_key.setCompleter(comp)

        btn_load = QPushButton("Carregar")
        top.addWidget(self.le_key); top.addWidget(btn_load)
        v.addLayout(top)

        self.formw = QWidget(); self.form = QFormLayout(self.formw)
        self.widgets = {}
        v.addWidget(self.formw)

        bar = QHBoxLayout()
        btn_save = QPushButton("Salvar"); btn_close = QPushButton("Fechar")
        bar.addWidget(btn_save); bar.addStretch(1); bar.addWidget(btn_close)
        v.addLayout(bar)

        btn_load.clicked.connect(self.load_record)
        btn_save.clicked.connect(self.save_record)
        btn_close.clicked.connect(self.reject)

    def load_record(self):
        key = self.le_key.text().strip()
<<<<<<< HEAD
        if not key:
            return

=======
        if not key: return
>>>>>>> parent of 43624db (CORREÇÕES DAS JANELAS)
        csv = cfg_get("geral_multas_csv")
        self.df = ensure_status_cols(pd.read_csv(csv, dtype=str).fillna(""), csv_path=csv)
        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""
<<<<<<< HEAD

        rows = self.df.index[self.df.get("FLUIG", pd.Series([], dtype=str)).astype(str) == key].tolist()
=======
        rows = self.df.index[self.df["FLUIG"].astype(str)==key].tolist()
>>>>>>> parent of 43624db (CORREÇÕES DAS JANELAS)
        if not rows:
            QMessageBox.warning(self,"Aviso","FLUIG não encontrado"); return
        i = rows[0]
<<<<<<< HEAD

        # limpar form anterior
        while self.form.count():
            item = self.form.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.widgets.clear()

        # colunas SEM *_STATUS e sem as ignoradas
        cols_sem_status = [col for col in self.df.columns if not str(col).endswith("_STATUS") and col not in IGNORED_COLS]

        for col in cols_sem_status:
            if col in self.widgets:
                continue
            if col in DATE_COLS_MUL:
                d = QDateEdit()
                d.setCalendarPopup(True)
                d.setDisplayFormat(DATE_FORMAT)
                d.setMinimumDate(QDate(1752, 9, 14))
                d.setSpecialValueText("")
                qd = to_qdate_flexible(self.df.at[i, col])
                d.setDate(qd if qd.isValid() else d.minimumDate())
                s = QComboBox(); s.addItems(["", "Pendente", "Pago", "Vencido"])
                s.setCurrentText(self.df.at[i, f"{col}_STATUS"] if f"{col}_STATUS" in self.df.columns else "")
                box = QWidget(); hb = QHBoxLayout(box); hb.setContentsMargins(0, 0, 0, 0); hb.addWidget(d); hb.addWidget(s)
                self.form.addRow(col, box)
                self.widgets[col] = (d, s)
            elif col == "ORGÃO":
                cb = QComboBox(); cb.addItems(ORGAOS); cb.setCurrentText(self.df.at[i, col])
                self.form.addRow(col, cb)
                self.widgets[col] = cb
            else:
                w = QLineEdit(str(self.df.at[i, col]))
                self.form.addRow(col, w)
                self.widgets[col] = w

=======
        for c in [col for col in self.df.columns if not c.endswith("_STATUS")]:
            if c in self.widgets: continue
            if c in DATE_COLS:
                from PyQt6.QtWidgets import QDateEdit
                d = QDateEdit(); d.setCalendarPopup(True); d.setDisplayFormat(DATE_FORMAT)
                d.setMinimumDate(QDate(1752,9,14)); d.setSpecialValueText("")
                qd = to_qdate_flexible(self.df.at[i,c])
                d.setDate(qd if qd.isValid() else d.minimumDate())
                s = QComboBox(); s.addItems(["","Pendente","Pago","Vencido"])
                s.setCurrentText(self.df.at[i, f"{c}_STATUS"] if f"{c}_STATUS" in self.df.columns else "")
                box = QWidget(); hb = QHBoxLayout(box); hb.setContentsMargins(0,0,0,0); hb.addWidget(d); hb.addWidget(s)
                self.form.addRow(c,box); self.widgets[c]=(d,s)
            elif c=="ORGÃO":
                cb=QComboBox(); cb.addItems(ORGAOS); cb.setCurrentText(self.df.at[i,c])
                self.form.addRow(c,cb); self.widgets[c]=cb
            else:
                w=QLineEdit(self.df.at[i,c]); self.form.addRow(c,w); self.widgets[c]=w
>>>>>>> parent of 43624db (CORREÇÕES DAS JANELAS)
        self.current_index = i

    def save_record(self):
        if not hasattr(self, "current_index"):
            return
        i = self.current_index
        for c, w in self.widgets.items():
            if isinstance(w, tuple):
                d, s = w
                self.df.at[i, c] = "" if d.date() == d.minimumDate() else d.date().toString(DATE_FORMAT)
                self.df.at[i, f"{c}_STATUS"] = s.currentText()
            else:
                self.df.at[i, c] = w.currentText() if isinstance(w, QComboBox) else w.text().strip()
        self.df.to_csv(cfg_get("geral_multas_csv"), index=False)
        QMessageBox.information(self, "Sucesso", "Multa editada.")
        self.accept()


# ---------------------- DIALOGO: EXCLUIR ----------------------
class ExcluirDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Excluir Multa")
        self.resize(520, 160)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        v = QVBoxLayout(self)
        top = QHBoxLayout()

        csv = cfg_get("geral_multas_csv")
        self.df = ensure_status_cols(pd.read_csv(csv, dtype=str).fillna(""), csv_path=csv)
        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""
            self.df.to_csv(csv, index=False)

        self.le_key = QLineEdit(); self.le_key.setPlaceholderText("Digite FLUIG para excluir")
        comp = QCompleter(sorted(self.df["FLUIG"].dropna().astype(str).unique()))
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.le_key.setCompleter(comp)

        btn_delete = QPushButton("Excluir")
        top.addWidget(self.le_key); top.addWidget(btn_delete)
        v.addLayout(top)

        bar = QHBoxLayout()
        btn_close = QPushButton("Fechar"); bar.addStretch(1); bar.addWidget(btn_close)
        v.addLayout(bar)

        btn_delete.clicked.connect(self.do_delete)
        btn_close.clicked.connect(self.reject)

    def do_delete(self):
        key = self.le_key.text().strip()
        if not key:
            return
        csv = cfg_get("geral_multas_csv")
        self.df = ensure_status_cols(pd.read_csv(csv, dtype=str).fillna(""), csv_path=csv)
        rows = self.df.index[self.df["FLUIG"].astype(str) == key].tolist()
        if not rows:
            QMessageBox.warning(self, "Aviso", "FLUIG não encontrado"); return
        i = rows[0]
        try:
            infr  = str(self.df.at[i, "INFRATOR"]) if "INFRATOR" in self.df.columns else ""
            ano   = str(self.df.at[i, "ANO"]) if "ANO" in self.df.columns else ""
            mes   = str(self.df.at[i, "MES"]) if "MES" in self.df.columns else ""
            placa = str(self.df.at[i, "PLACA"]) if "PLACA" in self.df.columns else ""
            notif = str(self.df.at[i, "NOTIFICACAO"]) if "NOTIFICACAO" in self.df.columns else ""
            fluig = str(self.df.at[i, "FLUIG"]) if "FLUIG" in self.df.columns else ""
            root = cfg_get("multas_root")
            sub = f"{placa}_{notif}_FLUIG({fluig})"
            path = os.path.join(root, infr.strip(), str(ano).strip(), str(mes).strip(), sub)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                # limpar diretórios vazios até 3 níveis acima (mas sempre dentro do root)
                p = os.path.dirname(path)
                root_abs = os.path.abspath(root)
                for _ in range(3):
                    if not p:
                        break
                    p_abs = os.path.abspath(p)
                    if os.path.isdir(p) and not os.listdir(p) and os.path.commonpath([p_abs, root_abs]) == root_abs:
                        try:
                            os.rmdir(p)
                        except:
                            break
                        p = os.path.dirname(p)
                    else:
                        break
            if os.path.isdir(path):
                QMessageBox.warning(self, "Aviso", "Pasta não removida")
        except:
            pass

        self.df = self.df.drop(i).reset_index(drop=True)
        self.df.to_csv(csv, index=False)
        QMessageBox.information(self, "Sucesso", "Multa excluída.")
        self.accept()


# ---------------------- VIEW PRINCIPAL (GERAL) ----------------------
class GeralMultasView(QWidget):
    def __init__(self, parent_for_edit=None):
        super().__init__()
        self.parent_for_edit = parent_for_edit

        fm = QFontMetrics(self.font())
        self.max_pix = fm.horizontalAdvance("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

        df = pd.read_csv(cfg_get("geral_multas_csv"), dtype=str).fillna("")
        self.df_original = ensure_status_cols(df, csv_path=cfg_get("geral_multas_csv"))

        if "COMENTARIO" not in self.df_original.columns:
            self.df_original["COMENTARIO"] = ""
            self.df_original.to_csv(cfg_get("geral_multas_csv"), index=False)

        self.df_filtrado = self.df_original.copy()

        # Mostrar tudo que não é *_STATUS, EXCETO as colunas que você quer ignorar
        self.cols_show = [c for c in self.df_original.columns if not c.endswith("_STATUS") and c not in IGNORED_COLS]

        root = QVBoxLayout(self)

        # Cabeçalho
        header_card = QFrame(); header_card.setObjectName("card"); apply_shadow(header_card, radius=18)
        hv = QVBoxLayout(header_card)
        title = QLabel("Multas em Aberto")
        title.setFont(QFont("Arial", 18, weight=QFont.Weight.Bold))
        hv.addWidget(title)

        # Filtros por coluna (mantive a sua UI, mas agora ela não inclui colunas ignoradas)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        self.filtros_layout = QHBoxLayout(inner)
        self.filtros_layout.setContentsMargins(0, 0, 0, 0)
        self.filtros_layout.setSpacing(8)
        self.mode_filtros = {}; self.multi_filtros = {}; self.text_filtros = {}

        for coluna in self.cols_show:
            box = QVBoxLayout()
            label = QLabel(coluna); label.setObjectName("colTitle"); label.setWordWrap(True); label.setMaximumWidth(self.max_pix)
            line1 = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos", "Excluir vazios", "Somente vazios"]); mode.currentTextChanged.connect(self.atualizar_filtro)
            ms = CheckableComboBox(self.df_original[coluna].dropna().astype(str).unique()); ms.changed.connect(self.atualizar_filtro)
            line1.addWidget(mode); line1.addWidget(ms)
            box.addWidget(label); box.addLayout(line1)
            line2 = QVBoxLayout()
            btn_plus = QPushButton("+"); btn_plus.setFixedWidth(28)
            row = QHBoxLayout(); row.addLayout(line2, 1); row.addWidget(btn_plus)
            box.addLayout(row)
            self.mode_filtros[coluna] = mode; self.multi_filtros[coluna] = ms; self.text_filtros[coluna] = []
            self._add_text_row(coluna, line2)
            btn_plus.clicked.connect(lambda _, c=coluna, l=line2: self._add_text_row(c, l))
            self.filtros_layout.addLayout(box)

        scroll.setWidget(inner)
        hv.addWidget(scroll)
        root.addWidget(header_card)

        # Tabela
        table_card = QFrame(); table_card.setObjectName("glass"); apply_shadow(table_card, radius=18, blur=60, color=QColor(0, 0, 0, 80))
        tv = QVBoxLayout(table_card)
        self.tabela = QTableWidget()
        self.tabela.setAlternatingRowColors(True)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabela.setSortingEnabled(True)
        self.tabela.horizontalHeader().setSortIndicatorShown(True)
        self.tabela.cellDoubleClicked.connect(self.on_double_click)
        tv.addWidget(self.tabela)

        buttons = QHBoxLayout()
        btn_visao = QPushButton("Visão Geral"); btn_visao.clicked.connect(self.mostrar_visao)
        btn_limpar = QPushButton("Limpar filtros"); btn_limpar.clicked.connect(self.limpar_filtros)
        btn_inserir = QPushButton("Inserir"); btn_inserir.clicked.connect(lambda: self.parent_for_edit.inserir())
        btn_editar = QPushButton("Editar"); btn_editar.clicked.connect(lambda: self.parent_for_edit.editar())
        btn_excluir = QPushButton("Excluir"); btn_excluir.setObjectName("danger"); btn_excluir.clicked.connect(lambda: self.parent_for_edit.excluir())
        btn_fluig = QPushButton("CONFERIR FLUIG"); btn_fluig.clicked.connect(lambda: self.parent_for_edit.conferir_fluig())
        btn_past = QPushButton("FASE PASTORES"); btn_past.clicked.connect(lambda: self.parent_for_edit.fase_pastores())
        btn_export = QPushButton("Exportar Excel"); btn_export.clicked.connect(self.exportar_excel)
        buttons.addWidget(btn_visao); buttons.addWidget(btn_limpar); buttons.addWidget(btn_inserir); buttons.addWidget(btn_editar); buttons.addWidget(btn_excluir); buttons.addWidget(btn_fluig); buttons.addWidget(btn_past); buttons.addStretch(1); buttons.addWidget(btn_export)
        tv.addLayout(buttons)
        root.addWidget(table_card)

        self.preencher_tabela(self.df_filtrado)

    def _add_text_row(self, col, where):
        le = QLineEdit(); le.setPlaceholderText(f"Filtrar {col}..."); le.setMaximumWidth(self.max_pix); le.textChanged.connect(self.atualizar_filtro)
        self.text_filtros[col].append(le); where.addWidget(le)

    def recarregar(self):
        df = pd.read_csv(cfg_get("geral_multas_csv"), dtype=str).fillna("")
        self.df_original = ensure_status_cols(df, csv_path=cfg_get("geral_multas_csv"))
        if "COMENTARIO" not in self.df_original.columns:
            self.df_original["COMENTARIO"] = ""
            self.df_original.to_csv(cfg_get("geral_multas_csv"), index=False)

        self.df_filtrado = self.df_original.copy()
        self.cols_show = [c for c in self.df_original.columns if not c.endswith("_STATUS") and c not in IGNORED_COLS]
        self.atualizar_filtro()

    def mostrar_visao(self):
        dlg = SummaryDialog(self.df_filtrado[self.cols_show])
        dlg.exec()

    def limpar_filtros(self):
        for mode in self.mode_filtros.values():
            mode.blockSignals(True); mode.setCurrentIndex(0); mode.blockSignals(False)
        for ms in self.multi_filtros.values():
            vals = [ms.itemText(i) for i in range(ms.count())]
            ms.set_values(vals)
        for col, arr in self.text_filtros.items():
            for i, le in enumerate(arr):
                le.blockSignals(True)
                if i == 0:
                    le.clear()
                else:
                    le.setParent(None)
            self.text_filtros[col] = [arr[0]]
            arr[0].blockSignals(False)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()
        # filtro “em aberto”: se houver STATUS, mantenha os que não são "Pago"
        if "STATUS" in df.columns:
            df = df[df["STATUS"].astype(str).str.lower() != "pago"]

        for coluna in self.cols_show:
            mode = self.mode_filtros[coluna].currentText()
            if mode == "Excluir vazios":
                df = df[df[coluna].astype(str) != ""]
            elif mode == "Somente vazios":
                df = df[df[coluna].astype(str) == ""]

            sels = [s for s in self.multi_filtros[coluna].selected_values() if s]
            if sels:
                df = df[df[coluna].astype(str).isin(sels)]

            termos = []
            for le in self.text_filtros[coluna]:
                t = le.text().strip()
                if t:
                    termos.append(t)
            if termos:
                s = df[coluna].astype(str).str.lower()
                rgx = "|".join(re.escape(t.lower()) for t in termos)
                df = df[s.str.contains(rgx, na=False)]

        self.df_filtrado = df

        # atualizar opções dos combos após filtro
        for col in self.cols_show:
            ms = self.multi_filtros[col]
            current_sel = ms.selected_values()
            ms.set_values(self.df_filtrado[col].dropna().astype(str).unique())
            if current_sel:
                for i in range(ms.count()):
                    if ms.itemText(i) in current_sel:
                        idx = ms.model().index(i, 0)
                        ms.model().setData(idx, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
                ms._update_text()

        self.preencher_tabela(self.df_filtrado)

    def preencher_tabela(self, df):
        # garantir coluna de comentário
        if "COMENTARIO" not in df.columns:
            df = df.copy()
            df["COMENTARIO"] = ""

        show = df[self.cols_show].reset_index(drop=True)
        df_idx = df.reset_index(drop=True)

        self.tabela.clear()
        self.tabela.setColumnCount(len(show.columns) + 1)  # +1 para coluna Ações
        self.tabela.setRowCount(len(show))
        headers = [str(c) for c in show.columns] + ["Ações"]
        self.tabela.setHorizontalHeaderLabels(headers)

        for i in range(len(show)):
            for j, col in enumerate(show.columns):
                val = "" if pd.isna(show.iat[i, j]) else str(show.iat[i, j])
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

                # pintar status SOMENTE para as três datas oficiais
                if col in DATE_COLS_MUL:
                    st = str(df_idx.iloc[i].get(f"{col}_STATUS", ""))
                    _paint_status(it, st)

                self.tabela.setItem(i, j, it)

            # coluna Ações: Comentar
            key = str(df_idx.iloc[i].get("FLUIG", "")).strip()
            btn_comment = QPushButton("Comentar")
            if "COMENTARIO" in df_idx.columns:
                btn_comment.setToolTip(str(df_idx.iloc[i].get("COMENTARIO", "")).strip())
            btn_comment.clicked.connect(lambda _, k=key: self.parent_for_edit.comentar_with_key(k))
            self.tabela.setCellWidget(i, len(show.columns), btn_comment)

        self.tabela.resizeColumnsToContents()
        self.tabela.resizeRowsToContents()

    def exportar_excel(self):
        try:
            self.df_filtrado[self.cols_show].to_excel("geral_multas_filtrado.xlsx", index=False)
            QMessageBox.information(self, "Exportado", "geral_multas_filtrado.xlsx criado.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def on_double_click(self, row, col):
        if self.parent_for_edit is None:
            return
        dfv = self.df_filtrado.reset_index(drop=True)
        key = dfv.iloc[row].get("FLUIG", "")
        if not key:
            return
        self.parent_for_edit.editar_with_key(key)


# ---------------------- JANELA (CONTÊINER) ----------------------
class InfraMultasWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Infrações e Multas")
        self.resize(1240, 820)

        lay = QVBoxLayout(self)
        self.view_geral = GeralMultasView(self)
        lay.addWidget(self.view_geral)

        self.watcher = QFileSystemWatcher()
        csv = cfg_get("geral_multas_csv")
        if os.path.exists(csv):
            self.watcher.addPath(csv)
        self.watcher.fileChanged.connect(self._csv_changed)

    def _csv_changed(self, path):
        if not os.path.exists(path):
            QTimer.singleShot(500, lambda: self._readd_watch(path))
            return
        QTimer.singleShot(500, self.reload_geral)

    def _readd_watch(self, path):
        if os.path.exists(path):
            self.watcher.addPath(path)
        self.reload_geral()

    def reload_geral(self):
        self.view_geral.recarregar()

    def conferir_fluig(self):
        try:
            detalhamento_path = cfg_get("detalhamento_path")
            df_det = pd.read_excel(detalhamento_path, dtype=str).fillna("")
            if df_det.empty or len(df_det.columns) < 2:
                QMessageBox.warning(self, "Aviso", "Planilha inválida."); return

            status_col = next((c for c in df_det.columns if c.strip().lower() == "status"), df_det.columns[1])
            mask_aberta = df_det[status_col].astype(str).str.strip().str.lower().eq("aberta")
            df_open = df_det[mask_aberta].copy()

            if "Nº Fluig" in df_open.columns:
                fcol = "Nº Fluig"
            else:
                fcol = next((c for c in df_open.columns if "fluig" in c.lower()), None)
            if not fcol:
                QMessageBox.warning(self, "Aviso", "Coluna de Fluig não encontrada."); return

            df_csv = ensure_status_cols(pd.read_csv(cfg_get("geral_multas_csv"), dtype=str).fillna(""), csv_path=cfg_get("geral_multas_csv"))
            if "COMENTARIO" not in df_csv.columns:
                df_csv["COMENTARIO"] = ""
                df_csv.to_csv(cfg_get("geral_multas_csv"), index=False)

            fluig_det = set(df_open[fcol].astype(str).str.strip())
            fluig_csv = set(df_csv["FLUIG"].astype(str).str.strip()) if "FLUIG" in df_csv.columns else set()
            no_csv_codes = sorted([c for c in fluig_det if c and c not in fluig_csv])
            no_det_codes = sorted([c for c in fluig_csv if c and c not in fluig_det])

            left_cols = [fcol] + [c for c in ["Placa", "Nome", "AIT", "Data Limite", "Data Infração", "Status"] if c in df_open.columns]
            df_left = df_open[df_open[fcol].astype(str).str.strip().isin(no_csv_codes)][left_cols].copy()
            df_left.rename(columns={fcol: "Nº Fluig"}, inplace=True)

            right_cols = [c for c in ["FLUIG", "PLACA", "INFRATOR", "NOTIFICACAO", "ANO", "MES", "COMENTARIO"] if c in df_csv.columns]
            df_right = df_csv[df_csv["FLUIG"].astype(str).str.strip().isin(no_det_codes)][right_cols].copy()

            dlg = ConferirFluigDialog(self, df_left, df_right)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def inserir(self, prefill_fluig=None):
        dlg = InserirDialog(self, prefill_fluig)
        dlg.exec()
        self.reload_geral()

    def editar(self):
        dlg = EditarDialog(self)
        dlg.exec()
        self.reload_geral()

    def editar_with_key(self, key):
        dlg = EditarDialog(self)
        dlg.le_key.setText(str(key))
        dlg.load_record()
        dlg.exec()
        self.reload_geral()

    def excluir(self):
        dlg = ExcluirDialog(self)
        dlg.exec()
        self.reload_geral()

    def fase_pastores(self):
        try:
            path = cfg_get("pastores_file")
            if not path or not os.path.exists(path):
                QMessageBox.warning(self, "Aviso", "Planilha Fase Pastores não configurada na aba Base.")
                return
            dfp = pd.read_excel(path, dtype=str).fillna("")
            fcol = next((c for c in dfp.columns if "fluig" in c.lower()), None)
            dcol = next((c for c in dfp.columns if "data" in c.lower() and "pastor" in c.lower()), None)
            tcol = next((c for c in dfp.columns if "tipo" in c.lower()), None)
            if not fcol or not dcol or not tcol:
                QMessageBox.warning(self, "Aviso", "Colunas inválidas em Fase Pastores.")
                return

            df = ensure_status_cols(pd.read_csv(cfg_get("geral_multas_csv"), dtype=str).fillna(""), csv_path=None)
            if "COMENTARIO" not in df.columns:
                df["COMENTARIO"] = ""

            idx = {str(f).strip(): i for i, f in enumerate(df.get("FLUIG", pd.Series([], dtype=str)).astype(str))}
            changed = False
            for _, r in dfp.iterrows():
                f = str(r[fcol]).strip()
                tipo = str(r[tcol]).upper()
                data = str(r[dcol]).strip()
                if not f or f not in idx:
                    continue
                if "PASTOR" not in tipo or not data:
                    continue
                qd = _parse_dt_any(data)
                if not qd.isValid():
                    continue
                i = idx[f]
                df.at[i, "SGU"] = qd.toString(DATE_FORMAT)
                df.at[i, "SGU_STATUS"] = "Pago"
                changed = True
            if changed:
                df.to_csv(cfg_get("geral_multas_csv"), index=False)
                QMessageBox.information(self, "Sucesso", "Atualizado.")
            else:
                QMessageBox.information(self, "Sucesso", "Nada para atualizar.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
        self.reload_geral()

    # ===== Novo: comentar por FLUIG =====
    def comentar_with_key(self, key):
        key = str(key).strip()
        if not key:
            QMessageBox.warning(self, "Comentário", "FLUIG inválido para comentar.")
            return
        csv = cfg_get("geral_multas_csv")
        df = pd.read_csv(csv, dtype=str).fillna("")
        if "COMENTARIO" not in df.columns:
            df["COMENTARIO"] = ""
        rows = df.index[df.get("FLUIG", pd.Series([], dtype=str)).astype(str).str.strip() == key].tolist()
        if not rows:
            QMessageBox.warning(self, "Comentário", f"FLUIG {key} não encontrado no CSV.")
            return
        i = rows[0]
        atual = str(df.at[i, "COMENTARIO"])
        texto, ok = QInputDialog.getMultiLineText(self, "Comentário", f"FLUIG {key} - Digite/edite o comentário:", atual)
        if ok:
            df.at[i, "COMENTARIO"] = texto.strip()
            df.to_csv(csv, index=False)
            QMessageBox.information(self, "Comentário", "Comentário salvo.")
            self.reload_geral()