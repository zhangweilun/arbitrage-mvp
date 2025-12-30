import requests

def get_token_price_usd(token_id: str) -> float:
    """
    从 CoinGecko 获取价格。
    常见 token_id: "solana", "usd-coin", "bitcoin"
    """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
    resp = requests.get(url)
    data = resp.json()
    return data[token_id]["usd"]

# 使用
sol_price = get_token_price_usd("solana")      # ~20.0

print(f"Solana price in USD: {sol_price}")