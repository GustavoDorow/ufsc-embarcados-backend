
import requests
from flask import abort, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from .comum import (
    abrir_banco, criar_aplicacao, endereco_servico, interpretar_data,
    ler_campos_json, validar_identificador,
)

app = criar_aplicacao(__name__)
QUARTOS_URL = endereco_servico("quartos", 5001)
PESSOAS_URL = endereco_servico("pessoas", 5002)
with abrir_banco("senhas") as banco:
    banco.execute("""
        CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY,
            pessoa_id INTEGER NOT NULL,
            quarto_id INTEGER NOT NULL,
            codigo_hash TEXT NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT NOT NULL
        )
    """)


def validar_codigo(codigo):
    if not isinstance(codigo, str) or len(codigo) != 6 or not codigo.isascii() or not codigo.isdigit():
        raise ValueError("O código deve ser um texto com seis dígitos, como 012345.")
    return codigo


def preparar_senha(dados, quarto_ids):
    pessoa_id = validar_identificador(dados["pessoa_id"], "pessoa_id")
    codigo = validar_codigo(dados["codigo"])
    inicio = interpretar_data(dados["inicio"])
    fim = interpretar_data(dados["fim"])
    if inicio >= fim:
        raise ValueError("O fim da validade deve ser posterior ao início.")
    consultas = [(f"{PESSOAS_URL}/pessoas/{pessoa_id}", f"Pessoa {pessoa_id}")]
    consultas.extend((f"{QUARTOS_URL}/quartos/{quarto_id}", f"Quarto {quarto_id}")
                     for quarto_id in quarto_ids)
    for url, entidade in consultas:
        resposta = requests.get(url, timeout=3)
        if resposta.status_code == 404:
            raise ValueError(f"{entidade} não encontrado para cadastrar a senha.")
        resposta.raise_for_status()
    return pessoa_id, codigo, inicio.isoformat(), fim.isoformat()


def verificar_conflito_senha(banco, quarto_id, codigo, inicio, fim, senha_id=None):
    sobrepostas = banco.execute(
        "SELECT id, codigo_hash FROM senhas WHERE quarto_id = ? AND inicio < ? AND fim > ?",
        (quarto_id, fim, inicio),
    ).fetchall()
    for senha in sobrepostas:
        if senha["id"] != senha_id and check_password_hash(senha["codigo_hash"], codigo):
            abort(409, description=f"Código já utilizado no quarto {quarto_id} durante esse período.")


def inserir_senha(banco, pessoa_id, quarto_id, codigo_hash, inicio, fim):
    cursor = banco.execute(
        "INSERT INTO senhas (pessoa_id, quarto_id, codigo_hash, inicio, fim) VALUES (?, ?, ?, ?, ?)",
        (pessoa_id, quarto_id, codigo_hash, inicio, fim),
    )
    return dict(id=cursor.lastrowid, pessoa_id=pessoa_id, quarto_id=quarto_id,
                inicio=inicio, fim=fim)


def salvar_senha(senha_id=None):
    dados = ler_campos_json("pessoa_id", "quarto_id", "codigo", "inicio", "fim")
    quarto_id = validar_identificador(dados["quarto_id"], "quarto_id")
    pessoa_id, codigo, inicio, fim = preparar_senha(dados, [quarto_id])
    codigo_hash = generate_password_hash(codigo)
    with abrir_banco("senhas") as banco:
        banco.execute("BEGIN IMMEDIATE")
        if senha_id is not None:
            existente = banco.execute("SELECT id FROM senhas WHERE id = ?", (senha_id,)).fetchone()
            if existente is None:
                abort(404, description="Senha não encontrada.")
        verificar_conflito_senha(banco, quarto_id, codigo, inicio, fim, senha_id)
        if senha_id is None:
            criada = inserir_senha(banco, pessoa_id, quarto_id, codigo_hash, inicio, fim)
            senha_id = criada["id"]
            status = 201
        else:
            banco.execute(
                "UPDATE senhas SET pessoa_id = ?, quarto_id = ?, codigo_hash = ?, inicio = ?, fim = ? WHERE id = ?",
                (pessoa_id, quarto_id, codigo_hash, inicio, fim, senha_id),
            )
            status = 200
    return jsonify(id=senha_id, pessoa_id=pessoa_id, quarto_id=quarto_id,
                   inicio=inicio, fim=fim), status


@app.post("/senhas")
def cadastrar_senha():
    return salvar_senha()


@app.post("/senhas/lote")
def cadastrar_senhas_lote():
    dados = ler_campos_json("pessoa_id", "quarto_ids", "codigo", "inicio", "fim")
    quarto_ids = dados["quarto_ids"]
    if not isinstance(quarto_ids, list) or not quarto_ids:
        raise ValueError("O campo quarto_ids deve ser uma lista não vazia de inteiros positivos.")
    for quarto_id in quarto_ids:
        validar_identificador(quarto_id, "quarto_ids")
    if len(set(quarto_ids)) != len(quarto_ids):
        raise ValueError("O campo quarto_ids não pode conter quartos repetidos.")
    pessoa_id, codigo, inicio, fim = preparar_senha(dados, quarto_ids)
    codigo_hash = generate_password_hash(codigo)
    criadas = []
    with abrir_banco("senhas") as banco:
        banco.execute("BEGIN IMMEDIATE")
        for quarto_id in quarto_ids:
            verificar_conflito_senha(banco, quarto_id, codigo, inicio, fim)
            criadas.append(inserir_senha(banco, pessoa_id, quarto_id, codigo_hash, inicio, fim))
    return jsonify(criadas), 201


@app.put("/senhas/<int:senha_id>")
def atualizar_senha(senha_id):
    return salvar_senha(senha_id)


@app.get("/senhas")
def listar_senhas():
    with abrir_banco("senhas") as banco:
        senhas = banco.execute(
            "SELECT id, pessoa_id, quarto_id, inicio, fim FROM senhas ORDER BY id"
        ).fetchall()
    return jsonify([dict(senha) for senha in senhas])


@app.post("/senhas/validar")
def verificar_senha():
    dados = ler_campos_json("quarto_id", "codigo", "instante")
    quarto_id = validar_identificador(dados["quarto_id"], "quarto_id")
    codigo = validar_codigo(dados["codigo"])
    instante = interpretar_data(dados["instante"])
    with abrir_banco("senhas") as banco:
        senhas = banco.execute("SELECT * FROM senhas WHERE quarto_id = ?", (quarto_id,)).fetchall()
    motivo = "codigo_incorreto"
    for senha in senhas:
        if check_password_hash(senha["codigo_hash"], codigo):
            if interpretar_data(senha["inicio"]) <= instante < interpretar_data(senha["fim"]):
                return jsonify(autorizado=True, motivo="senha_valida", pessoa_id=senha["pessoa_id"])
            motivo = "fora_da_validade"
    return jsonify(autorizado=False, motivo=motivo, pessoa_id=None)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003)
