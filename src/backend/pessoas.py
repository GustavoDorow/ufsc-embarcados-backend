
from flask import abort, jsonify

from .comum import abrir_banco, criar_aplicacao, ler_campos_json, validar_texto

app = criar_aplicacao(__name__)
with abrir_banco("pessoas") as banco:
    banco.execute("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('hospede', 'limpeza', 'manutencao'))
        )
    """)


@app.get("/pessoas")
def listar_pessoas():
    with abrir_banco("pessoas") as banco:
        pessoas = banco.execute("SELECT * FROM pessoas ORDER BY id").fetchall()
    return jsonify([dict(pessoa) for pessoa in pessoas])


@app.get("/pessoas/<int:pessoa_id>")
def consultar_pessoa(pessoa_id):
    with abrir_banco("pessoas") as banco:
        pessoa = banco.execute("SELECT * FROM pessoas WHERE id = ?", (pessoa_id,)).fetchone()
    if pessoa is None:
        abort(404, description="Pessoa não encontrada.")
    return jsonify(dict(pessoa))


@app.post("/pessoas")
def cadastrar_pessoa():
    dados = ler_campos_json("nome", "tipo")
    nome = validar_texto(dados["nome"], "nome")
    if dados["tipo"] not in ("hospede", "limpeza", "manutencao"):
        raise ValueError("Tipo inválido. Use hospede, limpeza ou manutencao.")
    with abrir_banco("pessoas") as banco:
        cursor = banco.execute(
            "INSERT INTO pessoas (nome, tipo) VALUES (?, ?)", (nome, dados["tipo"])
        )
        pessoa_id = cursor.lastrowid
    return jsonify(id=pessoa_id, nome=nome, tipo=dados["tipo"]), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002)
