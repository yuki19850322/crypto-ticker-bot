#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import time
import threading
import json
import requests
from datetime import datetime
from pycoingecko import CoinGeckoAPI

# CoinGeckoのAPIクライアントを初期化
cg = CoinGeckoAPI()

# ステーブルコインとLSTの情報を格納する辞書（デフォルトトークン用）
STABLECOINS = {
    'usdt': {
        'name': 'Tether',
        'description': 'Tether (USDT)は、米ドルに価格が連動するように設計されたステーブルコインです。各USDTは1米ドルの価値を持つ資産によって裏付けられています。',
        'issuer': 'Tether Limited',
        'launch_date': '2014年10月',
        'website': 'https://tether.to/',
        'market_cap_rank': '3位前後（変動あり）',
        'blockchain': 'マルチチェーン（Ethereum, Tron, Solana, その他）'
    },
    'usdc': {
        'name': 'USD Coin',
        'description': 'USD Coin (USDC)は、米ドルに1:1で価格が連動するステーブルコインです。Circle社とCoinbase社が共同で設立したCENTRE consortiumによって発行されています。',
        'issuer': 'Circle Internet Financial',
        'launch_date': '2018年9月',
        'website': 'https://www.circle.com/usdc',
        'market_cap_rank': '5位前後（変動あり）',
        'blockchain': 'マルチチェーン（Ethereum, Solana, Avalanche, その他）'
    },
    'dai': {
        'name': 'Dai',
        'description': 'Dai (DAI)は、MakerDAOプロトコルによって発行される分散型ステーブルコインです。暗号資産を担保として生成され、米ドルに価格が連動するように設計されています。',
        'issuer': 'MakerDAO',
        'launch_date': '2017年12月',
        'website': 'https://makerdao.com/',
        'market_cap_rank': '20位前後（変動あり）',
        'blockchain': 'Ethereum'
    },
    'busd': {
        'name': 'Binance USD',
        'description': 'Binance USD (BUSD)は、Binanceと提携してPaxos Trust Companyによって発行されるステーブルコインです。米ドルに1:1で価格が連動するように設計されています。',
        'issuer': 'Paxos Trust Company',
        'launch_date': '2019年9月',
        'website': 'https://paxos.com/busd/',
        'market_cap_rank': '以前は上位だったが、2023年以降発行停止',
        'blockchain': 'マルチチェーン（Ethereum, BNB Chain）'
    }
}

LST_TOKENS = {
    'steth': {
        'name': 'Lido Staked ETH',
        'description': 'Lido Staked ETH (stETH)は、Lidoプロトコルを通じてステーキングされたETHを表すトークンです。保有者はイーサリアムのステーキング報酬を受け取ることができます。',
        'issuer': 'Lido DAO',
        'launch_date': '2020年12月',
        'website': 'https://lido.fi/',
        'market_cap_rank': '10位前後（変動あり）',
        'blockchain': 'Ethereum'
    },
    'reth': {
        'name': 'Rocket Pool ETH',
        'description': 'Rocket Pool ETH (rETH)は、Rocket Poolプロトコルを通じてステーキングされたETHを表すトークンです。分散型のイーサリアムステーキングプールとして機能します。',
        'issuer': 'Rocket Pool',
        'launch_date': '2021年11月',
        'website': 'https://rocketpool.net/',
        'market_cap_rank': '50位前後（変動あり）',
        'blockchain': 'Ethereum'
    },
    'cbeth': {
        'name': 'Coinbase Wrapped Staked ETH',
        'description': 'Coinbase Wrapped Staked ETH (cbETH)は、Coinbaseのステーキングサービスを通じてステーキングされたETHを表すトークンです。',
        'issuer': 'Coinbase',
        'launch_date': '2022年8月',
        'website': 'https://www.coinbase.com/',
        'market_cap_rank': '30位前後（変動あり）',
        'blockchain': 'Ethereum'
    },
    'ldo': {
        'name': 'Lido DAO Token',
        'description': 'Lido DAO Token (LDO)は、Lidoプロトコルの分散型自律組織（DAO）の統治トークンです。LDO保有者はプロトコルの重要な決定に投票できます。',
        'issuer': 'Lido DAO',
        'launch_date': '2020年12月',
        'website': 'https://lido.fi/',
        'market_cap_rank': '40位前後（変動あり）',
        'blockchain': 'Ethereum'
    }
}

# CoinGeckoのIDとシンボルのマッピング（デフォルトトークン用）
COINGECKO_IDS = {
    'usdt': 'tether',
    'usdc': 'usd-coin',
    'dai': 'dai',
    'busd': 'binance-usd',
    'steth': 'staked-ether',
    'reth': 'rocket-pool-eth',
    'cbeth': 'coinbase-wrapped-staked-eth',
    'ldo': 'lido-dao'
}

# 全トークンのリストを作成（デフォルトトークン用）
ALL_TOKENS = {**STABLECOINS, **LST_TOKENS}

# 価格データを保存するグローバル変数
price_data = {}
ohlcv_data = {}
token_cache = {}  # トークン情報のキャッシュ

# トークンリストのキャッシュ（検索用）
all_coins_cache = None
last_cache_update = 0
CACHE_DURATION = 3600  # キャッシュの有効期間（秒）

def get_all_coins():
    """CoinGeckoから全トークンリストを取得する関数（キャッシュ付き）"""
    global all_coins_cache, last_cache_update
    
    current_time = time.time()
    if all_coins_cache is None or (current_time - last_cache_update) > CACHE_DURATION:
        try:
            all_coins_cache = cg.get_coins_list()
            last_cache_update = current_time
            print(f"Updated coin list cache with {len(all_coins_cache)} coins")
        except Exception as e:
            print(f"Error fetching coin list: {e}")
            if all_coins_cache is None:
                all_coins_cache = []  # エラー時に空リストを返す
    
    return all_coins_cache

def search_coins(query):
    """トークンを検索する関数"""
    if not query or len(query) < 2:
        return []
    
    query = query.lower()
    all_coins = get_all_coins()
    
    # 検索語に一致するトークンをフィルタリング
    matching_coins = [
        coin for coin in all_coins 
        if query in coin['name'].lower() or query in coin['symbol'].lower()
    ]
    
    # 最大20件まで返す
    return matching_coins[:20]

def get_token_info_from_coingecko(coin_id):
    """CoinGeckoからトークンの詳細情報を取得する関数（キャッシュ付き）"""
    if coin_id in token_cache:
        return token_cache[coin_id]
    
    try:
        # CoinGeckoからトークン情報を取得
        coin_data = cg.get_coin_by_id(id=coin_id)
        
        # 必要な情報を抽出
        info = {
            'name': coin_data.get('name', 'Unknown'),
            'symbol': coin_data.get('symbol', '').upper(),
            'description': coin_data.get('description', {}).get('ja', coin_data.get('description', {}).get('en', '情報がありません')),
            'issuer': coin_data.get('developer_data', {}).get('organization_name', '不明'),
            'launch_date': '不明',  # CoinGeckoでは正確な発行日が取得しにくい
            'website': coin_data.get('links', {}).get('homepage', [''])[0],
            'market_cap_rank': f"{coin_data.get('market_cap_rank', '不明')}位",
            'blockchain': ', '.join(coin_data.get('platforms', {}).keys()) if coin_data.get('platforms') else '不明'
        }
        
        # キャッシュに保存
        token_cache[coin_id] = info
        return info
    except Exception as e:
        print(f"Error fetching token info for {coin_id}: {e}")
        return {
            'name': f"Unknown ({coin_id})",
            'symbol': coin_id.upper(),
            'description': '情報を取得できませんでした',
            'issuer': '不明',
            'launch_date': '不明',
            'website': '',
            'market_cap_rank': '不明',
            'blockchain': '不明'
        }

def get_token_info(symbol_or_id):
    """トークンの詳細情報を取得する関数"""
    # デフォルトトークンの場合
    if symbol_or_id in ALL_TOKENS:
        return ALL_TOKENS[symbol_or_id]
    
    # CoinGecko IDの場合
    if symbol_or_id in COINGECKO_IDS:
        coin_id = COINGECKO_IDS[symbol_or_id]
    else:
        coin_id = symbol_or_id
    
    # CoinGeckoから情報を取得
    return get_token_info_from_coingecko(coin_id)

def get_token_price(symbol_or_id):
    """トークンの現在価格をCoinGeckoから取得する関数"""
    try:
        # シンボルをCoinGecko IDに変換
        if symbol_or_id in COINGECKO_IDS:
            coin_id = COINGECKO_IDS[symbol_or_id]
        else:
            coin_id = symbol_or_id
            
        # CoinGeckoから価格データを取得
        price_data_response = cg.get_price(ids=coin_id, vs_currencies='usd')
        if coin_id not in price_data_response:
            print(f"No price data for {coin_id}")
            return None
            
        price = price_data_response[coin_id]['usd']
        
        # 価格データを保存
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if symbol_or_id not in price_data:
            price_data[symbol_or_id] = []
        
        # 最大100ポイントまで保存
        price_data[symbol_or_id].append({'timestamp': timestamp, 'price': price})
        if len(price_data[symbol_or_id]) > 100:
            price_data[symbol_or_id].pop(0)
            
        return price
    except Exception as e:
        print(f"Error fetching price for {symbol_or_id}: {e}")
        return None

def get_historical_data(symbol_or_id, days=30):
    """トークンの過去の価格データをCoinGeckoから取得する関数"""
    try:
        # シンボルをCoinGecko IDに変換
        if symbol_or_id in COINGECKO_IDS:
            coin_id = COINGECKO_IDS[symbol_or_id]
        else:
            coin_id = symbol_or_id
            
        # CoinGeckoから過去のデータを取得
        market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=days)
        
        # 価格データをDataFrameに変換
        prices = market_data['prices']
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # OHLC形式に変換
        df.set_index('timestamp', inplace=True)
        ohlc = df['price'].resample('D').ohlc()
        ohlc.reset_index(inplace=True)
        
        return ohlc
    except Exception as e:
        print(f"Error fetching historical data for {symbol_or_id}: {e}")
        return pd.DataFrame()

def update_price_data():
    """バックグラウンドで価格データを更新する関数"""
    while True:
        # デフォルトトークンの価格を更新
        for symbol in ALL_TOKENS.keys():
            get_token_price(symbol)
        
        # 現在表示中のカスタムトークンの価格も更新
        for symbol in price_data.keys():
            if symbol not in ALL_TOKENS:
                get_token_price(symbol)
                
        time.sleep(60)  # 1分ごとに更新

# Dashアプリケーションの初期化
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # Renderでのデプロイに必要

# アプリケーションのレイアウト
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("魔王の弟子のなんか凄いBOT", className="text-center my-4"),
            html.P("暗号通貨の詳細情報、価格、リアルタイムチャートを表示します。", className="text-center mb-4"),
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("トークン検索"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id='token-search-input',
                                placeholder='トークン名またはシンボルを入力...',
                                type='text',
                                className="mb-2"
                            ),
                        ], width=9),
                        dbc.Col([
                            dbc.Button("検索", id='token-search-button', color="primary", className="w-100"),
                        ], width=3),
                    ]),
                    html.Div(id='token-search-results', className="mt-3"),
                    html.Hr(),
                    dbc.Label("または定義済みトークンから選択:"),
                    dcc.Dropdown(
                        id='token-dropdown',
                        options=[
                            {'label': f"{info['name']} ({symbol.upper()})", 'value': symbol}
                            for symbol, info in ALL_TOKENS.items()
                        ],
                        value='usdt'  # デフォルト値
                    ),
                    html.Div(id='token-type-display', className="mt-2")
                ])
            ], className="mb-4"),
            
            dbc.Card([
                dbc.CardHeader("トークン情報"),
                dbc.CardBody(id='token-info')
            ], className="mb-4")
        ], width=4),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("価格チャート"),
                dbc.CardBody([
                    dcc.Graph(id='price-chart'),
                    dcc.Interval(
                        id='interval-component',
                        interval=30*1000,  # 30秒ごとに更新
                        n_intervals=0
                    )
                ])
            ], className="mb-4"),
            
            dbc.Card([
                dbc.CardHeader("ヒストリカルチャート"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("期間:"),
                            dcc.Dropdown(
                                id='days-dropdown',
                                options=[
                                    {'label': '7日間', 'value': 7},
                                    {'label': '14日間', 'value': 14},
                                    {'label': '30日間', 'value': 30},
                                    {'label': '90日間', 'value': 90}
                                ],
                                value=30
                            )
                        ], width=6)
                    ], className="mb-3"),
                    dcc.Graph(id='historical-chart')
                ])
            ])
        ], width=8)
    ]),
    
    # 現在選択中のトークンIDを保存する隠しフィールド
    dcc.Store(id='current-token-id', data='usdt'),
    
], fluid=True)

@app.callback(
    Output('token-search-results', 'children'),
    Input('token-search-button', 'n_clicks'),
    State('token-search-input', 'value'),
    prevent_initial_call=True
)
def update_search_results(n_clicks, search_term):
    if not search_term:
        return []
    
    matching_coins = search_coins(search_term)
    
    if not matching_coins:
        return html.Div("該当するトークンが見つかりませんでした", className="text-danger")
    
    return [
        html.Div([
            dbc.Button(
                f"{coin['name']} ({coin['symbol'].upper()})",
                id={'type': 'search-result', 'index': coin['id']},
                color="link",
                className="text-left p-1 d-block w-100"
            )
        ]) for coin in matching_coins
    ]

@app.callback(
    [Output('current-token-id', 'data'),
     Output('token-search-input', 'value')],
    [Input({'type': 'search-result', 'index': dash.dependencies.ALL}, 'n_clicks'),
     Input('token-dropdown', 'value')],
    [State('current-token-id', 'data')],
    prevent_initial_call=True
)
def update_selected_token(search_clicks, dropdown_value, current_token):
    ctx = callback_context
    if not ctx.triggered:
        return current_token, ""
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # 検索結果からの選択
    if 'search-result' in trigger_id:
        # JSONから選択されたトークンIDを抽出
        token_id = json.loads(trigger_id.split('.')[0])['index']
        return token_id, ""
    
    # ドロップダウンからの選択
    elif 'token-dropdown' in trigger_id:
        return dropdown_value, ""
    
    return current_token, ""

@app.callback(
    Output('token-type-display', 'children'),
    Input('current-token-id', 'data')
)
def update_token_type(selected_token):
    if selected_token in STABLECOINS:
        return html.Div("カテゴリ: ステーブルコイン", className="text-info")
    elif selected_token in LST_TOKENS:
        return html.Div("カテゴリ: Liquid Staking Token (LST)", className="text-success")
    else:
        return html.Div("カテゴリ: カスタムトークン", className="text-warning")

@app.callback(
    Output('token-info', 'children'),
    Input('current-token-id', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_token_info(selected_token, n):
    if not selected_token:
        return html.P("トークンを選択してください")
    
    info = get_token_info(selected_token)
    price = get_token_price(selected_token)
    
    price_display = f"${price:.4f}" if price else "取得できません"
    
    # シンボルを取得
    if selected_token in ALL_TOKENS:
        symbol = selected_token.upper()
    else:
        symbol = info.get('symbol', selected_token.upper())
    
    return html.Div([
        html.H4(f"{info['name']} ({symbol})"),
        html.P(f"現在価格: {price_display}", className="text-primary fw-bold"),
        html.Hr(),
        html.P(info['description']),
        html.Div([
            html.P([html.Strong("発行元: "), info['issuer']]),
            html.P([html.Strong("発行日: "), info['launch_date']]),
            html.P([html.Strong("公式サイト: "), 
                   html.A(info['website'], href=info['website'], target="_blank") if info['website'] else "不明"]),
            html.P([html.Strong("時価総額ランク: "), info['market_cap_rank']]),
            html.P([html.Strong("ブロックチェーン: "), info['blockchain']])
        ])
    ])

@app.callback(
    Output('price-chart', 'figure'),
    Input('current-token-id', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_price_chart(selected_token, n):
    if not selected_token or selected_token not in price_data or not price_data[selected_token]:
        # データがない場合は空のチャートを返す
        return go.Figure().update_layout(title="データがありません")
    
    data = price_data[selected_token]
    
    # シンボルを取得
    if selected_token in ALL_TOKENS:
        symbol = selected_token.upper()
    else:
        info = get_token_info(selected_token)
        symbol = info.get('symbol', selected_token.upper())
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[item['timestamp'] for item in data],
        y=[item['price'] for item in data],
        mode='lines+markers',
        name=symbol
    ))
    
    fig.update_layout(
        title=f"{symbol} リアルタイム価格",
        xaxis_title="時間",
        yaxis_title="価格 (USD)",
        hovermode="x unified"
    )
    
    return fig

@app.callback(
    Output('historical-chart', 'figure'),
    Input('current-token-id', 'data'),
    Input('days-dropdown', 'value')
)
def update_historical_chart(selected_token, days):
    if not selected_token:
        return go.Figure().update_layout(title="トークンを選択してください")
    
    df = get_historical_data(selected_token, days)
    
    if df.empty:
        return go.Figure().update_layout(title="データがありません")
    
    # シンボルを取得
    if selected_token in ALL_TOKENS:
        symbol = selected_token.upper()
    else:
        info = get_token_info(selected_token)
        symbol = info.get('symbol', selected_token.upper())
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    )])
    
    fig.update_layout(
        title=f"{symbol} {days}日間のチャート",
        xaxis_title="日時",
        yaxis_title="価格 (USD)",
        xaxis_rangeslider_visible=False
    )
    
    return fig

if __name__ == '__main__':
    # バックグラウンドで価格データを更新するスレッドを開始
    price_thread = threading.Thread(target=update_price_data, daemon=True)
    price_thread.start()
    
    # 起動時にトークンリストをキャッシュ
    get_all_coins()
    
    # アプリケーションを起動
    app.run(debug=False, host='0.0.0.0')
