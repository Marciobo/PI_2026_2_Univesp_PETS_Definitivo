from flask import Flask, request, render_template, redirect, url_for, flash
import datetime as dt
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from models.mock import MockAnuncio, MockPagination
from flask_bootstrap import Bootstrap5
import os
from dotenv import load_dotenv
from db import conectar
from werkzeug.utils import secure_filename
from config import CATEGORIAS, EXTENSOES_PERMITIDAS, NUMERO_MAXIMO_FOTOS, TAMANHO_MAXIMO_ARQUIVO, MAPPING_CATEGORIAS
from uuid import uuid4
from gravarimagem import upload_imagem, excluir_imagem
load_dotenv()

# Esses passos são para configurar a aplicação. Podem ser definidos em uma função à parte ou em __init__.py.

if 'CA_PEM_CONTENT' in os.environ:
    with open('ca.pem', 'w') as f:
        f.write(os.environ['CA_PEM_CONTENT'].replace('\\n', '\n'))
app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY')
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['CATEGORIAS'] = CATEGORIAS
app.config['MAPPING_CATEGORIAS'] = MAPPING_CATEGORIAS
bootstrap = Bootstrap5(app)

# ------------ DEFINIÇÕES DE ROTAS ABAIXO ------------

@app.route('/', methods = ['GET'])
def home():
    """
    Rota padrão do site. É a página inicial.
    """
    page = request.args.get('page', 1, type = int)
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("""SELECT a.id, 
                             a.titulo, 
                             a.categoria, 
                             a.descricao, 
                             a.preco, 
                             coalesce(min(ia.url), '/static/sample_images/placeholder.jpg') as url 
                   FROM anuncios AS a LEFT JOIN imagens_anuncio AS ia ON ia.id_anuncio = a.id 
                   GROUP BY 1,2,3,4,5
                   ORDER BY data_atualizacao DESC LIMIT %s OFFSET %s""", (12, (page-1)*12))
    items = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total_count FROM anuncios")
    total_count = cursor.fetchall()[0]['total_count']
    pagination = MockPagination(items, page,  12, total_count)
    return render_template('home.html', pagination = pagination)
    
@app.route('/classificados/<int:id>', methods = ['GET'])
def detalhe_anuncio(id):
    """Rota de mostrar anúncio com detalhes."""

    # Puxando informações do anúncio e do autor
    conexao = conectar()
    cur = conexao.cursor(dictionary = True)
    cur.execute("""SELECT a.id, a.titulo, a.descricao, a.preco, a.tipo, a.categoria, a.status, a.data_criacao, a.data_atualizacao, 
                        a.email_morador as email, a.nome_morador as autor, a.telefone, a.apartamento as apto  
                   FROM anuncios a WHERE a.id = %s LIMIT 1""", (id,))
    anuncio = cur.fetchall()
    if not anuncio:
        return "Classificado não encontrado", 404
    anuncio = anuncio[0]

    # Puxando as imagens do anúncio
    cur.execute("SELECT url FROM imagens_anuncio WHERE id_anuncio = %s ORDER BY url ASC", (id,))
    imagens = cur.fetchall()
    anuncio['imagens'] = [item['url'] for item in imagens]
    conexao.close()

    # Mandando pro front
    return render_template('classificados.html', anuncio = anuncio)

@app.route('/anunciar', methods = ['GET', 'POST'])
def criar_anuncio():
    if request.method == 'GET':
        return render_template('criar_anuncio.html', dados = dict())
    else:
        if "" in {request.form['titulo'].strip(), request.form['descricao'].strip(),
                  request.form['autor'].strip(), request.form['categoria'].strip()}: 
            flash('Erro ao criar anúncio: por favor, preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('criar_anuncio'))
        else:
            try:
                conexao = conectar()
                cursor = conexao.cursor()
                id_fotos = []

                # Inserindo dados do anúncio
                dados_anuncio = (
                    request.form['titulo'],
                    request.form['descricao'],
                    request.form['categoria'],
                    request.form['tipo'],
                    #None if request.form['preco'] == "" else request.form['preco'],
                    None if request.form['preco'] == "" else float(request.form['preco'].replace(',', '.')),
                    request.form['autor'],
                    request.form['email'],
                    request.form['apartamento'],
                    request.form['telefone'],
                    dt.datetime.now(), # data criação
                    dt.datetime.now()  # data atualização
                )
                cursor.execute("INSERT INTO anuncios (titulo, descricao, categoria, tipo, preco, nome_morador, email_morador, apartamento, telefone, data_criacao, data_atualizacao) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (dados_anuncio))
                id_anuncio = cursor.lastrowid

                # Lidando com as imagens
                fotos_lista = request.files.getlist('fotos_anuncio')
                
                if fotos_lista and fotos_lista[0] != "":
                    ordem = 1
                    
                    for foto in fotos_lista:
                        # Validando extensão do arquivo
                        filename = foto.filename
                        if filename == "" or filename == " ":
                            continue
                        if '.' not in filename:
                            flash(f"Erro ao processar arquivo {foto.filename}: arquivo sem extensão.", "warning")
                            continue
                        extensao = filename.rsplit('.', 1)[1].lower() 
                        if extensao not in EXTENSOES_PERMITIDAS:
                            flash(f"Erro ao processar arquivo {foto.filename}: extensão não permitida (jpg, png, gif).", "warning")
                            continue

                        # Validando tamanho do arquivo
                        foto.seek(0, os.SEEK_END)  # Move o "cursor" para o fim do arquivo
                        tamanho_arquivo = foto.tell() # Pega a posição atual (que é o tamanho em bytes)
                        foto.seek(0)
                        if tamanho_arquivo > TAMANHO_MAXIMO_ARQUIVO:
                            flash(f"Erro ao processar arquivo {foto.filename}: tamanho máximo do arquivo excedido (8mb).", "warning")
                            continue
                        
                        # Criando nome aleatório para o arquivo e salvando
                        nome_unico = str(uuid4()) + "." + extensao
                        caminho = os.path.join(UPLOAD_FOLDER, nome_unico)
                        foto.save(caminho)
                        url, id_cloudinary = upload_imagem(caminho)
                        id_fotos.append(id_cloudinary)
                        dados_imagem = (
                            id_anuncio,
                            url,
                            nome_unico,
                            ordem,
                            id_cloudinary
                        )
                        cursor.execute("INSERT INTO imagens_anuncio (id_anuncio, url, nome_arquivo, ordem, id_cloudinary) VALUES (%s, %s, %s, %s, %s)", dados_imagem)
                        os.remove(caminho)
                        ordem += 1
                        if ordem > NUMERO_MAXIMO_FOTOS:
                            break

                # Comitando a transação e redirecionando para home. Talvez redirecionar para o próprio anúncio
                conexao.commit() 
                conexao.close()
                return redirect(url_for('home'))
            
            except Exception as e:
                flash('Ocorreu algum erro ao criar o anuncio', 'danger')
                print(e)
                conexao.rollback()
                conexao.close()
                for i in id_fotos:
                    excluir_imagem(i)

                return render_template('criar_anuncio.html', dados = request.form)
            
@app.route('/classificado/editar/<int:id>', methods=['GET', 'POST'])
def editar_anuncio(id):
    if request.method == 'GET':
        try:
            conexao = conectar()
            cursor = conexao.cursor(dictionary=True)

            cursor.execute("SELECT * FROM anuncios WHERE id = %s LIMIT 1", (id,))
            anuncio = cursor.fetchone()

            if not anuncio:
                flash('Anúncio não encontrado', 'error')
                return redirect(url_for('home'))

            cursor.execute("SELECT * FROM imagens_anuncio WHERE id_anuncio = %s", (id,))
            anuncio['imagens'] = cursor.fetchall()

            return render_template('editar_anuncio.html', anuncio=anuncio)

        except Exception as e:
            print(e)
            flash(f'Erro ao carregar anúncio: {e}', 'danger')
            return redirect(url_for('home'))

    else:  
        if "" in {
            request.form['titulo'].strip(),
            request.form['descricao'].strip()
        }:
            flash('Preencha os campos obrigatórios.', 'error')
            return redirect(url_for('editar_anuncio', id=id))

        try:
            fotos_salvas = []
            conexao = conectar()
            cursor = conexao.cursor()

            preco_raw = request.form.get('preco', '').strip()
            if preco_raw:
                preco = float(preco_raw.replace(',', '.'))
            else:
                preco = None

            dados = (
                request.form['titulo'],
                request.form['descricao'],
                request.form['categoria'],
                request.form['tipo'],
                request.form['autor'],
                request.form['email'],
                request.form['apartamento'],
                request.form['telefone'],
                preco,
                dt.datetime.now(),
                id
            )

            cursor.execute("""
                UPDATE anuncios
                SET titulo = %s,
                    descricao = %s,
                    categoria = %s,
                    tipo = %s,
                    nome_morador = %s,
                    email_morador = %s,
                    apartamento = %s,
                    telefone = %s,
                    preco = %s,
                    data_atualizacao = %s
                WHERE id = %s
            """, dados)

            # Remover imagens deletadas
            imgs_para_remover = request.form.getlist('imagens_para_remover')
            if imgs_para_remover:
                query = f"SELECT id_cloudinary FROM imagens_anuncio WHERE id IN ({','.join(['%s']*len(imgs_para_remover))})"
                cursor.execute(query, imgs_para_remover)
                arquivos = [resultado[0] for resultado in cursor.fetchall()]
                for arquivo in arquivos:
                    excluir_imagem(arquivo)
                for id_img in imgs_para_remover:
                    cursor.execute("DELETE FROM imagens_anuncio WHERE id = %s", (id_img,))

            # Adicionar imagens novas
            fotos_lista = request.files.getlist('fotos_anuncio')
            id_anuncio = id
            cursor.execute("SELECT COUNT(*) AS total_imgs FROM imagens_anuncio WHERE id_anuncio = %s", (id_anuncio,))
            results = cursor.fetchall()
            if results:
                ordem = results[0][0]
            else:
                ordem = 1

            if fotos_lista and fotos_lista[0] != "":
                id_fotos = []
                for foto in fotos_lista:
                    # Validando extensão do arquivo
                    filename = foto.filename
                    if filename == "" or filename == " ":
                        continue
                    if '.' not in filename:
                        flash(f"Erro ao processar arquivo {foto.filename}: arquivo sem extensão.", "warning")
                        continue
                    extensao = filename.rsplit('.', 1)[1].lower() 
                    if extensao not in EXTENSOES_PERMITIDAS:
                        flash(f"Erro ao processar arquivo {foto.filename}: extensão não permitida (jpg, png, gif).", "warning")
                        continue

                    # Validando tamanho do arquivo
                    foto.seek(0, os.SEEK_END)  # Move o "cursor" para o fim do arquivo
                    tamanho_arquivo = foto.tell() # Pega a posição atual (que é o tamanho em bytes)
                    foto.seek(0)
                    if tamanho_arquivo > TAMANHO_MAXIMO_ARQUIVO:
                        flash(f"Erro ao processar arquivo {foto.filename}: tamanho máximo do arquivo excedido (8mb).", "warning")
                        continue
                    
                    # Criando nome aleatório para o arquivo e salvando
                    nome_unico = str(uuid4()) + "." + extensao
                    caminho = os.path.join(UPLOAD_FOLDER, nome_unico)
                    foto.save(caminho)
                    url, id_cloudinary = upload_imagem(caminho)
                    id_fotos.append(id_cloudinary)
                    dados_imagem = (
                        id_anuncio,
                        url,
                        nome_unico,
                        ordem,
                        id_cloudinary
                    )
                    cursor.execute("INSERT INTO imagens_anuncio (id_anuncio, url, nome_arquivo, ordem, id_cloudinary) VALUES (%s, %s, %s, %s, %s)", dados_imagem)
                    os.remove(caminho)
                    ordem += 1
                    if ordem > NUMERO_MAXIMO_FOTOS:
                        break

            conexao.commit()
            conexao.close()

            flash('Anúncio atualizado com sucesso!', 'success')

            return redirect(url_for('detalhe_anuncio', id=id))

        except Exception as e:
            print(e)
            for i in id_fotos: # Removendo as fotos salvas no cloudinary se a transação falha.
                excluir_imagem(i)
            conexao.rollback()
            flash('Erro ao atualizar anúncio', 'danger')
            return redirect(url_for('editar_anuncio', id=id))
        
@app.route('/classificado/deletar/<int:id>', methods=['POST'])
def deletar_anuncio(id):
    try:
        conexao = conectar()
        cursor = conexao.cursor()

        #Busca pelo anúncio
        cursor.execute("SELECT * FROM anuncios WHERE id = %s", (id,))
        if not cursor.fetchone():
            flash('Anúncio não encontrado', 'danger')
            return redirect(url_for('home'))
        
        #Deletar avaliações
        cursor.execute("DELETE FROM avaliacoes WHERE id_anuncio = %s", (id,))

        # Excluir as imagens salvas em disco
        cursor.execute("SELECT nome_arquivo FROM imagens_anuncio WHERE id_anuncio = %s", (id,))
        arquivos = [resultado[0] for resultado in cursor.fetchall()]
        for arquivo in arquivos:
            excluir_imagem(arquivo)

        # Excluir resto das informações dos anúncios
        cursor.execute("DELETE FROM imagens_anuncio WHERE id_anuncio = %s", (id,))
        cursor.execute("DELETE FROM anuncios WHERE id = %s", (id,))

        conexao.commit()

        flash('Anúncio deletado com sucesso!', 'success')
        return redirect(url_for('home'))

    except Exception as e:
        print(e)
        flash('Erro ao deletar anúncio', 'error')
        return redirect(url_for('home'))
    
@app.route('/categorias/<string:categoria>/', methods = ['GET'])
def lista_categorias(categoria):
    """
    Rota de anúncio por categoria.
    """

    categoria = categoria.lower().strip()

    # A razão que eu preciso fazer isso é porque o nome da url não pode ser o nome formatadinho da categoria no front e no DB.
    # Então tive que criar um mapping que pega o nome que vai na url e pareia com o nome certinho da categoria.
    valid_category = False
    for nome_categoria, url_curb in MAPPING_CATEGORIAS.items():
        if url_curb == categoria:
            categoria = nome_categoria
            valid_category = True
            break
    if not valid_category:
        flash("Categoria não existente.", category = "warning")
        return redirect(url_for('home'))

    page = request.args.get('page', 1, type = int)
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("""SELECT a.id, 
                             a.titulo, 
                             a.categoria, 
                             a.descricao, 
                             a.preco, 
                             coalesce(min(ia.url), '/static/sample_images/placeholder.jpg') as url 
                   FROM anuncios AS a LEFT JOIN imagens_anuncio AS ia ON ia.id_anuncio = a.id 
                   WHERE categoria = %s
                   GROUP BY 1,2,3,4,5
                   ORDER BY data_atualizacao DESC LIMIT %s OFFSET %s""", (categoria, 12, (page-1)*12))
    items = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total_count FROM anuncios WHERE categoria = %s", (categoria,))
    total_count = cursor.fetchall()[0]['total_count']
    pagination = MockPagination(items, page,  12, total_count)
    return render_template('categoria.html', categoria = categoria, pagination = pagination)

@app.route('/buscar', methods=['GET'])
def buscar():
    """
    Rota de busca por texto.
    """
    page = request.args.get('page', 1, type=int)
    termo = request.args.get('q', '').strip()
    if not termo:
        return redirect(url_for('home'))
    like = f'%{termo}%'
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("""SELECT a.id, 
                             a.titulo, 
                             a.categoria, 
                             a.descricao, 
                             a.preco,
                             coalesce(min(ia.url), '/static/sample_images/placeholder.jpg') as url
                   FROM anuncios AS a LEFT JOIN imagens_anuncio AS ia ON ia.id_anuncio = a.id
                   WHERE a.titulo LIKE %s OR a.descricao LIKE %s
                   GROUP BY 1,2,3,4,5
                   ORDER BY data_atualizacao DESC LIMIT %s OFFSET %s""",
                   (like, like, 12, (page - 1) * 12))
    items = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total_count FROM anuncios WHERE titulo LIKE %s OR descricao LIKE %s", (like, like))
    total_count = cursor.fetchall()[0]['total_count']
    conexao.close()
    pagination = MockPagination(items, page, 12, total_count)
    return render_template('home.html', pagination=pagination, titulo=f'Resultados para "{termo}"')

# ------------ FIM DAS DEFINIÇÕES DE ROTA ------------

if __name__ == '__main__':
    app.run(debug = True)
