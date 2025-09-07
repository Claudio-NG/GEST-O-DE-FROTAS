from __future__ import annotations

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

        self._wire()
        self._apply_preset("MES_ATUAL")
        self._apply_theme()

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