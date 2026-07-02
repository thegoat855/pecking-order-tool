# pecking-order-tool
# Pecking Order Deviation Calculator

A quantitative tool testing where Myers' (1984) Pecking Order Theory applies —
and where it doesn't — across public companies. Built on the Shyam-Sunder &
Myers (1999) regression framework.

**Live demo:** https://thegoat855.github.io/pecking-order-tool/calculator.html

---

## What it does

For any public company, it computes:
- **Financing Deficit** = Dividends + CapEx − Operating Cash Flow
- **β (beta)** = how many $ of debt the company issues per $ of deficit
- **Adherence Score** = how close β is to 1 (the value pecking order predicts)
- **Surplus/Deficit Profile** = whether the theory is even applicable to this firm

The key finding: pecking order theory's predictive power is conditional on whether
a firm faces a genuine financing deficit. Cash-rich mature firms structurally exit
the theory's applicability.

---

## Repo structure

```
pecking-order-tool/
├── calculator.html        ← frontend (deploy to GitHub Pages)
├── data/
│   └── financials.csv     ← verified 5-company dataset (FY2021-2025)
├── src/
│   └── deviation_score.py ← standalone Python scoring script
├── methodology.md         ← full methodology write-up
└── backend/
    ├── app.py             ← Flask API (deploy to Render)
    ├── requirements.txt
    ├── render.yaml
    └── README.md
```

---

## Deploying in 3 steps

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pecking-order-tool.git
git push -u origin main
```

### Step 2 — Deploy backend to Render (free tier)

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **New → Web Service**
3. Connect your repo, set **Root Directory** to `backend`
4. Render auto-detects `render.yaml` — just click **Deploy**
5. Copy your Render URL (looks like `https://pecking-order-api.onrender.com`)

### Step 3 — Update frontend with your backend URL

Open `calculator.html`, find this line near the top of the `<script>` tag:

```javascript
const API_BASE = 'http://localhost:5000';
```

Replace it with your Render URL:

```javascript
const API_BASE = 'https://pecking-order-api.onrender.com';
```

Then commit and push that change:

```bash
git add calculator.html
git commit -m "point frontend to deployed backend"
git push
```

### Step 4 — Enable GitHub Pages (frontend hosting)

1. Go to your repo on GitHub → **Settings → Pages**
2. Source: **Deploy from a branch** → branch: `main`, folder: `/ (root)`
3. Click Save — your frontend is live at `https://YOUR_USERNAME.github.io/pecking-order-tool/calculator.html`

---

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
python app.py
# runs at http://localhost:5000

# Frontend
# Just open calculator.html in a browser — it already points to localhost:5000
```

---

## Data sources

All financial data sourced from stockanalysis.com cash flow statements
(derived from SEC 10-K filings via Fiscal.ai). Verified June 30, 2026.

| Company | Ticker | Source |
|---------|--------|--------|
| Procter & Gamble | PG | stockanalysis.com/stocks/pg/financials/cash-flow-statement |
| Apple | AAPL | stockanalysis.com/stocks/aapl/financials/cash-flow-statement |
| Tesla | TSLA | stockanalysis.com/stocks/tsla/financials/cash-flow-statement |
| AT&T | T | stockanalysis.com/stocks/t/financials/cash-flow-statement |
| Peloton | PTON | stockanalysis.com/stocks/pton/financials/cash-flow-statement |

---

## References

- Myers, S. C. (1984). The capital structure puzzle. *Journal of Finance*, 39(3), 575–592.
- Shyam-Sunder, L., & Myers, S. C. (1999). Testing static tradeoff against pecking order
  models of capital structure. *Journal of Financial Economics*, 51(2), 219–244.
- Malmendier, U., & Tate, G. (2005). CEO overconfidence and corporate investment.
  *Journal of Finance*, 60(6), 2661–2700.
