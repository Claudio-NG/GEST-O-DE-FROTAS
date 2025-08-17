import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QGridLayout, QMessageBox
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from utils import apply_shadow
from config import cfg_get, cfg_set, cfg_all

class _PathRow(QWidget):
    def __init__(self, label, key, mode="file"):
        super().__init__()
        self.key = key
        self.mode = mode
        h = QHBoxLayout(self)
        self.lab = QLabel(label)
        self.ed = QLineEdit(cfg_get(key))
        self.btn = QPushButton("...")
        self.btn.clicked.connect(self.pick)
        h.addWidget(self.lab)
        h.addWidget(self.ed, 1)
        h.addWidget(self.btn)
    def pick(self):
        if self.mode == "dir":
            p = QFileDialog.getExistingDirectory(self, "Selecionar pasta", self.ed.text().strip() or os.getcwd())
        else:
            p, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo", "", "Todos (*)")
        if p:
            self.ed.setText(p)
    def value(self):
        return self.ed.text().strip()

class BaseWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Base")
        self.resize(900, 600)
        root = QVBoxLayout(self)
        card = QFrame(); card.setObjectName("card"); apply_shadow(card, radius=18)
        v = QVBoxLayout(card)
        grid = QGridLayout()
        self.rows = []
        rows_cfg = [
            ("GERAL_MULTAS.CSV", "geral_multas_csv", "file"),
            ("Pasta MULTAS", "multas_root", "dir"),
            ("Detalhamento (planilha)", "detalhamento_path", "file"),
            ("Fase Pastores (planilha)", "pastores_file", "file"),
            ("Diretório Pastores", "pastores_dir", "dir"),
            ("Extrato Geral (Combustível)", "extrato_geral_path", "file"),
            ("Extrato Simplificado (Combustível)", "extrato_simplificado_path", "file"),
            ("Arquivo de usuários", "users_file", "file")
        ]
        for i, (lab, key, mode) in enumerate(rows_cfg):
            r = _PathRow(lab, key, mode)
            self.rows.append(r)
            grid.addWidget(r, i//2, i%2)
        v.addLayout(grid)
        bar = QHBoxLayout()
        btn_reload = QPushButton("Recarregar")
        btn_save = QPushButton("Salvar")
        bar.addStretch(1)
        bar.addWidget(btn_reload)
        bar.addWidget(btn_save)
        v.addLayout(bar)
        root.addWidget(card)
        btn_save.clicked.connect(self.do_save)
        btn_reload.clicked.connect(self.do_reload)
    def do_reload(self):
        data = cfg_all()
        for r in self.rows:
            r.ed.setText(str(data.get(r.key, "")))
    def do_save(self):
        for r in self.rows:
            cfg_set(r.key, r.value())
        QMessageBox.information(self, "Base", "Configurações salvas.")
