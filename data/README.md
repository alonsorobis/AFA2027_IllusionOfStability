# `data/` — datasets for the AFA 2027 *Illusion of Stability* paper

All datasets used by the paper are catalogued here. Each download is logged
in `download_log.md` with the source URL, the access date, the SHA256 of the
returned file and the script that produced it.

## Layout

```
data/
├── README.md            # this file
├── download_log.md      # per-download manifest (date, source, sha256, script)
├── raw/                 # raw downloads, never edited by hand
├── processed/           # cleaned and aligned datasets, written by scripts
└── scripts/             # download and processing code
```

## Sources

| Source | What | Endpoint | Frequency | Notes |
|--------|------|----------|-----------|-------|
| Coinbase Exchange | USDC, USDT, DAI candles (USD pairs) | public REST | minute / hour / day | secondary-market price |
| Binance | USDC/USDT pair for USDC-USD reconstruction | public REST | minute / hour / day | used to reconstruct USDC-USD when Coinbase USDC-USD pair gaps |
| DefiLlama | stablecoin supply by chain | public REST | daily | issuer-side aggregate stake |
| FRED | macro controls (DGS10, T10Y2Y, BAMLH0A0HYM2, etc.) | public REST | daily | requires FRED API key in env var `FRED_API_KEY` |
| World Bank | personal remittances received as share of GDP | public REST | annual | cross-border-corridor exposure proxy |
| World Bank Remittance Prices Worldwide | per-corridor fee and speed | public REST | quarterly | incumbent-rail cost component |
| Banco Central do Brasil (BCB) | cross-border flow statistics | public REST | monthly | identifies Brazil-ban policy event |
| ECB SDMX | SEPA SCT Inst volumes | public SDMX | quarterly | EU instant-payment incumbent benchmark |
| Federal Reserve | FedNow volumes (where published) | public CSV | quarterly | US incumbent benchmark |
| Circle, Tether | reserve attestations | public PDF / HTML | monthly | issuer reserve quality |

## Rule for refresh

The AFA 2027 timing rule means no dataset downloaded before 2026-06-01 can
be used as input to the published results. The data layer is built from
fresh public downloads on or after 2026-06-01. Datasets downloaded by the
author for prior projects (Human×AI working paper, JoES survey) are
retained on disk for cross-check only and are NOT referenced by any code
under `simulation/`.

## Status

- 2026-06-01: download scripts written. None executed yet. The author or
  AI assistant runs them in session 02 with provenance logged in
  `download_log.md`.
