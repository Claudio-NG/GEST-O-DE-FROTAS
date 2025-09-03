# auth.py (SUBSTITUA a classe inteira por esta versão ou ajuste estes pontos)

import os
import pandas as pd
from typing import Tuple
from config import cfg_get
from constants import USERS_FILE as USERS_FILE_DEFAULT

import os, json

REMEMBER_FILE = "remember.json"

class AuthService:
    def __init__(self):
        self.current_user = None
        # tenta carregar lembrado
        if os.path.exists(REMEMBER_FILE):
            try:
                with open(REMEMBER_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._remembered = data.get("user")
            except:
                self._remembered = None
        else:
            self._remembered = None

    def get_remembered_user(self):
        return self._remembered

    def set_remember(self, user, remember):
        if remember:
            with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
                json.dump({"user": user}, f)
            self._remembered = user
        else:
            if os.path.exists(REMEMBER_FILE):
                os.remove(REMEMBER_FILE)
            self._remembered = None

    def login(self, user, pwd):
        # sua lógica real de login
        if not user or not pwd:
            return False, "Usuário/senha inválidos"
        self.current_user = user
        return True, "OK"


class AuthService:
    def __init__(self, users_path: str | None = None):
        self.users_path = users_path or cfg_get("users_file") or USERS_FILE_DEFAULT
        self.current_user: str | None = None         # <<<<<< ADICIONEI
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.users_path):
            df = pd.DataFrame(columns=['email','password','last_login','permissions','remember'])
            df.to_csv(self.users_path, index=False)

    def _load(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.users_path, dtype=str, parse_dates=['last_login'])
        except Exception:
            return pd.DataFrame(columns=['email','password','last_login','permissions','remember'])

    def _save(self, df: pd.DataFrame):
        df.to_csv(self.users_path, index=False)

    def login(self, user: str, password: str) -> Tuple[bool, str]:
        email = (user or "").strip().lower()
        pwd = (password or "").strip()
        if not email or not pwd:
            return False, "Informe usuário e senha."

        df = self._load()
        if df.empty or 'email' not in df.columns or 'password' not in df.columns:
            return False, "Base de usuários inválida."

        df['email'] = df['email'].astype(str).str.strip().str.lower()
        df['password'] = df['password'].astype(str)

        hits = df.index[df['email'] == email].tolist()
        if not hits:
            return False, "Usuário não encontrado."
        i = hits[0]
        if str(df.at[i, 'password']).strip() != pwd:
            return False, "Senha incorreta."

        df.at[i, 'last_login'] = pd.Timestamp.now()
        self._save(df)

        self.current_user = email             # <<<<<< ADICIONEI
        return True, ""

    # util pra marcar/desmarcar "lembrar-me" no CSV
    def set_remember(self, email: str, remember: bool):
        df = self._load()
        email_n = (email or "").strip().lower()
        idxs = df.index[df['email'].astype(str).str.strip().str.lower() == email_n].tolist()
        if idxs:
            df.at[idxs[0], 'remember'] = bool(remember)
            self._save(df)

    # pega o último usuário marcado como remember=True (se houver)
    def get_remembered_user(self) -> str | None:
        df = self._load()
        if 'remember' not in df.columns or df.empty:
            return None
        try:
            remembered = df[df['remember'].astype(str).str.lower().isin(["true","1","yes","y","sim"])]
            if remembered.empty:
                return None
            # mais recente pelo last_login, se houver
            if 'last_login' in remembered.columns:
                remembered = remembered.sort_values('last_login', ascending=False)
            return str(remembered.iloc[0]['email']).strip().lower()
        except:
            return None

    def list_users(self) -> pd.DataFrame:
        return self._load()

    def upsert_user(self, email: str, password: str, permissions=None, remember: bool=False):
        df = self._load()
        email_n = (email or "").strip().lower()
        pwd = (password or "").strip()
        if not email_n or not pwd:
            raise ValueError("E-mail e senha são obrigatórios.")

        if 'permissions' not in df.columns:
            df['permissions'] = ""
        if 'remember' not in df.columns:
            df['remember'] = False

        idxs = df.index[df['email'].astype(str).str.strip().str.lower() == email_n].tolist()
        perms_val = permissions if permissions is not None else ""
        if isinstance(perms_val, list):
            perms_val = str(perms_val)

        if idxs:
            i = idxs[0]
            df.at[i, 'password'] = pwd
            df.at[i, 'permissions'] = perms_val
            df.at[i, 'remember'] = bool(remember)
        else:
            df.loc[len(df)] = {
                'email': email_n,
                'password': pwd,
                'last_login': pd.Timestamp.now(),
                'permissions': perms_val,
                'remember': bool(remember),
            }
        self._save(df)