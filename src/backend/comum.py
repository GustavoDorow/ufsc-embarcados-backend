"""Funções pequenas compartilhadas; cada serviço abre somente seu próprio banco."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


def criar_aplicacao(nome):
    """Padroniza erros JSON sem esconder falhas como respostas de sucesso."""
    app = Flask(nome)
    app.json.ensure_ascii = False

    @app.errorhandler(HTTPException)
    def responder_erro_http(erro):
        return jsonify(erro=erro.description), erro.code

    @app.errorhandler(ValueError)
    def responder_dado_invalido(erro):
        return jsonify(erro=str(erro)), 400

    @app.errorhandler(sqlite3.IntegrityError)
    def responder_conflito_banco(erro):
        return jsonify(erro="Registro duplicado ou referência inválida."), 409

    @app.errorhandler(sqlite3.Error)
    def responder_falha_banco(erro):
        app.logger.exception("Falha no banco do serviço")
        return jsonify(erro="Não foi possível gravar ou consultar o banco."), 503

    @app.errorhandler(requests.RequestException)
    def responder_falha_servico(erro):
        app.logger.warning("Falha na comunicação entre serviços: %s", erro)
        return jsonify(erro="Não foi possível consultar outro serviço."), 503

    return app


@contextmanager
def abrir_banco(nome):
    """Abre um SQLite por serviço e confirma ou desfaz a operação ao terminar."""
    pasta = Path(os.environ.get("DADOS_DIR", "dados"))
    pasta.mkdir(parents=True, exist_ok=True)
    banco = sqlite3.connect(pasta / f"{nome}.sqlite3", timeout=5)
    banco.row_factory = sqlite3.Row
    try:
        with banco:
            yield banco
    finally:
        banco.close()


def ler_campos_json(*campos):
    """Exige um objeto JSON com os campos necessários para a operação."""
    dados = request.get_json()
    if not isinstance(dados, dict):
        raise ValueError("Envie um objeto JSON.")
    for campo in campos:
        if campo not in dados:
            raise ValueError(f"Campo obrigatório: {campo}.")
    return dados


def validar_texto(valor, campo):
    """Remove espaços externos e rejeita texto vazio."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"O campo {campo} deve ser um texto não vazio.")
    return valor.strip()


def validar_identificador(valor, campo):
    """Identificadores de pessoas e quartos são inteiros positivos."""
    if type(valor) is not int or valor < 1:
        raise ValueError(f"O campo {campo} deve ser um inteiro positivo.")
    return valor


def interpretar_data(valor):
    """Converte uma data ISO 8601 com fuso para UTC."""
    if not isinstance(valor, str):
        raise ValueError("A data deve ser um texto ISO 8601 com fuso horário.")
    try:
        data = datetime.fromisoformat(valor)
    except ValueError:
        raise ValueError("Data inválida. Exemplo: 2026-11-09T14:00:00-03:00.")
    if data.tzinfo is None:
        raise ValueError("Informe o fuso horário na data, como -03:00 ou +00:00.")
    return data.astimezone(timezone.utc)


def endereco_servico(nome, porta):
    """Permite configurar URLs internas sem alterar o código dos serviços."""
    return os.environ.get(f"{nome.upper()}_URL", f"http://127.0.0.1:{porta}")
