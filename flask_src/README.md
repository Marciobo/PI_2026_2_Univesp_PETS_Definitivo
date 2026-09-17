# Sobre as pastas

Cada pasta do projeto serve um propósito bastante simples e bastante específico. Novas pastas podem ser adicionadas sem problemas caso seja necessário.

- routes/ - caso queiram usar o recurso de Blueprints para facilitar a construção de rotas HTTP, recomendo criar um arquivo para cada endpoint na pasta rotas. Se não, adicionar as rotas em app.py mesmo.

- static/ - estilos css e recursos para renderizar no front-end. Fora isso, tem a pasta /uploads/ para gerenciar upload de arquivos. Caso queira armazenar as imagens dos classificados localmente, armazenar nessa pasta.

- templates/ - htmls do front para serem utilizados no render_template(). Nada demais aqui.

- models/ - caso forem usar sqlalchemy para fazer integração com o banco de dados, cada tabela precisa ter um modelo dentro de models. E.g. table classificados -> classificados.py com modelo Classificado 

De resto, todos os outros arquivos python podem ir em flask_src/ padrão.