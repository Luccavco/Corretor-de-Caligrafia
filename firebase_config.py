"""Configuracao central do Firebase.
Contem a chave publica (apiKey) para o Pyrebase (login/registro)
e inicializa o firebase-admin para acessar o Firestore com privilegios."""

import os
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase


# Chave publica do projeto Firebase (pode ficar no codigo, e publica mesmo).
# As regras de seguranca do Firestore que protegem os dados.
API_KEY = "AIzaSyAg1e77lJJqKtC-KBadiQgm0lRdmhdmMd0"

# Configuracao do Pyrebase (autenticacao email/senha).
# Os campos que nao usamos ficam com placeholders — a biblioteca exige.
PYREBASE_CONFIG = {
    "apiKey": API_KEY,
    "authDomain": "caligrafia.firebaseapp.com",
    "projectId": "caligrafia",
    "storageBucket": "caligrafia.appspot.com",
    "messagingSenderId": "0",
    "appId": "0",
    "databaseURL": "",
}

CREDENCIAIS_ADMIN = "firebase_credentials.json"


_pyrebase_app = None
_firestore_client = None


def get_pyrebase_auth():
    """Cliente Pyrebase para autenticar usuarios (login/registro)."""
    global _pyrebase_app
    if _pyrebase_app is None:
        _pyrebase_app = pyrebase.initialize_app(PYREBASE_CONFIG)
    return _pyrebase_app.auth()


def get_firestore():
    """Cliente do Firestore para ler/escrever dados dos usuarios."""
    global _firestore_client
    if _firestore_client is None:
        if not firebase_admin._apps:
            cred = credentials.Certificate(CREDENCIAIS_ADMIN)
            firebase_admin.initialize_app(cred)
        _firestore_client = firestore.client()
    return _firestore_client
