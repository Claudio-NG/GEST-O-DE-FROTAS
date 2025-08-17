import os, ast, re, shutil, unicodedata
from glob import glob
import pandas as pd
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QMessageBox
from constants import DATE_COLS, STATUS_COLOR, GERAL_MULTAS_CSV, MULTAS_ROOT, PASTORES_DIR

def _parse_dt_any(s):
    s = str(s).strip()
    if not s:
        return QDate()
    for fmt in ["dd/MM/yyyy","dd-MM-yyyy","yyyy-MM-dd","yyyy/MM/dd"]:
        q = QDate.fromString(s, fmt)
        if q.isValid():
            return q
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return QDate(int(dt.year), int(dt.month), int(dt.day))
    except:
        pass
    return QDate()

def _norm(s):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(ch)).lower()

def _pick_fase_pastores():
    base = os.path.join(PASTORES_DIR, "Notificações de Multas - Fase Pastores.xlsx")
    if os.path.exists(base):
        return base
    cands = []
    for p in ("*Fase*Pastor*.xls*", "*fase*pastor*.xls*"):
        cands += glob(os.path.join(PASTORES_DIR, p))
    cands = [p for p in cands if os.path.isfile(p)]
    if not cands:
        return ""
    return max(cands, key=lambda p: os.path.getmtime(p))

def load_fase_pastores():
    path = _pick_fase_pastores()
    if not path:
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    try:
        df = pd.read_excel(path, dtype=str, engine="openpyxl").fillna("")
    except Exception as e:
        QMessageBox.critical(None, "Erro", str(e))
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    fcol = next((c for c in df.columns if "fluig" in c.lower()), None)
    dcol = next((c for c in df.columns if "data pastores" in c.lower() or ("pastores" in c.lower() and "data" in c.lower())), None)
    tcol = next((c for c in df.columns if "tipo" in c.lower()), None)
    if not fcol or not dcol or not tcol:
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    out = df[[fcol, dcol, tcol]].copy()
    out.columns = ["FLUIG","DATA_PASTORES","TIPO"]
    out["FLUIG"] = out["FLUIG"].astype(str).str.strip()
    out["DATA_PASTORES"] = out["DATA_PASTORES"].astype(str).str.strip()
    out["TIPO"] = out["TIPO"].astype(str).str.strip()
    return out

def load_fase_pastores_from(path):
    if not path or not os.path.exists(path):
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    try:
        df = pd.read_excel(path, dtype=str, engine="openpyxl").fillna("")
    except Exception as e:
        QMessageBox.critical(None, "Erro", str(e))
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    fcol = next((c for c in df.columns if "fluig" in c.lower()), None)
    dcol = next((c for c in df.columns if "data pastores" in c.lower() or ("pastores" in c.lower() and "data" in c.lower())), None)
    tcol = next((c for c in df.columns if "tipo" in c.lower()), None)
    if not fcol or not dcol or not tcol:
        return pd.DataFrame(columns=["FLUIG","DATA_PASTORES","TIPO"])
    out = df[[fcol, dcol, tcol]].copy()
    out.columns = ["FLUIG","DATA_PASTORES","TIPO"]
    out["FLUIG"] = out["FLUIG"].astype(str).str.strip()
    out["DATA_PASTORES"] = out["DATA_PASTORES"].astype(str).str.strip()
    out["TIPO"] = out["TIPO"].astype(str).str.strip()
    return out

def _paint_status(item, status):
    if status:
        bg = STATUS_COLOR.get(status)
        if bg:
            item.setBackground(bg)
            yiq = (bg.red()*299 + bg.green()*587 + bg.blue()*114) / 1000
            item.setForeground(QColor("#000000" if yiq >= 160 else "#FFFFFF"))

def parse_permissions(perms):
    if isinstance(perms, list):
        return perms
    if isinstance(perms, str):
        s = perms.strip()
        if s.lower() in ("todos","all","*",""):
            return 'todos'
        try:
            return ast.literal_eval(s)
        except:
            return [p.strip() for p in s.split(",") if p.strip()]
    return 'todos'

def apply_shadow(w, radius=20, blur=40, color=QColor(0,0,0,100)):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(8)
    eff.setColor(color)
    w.setGraphicsEffect(eff)
    w.setStyleSheet(f"border-radius:{radius}px;")

def ensure_status_cols(df, csv_path=None):
    changed = False
    for c in DATE_COLS:
        sc = f"{c}_STATUS"
        if sc not in df.columns:
            df[sc] = ""
            changed = True
    if changed and csv_path:
        try:
            df.to_csv(csv_path, index=False)
        except:
            pass
    return df

def to_qdate_flexible(val):
    if not isinstance(val, str) or not val.strip():
        return QDate()
    for fmt in ["dd-MM-yyyy","dd/MM/yyyy","yyyy-MM-dd","yyyy/MM/dd"]:
        qd = QDate.fromString(val.strip(), fmt)
        if qd.isValid():
            return qd
    return QDate()

def build_multa_dir(infrator, ano, mes, placa, notificacao, fluig):
    sub = f"{placa}_{notificacao}_FLUIG({fluig})"
    return os.path.join(MULTAS_ROOT, str(infrator).strip(), str(ano).strip(), str(mes).strip(), sub)

def gerar_geral_multas_csv(root=MULTAS_ROOT, output=GERAL_MULTAS_CSV):
    rows = []
    if os.path.isdir(root):
        for infrator in os.listdir(root):
            infrator_dir = os.path.join(root, infrator)
            if not os.path.isdir(infrator_dir):
                continue
            for ano in os.listdir(infrator_dir):
                ano_dir = os.path.join(infrator_dir, ano)
                if not os.path.isdir(ano_dir):
                    continue
                for mes in os.listdir(ano_dir):
                    mes_dir = os.path.join(ano_dir, mes)
                    if not os.path.isdir(mes_dir):
                        continue
                    for folder in os.listdir(mes_dir):
                        fdir = os.path.join(mes_dir, folder)
                        if not os.path.isdir(fdir):
                            continue
                        parts = folder.split('_')
                        placa = parts[0] if len(parts)>0 else ""
                        notificacao = parts[1] if len(parts)>1 else ""
                        fluig = ""
                        if len(parts)>2 and '(' in parts[2] and ')' in parts[2]:
                            fluig = parts[2].split('(')[1].split(')')[0]
                        rows.append({
                            "INFRATOR": infrator,
                            "ANO": ano,
                            "MES": mes,
                            "PLACA": placa,
                            "NOTIFICACAO": notificacao,
                            "FLUIG": fluig,
                            "ORGÃO": "",
                            "DATA INDITACAO": "",
                            "BOLETO": "",
                            "LANÇAMENTO NFF": "",
                            "VALIDACAO NFF": "",
                            "CONCLUSAO": "",
                            "SGU": ""
                        })
    df = pd.DataFrame(rows)
    df = ensure_status_cols(df)
    df.to_csv(output, index=False)

def ensure_base_csv():
    if not os.path.exists(GERAL_MULTAS_CSV):
        os.makedirs(os.path.dirname(GERAL_MULTAS_CSV), exist_ok=True)
        gerar_geral_multas_csv()