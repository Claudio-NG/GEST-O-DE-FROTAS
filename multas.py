import os, re, shutil, pandas as pd
from PyQt6.QtCore import Qt, QDate, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
    QDialog, QFormLayout, QFileDialog, QSizePolicy, QScrollArea, QInputDialog,
    QDateEdit, QCompleter
)

from gestao_frota_single import (
    DATE_FORMAT, DATE_COLS, STATUS_COLOR,
    GERAL_MULTAS_CSV, MULTAS_ROOT, PASTORES_DIR, ORGAOS,
    PORTUGUESE_MONTHS,
    cfg_get, cfg_set, cfg_all
)
from utils import (
    ensure_status_cols, apply_shadow, _paint_status, to_qdate_flexible,
    build_multa_dir, _parse_dt_any, CheckableComboBox, SummaryDialog, ConferirFluigDialog
)


DATE_COLS_MUL = ["DATA INDICAÇÃO", "BOLETO", "SGU"] 

IGNORED_COLS = {"LANÇAMENTOS DE NFF", "VALIDAÇÃO", "CONCLUSÃO"}

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

        # ordem: FLUIG primeiro + demais colunas SEM *_STATUS (pulando ignoradas)
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
    
            if "MES" in self.widgets:
                self.widgets["MES"].setText(PORTUGUESE_MONTHS.get(dt.month, ""))
            if "ANO" in self.widgets:
                self.widgets["ANO"].setText(str(dt.year))
        except:
            pass

        
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
        if not key:
            return

        csv = cfg_get("geral_multas_csv")
        self.df = ensure_status_cols(pd.read_csv(csv, dtype=str).fillna(""), csv_path=csv)
        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""

        rows = self.df.index[self.df.get("FLUIG", pd.Series([], dtype=str)).astype(str) == key].tolist()
        if not rows:
            QMessageBox.warning(self, "Aviso", "FLUIG não encontrado")
            return
        i = rows[0]

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



# --- no topo do multas.py (se já existir, mantenha) ---
import os
import re
import pandas as pd

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QScrollArea, QHBoxLayout, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)


from utils import apply_shadow, ensure_status_cols, CheckableComboBox


# ✅ só essas 3 datas contam para status/pintura
DATE_COLS_MUL = ["DATA INDICAÇÃO", "BOLETO", "SGU"]

# ✅ colunas que NÃO devem aparecer (nem em tabela, nem em filtros)
IGNORED_COLS = {"LANÇAMENTO NFF", "VALIDACAO NFF", "CONCLUSAO"}


def _paint_status(item: QTableWidgetItem, status: str):
    st = (status or "").strip()
    if not st:
        return
    if st in STATUS_COLOR:
        bg = STATUS_COLOR[st]
        item.setBackground(bg)
        yiq = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
        item.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))


# ---------------------- VIEW PRINCIPAL (GERAL) ----------------------
class GeralMultasView(QWidget):
    """
    - 1 (um) campo de texto global que filtra TODAS as colunas.
    - Para cada coluna, mantém SOMENTE os botões (modo vazios/cheios + multiseleção de valores).
    - Colunas LANÇAMENTO NFF / VALIDACAO NFF / CONCLUSAO são ignoradas.
    - Pintura de status só em: DATA INDICAÇÃO, BOLETO, SGU.
    """
    def __init__(self, parent_for_edit=None):
        super().__init__()
        self.parent_for_edit = parent_for_edit

        fm = QFontMetrics(self.font())
        self.max_pix = fm.horizontalAdvance("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

        # carga
        df = pd.read_csv(cfg_get("geral_multas_csv"), dtype=str).fillna("")
        self.df_original = ensure_status_cols(df, csv_path=cfg_get("geral_multas_csv"))

        # garantir coluna de comentário persistida
        if "COMENTARIO" not in self.df_original.columns:
            self.df_original["COMENTARIO"] = ""
            self.df_original.to_csv(cfg_get("geral_multas_csv"), index=False)

        self.df_filtrado = self.df_original.copy()

        # colunas visíveis: tudo que não é *_STATUS e não está ignorado
        self.cols_show = [c for c in self.df_original.columns if not c.endswith("_STATUS") and c not in IGNORED_COLS]

        root = QVBoxLayout(self)

        # ===== Cabeçalho =====
        header_card = QFrame(); header_card.setObjectName("card"); apply_shadow(header_card, radius=18)
        hv = QVBoxLayout(header_card)

        title = QLabel("Multas em Aberto")
        title.setFont(QFont("Arial", 18, weight=QFont.Weight.Bold))
        hv.addWidget(title)

        # ---- Campo ÚNICO de filtro global ----
        sc_global = QScrollArea(); sc_global.setWidgetResizable(True)
        wrap_g = QWidget(); rowg = QHBoxLayout(wrap_g)
        rowg.addWidget(QLabel("Filtro global:"))
        self.global_box = QLineEdit()
        self.global_box.setPlaceholderText("Digite aqui para filtrar em TODAS as colunas…")
        self.global_box.setMaximumWidth(self.max_pix)
        self.global_box.textChanged.connect(self.atualizar_filtro)
        rowg.addWidget(self.global_box, 1)
        sc_global.setWidget(wrap_g)
        hv.addWidget(sc_global)

        # ---- Botões por coluna (modo + multiseleção) — sem texto por coluna ----
        sc_seg = QScrollArea(); sc_seg.setWidgetResizable(True)
        inner = QWidget(); hl = QHBoxLayout(inner); hl.setContentsMargins(0,0,0,0); hl.setSpacing(8)

        self.mode_filtros = {}   # coluna -> QComboBox ("Todos/Excluir vazios/Somente vazios")
        self.multi_filtros = {}  # coluna -> CheckableComboBox (valores únicos da coluna)

        for coluna in self.cols_show:
            box = QVBoxLayout()
            lbl = QLabel(coluna); lbl.setObjectName("colTitle"); lbl.setWordWrap(True); lbl.setMaximumWidth(self.max_pix)
            box.addWidget(lbl)

            line = QHBoxLayout()
            mode = QComboBox(); mode.addItems(["Todos", "Excluir vazios", "Somente vazios"])
            mode.currentTextChanged.connect(self.atualizar_filtro)
            ms = CheckableComboBox(self.df_original[coluna].dropna().astype(str).unique()); ms.changed.connect(self.atualizar_filtro)
            line.addWidget(mode); line.addWidget(ms)
            box.addLayout(line)

            hl.addLayout(box)
            self.mode_filtros[coluna] = mode
            self.multi_filtros[coluna] = ms

        sc_seg.setWidget(inner)
        hv.addWidget(sc_seg)
        root.addWidget(header_card)

        # ===== Tabela =====
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

        self.atualizar_filtro()  # render inicial

    # ===== ações =====
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
        from relatorios import SummaryDialog  # se você já tiver esse dialog
        try:
            dlg = SummaryDialog(self.df_filtrado[self.cols_show])
            dlg.exec()
        except Exception:
            QMessageBox.information(self, "Visão Geral", "Resumo indisponível.")

    def limpar_filtros(self):
        # limpa campo global
        self.global_box.blockSignals(True); self.global_box.clear(); self.global_box.blockSignals(False)
        # reset botões por coluna
        for mode in self.mode_filtros.values():
            mode.blockSignals(True); mode.setCurrentIndex(0); mode.blockSignals(False)
        for ms in self.multi_filtros.values():
            vals = [ms.itemText(i) for i in range(ms.count())]
            ms.set_values(vals)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()

        # mantém apenas "em aberto" se existir coluna STATUS geral
        if "STATUS" in df.columns:
            df = df[df["STATUS"].astype(str).str.lower() != "pago"]

        # ---- filtro global (todas as colunas) ----
        from utils import df_apply_global_texts
        texts = [self.global_box.text()]
        df = df_apply_global_texts(df, texts)

        # ---- botões por coluna (modo + multiseleção) ----
        for coluna in self.cols_show:
            # modo vazios/cheios
            mode = self.mode_filtros[coluna].currentText()
            if mode == "Excluir vazios":
                df = df[df[coluna].astype(str).str.strip() != ""]
            elif mode == "Somente vazios":
                df = df[df[coluna].astype(str).str.strip() == ""]

            # multiseleção
            sels = [s for s in self.multi_filtros[coluna].selected_values() if s]
            if sels:
                df = df[df[coluna].astype(str).isin(sels)]

        self.df_filtrado = df
        self.preencher_tabela(self.df_filtrado)

    def preencher_tabela(self, df):
        # garantir COMENTARIO
        if "COMENTARIO" not in df.columns:
            df = df.copy(); df["COMENTARIO"] = ""

        show = df[self.cols_show].reset_index(drop=True)
        df_idx = df.reset_index(drop=True)

        self.tabela.clear()
        self.tabela.setColumnCount(len(show.columns) + 1)  # +1 Ações
        self.tabela.setRowCount(len(show))
        headers = [str(c) for c in show.columns] + ["Ações"]
        self.tabela.setHorizontalHeaderLabels(headers)

        for i in range(len(show)):
            for j, col in enumerate(show.columns):
                val = "" if pd.isna(show.iat[i, j]) else str(show.iat[i, j])
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

                # pintar status SOMENTE nas 3 datas oficiais
                if col in DATE_COLS_MUL:
                    st = str(df_idx.iloc[i].get(f"{col}_STATUS", ""))
                    _paint_status(it, st)

                self.tabela.setItem(i, j, it)

            # coluna Ações: Comentar
            key = str(df_idx.iloc[i].get("FLUIG", "")).strip()
            btn_comment = QPushButton("Comentar")
            if "COMENTARIO" in df_idx.columns:
                btn_comment.setToolTip(str(df_idx.iloc[i].get("COMENTARIO", "")).strip())
            if self.parent_for_edit:
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


# multas.py
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel,
    QTabWidget, QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox
)
import pandas as pd

from gestao_frota_single import cfg_get, ensure_status_cols, DATE_COLS
from utils import apply_shadow, GlobalFilterBar, df_apply_global_texts

# Se não existir na sua base, deixe o stub para não quebrar import:
try:
    from multas import CenarioGeralWindow as _CGW_CHECK  # se a classe estiver noutro arquivo seu
except Exception:
    _CGW_CHECK = None

class CenarioGeralWindow(QWidget):
    """
    Cenário Geral de Multas com cálculo de pontuação por valor.
    Abre em ABA e tem filtro global único.
    """
    def __init__(self):
        super().__init__()
        self.df_base = self._load_df()

        root = QVBoxLayout(self)

        # header + filtro
        head = QFrame(); head.setObjectName("card"); apply_shadow(head, radius=16)
        hv = QVBoxLayout(head)
        hv.addWidget(QLabel("Cenário Geral de Multas"), alignment=Qt.AlignmentFlag.AlignLeft)
        self.filter = GlobalFilterBar("Filtro global:")
        self.filter.changed.connect(self._apply_filter)
        hv.addWidget(self.filter)
        root.addWidget(head)

        # tabela
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.table, 1)

        self._apply_filter()

    def _load_df(self) -> pd.DataFrame:
        path = cfg_get("geral_multas_csv")
        if not path:
            QMessageBox.information(self, "Cenário Geral", "Configure o caminho do GERAL_MULTAS.csv em Base.")
            return pd.DataFrame()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Cenário Geral", f"Arquivo não encontrado:\n{path}")
            return pd.DataFrame()
        df = pd.read_csv(path, dtype=str).fillna("")
        df = ensure_status_cols(df, csv_path=None)

        # normaliza valor e cria SCORE
        def _to_num(s: str) -> float:
            s = str(s or "").strip()
            s = s.replace(".", "").replace(",", ".")
            try: return float(s)
            except: return 0.0

        if "VALOR" not in df.columns:
            cand = [c for c in df.columns if c.upper() in ("VALOR MULTA","VALOR_MULTA","VALOR DA MULTA")]
            df["VALOR"] = df[cand[0]] if cand else ""

        df["VALOR_NUM"] = df["VALOR"].map(_to_num)
        def _score(v):
            v = float(v or 0)
            if v >= 1000: return 5
            if v >= 500:  return 3
            if v >= 200:  return 2
            return 1
        df["SCORE"] = df["VALOR_NUM"].map(_score)

        # Nome do motorista
        if "INFRATOR" in df.columns:
            df["MOTORISTA"] = df["INFRATOR"]
        elif "NOME" in df.columns:
            df["MOTORISTA"] = df["NOME"]
        else:
            df["MOTORISTA"] = ""

        return df

    def _apply_filter(self):
        texts = self.filter.values()
        dfv = df_apply_global_texts(self.df_base, texts)

        # colunas principais
        cols = []
        for c in ["FLUIG","MOTORISTA","PLACA","ÓRGÃO","ORGÃO","ORGAO","INFRACAO","INFRAÇÃO","TIPO INFRAÇÃO","VALOR","VALOR_NUM","SCORE"]:
            if c in dfv.columns and c not in cols:
                cols.append(c)
        # adiciona datas oficiais
        for c in DATE_COLS:
            if c in dfv.columns: cols.append(c)

        if not cols:
            cols = list(dfv.columns)

        self._fill_table(dfv, cols)

    def _fill_table(self, df, cols):
        self.table.clear()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            for j, c in enumerate(cols):
                v = "" if pd.isna(r.get(c, "")) else str(r.get(c, ""))
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, j, it)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

import os

class InfraMultasWindow(QWidget):
    """
    Tela principal de 'Infrações e Multas' com:
      - Filtro global padrão (com +)
      - Botões: 'Multas em Aberto' e 'Cenário Geral'
      - Abre abas internas via QTabWidget, mas também integra com add_or_focus do MainWindow
    """
    def __init__(self):
        super().__init__()
        self.df_base = self._load_df()

        root = QVBoxLayout(self)

        # Barra superior com ações
        top = QFrame(); top.setObjectName("card"); apply_shadow(top, radius=16)
        tv = QVBoxLayout(top)

        row1 = QHBoxLayout()
        btn_aberto = QPushButton("Multas em Aberto")
        btn_cenario = QPushButton("Cenário Geral")
        btn_aberto.clicked.connect(self._open_multas_aberto)
        btn_cenario.clicked.connect(self._open_cenario_geral)
        row1.addWidget(btn_aberto); row1.addWidget(btn_cenario); row1.addStretch(1)
        tv.addLayout(row1)

        # Filtro global
        self.filter = GlobalFilterBar("Filtro global:")
        self.filter.changed.connect(self._apply_filter_self)
        tv.addWidget(self.filter)

        root.addWidget(top)

        # Abas internas (lista + resultados)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # Aba: Lista
        self.tab_lista = QWidget(); lv = QVBoxLayout(self.tab_lista)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        lv.addWidget(self.table)
        self.tabs.addTab(self.tab_lista, "LISTA")

        self._apply_filter_self()

    def _load_df(self) -> pd.DataFrame:
        path = cfg_get("geral_multas_csv")
        if not path:
            QMessageBox.information(self, "Multas", "Configure o caminho do GERAL_MULTAS.csv em Base.")
            return pd.DataFrame()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Multas", f"Arquivo não encontrado:\n{path}")
            return pd.DataFrame()
        df = pd.read_csv(path, dtype=str).fillna("")
        return ensure_status_cols(df, csv_path=None)

    # === Filtro local (aba LISTA) ===
    def _apply_filter_self(self):
        texts = self.filter.values()
        dfv = df_apply_global_texts(self.df_base, texts)
        self._fill_table(dfv)

    def _fill_table(self, df):
        headers = list(df.columns)
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            for j, c in enumerate(headers):
                v = "" if pd.isna(r.get(c, "")) else str(r.get(c, ""))
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, j, it)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    # === Ações dos botões ===
    def _open_cenario_geral(self):
        """
        Abre a aba 'Cenário Geral' usando o add_or_focus do MainWindow, se disponível.
        Se estiver rodando fora do MainWindow, abre como aba interna.
        """
        # tenta abrir na MainWindow (abas principais)
        mw = self._find_mainwindow_with_tabs()
        if mw is not None and hasattr(mw, "add_or_focus"):
            mw.add_or_focus("Cenário Geral de Multas", lambda: CenarioGeralWindow())
            return

        # fallback: aba interna
        w = CenarioGeralWindow()
        self.tabs.addTab(w, "CENÁRIO GERAL")
        self.tabs.setCurrentWidget(w)

    def _open_multas_aberto(self):
        """
        Filtra e mostra apenas multas 'em aberto'.
        Regra simples: qualquer *_STATUS em ('Pendente','Vencido') conta como em aberto.
        """
        df = self.df_base.copy()
        if df.empty:
            QMessageBox.information(self, "Multas em Aberto", "Não há dados.")
            return
        st_cols = [c for c in df.columns if c.endswith("_STATUS")]
        if not st_cols:
            QMessageBox.information(self, "Multas em Aberto", "Colunas *_STATUS não encontradas.")
            return

        mask = pd.Series(False, index=df.index)
        for c in st_cols:
            sc = df[c].astype(str).str.strip()
            mask |= sc.isin(["Pendente","Vencido"])
        view = df[mask].copy()

        # Abre como aba interna “ABERTAS”
        w = QWidget(); v = QVBoxLayout(w)
        info = QFrame(); info.setObjectName("card"); apply_shadow(info, radius=14)
        iv = QHBoxLayout(info)
        iv.addWidget(QLabel(f"Encontradas {len(view)} multas em aberto."))
        v.addWidget(info)
        t = QTableWidget(); v.addWidget(t, 1)
        t.setAlternatingRowColors(True); t.setSortingEnabled(True)
        t.horizontalHeader().setSortIndicatorShown(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        t.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        headers = list(view.columns); t.setColumnCount(len(headers)); t.setHorizontalHeaderLabels(headers); t.setRowCount(len(view))
        for i, (_, r) in enumerate(view.iterrows()):
            for j, c in enumerate(headers):
                it = QTableWidgetItem(str(r.get(c, ""))); it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                t.setItem(i, j, it)
        t.resizeColumnsToContents(); t.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(w, "ABERTAS")
        self.tabs.setCurrentWidget(w)

    def _find_mainwindow_with_tabs(self):
        # Sobe na hierarquia procurando um QMainWindow com atributo tab_widget
        p = self.parent()
        while p is not None:
            if hasattr(p, "tab_widget"):
                return p
            p = p.parent()
        return None
