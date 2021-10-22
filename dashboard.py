# https://gist.github.com/lars-tiede/01e5f5a551f29a5f300e

# based on work from https://towardsdatascience.com/building-a-cryptocurrency-dashboard-using-plotly-and-binance-api-352e7f6f62c9
# new binance API added and TIMEOU logic implemented

import asyncio
import threading
from asyncio import exceptions

import time

import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from binance.client import Client, AsyncClient
import configparser
from binance.streams import BinanceSocketManager

SOCKET_TIMEOUT = 15
assets = []
values = []

token_usdt = {}
token_pairs = []

api_key = ""
secret_key = ""

def initialize():
    config = configparser.ConfigParser()
    config.read_file(open('./config.cfg'))
    api_key = config.get('BINANCE', 'API_KEY')
    secret_key = config.get('BINANCE', 'SECRET_KEY')
    client = Client(api_key, secret_key, tld='us')
    info = client.get_account()

    for index in range(len(info['balances'])):
        for key in info['balances'][index]:
            value = info['balances'][index][key]
            if value != 'BTC' and value != 'ETH' and value != 'BNB':
                continue
            assets.append(info['balances'][index]['asset'])
            values.append(info['balances'][index]['free'])

    for token in assets:
        token_pairs.append(token + 'USDT')


def total_amount_usdt(assets, values, token_usdt):
    total_amount = 0
    if len(token_usdt) != len(assets):
        return 0
    for i, token in enumerate(assets):
        if token != 'USDT':
            total_amount += float(values[i]) * float(token_usdt[token + 'USDT'])
        else:
            total_amount += float(values[i]) * 1
    return total_amount


def total_amount_btc(assets, values, token_usdt):
    total_amount = 0
    if len(token_usdt) != len(assets):
        return 0
    for i, token in enumerate(assets):
        if token != 'BTC' and token != 'USDT':
            total_amount += float(values[i]) \
                            * float(token_usdt[token + 'USDT']) \
                            / float(token_usdt['BTCUSDT'])
        if token == 'BTC':
            total_amount += float(values[i]) * 1
        else:
            total_amount += float(values[i]) \
                            / float(token_usdt['BTCUSDT'])
    return total_amount


def assets_usdt(assets, values, token_usdt):
    assets_in_usdt = []
    if len(token_usdt) != len(assets):
        return []
    for i, token in enumerate(assets):
        if token != 'USDT':
            assets_in_usdt.append(
                float(values[i]) * float(token_usdt[token + 'USDT'])
            )
        else:
            assets_in_usdt.append(float(values[i]) * 1)
    return assets_in_usdt


def initialize_layout(app):
    if 'BNBUSDT' in token_usdt:
        value = float(token_usdt['BNBUSDT'])
    else:
        value = 0
    app.layout = html.Div([
        html.Div([
            html.Div([
                dcc.Graph(
                    id='figure-1',
                    figure={
                        'data': [
                            go.Indicator(
                                mode="number",
                                value=total_amount_usdt(assets, values, token_usdt),
                            )
                        ],
                        'layout':
                            go.Layout(
                                title="Portfolio Value (USDT)"
                            )
                    }
                )], style={'width': '30%', 'height': '300px',
                           'display': 'inline-block'}),
            html.Div([
                dcc.Graph(
                    id='figure-2',
                    figure={
                        'data': [
                            go.Indicator(
                                mode="number",
                                value=total_amount_btc(assets, values, token_usdt),
                                number={'valueformat': 'g'}
                            )
                        ],
                        'layout':
                            go.Layout(
                                title="Portfolio Value (BTC)"
                            )
                    }
                )], style={'width': '30%', 'height': '300px',
                           'display': 'inline-block'}),
            html.Div([
                dcc.Graph(
                    id='figure-3',
                    figure={
                        'data': [
                            go.Indicator(
                                mode="number",
                                value = value,
                                number = {'valueformat': 'g'}
                            )
                        ],
                        'layout':
                            go.Layout(
                                title = "BNB/USDT"
                            )
                    }
                )],
                style={'width': '30%', 'height': '300px', 'display': 'inline-block'})
        ]),
        html.Div([
            html.Div([
                dcc.Graph(
                    id='figure-4',
                    figure={
                        'data': [
                            go.Pie(
                                labels=assets,
                                values=assets_usdt(assets, values, token_usdt),
                                hoverinfo="label+percent"
                            )
                        ],
                        'layout':
                            go.Layout(
                                title="Portfolio Distribution (in USDT)"
                            )
                    }
                )], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([
                dcc.Graph(
                    id='figure-5',
                    figure={
                        'data': [
                            go.Bar(
                                x=assets,
                                y=values,
                                name="Token Quantities For Different Assets",
                            )
                        ],
                        'layout':
                            go.Layout(
                                showlegend=False,
                                title="Tokens distribution"
                            )
                    }
                )], style={'width': '50%', 'display': 'inline-block'}),
            dcc.Interval(
                id='1-second-interval',
                interval=1000,  # 1000 milliseconds
                n_intervals=0
            )
        ]),
    ])

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server


@app.callback(Output('figure-1', 'figure'),
              Output('figure-2', 'figure'),
              Output('figure-3', 'figure'),
              Output('figure-4', 'figure'),
              Output('figure-5', 'figure'),
              Input('1-second-interval', 'n_intervals'))
def update_layout(n):
    if 'BNBUSDT' in token_usdt:
        value = float(token_usdt['BNBUSDT'])
    else:
        value = 0
    figure1 = {
        'data': [
            go.Indicator(
                mode="number",
                value=total_amount_usdt(assets, values, token_usdt),
            )
        ],
        'layout':
            go.Layout(
                title="Portfolio Value (USDT)"
            )
    }
    figure2 = {
        'data': [
            go.Indicator(
                mode="number",
                value=total_amount_btc(assets, values, token_usdt),
                number={'valueformat': 'g'}
            )
        ],
        'layout':
            go.Layout(
                title="Portfolio Value (BTC)"
            )
    }
    figure3 = {
        'data': [
            go.Indicator(
                mode = "number",
                value = value,
                number = {'valueformat': 'g'}
            )
        ],
        'layout':
            go.Layout(
                title="BNB/USDT"
            )
    }
    figure4 = {
        'data': [
            go.Pie(
                labels=assets,
                values=assets_usdt(assets, values, token_usdt),
                hoverinfo="label+percent"
            )
        ],
        'layout':
            go.Layout(
                title="Portfolio Distribution (in USDT)"
            )
    }
    figure5 = {
        'data': [
            go.Bar(
                x=assets,
                y=values,
                name="Token Quantities For Different Assets",
            )
        ],
        'layout':
            go.Layout(
                showlegend=False,
                title="Tokens distribution"
            )
    }

    return figure1, figure2, figure3, figure4, figure5


async def get_data():
    client = await AsyncClient.create()
    bsm = BinanceSocketManager(client)
    while True:
        for tokenpair in token_pairs:
            async with bsm.symbol_ticker_socket(symbol=tokenpair) as stream:
                res = await stream.recv()
                global token_usdt
                token_usdt[res['s']] = res['c']
    await client.close_connection()


def start_update(async_client):
    def update():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        bm = BinanceSocketManager(async_client, loop)

        while True:
            for tokenpair in token_pairs:
                #socket = bm.symbol_ticker_socket(symbol=tokenpair)
                async def update_async():
                    #async with socket:
                    async with bm.symbol_ticker_socket(symbol=tokenpair) as stream:
                        data = ""
                        try:
                            #data = await asyncio.wait_for(socket.recv(), timeout=SOCKET_TIMEOUT)
                            data = await asyncio.wait_for(stream.recv(), timeout=SOCKET_TIMEOUT)
                        except exceptions.TimeoutError as e:
                            print(e)
                            await disconnect_callback(async_client=async_client)
                        if data:
                            global token_usdt
                            token_usdt[data['s']] = data['c']
                        else:
                            print("No data received. Reconnecting..")
                loop.run_until_complete(update_async())
            time.sleep(1)

    threading.Thread(target=update, daemon=True).start()


async def disconnect_callback(async_client):
    await async_client.close_connection()
    time.sleep(5)
    async_client = await AsyncClient.create(api_key, secret_key, tld='us')
    start_update(async_client)

async def main():
    initialize()
    initialize_layout(app)
    async_client = await AsyncClient.create(api_key, secret_key, tld='us')
    start_update(async_client)
    app.run_server(host='127.0.0.1', port='8050', debug=False)
    await async_client.close_connection()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())