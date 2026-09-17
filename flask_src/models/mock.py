import math
import datetime as dt

class MockAnuncio():
    """
        Classe de mock de anúncio só pra pequenos testes.
    """
    def __init__(self, id, titulo, descricao, autor, categoria = "Outros", preco = None, thumbnail = '1.jpeg'):
        self.id = id
        self.titulo = titulo
        self.descricao = descricao
        self.autor = autor
        self.categoria = categoria
        self.preco = preco
        self.thumbnail = thumbnail


class MockAnuncioDetalhado():
    """
        Classe com mock de anúncio detalhado para grandes testes.
    """

    def __init__(self, id, 
                 titulo, 
                 descricao, 
                 autor,
                 apto = 302, 
                 telefone = '11 9329873287',
                 email = 'sample_email@email.com',
                 categoria = "Outros", 
                 tipo = 'Produto',
                 preco = None, 
                 thumbnail = '1.jpeg',
                 imagens = ['https://www.receiteria.com.br/wp-content/uploads/bolo-simples-de-chocolate.jpeg',
                            'https://cdn.awsli.com.br/600x1000/2658/2658919/produto/257217253/fatia-de-bolo-vegano-de-brigadeiro-com-morangos-a3liq2p83s.png',
                            'https://s2-receitas.glbimg.com/QLj9I-7FXucI8zSGLskH4hTPgXw=/1280x0/filters:format(jpeg)/https://i.s3.glbimg.com/v1/AUTH_1f540e0b94d8437dbbc39d567a1dee68/internal_photos/bs/2022/V/Z/7jJ0zHQvqiPIKEQQxPXw/bolo-facil-de-liquidificador.jpg', 
                            'https://www.sabornamesa.com.br/media/k2/items/cache/964a78b2d96f3061f52701ec46354cb6_XL.jpg'],
                 data_criacao = dt.date(2026,1,1),
                 data_ultima_atualizacao = dt.date.today(),
                 ativo = True):
        self.id = id
        self.titulo = titulo
        self.descricao = descricao
        self.autor = autor
        self.apto = apto
        self.telefone = telefone
        self.email = email
        self.categoria = categoria
        self.tipo = tipo
        self.preco = preco
        self.thumbnail = thumbnail
        self.imagens = imagens
        self.data_criacao = data_criacao
        self.data_ultima_atualizacao = data_ultima_atualizacao
        self.ativo = ativo

class MockPagination:
    """
        Classe que faz um mock da classe de paginação do SQL Alchemy. Pode servir de template para criar a própria classe de paginação nossa,
        caso não queiramos usar o sql alchemy e só pingar o DB na raça.
    """
    def __init__(self, items, page, per_page, total):
        self.items = items       # A lista de anúncios desta página específica
        self.page = page         # Página atual (ex: 1)
        self.per_page = per_page # Quantos itens por página (ex: 10)
        self.total = total       # Total de anúncios no banco inteiro (ex: 50)

    @property
    def pages(self):
        """Calcula o total de páginas"""
        if self.per_page == 0 or self.total == 0:
            return 0
        return math.ceil(self.total / self.per_page)

    @property
    def has_prev(self):
        """Tem página anterior?"""
        return self.page > 1

    @property
    def has_next(self):
        """Tem próxima página?"""
        return self.page < self.pages

    @property
    def prev_num(self):
        """Número da página anterior"""
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self):
        """Número da próxima página"""
        return self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=1, left_current=2, right_current=2, right_edge=1):
        """
        Método mágico que o Jinja usa para desenhar os números (1, 2, 3 ... 8, 9)
        Ele retorna 'None' onde devem aparecer os três pontinhos (...)
        """
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (self.page - left_current - 1 < num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num