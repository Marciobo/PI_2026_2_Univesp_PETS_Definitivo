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

@app.route('/', methods=['GET'])
def home():
    """
    Rota padrão do site.
    Exibe a página inicial com os animais cadastrados.
    """

    page = request.args.get('page', 1, type=int)

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # Busca os animais cadastrados.
    # A consulta também busca uma foto para representar cada animal.
    cursor.execute("""
        SELECT
            a.id_animal,
            a.nome,
            a.especie,
            a.idade_aproximada,
            a.porte,
            a.sexo,
            a.codigo_chip,
            a.status,
            a.observacoes,
            COALESCE(
                MIN(f.caminho_foto),
                '/static/sample_images/placeholder.jpg'
            ) AS foto
        FROM animais AS a
        LEFT JOIN fotos_animais AS f
            ON f.id_animal = a.id_animal
        GROUP BY
            a.id_animal,
            a.nome,
            a.especie,
            a.idade_aproximada,
            a.porte,
            a.sexo,
            a.codigo_chip,
            a.status,
            a.observacoes
        ORDER BY a.data_cadastro DESC
        LIMIT %s OFFSET %s
    """, (12, (page - 1) * 12))

    items = cursor.fetchall()

    # Conta quantos animais existem no banco.
    cursor.execute("""
        SELECT COUNT(*) AS total_count
        FROM animais
    """)

    total_count = cursor.fetchall()[0]['total_count']
    
    pagination = MockPagination(
        items,
        page,
        12,
        total_count
    )

    conexao.close()

    return render_template(
        'home.html',
        pagination=pagination
    )

app.route('/anunciar', methods=['GET', 'POST'])
def criar_animal():
    """
    Rota responsável pelo cadastro de um novo animal.

    GET:
        Mostra o formulário.

    POST:
        Recebe os dados do cachorro, salva no banco
        e cadastra suas fotos.
    """

    if request.method == 'GET':
        return render_template(
            'criar_anuncio.html',
            dados=dict()
        )

    else:

        # Verifica se os campos obrigatórios foram preenchidos.
        if "" in {
            request.form['nome'].strip(),
            request.form['especie'].strip(),
            request.form['idade_aproximada'].strip(),
            request.form['porte'].strip(),
            request.form['sexo'].strip(),
            request.form['status'].strip()
        }:

            flash(
                'Erro ao cadastrar animal: por favor, preencha todos os campos obrigatórios.',
                'danger'
            )

            return redirect(
                url_for('criar_anuncio')
            )

        else:

            try:

                conexao = conectar()
                cursor = conexao.cursor()

                id_fotos = []

                # -------------------------------------------------
                # Inserindo os dados do animal
                # -------------------------------------------------

                dados_animal = (
                    request.form['nome'],
                    request.form['especie'],
                    request.form['idade_aproximada'],
                    request.form['porte'],
                    request.form['sexo'],
                    request.form['codigo_chip'],
                    request.form['status'],
                    request.form['observacoes'],
                    dt.datetime.now()
                )

                cursor.execute("""
                    INSERT INTO animais
                    (
                        nome,
                        especie,
                        idade_aproximada,
                        porte,
                        sexo,
                        codigo_chip,
                        status,
                        observacoes,
                        data_cadastro
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, dados_animal)

                # Recupera o ID do animal que acabou de ser cadastrado.
                id_animal = cursor.lastrowid


                # -------------------------------------------------
                # Lidando com as imagens
                # -------------------------------------------------

                fotos_lista = request.files.getlist(
                    'fotos_animal'
                )

                if fotos_lista and fotos_lista[0] != "":

                    ordem = 1

                    for foto in fotos_lista:

                        # Validando extensão do arquivo
                        filename = foto.filename

                        if filename == "" or filename == " ":
                            continue

                        if '.' not in filename:
                            flash(
                                f"Erro ao processar arquivo {foto.filename}: arquivo sem extensão.",
                                "warning"
                            )
                            continue

                        extensao = filename.rsplit(
                            '.',
                            1
                        )[1].lower()

                        if extensao not in EXTENSOES_PERMITIDAS:
                            flash(
                                f"Erro ao processar arquivo {foto.filename}: extensão não permitida.",
                                "warning"
                            )
                            continue


                        # Validando tamanho do arquivo
                        foto.seek(0, os.SEEK_END)

                        tamanho_arquivo = foto.tell()

                        foto.seek(0)

                        if tamanho_arquivo > TAMANHO_MAXIMO_ARQUIVO:
                            flash(
                                f"Erro ao processar arquivo {foto.filename}: tamanho máximo do arquivo excedido.",
                                "warning"
                            )
                            continue


                        # Criando nome aleatório para o arquivo
                        # e salvando temporariamente.
                        nome_unico = str(uuid4()) + "." + extensao

                        caminho = os.path.join(
                            UPLOAD_FOLDER,
                            nome_unico
                        )

                        foto.save(caminho)


                        # Envia a imagem para o serviço
                        # de armazenamento utilizado pelo projeto.
                        url, id_cloudinary = upload_imagem(caminho)

                        id_fotos.append(id_cloudinary)


                        # -------------------------------------------------
                        # Salvando informações da foto no banco
                        # -------------------------------------------------

                        dados_imagem = (
                            id_animal,
                            url,
                            ordem,
                            dt.datetime.now()
                        )

                        cursor.execute("""
                            INSERT INTO fotos_animais
                            (
                                id_animal,
                                caminho_foto,
                                ordem,
                                data_cadastro
                            )
                            VALUES
                            (
                                %s,
                                %s,
                                %s,
                                %s
                            )
                        """, dados_imagem)


                        # Remove a cópia temporária da imagem.
                        os.remove(caminho)

                        ordem += 1


                        # Impede que o usuário ultrapasse
                        # o número máximo de fotos permitido.
                        if ordem > NUMERO_MAXIMO_FOTOS:
                            break


                # Comitando a transação e redirecionando para home.
                conexao.commit()
                conexao.close()

                return redirect(
                    url_for('home')
                )


            except Exception as e:

                flash(
                    'Ocorreu algum erro ao cadastrar o animal.',
                    'danger'
                )

                print(e)

                conexao.rollback()
                conexao.close()

                # Remove as imagens que foram enviadas
                # caso a transação do banco tenha falhado.
                for i in id_fotos:
                    excluir_imagem(i)

                return render_template(
                    'criar_anuncio.html',
                    dados=request.form
                )

@app.route('/classificado/editar/<int:id>', methods=['GET', 'POST'])
def editar_animal(id):
    """
    Rota responsável pela edição de um animal cadastrado.

    GET:
        Busca os dados atuais e mostra o formulário preenchido.

    POST:
        Recebe os novos dados e atualiza o animal no banco.
    """

    if request.method == 'GET':

        try:

            conexao = conectar()
            cursor = conexao.cursor(dictionary=True)

            # Busca o animal pelo ID.
            cursor.execute("""
                SELECT *
                FROM animais
                WHERE id_animal = %s
                LIMIT 1
            """, (id,))

            anuncio = cursor.fetchone()


            # Verifica se o animal existe.
            if not anuncio:

                flash(
                    'Animal não encontrado',
                    'error'
                )

                conexao.close()

                return redirect(
                    url_for('home')
                )


            # Busca as fotos do animal.
            cursor.execute("""
                SELECT *
                FROM fotos_animais
                WHERE id_animal = %s
                ORDER BY ordem ASC
            """, (id,))

            anuncio['imagens'] = cursor.fetchall()

            conexao.close()

            return render_template(
                'editar_anuncio.html',
                anuncio=anuncio
            )


        except Exception as e:

            print(e)

            flash(
                f'Erro ao carregar animal: {e}',
                'danger'
            )

            return redirect(
                url_for('home')
            )


    else:

        # Verifica os campos obrigatórios.
        if "" in {
            request.form['nome'].strip(),
            request.form['especie'].strip(),
            request.form['idade_aproximada'].strip(),
            request.form['porte'].strip(),
            request.form['sexo'].strip()
        }:

            flash(
                'Preencha os campos obrigatórios.',
                'error'
            )

            return redirect(
                url_for(
                    'editar_anuncio',
                    id=id
                )
            )


        try:

            fotos_salvas = []

            conexao = conectar()
            cursor = conexao.cursor()


            # -------------------------------------------------
            # Atualizando os dados do animal
            # -------------------------------------------------

            dados = (
                request.form['nome'],
                request.form['especie'],
                request.form['idade_aproximada'],
                request.form['porte'],
                request.form['sexo'],
                request.form['codigo_chip'],
                request.form['status'],
                request.form['observacoes'],
                id
            )


            cursor.execute("""
                UPDATE animais
                SET
                    nome = %s,
                    especie = %s,
                    idade_aproximada = %s,
                    porte = %s,
                    sexo = %s,
                    codigo_chip = %s,
                    status = %s,
                    observacoes = %s
                WHERE id_animal = %s
            """, dados)


            # -------------------------------------------------
            # Remover imagens selecionadas para exclusão
            # -------------------------------------------------

            imgs_para_remover = request.form.getlist(
                'imagens_para_remover'
            )


            if imgs_para_remover:

                # Busca os caminhos das imagens que serão removidas.
                query = f"""
                    SELECT caminho_foto
                    FROM fotos_animais
                    WHERE id_foto IN
                    ({','.join(['%s'] * len(imgs_para_remover))})
                """

                cursor.execute(
                    query,
                    imgs_para_remover
                )

                arquivos = [
                    resultado[0]
                    for resultado in cursor.fetchall()
                ]


                # Remove os registros das fotos no banco.
                for id_img in imgs_para_remover:

                    cursor.execute("""
                        DELETE FROM fotos_animais
                        WHERE id_foto = %s
                    """, (id_img,))


            # -------------------------------------------------
            # Adicionar novas imagens
            # -------------------------------------------------

            fotos_lista = request.files.getlist(
                'fotos_animal'
            )

            id_animal = id


            # Descobre quantas fotos o animal já possui.
            cursor.execute("""
                SELECT COUNT(*) AS total_imgs
                FROM fotos_animais
                WHERE id_animal = %s
            """, (id_animal,))

            results = cursor.fetchall()


            if results:
                ordem = results[0][0] + 1
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
                        flash(
                            f"Erro ao processar arquivo {foto.filename}: arquivo sem extensão.",
                            "warning"
                        )
                        continue

                    extensao = filename.rsplit(
                        '.',
                        1
                    )[1].lower()

                    if extensao not in EXTENSOES_PERMITIDAS:
                        flash(
                            f"Erro ao processar arquivo {foto.filename}: extensão não permitida.",
                            "warning"
                        )
                        continue


                    # Validando tamanho do arquivo
                    foto.seek(0, os.SEEK_END)

                    tamanho_arquivo = foto.tell()

                    foto.seek(0)

                    if tamanho_arquivo > TAMANHO_MAXIMO_ARQUIVO:
                        flash(
                            f"Erro ao processar arquivo {foto.filename}: tamanho máximo do arquivo excedido.",
                            "warning"
                        )
                        continue


                    # Criando nome aleatório para o arquivo.
                    nome_unico = str(uuid4()) + "." + extensao

                    caminho = os.path.join(
                        UPLOAD_FOLDER,
                        nome_unico
                    )

                    foto.save(caminho)


                    # Faz upload da imagem.
                    url, id_cloudinary = upload_imagem(caminho)

                    id_fotos.append(id_cloudinary)


                    # Dados da nova foto.
                    dados_imagem = (
                        id_animal,
                        url,
                        ordem,
                        dt.datetime.now()
                    )


                    # Insere a nova foto na tabela
                    # FOTOS_ANIMAIS.
                    cursor.execute("""
                        INSERT INTO fotos_animais
                        (
                            id_animal,
                            caminho_foto,
                            ordem,
                            data_cadastro
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s
                        )
                    """, dados_imagem)


                    # Remove a cópia temporária.
                    os.remove(caminho)

                    ordem += 1


                    if ordem > NUMERO_MAXIMO_FOTOS:
                        break


            conexao.commit()
            conexao.close()


            flash(
                'Animal atualizado com sucesso!',
                'success'
            )


            return redirect(
                url_for(
                    'detalhe_anuncio',
                    id=id
                )
            )


        except Exception as e:

            print(e)

            for i in fotos_salvas:
                excluir_imagem(i)

            conexao.rollback()

            conexao.close()

            flash(
                'Erro ao atualizar animal.',
                'danger'
            )

            return redirect(
                url_for(
                    'editar_anuncio',
                    id=id
                )
            )

@app.route('/classificado/deletar/<int:id>', methods=['POST'])
def deletar_animal(id):
    """
    Exclui um animal e suas fotos do banco de dados.
    """

    try:

        conexao = conectar()
        cursor = conexao.cursor()


        # -------------------------------------------------
        # Busca pelo animal
        # -------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM animais
            WHERE id_animal = %s
        """, (id,))


        if not cursor.fetchone():

            flash(
                'Animal não encontrado',
                'danger'
            )

            conexao.close()

            return redirect(
                url_for('home')
            )


        # -------------------------------------------------
        # Excluir as fotos do animal
        # -------------------------------------------------

        cursor.execute("""
            SELECT caminho_foto
            FROM fotos_animais
            WHERE id_animal = %s
        """, (id,))


        arquivos = [
            resultado[0]
            for resultado in cursor.fetchall()
        ]


        # Exclui os registros das fotos.
        cursor.execute("""
            DELETE FROM fotos_animais
            WHERE id_animal = %s
        """, (id,))


        # -------------------------------------------------
        # Excluir o animal
        # -------------------------------------------------

        cursor.execute("""
            DELETE FROM animais
            WHERE id_animal = %s
        """, (id,))


        conexao.commit()

        conexao.close()


        flash(
            'Animal deletado com sucesso!',
            'success'
        )


        return redirect(
            url_for('home')
        )


    except Exception as e:

        print(e)

        flash(
            'Erro ao deletar animal',
            'error'
        )

        return redirect(
            url_for('home')
        )


    
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
