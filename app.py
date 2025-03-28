from flask import Flask, render_template, request
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure

app = Flask(__name__)

# URI de conexão com o MongoDB Atlas
app.config["MONGO_URI"] = "mongodb+srv://leonardoarmbruster:Leperfekt210822.@mongodb.fcezg.mongodb.net/CAMPL?retryWrites=true&w=majority"

# Conexão com o MongoDB Atlas
mongo = PyMongo(app)

@app.route("/chamada", methods=["GET", "POST"])
def chamada():
    try:
        # Verifica se a coleção 'Lista_chamada' existe e tenta encontrar documentos nela
        lista_chamada = mongo.db.Lista_chamada.find()

        # Verifica se a coleção está vazia (usando count_documents)
        if mongo.db.Lista_chamada.count_documents({}) == 0:
            # Caso a coleção esteja vazia, cria um exemplo de chamada
            mongo.db.Lista_chamada.insert_one({
                "nome_aluno": "João Silva",
                "presenca": True
            })

            return "Coleção 'Lista_chamada' estava vazia. Um exemplo foi adicionado."

        return render_template("chamada.html", lista_chamada=lista_chamada)

    except ConnectionFailure:
        return "Erro ao acessar o banco de dados. Verifique a conexão com o MongoDB."

if __name__ == '__main__':
    app.run(debug=True)
