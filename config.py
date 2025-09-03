import os, json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CFG_PATH = str(BASE_DIR / "base.json")

DEFAULTS = {
    "geral_multas_csv": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\GERAL_MULTAS.csv",
    "multas_root": r"T:\Veiculos\VEÍCULOS - RN\MULTAS",
    "detalhamento_path": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\Notificações de Multas - Detalhamento.xlsx",
    "pastores_file": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\Notificações de Multas - Fase Pastores.xlsx",
    # NOVO: caminho da planilha 3
    "condutor_identificado_path": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\Notificações de Multas - Condutor Identificado.xlsx",
    "pastores_dir": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS",
    "extrato_geral_path": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\ExtratoGeral.xlsx",
    "extrato_simplificado_path": r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\ExtratoSimplificado.xlsx",
    "users_file": "users.csv"
}

def _load():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except:
            pass
    return {}

def _save(data):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def cfg_get(key):
    data = _load()
    if key in data and str(data[key]).strip():
        return data[key]
    return DEFAULTS.get(key, "")

def cfg_set(key, value):
    data = _load()
    data[key] = value
    _save(data)

def cfg_all():
    data = _load()
    out = DEFAULTS.copy()
    out.update({k: v for k, v in data.items() if str(v).strip()})
    return out