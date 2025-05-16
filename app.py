from flask import Flask, render_template, request, redirect, url_for, flash
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session
from bson import ObjectId









app = Flask(__name__)
app.config["SECRET_KEY"] = "Leperfetk210822."  # Necessário para usar flash messages

# Conexão com o MongoDB Atlas (Altere suas credenciais de forma segura)
app.config["MONGO_URI"] = "mongodb+srv://leonardoarmbruster:Leperfekt210822.@mongodb.fcezg.mongodb.net/CAMPL?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/')
def index():
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Verifica se a cole o de usu rios existe
    if 'usuarios' not in mongo.db.list_collection_names():
        mongo.db.create_collection('usuarios')
        # Cria um usu rio administrador padr o, com email 'admin@admin.com' e senha 'admin'
        mongo.db.usuarios.insert_one({
            "email": 'admin@admin.com',
            "senha": generate_password_hash('admin')
        })
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        user = mongo.db.usuarios.find_one({'email': email})
        if user and check_password_hash(user['senha'], senha):
            session['email'] = email
            return redirect(url_for('chamada'))
        else:
            flash('Usuario ou senha invalido')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/lista_presenca', methods=['GET'])
def lista_presenca():
    selected_classe = request.args.get('classe')  # ID da classe selecionada (como string)
    registros = []

    # Obtém todas as classes
    classes = list(mongo.db.classes.find())

    if selected_classe:
        try:
            classe_obj_id = ObjectId(selected_classe)
            selected_classe_obj = mongo.db.classes.find_one({"_id": classe_obj_id})
            selected_classe_nome = selected_classe_obj['classe'] if selected_classe_obj else None

            # Filtra registros da classe selecionada
            registros = list(mongo.db.Lista_chamada.find({"classe_id": ObjectId(selected_classe)}))
        except Exception as e:
            flash(f"Erro ao buscar registros: {e}", "error")
            selected_classe_nome = None
    else:
        # Exibe todas as presenças de todas as classes
        registros = list(mongo.db.Lista_chamada.find())

    return render_template(
        'lista_presenca.html',
        classes=classes,
        selected_classe=selected_classe,
        selected_classe_nome=selected_classe_nome if selected_classe else None,
        registros=registros
    )

@app.route("/salvar_presenca", methods=["POST"])
def salvar_presenca():
    try:
        classe_id = request.form.get('classe_id')
        if not classe_id:
            flash("Classe não selecionada.")
            return redirect(url_for('chamada'))

        aluno_ids = request.form.getlist('aluno_id[]')

        for aluno_id in aluno_ids:
            presente = f'presenca_{aluno_id}' in request.form

            aluno = mongo.db.estudantes.find_one({"_id": ObjectId(aluno_id)})
            classe = mongo.db.classes.find_one({"_id": ObjectId(classe_id)})

            mongo.db.Lista_chamada.insert_one({
                "data": datetime.now(),
                "nome_aluno": aluno['nome'] if aluno else None,
                "email_aluno": aluno['email'] if aluno else None,
                "nome_classe": classe['classe'] if classe else None,
                "presenca": presente,
                "classe_id": ObjectId(classe_id),
            })

        flash("Presenças registradas com sucesso!")
        return redirect(url_for('chamada', classe_id=classe_id))

    except Exception as e:
        flash(f"Ocorreu um erro ao registrar as presenças: {str(e)}")
        return redirect(url_for('chamada'))
@app.route("/chamada", methods=["GET", "POST"])
def chamada():
    try:
        classe_id = request.args.get('classe_id')

        if classe_id:
            classe = mongo.db.classes.find_one({"_id": ObjectId(classe_id)})
            alunos = list(mongo.db.estudantes.find({"classe_id": ObjectId(classe_id)}))
        else:
            classe = None
            alunos = list(mongo.db.estudantes.find())

        classes = list(mongo.db.classes.find())

        # Converte os _id para string para usar no template
        for aluno in alunos:
            aluno['_id'] = str(aluno['_id'])

        return render_template("chamada.html", classes=classes, alunos=alunos, classe=classe)

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

        flash("Classe adicionada com sucesso!", "success")
        
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
    app.run(debug=True, host='0.0.0.0')

