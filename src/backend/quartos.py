
from flask import abort, jsonify, request

from .comum import abrir_banco, criar_aplicacao, ler_campos_json, validar_texto

app = criar_aplicacao(__name__)
with abrir_banco("quartos") as banco:
    banco.execute("""
        CREATE TABLE IF NOT EXISTS quartos (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            fechadura_id TEXT NOT NULL UNIQUE
        )
    """)


@app.get("/quartos")
def listar_quartos():
    with abrir_banco("quartos") as banco:
        if "fechadura_id" in request.args:
            registros = banco.execute(
                "SELECT * FROM quartos WHERE fechadura_id = ?",
                (request.args["fechadura_id"],),
            ).fetchall()
        else:
            registros = banco.execute("SELECT * FROM quartos ORDER BY id").fetchall()
    return jsonify([dict(registro) for registro in registros])


@app.get("/quartos/<int:quarto_id>")
def consultar_quarto(quarto_id):
    with abrir_banco("quartos") as banco:
        quarto = banco.execute("SELECT * FROM quartos WHERE id = ?", (quarto_id,)).fetchone()
    if quarto is None:
        abort(404, description="Quarto não encontrado.")
    return jsonify(dict(quarto))


@app.post("/quartos")
def cadastrar_quarto():
    dados = ler_campos_json("nome", "fechadura_id")
    nome = validar_texto(dados["nome"], "nome")
    fechadura_id = validar_texto(dados["fechadura_id"], "fechadura_id")
    with abrir_banco("quartos") as banco:
        cursor = banco.execute(
            "INSERT INTO quartos (nome, fechadura_id) VALUES (?, ?)", (nome, fechadura_id)
        )
        quarto_id = cursor.lastrowid
    return jsonify(id=quarto_id, nome=nome, fechadura_id=fechadura_id), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
