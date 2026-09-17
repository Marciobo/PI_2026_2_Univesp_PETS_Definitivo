import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_imagem(caminho_imagem):
    resultado = cloudinary.uploader.upload(caminho_imagem)
    
    # URL da imagem hospedada
    url, id = resultado.get("secure_url"), resultado.get("public_id")
    
    return url, id

def excluir_imagem(public_id):
    cloudinary.uploader.destroy(public_id)
    return

# Teste
#if __name__ == "__main__":
#    url_imagem = upload_imagem("C:/MySQL/bd_classificados_diagrama.png")
#    print("Imagem disponível em:", url_imagem)
#
# VARIÁVEIS DE AMBIENTE PARA O CLOUDINARY (EXEMPLO):
# CLOUDINARY_URL=cloudinary://<your_api_key>:<your_api_secret>@dumthoq7j