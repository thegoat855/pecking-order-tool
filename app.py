"""
Pecking Order Deviation Calculator — Backend
==============================================
Fetches real cash flow statement data via yfinance for any public ticker
and computes the pecking order deviation score.

NOTE: yfinance pulls live data from Yahoo Finance. This requires normal
internet access — it will NOT work in network-restricted sandboxes, only
when run locally or deployed somewhere with open internet access.

Run locally:
    pip install flask flask-cors yfinance
    python app.py
Then open calculator.html in a browser (uses Render)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import math
import plotly.graph_objects as go
import plotly.utils
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def safe_get(series, label):
    try:
        row = series.loc[label]
        return row.tolist()
    except KeyError:
        return None


def compute_regression(xs, ys):
    n = len(xs)
    if n < 2:
        return None, None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None, None
    beta = sxy / sxx
    alpha = my - beta * mx
    sst = sum((y - my) ** 2 for y in ys)
    ssr = sum((y - (alpha + beta * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - (ssr / sst) if sst != 0 else None
    return beta, r2


def deviation_score(beta):
    if beta is None or math.isnan(beta):
        return None
    return max(0, min(100, 100 - 50 * abs(beta - 1)))


def is_bad(v):
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return False


def fetch_company_data(ticker):
    """Fetch and process cash flow data for a single ticker.
    Returns dict with rows, xs, ys, beta, r2, score, profile."""
    stock = yf.Ticker(ticker)
    cf = stock.cashflow

    if cf is None or cf.empty:
        return None

    years = [str(c.year) for c in cf.columns]

    ocf = safe_get(cf, 'Operating Cash Flow') or safe_get(cf, 'Cash Flow From Continuing Operating Activities')
    capex = safe_get(cf, 'Capital Expenditure')
    div = safe_get(cf, 'Cash Dividends Paid') or safe_get(cf, 'Common Stock Dividend Paid')
    lt_debt = safe_get(cf, 'Net Long Term Debt Issuance') or safe_get(cf, 'Long Term Debt Issuance')
    st_debt = safe_get(cf, 'Net Short Term Debt Issuance') or safe_get(cf, 'Short Term Debt Issuance')
    equity = safe_get(cf, 'Net Common Stock Issuance') or safe_get(cf, 'Common Stock Issuance')

    if not ocf or not capex:
        return None

    div = div or [0] * len(years)
    lt_debt = lt_debt or [0] * len(years)
    st_debt = st_debt or [0] * len(years)
    equity = equity or [0] * len(years)

    rows = []
    xs, ys = [], []
    for i, yr in enumerate(years):
        try:
            o, c, d, lt, st = ocf[i], capex[i], div[i], lt_debt[i], st_debt[i]
            if any(is_bad(v) for v in (o, c, d, lt, st)):
                continue
            capex_pos = abs(c)
            deficit = d + capex_pos - o
            debt_issued = lt + st
            xs.append(deficit)
            ys.append(debt_issued)
            rows.append({
                'year': yr, 'ocf': o, 'capex': capex_pos, 'dividends': d,
                'lt_debt': lt, 'st_debt': st,
                'equity': equity[i] if i < len(equity) else 0,
                'deficit': deficit, 'net_debt_issued': debt_issued,
            })
        except (IndexError, TypeError):
            continue

    beta, r2 = compute_regression(xs, ys)
    score = deviation_score(beta)
    avg_deficit = sum(xs) / len(xs) if xs else None
    profile = None
    if avg_deficit is not None:
        profile = 'deficit-dominant' if avg_deficit > 0 else 'surplus-dominant'

    return {
        'ticker': ticker,
        'rows': rows,
        'xs': xs,
        'ys': ys,
        'beta': beta,
        'r2': r2,
        'score': score,
        'avg_deficit': avg_deficit,
        'profile': profile,
        'n_years': len(xs),
    }


def make_per_company_chart(result):
    """Scatter + regression line for a single company."""
    xs = result['xs']
    ys = result['ys']
    years = [r['year'] for r in result['rows']]
    beta = result['beta']
    ticker = result['ticker']

    fig = go.Figure()

    # Scatter dots
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode='markers+text',
        text=years,
        textposition='top center',
        marker=dict(color='#D4A93E', size=10),
        name='Annual Data',
        hovertemplate='Year: %{text}<br>Deficit: $%{x:,.0f}M<br>Net Debt Issued: $%{y:,.0f}M<extra></extra>'
    ))

    # Regression line
    if beta is not None and len(xs) >= 2:
        x_min, x_max = min(xs), max(xs)
        alpha = (sum(ys) / len(ys)) - beta * (sum(xs) / len(xs))
        line_x = [x_min, x_max]
        line_y = [alpha + beta * x for x in line_x]
        fig.add_trace(go.Scatter(
            x=line_x, y=line_y,
            mode='lines',
            line=dict(color='#4FAE7A', width=2, dash='dash'),
            name=f'β = {beta:.2f}'
        ))

    # Perfect pecking order line (beta=1) for reference
    if len(xs) >= 2:
        x_min, x_max = min(xs), max(xs)
        fig.add_trace(go.Scatter(
            x=[x_min, x_max],
            y=[x_min, x_max],
            mode='lines',
            line=dict(color='#8A8F99', width=1, dash='dot'),
            name='β = 1 (ideal)'
        ))

    fig.update_layout(
        title=dict(
            text=f'{ticker} — Deficit vs. Net Debt Issued',
            font=dict(color='#E8E6DD', size=16)
        ),
        paper_bgcolor='#161A21',
        plot_bgcolor='#0E1116',
        font=dict(color='#8A8F99', family='monospace'),
        xaxis=dict(
            title='Financing Deficit ($M)',
            gridcolor='#262C36',
            zerolinecolor='#262C36',
        ),
        yaxis=dict(
            title='Net Debt Issued ($M)',
            gridcolor='#262C36',
            zerolinecolor='#262C36',
        ),
        legend=dict(bgcolor='#161A21', bordercolor='#262C36'),
        margin=dict(t=50, b=50, l=60, r=20),
        height=380,
    )

    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


def make_combined_chart(results):
    """All companies overlaid on one chart for comparison."""
    colors = ['#D4A93E', '#4FAE7A', '#C2604B', '#6B8FD4', '#B07FD4']
    fig = go.Figure()

    for i, result in enumerate(results):
        color = colors[i % len(colors)]
        xs = result['xs']
        ys = result['ys']
        years = [r['year'] for r in result['rows']]
        ticker = result['ticker']
        beta = result['beta']

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode='markers',
            marker=dict(color=color, size=9),
            name=ticker,
            hovertemplate=f'{ticker}<br>Year: %{{text}}<br>Deficit: $%{{x:,.0f}}M<br>Net Debt: $%{{y:,.0f}}M<extra></extra>',
            text=years,
        ))

        if beta is not None and len(xs) >= 2:
            x_min, x_max = min(xs), max(xs)
            alpha = (sum(ys) / len(ys)) - beta * (sum(xs) / len(xs))
            fig.add_trace(go.Scatter(
                x=[x_min, x_max],
                y=[alpha + beta * x for x in [x_min, x_max]],
                mode='lines',
                line=dict(color=color, width=1.5, dash='dash'),
                name=f'{ticker} β={beta:.2f}',
                showlegend=True,
            ))

    fig.update_layout(
        title=dict(
            text='All Companies — Deficit vs. Net Debt Issued',
            font=dict(color='#E8E6DD', size=16)
        ),
        paper_bgcolor='#161A21',
        plot_bgcolor='#0E1116',
        font=dict(color='#8A8F99', family='monospace'),
        xaxis=dict(title='Financing Deficit ($M)', gridcolor='#262C36', zerolinecolor='#262C36'),
        yaxis=dict(title='Net Debt Issued ($M)', gridcolor='#262C36', zerolinecolor='#262C36'),
        legend=dict(bgcolor='#161A21', bordercolor='#262C36'),
        margin=dict(t=50, b=50, l=60, r=20),
        height=450,
    )

    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


@app.route('/api/analyze')
def analyze():
    ticker = request.args.get('ticker', '').upper().strip()
    if not ticker:
        return jsonify({'error': 'No ticker provided'}), 400

    try:
        result = fetch_company_data(ticker)
    except Exception as e:
        return jsonify({'error': f'Could not fetch data for {ticker}: {str(e)}'}), 500

    if result is None:
        return jsonify({'error': f'No cash flow data found for {ticker}'}), 404

    chart = make_per_company_chart(result)
    result['chart'] = chart
    result.pop('xs')
    result.pop('ys')

    return jsonify(result)


@app.route('/api/combined-chart')
def combined_chart():
    """Takes comma-separated tickers and returns a combined chart."""
    tickers_raw = request.args.get('tickers', '')
    tickers = [t.strip().upper() for t in tickers_raw.split(',') if t.strip()]
    if not tickers:
        return jsonify({'error': 'No tickers provided'}), 400

    results = []
    for ticker in tickers:
        try:
            result = fetch_company_data(ticker)
            if result:
                results.append(result)
        except Exception:
            continue

    if not results:
        return jsonify({'error': 'Could not fetch data for any ticker'}), 404

    chart = make_combined_chart(results)
    return jsonify({'chart': chart, 'tickers': [r['ticker'] for r in results]})


@app.route('/')
def health():
    return jsonify({'status': 'ok', 'usage': '/api/analyze?ticker=AAPL'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
    app.run(debug=True, port=5000)
