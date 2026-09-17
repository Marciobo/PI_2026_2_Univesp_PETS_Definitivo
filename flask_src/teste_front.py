from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from models.mock import MockAnuncio, MockPagination, MockAnuncioDetalhado
from flask_bootstrap import Bootstrap5
import os
from dotenv import load_dotenv
from config import CATEGORIAS

load_dotenv()

# Esses passos são para configurar a aplicação. Podem ser definidos em uma função à parte ou em __init__.py.
app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY')
bootstrap = Bootstrap5(app)

# ------------ INJEÇÃO DE VARIÁVEIS GLOBAIS PARA OS TEMPLATES --------------
app.config['CATEGORIAS'] = CATEGORIAS

# ------------ DEFINIÇÕES DE ROTAS ABAIXO ------------

@app.route('/', methods = ['GET'])
def home():
    """
    Rota padrão do site. É a página inicial.
    """
    page = request.args.get('page', 1, type = int)
    
    # Atenção! Criei uma classe mock só pra visualizar anúncios quaisquer. Substituir por função real de puxar anúncios
    sample_anuncio = MockAnuncio(1, "Título", "Breve descrição do anúncio", autor = 'Nome do autor', categoria='Música', preco = '30,00', thumbnail= url_for('static', filename='sample_images/4.jpg'))
    # Na vida real aqui teria uma função de buscar os anúncios
    lista_anuncios = [sample_anuncio] * 12
    pagination = MockPagination(items = lista_anuncios, page = page, per_page = 12, total = 45)

    return render_template('home.html', pagination = pagination)

@app.route('/classificados/<id>', methods = ['GET'])
def detalhe_anuncio(id):
    """Rota de mostrar anúncio com detalhes."""
    anuncio_teste = MockAnuncioDetalhado(id =1, titulo = 'Título de teste', preco = '40,00', descricao = 'Uma descrição mais ou menos detalhada. ' * 20, autor = 'José Carlos')
    return render_template('classificados.html', anuncio = anuncio_teste)

@app.route('/criar', methods = ['GET', 'POST'])
def criar_anuncio():
    """
    Rota de criação de anúncio. Se quiser pode separar a lógica do GET e do POST, mas alguns preferem assim.
    """
    if request.method == 'POST':
        for key, value in request.form.items():
            print(f'{key}: {value}')
        flash('Anúncio criado com sucesso!', category = 'success')
        return redirect(url_for('home'))
    return render_template('criar_anuncio.html')    

@app.route('/classificados/<id>/editar', methods = ['GET', 'POST'])
def editar_anuncio(id):
    if request.method == 'POST':
        flash("Anúncio editado com sucesso.", category = 'success')
        for key, value in request.form.items():
            print(f"{key}: {value}")
        return redirect(url_for('detalhe_anuncio', id = id))
    else:
        anuncio_teste = MockAnuncioDetalhado(id =1, titulo = 'Título de teste', preco = '40,00', descricao = 'Uma descrição mais ou menos detalhada. ' * 20, autor = 'José Carlos')
        return render_template('editar_anuncio.html', anuncio = anuncio_teste)

@app.route('/classificados/<id>/deletar', methods = ['POST'])
def excluir_anuncio(id):
    flash("Anúncio excluído.", category = 'warning')
    return redirect(url_for('home'))

@app.route('/users_test/<string:user>')
def hello_user(user):
    """
    Rota de teste que não faz nada.
    """
    return f'<h1>Hello, {user}!</h1>'

# ------------ FIM DAS DEFINIÇÕES DE ROTA ------------

if __name__ == '__main__':
    app.run(debug = True)