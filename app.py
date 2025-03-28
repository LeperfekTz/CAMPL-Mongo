from flask import Flask, render_template, request, redirect, url_for, flash
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure
from datetime import datetime
app = Flask(__name__)
app.config["SECRET_KEY"] = "Leperfetk210822."  # Necessário para usar flash messages

# Conexão com o MongoDB Atlas (Altere suas credenciais de forma segura)
app.config["MONGO_URI"] = "mongodb+srv://leonardoarmbruster:Leperfekt210822.@mongodb.fcezg.mongodb.net/CAMPL?retryWrites=true&w=majority"
mongo = PyMongo(app)


@app.route("/salvar_presenca", methods=["POST"])
def salvar_presenca():
    try:
        # Pega os dados do formulário (checkboxes com os IDs dos alunos presentes)
        presencas = request.form

        # Itera sobre todos os alunos e verifica quais estão presentes
        for aluno_id in presencas:
            if aluno_id.startswith('presenca_'):  # Verifica se o nome do campo é referente a um aluno presente
                aluno_id = aluno_id.split('_')[1]  # Pega o ID do aluno (que está após "presenca_")
                # Insere a presença do aluno na coleção Lista_chamada
                mongo.db.Lista_chamada.insert_one({
                    "aluno_id": aluno_id,
                    "presenca": True,
                    "data": datetime.now()
                })
        
        flash("Presenças registradas com sucesso!")  # Exibe mensagem de sucesso
        return redirect(url_for('chamada'))  # Redireciona de volta à página de chamada

    except Exception as e:
        flash(f"Ocorreu um erro ao registrar as presenças: {str(e)}")  # Exibe mensagem de erro
        return redirect(url_for('chamada'))

@app.route("/chamada", methods=["GET", "POST"])
def chamada():
    try:
        # Captura o ID da classe, se estiver presente
        classe_id = request.args.get('classe_id')  # Pega o valor do filtro
        
        # Busca todas as classes
        classes = list(mongo.db.classes.find())
        
        # Filtra alunos com base na classe selecionada
        if classe_id:
            # Filtra alunos pela classe_id
            alunos = list(mongo.db.estudantes.find({"classe_id": classe_id}))
        else:
            # Caso não tenha classe selecionada, exibe todos os alunos
            alunos = list(mongo.db.estudantes.find())
        
        return render_template("chamada.html", classes=classes, alunos=alunos)

    except ConnectionFailure:
        return "Erro ao acessar o banco de dados. Verifique a conexão com o MongoDB."


@app.route("/adicionar_classe", methods=["GET", "POST"])
def adicionar_classe():
    if request.method == "POST":
        nomes_classes = request.form.get("classe_nome")

        if nomes_classes:
            lista_classes = [nome.strip() for nome in nomes_classes.split(",")]  # Suporta múltiplas classes
            for nome_classe in lista_classes:
                if nome_classe:
                    mongo.db.classes.insert_one({"classe": nome_classe})  # Insere no banco

            flash("Classe(s) adicionada(s) com sucesso!")  # Exibe mensagem de sucesso
        
        return redirect(url_for("adicionar_classe"))  # Redireciona para evitar reenvio do formulário

    return render_template("adicionar_classe.html")

@app.route('/adicionar_estudante', methods=['GET', 'POST'])
def adicionar_estudante():
    if request.method == 'POST':
        # Recebe os dados do formulário
        nome = request.form['name']
        email = request.form['email']
        idade = request.form['age']
        classe_id = request.form['classe_id']
        
        # Insere os dados no MongoDB
        mongo.db.estudantes.insert_one({
            'nome': nome,
            'email': email,
            'idade': idade,
            'classe_id': classe_id  # Relaciona o aluno à classe
        })
        
        # Redireciona para a página de adicionar estudante
        return redirect(url_for('adicionar_estudante'))

    # Busca todas as classes para exibir no formulário
    classes = list(mongo.db.classes.find())

    return render_template('adicionar_estudante.html', classes=classes)



if __name__ == '__main__':
    app.run(debug=True)
