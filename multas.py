<<<<<<< HEAD
# multas.py — versão com ações clássicas (Inserir, Editar, Fase Pastores, Conferir FLUIG)
from __future__ import annotations

import os
import pandas as pd
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
=======
# multas.py
import os, re, shutil
import pandas as pd
from PyQt6.QtCore import Qt, QDate, QTimer, QFileSystemWatcher, QUrl
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QDesktopServices
>>>>>>> f9b717829de913f73d13717fa914335134ff238d
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

<<<<<<< HEAD
class MultasView(BaseView):
=======
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
        # coleta do formulário
        new = {}
        for c, w in self.widgets.items():
            if isinstance(w, tuple):
                d, s = w
                new[c] = "" if d.date() == d.minimumDate() else d.date().toString(DATE_FORMAT)
                new[f"{c}_STATUS"] = s.currentText()
            else:
                new[c] = w.currentText() if isinstance(w, QComboBox) else w.text().strip()

        # valida FLUIG único
        if new.get("FLUIG", "") in self.df["FLUIG"].astype(str).tolist():
            QMessageBox.warning(self, "Erro", "FLUIG já existe"); return

        # grava no CSV
        self.df.loc[len(self.df)] = new
        csv = cfg_get("geral_multas_csv")
        os.makedirs(os.path.dirname(csv), exist_ok=True)
        if "COMENTARIO" not in self.df.columns:
            self.df["COMENTARIO"] = ""
        self.df.to_csv(csv, index=False)

        # criar pasta da multa
        try:
            infr, ano, mes = new.get("INFRATOR", ""), new.get("ANO", ""), new.get("MES", "")
            placa, notificacao, fluig = new.get("PLACA", ""), new.get("NOTIFICACAO", ""), new.get("FLUIG", "")
            dest = build_multa_dir(infr, ano, mes, placa, notificacao, fluig)
            os.makedirs(dest, exist_ok=True)

            # índice por condutor (link)
            # tenta obter CPF se existir coluna; se não, passa vazio
            cpf = new.get("CPF", "")
            link_multa_em_condutor(infr, cpf, dest)

            if not os.path.isdir(dest):
                QMessageBox.warning(self, "Aviso", "Pasta da multa não foi criada (verifique permissões/caminho).")
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Falha ao criar a pasta da multa: {e}")

        # oferta para anexar o PDF na sequência
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
        os.makedirs(os.path.dirname(csv), exist_ok=True)
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

# ---------------------- VIEW PRINCIPAL ----------------------
class GeralMultasView(QWidget):
    """
    - Campo de texto global que filtra TODAS as colunas.
    - Por coluna: modo (Todos/Excluir vazios/Somente vazios) + multiseleção.
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

        title = QLabel("Infrações e Multas")
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
        try:
            dlg = SummaryDialog(self.df_filtrado[self.cols_show])
            dlg.exec()
        except Exception:
            QMessageBox.information(self, "Visão Geral", "Resumo indisponível.")

    def limpar_filtros(self):
        self.global_box.blockSignals(True); self.global_box.clear(); self.global_box.blockSignals(False)
        for mode in self.mode_filtros.values():
            mode.blockSignals(True); mode.setCurrentIndex(0); mode.blockSignals(False)
        for ms in self.multi_filtros.values():
            vals = [ms.itemText(i) for i in range(ms.count())]
            ms.set_values(vals)
        self.atualizar_filtro()

    def atualizar_filtro(self):
        df = self.df_original.copy()

        # Se existir STATUS geral, você pode optar por filtrar "em aberto" aqui
        # if "STATUS" in df.columns:
        #     df = df[df["STATUS"].astype(str).str.lower() != "pago"]

        from utils import df_apply_global_texts
        texts = [self.global_box.text()]
        df = df_apply_global_texts(df, texts)

        for coluna in self.cols_show:
            mode = self.mode_filtros[coluna].currentText()
            if mode == "Excluir vazios":
                df = df[df[coluna].astype(str).str.strip() != ""]
            elif mode == "Somente vazios":
                df = df[df[coluna].astype(str).str.strip() == ""]
            sels = [s for s in self.multi_filtros[coluna].selected_values() if s]
            if sels:
                df = df[df[coluna].astype(str).isin(sels)]

        self.df_filtrado = df
        self.preencher_tabela(self.df_filtrado)

    def _abrir_pasta_da_multa(self, infrator, ano, mes, placa, notificacao, fluig):
        """
        Cria/abre a pasta da multa usando o padrão de diretórios central do sistema.
        """
        try:
            dest = build_multa_dir(infrator, ano, mes, placa, notificacao, fluig)
            if not os.path.exists(dest):
                os.makedirs(dest, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
        except Exception as e:
            QMessageBox.warning(self, "Pasta da Multa", f"Não foi possível abrir a pasta.\n{e}")

    def preencher_tabela(self, df):
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
                if col in DATE_COLS_MUL:
                    st = str(df_idx.iloc[i].get(f"{col}_STATUS", ""))
                    _paint_status(it, st)
                self.tabela.setItem(i, j, it)

            # --- Ações por linha: Pasta + Comentar ---
            key = str(df_idx.iloc[i].get("FLUIG", "")).strip()
            infr  = str(df_idx.iloc[i].get("INFRATOR", "")).strip()
            ano   = str(df_idx.iloc[i].get("ANO", "")).strip()
            mes   = str(df_idx.iloc[i].get("MES", "")).strip()
            placa = str(df_idx.iloc[i].get("PLACA", "")).strip()
            notif = str(df_idx.iloc[i].get("NOTIFICACAO", "")).strip()

            wrap = QWidget()
            h = QHBoxLayout(wrap); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)

            btn_pasta = QPushButton("Pasta")
            btn_pasta.setToolTip("Abrir a pasta desta multa")
            btn_pasta.clicked.connect(
                lambda _, a=infr, b=ano, c=mes, d=placa, e=notif, f=key: self._abrir_pasta_da_multa(a, b, c, d, e, f)
            )
            h.addWidget(btn_pasta)

            btn_comment = QPushButton("Comentar")
            if "COMENTARIO" in df_idx.columns:
                btn_comment.setToolTip(str(df_idx.iloc[i].get("COMENTARIO", "")).strip())
            if self.parent_for_edit:
                btn_comment.clicked.connect(lambda _, k=key: self.parent_for_edit.comentar_with_key(k))
            h.addWidget(btn_comment)

            h.addStretch(1)
            self.tabela.setCellWidget(i, len(show.columns), wrap)

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
>>>>>>> f9b717829de913f73d13717fa914335134ff238d
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
<<<<<<< HEAD

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
=======
        i = rows[0]
        atual = str(df.at[i, "COMENTARIO"])
        texto, ok = QInputDialog.getMultiLineText(self, "Comentário", f"FLUIG {key} - Digite/edite o comentário:", atual)
        if ok:
            df.at[i, "COMENTARIO"] = texto.strip()
            df.to_csv(csv, index=False)
            QMessageBox.information(self, "Comentário", "Comentário salvo.")
            self.reload_geral()
>>>>>>> f9b717829de913f73d13717fa914335134ff238d
