"""SANDBOX (not for the paper): structural premium vs market-revealed depeg measures."""
import pandas as pd, numpy as np

def load(p):
    df = pd.read_parquet(p)
    cols = {c.lower(): c for c in df.columns}
    tcol = next((cols[c] for c in cols if c in ('time','timestamp','date','datetime')), None)
    ccol = next((cols[c] for c in cols if c in ('close','price','close_usd')), None)
    t = pd.Series(df[tcol].values) if tcol else df.index.to_series().reset_index(drop=True)
    c = df[ccol] if ccol else df.iloc[:, -1]
    if pd.api.types.is_datetime64_any_dtype(t):
        ts = pd.to_datetime(t, utc=True, errors='coerce')
    elif pd.api.types.is_numeric_dtype(t):
        ts = pd.to_datetime(t, unit='s', utc=True, errors='coerce')
    else:
        ts = pd.to_datetime(t, utc=True, errors='coerce')
    ts = ts.dt.tz_localize(None)
    return pd.DataFrame({'t': ts, 'p': pd.to_numeric(pd.Series(c.values), errors='coerce')}).dropna().sort_values('t')

def stats(d, label):
    p = d['p'].values
    print(f'  {label}: n={len(p)}, {d.t.min().date()}..{d.t.max().date()}')
    print(f'     mean={p.mean():.5f}  mean|1-p|={1e4*np.abs(1-p).mean():.2f}bps  E[(1-p)+]={1e4*np.maximum(0,1-p).mean():.2f}bps'
          f'  min={p.min():.4f}  p1={np.percentile(p,1):.4f}  freq<0.995={np.mean(p<0.995):.4f}')

for tic, f in [('USDC','data/raw/cryptocompare_usdc_usd_3600s_20260601.parquet'),
               ('USDT','data/raw/cryptocompare_usdt_usd_3600s_20260601.parquet')]:
    d = load(f)
    print('='*72); print(tic)
    stats(d, 'FULL SAMPLE (incl. SVB / Terra stress)')
    calm = d[(d.t >= '2024-01-01') & (d.t < '2026-01-01')]
    stats(calm, 'CALM 2024-2025 (outside calibration windows)')

du = load('data/raw/cryptocompare_usdc_usd_3600s_20260601.parquet').set_index('t')['p']
dt = load('data/raw/cryptocompare_usdt_usd_3600s_20260601.parquet').set_index('t')['p']
j = pd.concat({'usdc': du, 'usdt': dt}, axis=1).dropna()
jc = j[(j.index >= '2024-01-01') & (j.index < '2026-01-01')]
print('='*72)
print(f'USDT-USDC mean price gap: full={1e4*(j.usdt-j.usdc).mean():.2f}bps  calm24-25={1e4*(jc.usdt-jc.usdc).mean():.2f}bps')
print(f'structural reference: USDC 61.4 (depeg ~41), USDT 89.4 (depeg ~29); structural gap 28.0 bps')
