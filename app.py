from flask import jsonify
from flask_pymongo import PyMongo
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo.errors import ConnectionFailure
from datetime import datetime, time
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from bson.errors import InvalidId
import pandas as pd
import os



app = Flask(__name__)
app.config["SECRET_KEY"] = "Leperfetk210822."  # Necessário para usar flash messages

# Conexão com o MongoDB Atlas (Altere suas credenciais de forma segura)
app.config["MONGO_URI"] = "mongodb+srv://leonardoarmbruster:Leperfekt210822.@mongodb.fcezg.mongodb.net/CAMPL?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/')
def index():
    return redirect(url_for('login'))

from flask import jsonify


@app.route('/login', methods=['GET', 'POST'])
def login():
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

@app.route('/importar_alunos', methods=['GET', 'POST'])
def importar_alunos():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Nenhum arquivo enviado', 'danger')
            return redirect(request.url)

        try:
            df = pd.read_excel(file)
        except Exception as e:
            flash(f'Erro ao ler o arquivo Excel: {e}', 'danger')
            return redirect(request.url)

        alunos = []
        for _, row in df.iterrows():
            aluno = {
                "nome": row.get('nome'),
                "email": row.get('email'),
                "matricula": row.get('matricula'),
                "data_nascimento": None,
                "telefone": row.get('telefone'),
                "turma": row.get('turma'),
            }
            # Converter data_nascimento para datetime.date se vier no Excel
            if pd.notna(row.get('data_nascimento')):
                aluno["data_nascimento"] = pd.to_datetime(row['data_nascimento']).date()
            alunos.append(aluno)

        if alunos:
            mongo.db.alunos.insert_many(alunos)
            flash(f'{len(alunos)} alunos importados com sucesso!', 'success')
        else:
            flash('Nenhum aluno válido para importar.', 'warning')

        return redirect(url_for('importar_alunos'))

    return render_template('importar_alunos.html')

@app.route('/lista_presenca', methods=['GET'])
def lista_presenca():
    selected_classe = request.args.get('classe')  # ID da classe
    data_filtro = request.args.get('data')        # Data em formato 'YYYY-MM-DD'
    registros = []

    # Obtém todas as classes
    classes = list(mongo.db.classes.find())
    selected_classe_nome = None

    if selected_classe:
        try:
            classe_obj_id = ObjectId(selected_classe)
            selected_classe_obj = mongo.db.classes.find_one({"_id": classe_obj_id})
            selected_classe_nome = selected_classe_obj['classe'] if selected_classe_obj else None

            # Cria filtro para consulta
            filtro = {"classe_id": classe_obj_id}

            # Se a data foi informada, adiciona ao filtro
            if data_filtro:
                try:
                    data_obj = datetime.strptime(data_filtro, "%Y-%m-%d")
                    # Filtra pela data no mesmo dia (ignorar hora)
                    proximo_dia = data_obj.replace(hour=23, minute=59, second=59)
                    filtro["data"] = {"$gte": data_obj, "$lte": proximo_dia}
                except ValueError:
                    flash("Data inválida.", "error")

            registros = list(mongo.db.Lista_chamada.find(filtro))

        except Exception as e:
            flash(f"Erro ao buscar registros: {e}", "error")

    return render_template(
        'lista_presenca.html',
        classes=classes,
        selected_classe=selected_classe,
        selected_classe_nome=selected_classe_nome,
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
            presente_turno1 = f'presenca_{aluno_id}_1' in request.form
            presente_turno2 = f'presenca_{aluno_id}_2' in request.form

            aluno = mongo.db.estudantes.find_one({"_id": ObjectId(aluno_id)})
            classe = mongo.db.classes.find_one({"_id": ObjectId(classe_id)})

            mongo.db.Lista_chamada.insert_one({
                "data": datetime.utcnow(),
                "nome_aluno": aluno['nome'] if aluno else None,
                "email_aluno": aluno['email'] if aluno else None,
                "nome_classe": classe['classe'] if classe else None,
                "presenca_turno1": presente_turno1,
                "presenca_turno2": presente_turno2,
                "classe_id": ObjectId(classe_id),
                "presenca_adicional": None
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
            alunos = list(mongo.db.estudantes.find({"classe_id": classe_id}))   
        else:
            classe = None
            alunos = list(mongo.db.estudantes.find())

        classes = list(mongo.db.classes.find())

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


@app.route('/editar_estudante/<id>', methods=['GET', 'POST'])
def editar_estudante(id):
    try:
        estudante = mongo.db.estudantes.find_one({"_id": ObjectId(id)})
        if not estudante:
            flash("Estudante não encontrado.", "error")
            return redirect(url_for('adicionar_estudante'))

        # Converte o ObjectId para string para evitar problemas no template
        estudante['_id'] = str(estudante['_id'])

        if request.method == 'POST':
            if 'apagar' in request.form:
                mongo.db.estudantes.delete_one({"_id": ObjectId(id)})
                flash("Estudante apagado(a) com sucesso!", "success")
                return redirect(url_for('adicionar_estudante'))

            # Atualizar dados do estudante
            nome = request.form['name']
            email = request.form['email']
            idade = request.form['age']
            classe_id = request.form['classe_id']

            mongo.db.estudantes.update_one(
                {"_id": ObjectId(id)},
                {"$set": {
                    'nome': nome,
                    'email': email,
                    'idade': idade,
                    'classe_id': classe_id
                }}
            )

            flash("Estudante atualizado com sucesso!", "success")
            return redirect(url_for('adicionar_estudante'))

        # Buscar classes para dropdown
        classes = list(mongo.db.classes.find())

        return render_template('editar_estudante.html', estudante=estudante, classes=classes)

    except InvalidId:
        flash("ID inválido.", "error")
        return redirect(url_for('adicionar_estudante'))

@app.route('/editar_classe/<id>', methods=['GET', 'POST'])
def editar_classe(id):
    try:
        classe = mongo.db.classes.find_one({"_id": ObjectId(id)})
        if not classe:
            flash("Classe não encontrada.", "error")
            return redirect(url_for('adicionar_classe'))

        if request.method == 'POST':
            if 'apagar' in request.form:
                mongo.db.classes.delete_one({"_id": ObjectId(id)})
                flash("Classe apagada com sucesso!", "success")
                return redirect(url_for('adicionar_classe'))
            else:
                novo_nome = request.form.get("classe_nome")
                if novo_nome:
                    mongo.db.classes.update_one(
                        {"_id": ObjectId(id)},
                        {"$set": {"classe": novo_nome}}
                    )
                    flash("Classe atualizada com sucesso!", "success")
                    return redirect(url_for('adicionar_classe'))

        return render_template("editar_classe.html", classe=classe)

    except InvalidId:
        flash("ID de classe inválido.", "error")
        return redirect(url_for("adicionar_classe"))
    
@app.route('/pagina_com_modal')
def pagina_com_modal():
    classes = list(mongo.db.classes.find())
    # converter _id para string para evitar problemas no template:
    for c in classes:
        c['_id'] = str(c['_id'])
    return render_template("pagina_com_modal.html", classes=classes)


@app.route('/api/classes')
def listar_classes():
    classes_cursor = mongo.db.classes.find()
    classes = list(classes_cursor)
    lista = [{"id": str(c["_id"]), "nome": c["classe"]} for c in classes]  # <-- aqui
    return jsonify(lista)

@app.route('/api/estudantes')
def api_estudantes():
    estudantes = mongo.db.estudantes.find()
    result = []
    for e in estudantes:
        result.append({
            '_id': str(e['_id']),  # Convertendo ObjectId para string
            'nome': e.get('nome', ''),
            'classe_id': str(e['classe_id']) if 'classe_id' in e else ''
        })
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

