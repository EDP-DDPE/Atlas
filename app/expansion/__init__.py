"""Integração com o Expansion 3D (visualizador 3D das redes do Interplan).

O Expansion roda no mesmo servidor, em outra porta, e não consegue ler a sessão do Atlas.
Este blueprint expõe uma única rota que, para quem já está logado aqui, devolve um ticket
assinado e manda o usuário de volta ao Expansion. Nenhuma senha ou token do Azure sai daqui:
o ticket leva só matrícula, nome, e-mail e o indicador de administrador, vale poucos segundos
e é assinado com HMAC-SHA256 usando a frase secreta EXPANSION_SECRET do .env.
"""
