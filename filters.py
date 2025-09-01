from PyQt6.QtCore import QSortFilterProxyModel, Qt

class GlobalContainsProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tokens = []

    def setQuery(self, text: str):
        self.tokens = [t.strip().lower() for t in text.split('+') if t.strip()]
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.tokens:
            return True
        model = self.sourceModel()
        col_count = model.columnCount()
        # Para cada token, ele deve aparecer em pelo menos UMA coluna
        for tok in self.tokens:
            found = False
            for c in range(col_count):
                idx = model.index(source_row, c, source_parent)
                val = str(model.data(idx) or "").lower()
                if tok in val:
                    found = True
                    break
            if not found:
                return False
        return True
