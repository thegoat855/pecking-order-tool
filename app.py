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
Then open calculator.html in a browser (it calls http://localhost:5000).
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)  # allow the HTML frontend to call this from a file:// or other origin
CORS(app, origins=["https://thegoat855.github.io", "http://localhost:5000"])

def safe_get(series, label):
    """Pull a row from the yfinance cashflow dataframe by label, return
    list of values per year (most recent first), or None if missing."""
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


import math
def deviation_score(beta):
    if beta is None or (isinstance(beta, float) and math.isnan(beta)):
        return None
    return max(0, min(100, 100 - 50 * abs(beta - 1)))

@app.route('/api/analyze')
def analyze():
    ticker = request.args.get('ticker', '').upper().strip()
    if not ticker:
        return jsonify({'error': 'No ticker provided'}), 400

    try:
        stock = yf.Ticker(ticker)
        cf = stock.cashflow  # annual cash flow statement, columns = fiscal years
    except Exception as e:
        return jsonify({'error': f'Could not fetch data for {ticker}: {str(e)}'}), 500

    if cf is None or cf.empty:
        return jsonify({'error': f'No cash flow data found for {ticker}'}), 404

    years = [str(c.year) for c in cf.columns]

    # yfinance label names (these can vary slightly by company/filing type)
    ocf = safe_get(cf, 'Operating Cash Flow') or safe_get(cf, 'Cash Flow From Continuing Operating Activities')
    capex = safe_get(cf, 'Capital Expenditure')
    div = safe_get(cf, 'Cash Dividends Paid') or safe_get(cf, 'Common Stock Dividend Paid')
    lt_debt = safe_get(cf, 'Net Long Term Debt Issuance') or safe_get(cf, 'Long Term Debt Issuance')
    st_debt = safe_get(cf, 'Net Short Term Debt Issuance') or safe_get(cf, 'Short Term Debt Issuance')
    equity = safe_get(cf, 'Net Common Stock Issuance') or safe_get(cf, 'Common Stock Issuance')

    missing = [name for name, val in [
        ('Operating Cash Flow', ocf), ('Capital Expenditure', capex),
    ] if val is None]
    if missing:
        return jsonify({'error': f'{ticker}: missing required fields: {missing}. '
                                  f'Available rows: {list(cf.index)}'}), 422

    # Fill optional fields with zeros where genuinely absent (e.g. no dividend, no ST debt)
    div = div or [0] * len(years)
    lt_debt = lt_debt or [0] * len(years)
    st_debt = st_debt or [0] * len(years)
    equity = equity or [0] * len(years)

    rows = []
    xs, ys = [], []
    for i, yr in enumerate(years):
        try:
            o, c, d, lt, st = ocf[i], capex[i], div[i], lt_debt[i], st_debt[i]
            import math
if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (o, c, d, lt, st)):
    continue
            capex_pos = abs(c)  # capex often reported negative; normalize to positive spend
            deficit = d + capex_pos - o
            debt_issued = lt + st
            xs.append(deficit)
            ys.append(debt_issued)
            rows.append({
                'year': yr, 'ocf': o, 'capex': capex_pos, 'dividends': d,
                'lt_debt': lt, 'st_debt': st, 'equity': equity[i] if i < len(equity) else 0,
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

    return jsonify({
        'ticker': ticker,
        'rows': rows,
        'beta': beta,
        'r2': r2,
        'score': score,
        'avg_deficit': avg_deficit,
        'profile': profile,
        'n_years': len(xs),
    })


@app.route('/')
def health():
    return jsonify({'status': 'ok', 'usage': '/api/analyze?ticker=AAPL'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
