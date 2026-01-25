import os
import mercadopago
import database

def gerar_link_pagamento(produto, id_venda, valor_total):
    """
    Gera o link do Mercado Pago configurado para o domínio PythonAnywhere.
    Busca o token dinamicamente do banco de dados.
    """
    try:
        # 1. Busca as configurações no banco de dados
        configs = database.get_configuracoes()
        token_do_banco = configs.get('mercado_pago_token')
        
        # 2. Define o Access Token
        ACCESS_TOKEN = token_do_banco if token_do_banco else os.getenv("ACCESS_TOKEN")

        if not ACCESS_TOKEN:
            print("ERRO: Access Token do Mercado Pago não encontrado!")
            return None

        # Inicializa o SDK
        sdk = mercadopago.SDK(ACCESS_TOKEN)

        # 3. Configura seu domínio real do PythonAnywhere
        # O Webhook só funciona com links HTTPS reais como o seu
        LINK_EXTERNO = "https://denissousa827.pythonanywhere.com"

        preference_data = {
            "items": [
                {
                    "id": str(produto.get('id', '000')),
                    "title": f"{produto.get('nome', 'Produto')} + Envio",
                    "quantity": 1,
                    "unit_price": float(valor_total), # Valor total (produto + frete)
                    "currency_id": "BRL"
                }
            ],
            "external_reference": str(id_venda), # ID que o Webhook usará para achar a venda
            "back_urls": {
                "success": f"{LINK_EXTERNO}/sucesso",
                "failure": f"{LINK_EXTERNO}/homepage",
                "pending": f"{LINK_EXTERNO}/homepage"
            },
            # Esta linha abaixo é o "segredo" para a loja aprovar o pagamento sozinha:
            "notification_url": f"{LINK_EXTERNO}/webhook/mercadopago", 
            "auto_return": "approved",
            "payment_methods": {
                "installments": 12 
            }
        }

        # Cria a preferência de pagamento no Mercado Pago
        resultado = sdk.preference().create(preference_data)
        
        if "response" in resultado and "init_point" in resultado["response"]:
            # Retorna o link (Checkout Pro) para o cliente pagar
            return resultado["response"]["init_point"]
        else:
            print("Erro detalhado do MP:", resultado)
            return None

    except Exception as e:
        print(f"Erro crítico no pagamento: {e}")
        return None
