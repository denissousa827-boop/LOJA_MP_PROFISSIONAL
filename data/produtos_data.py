# data/produtos_data.py

# Dicionário principal com 15 produtos eletrônicos (ID, Nome, Preço)

PRODUTOS_ELETRONICOS = {
    # Itens com preços menores, conforme solicitado
    "P001": {"nome": "Fone de Ouvido Bluetooth TWS", "preco": 89.90, "descricao": "Áudio de alta fidelidade e bateria de longa duração."},
    "P002": {"nome": "Carregador Portátil 10000mAh", "preco": 65.50, "descricao": "Carregue seu celular em qualquer lugar, design slim."},
    "P003": {"nome": "Smartwatch com Monitor Cardíaco", "preco": 149.99, "descricao": "Notificações, monitoramento de sono e passos."},
    "P004": {"nome": "Mouse Sem Fio Ergonômico", "preco": 39.90, "descricao": "Conforto e precisão para o seu dia a dia."},
    "P005": {"nome": "Teclado Mecânico Compacto", "preco": 249.00, "descricao": "Switches táteis para digitação rápida e responsiva."},
    "P006": {"nome": "Webcam Full HD 1080p", "preco": 99.90, "descricao": "Ideal para videochamadas e streaming."},
    "P007": {"nome": "SSD Interno 500GB NVMe", "preco": 299.99, "descricao": "Velocidade ultrarrápida para boot e carregamento de jogos."},
    "P008": {"nome": "Tablet Android 10 polegadas", "preco": 599.00, "descricao": "Tela grande e processador rápido para multimídia."},
    "P009": {"nome": "Roteador Dual Band Wi-Fi 6", "preco": 189.90, "descricao": "Conexão estável e alta velocidade para toda a casa."},
    "P010": {"nome": "Caixa de Som Portátil Bluetooth", "preco": 79.99, "descricao": "Som potente e resistente à água."},
    "P011": {"nome": "Pendrive USB 3.0 64GB", "preco": 45.00, "descricao": "Transferência rápida de arquivos grandes."},
    "P012": {"nome": "Câmera de Segurança Smart Wi-Fi", "preco": 129.90, "descricao": "Monitoramento remoto com visão noturna."},
    "P013": {"nome": "Headset Gamer com LED RGB", "preco": 169.00, "descricao": "Microfone de alta sensibilidade e áudio imersivo."},
    "P014": {"nome": "Adaptador USB-C para HDMI", "preco": 55.90, "descricao": "Conecte seu notebook a monitores externos."},
    "P015": {"nome": "Cabo de Carregamento Rápido 2m", "preco": 29.90, "descricao": "Cabo trançado de alta durabilidade."}
}

def get_produtos():
    """Retorna o dicionário completo de produtos."""
    return PRODUTOS_ELETRONICOS

def get_produto_por_id(id_produto):
    """Retorna um produto específico pelo ID."""
    return PRODUTOS_ELETRONICOS.get(id_produto)
