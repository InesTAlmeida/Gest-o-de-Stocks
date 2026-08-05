import pandas as pd

def get_mock_inventory():
    """Retorna uma tabela simulada de produtos de um salão de beleza."""
    data = [
        {
            "id_produto": 101,
            "nome_produto": "Champô Hidratante 1000ml",
            "categoria": "Lavatório",
            "quantidade_stock": 8,
            "stock_minimo": 3,
            "preco_custo": 12.50,
            "preco_venda": 25.00,
        },
        {
            "id_produto": 102,
            "nome_produto": "Máscara Reparação Intensa 500g",
            "categoria": "Tratamento",
            "quantidade_stock": 2,
            "stock_minimo": 4,
            "preco_custo": 15.00,
            "preco_venda": 32.00,
        },
        {
            "id_produto": 103,
            "nome_produto": "Tinta Castanho Claro 6.0",
            "categoria": "Coloração",
            "quantidade_stock": 0,
            "stock_minimo": 5,
            "preco_custo": 4.20,
            "preco_venda": 10.00,
        },
        {
            "id_produto": 104,
            "nome_produto": "Óleo de Argan 100ml",
            "categoria": "Finalização",
            "quantidade_stock": 12,
            "stock_minimo": 2,
            "preco_custo": 8.00,
            "preco_venda": 18.50,
        },
        {
            "id_produto": 105,
            "nome_produto": "Pó Descolorante 500g",
            "categoria": "Coloração",
            "quantidade_stock": 1,
            "stock_minimo": 3,
            "preco_custo": 11.00,
            "preco_venda": 22.00,
        }
    ]
    
    df = pd.DataFrame(data)
    
    # Adicionar coluna calculada de Estado do Stock
    def calcular_estado(row):
        if row["quantidade_stock"] == 0:
            return "❌ Esgotado"
        elif row["quantidade_stock"] <= row["stock_minimo"]:
            return "⚠️ Stock Baixo"
        return "✅ OK"

    df["estado"] = df.apply(calcular_estado, axis=1)
    return df