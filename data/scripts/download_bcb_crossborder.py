"""Download Banco Central do Brasil cross-border statistics.

BCB exposes several open endpoints relevant for the Brazil-ban event:
    * Câmbio (FX) flow statistics by purpose code.
    * Balanço de Pagamentos (BPM6).
The exact dataset depends on the granularity needed for the calibration.
This skeleton fetches one canonical aggregate to make sure the endpoint
works; a finer slice is selected once MODEL.md §5 is operationalised.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

from common import RAW_DIR, append_manifest, ensure_raw_dir, utc_date

BCB_BPM6_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?formato=json"
)
# 2026-06-01: per author ruling, we only keep one SGS series (27688) and
# use BCB PDF reports for the Brazil cross-border stablecoin ban event
# identification. The previous placeholder series 21619 returned HTTP 406
# (invalid SGS code) and has been removed. Add more codes here only if the
# author confirms them against the BCB SGS catalogue.
SERIES_IDS = (
    "27688",   # confirmed working in session 03 (160 obs)
)


def main() -> int:
    ensure_raw_dir()
    date_tag = utc_date()
    for series in SERIES_IDS:
        url = BCB_BPM6_URL.format(series=series)
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            rows = r.json()
        except Exception as exc:
            print(f"WARNING: BCB {series} failed: {exc}")
            continue
        out_path = RAW_DIR / f"bcb_sgs_{series}_{date_tag}.json"
        out_path.write_text(json.dumps(rows, ensure_ascii=False))
        append_manifest(
            dataset=f"BCB SGS series {series}",
            source=url,
            script=Path(__file__).name,
            output=out_path,
            note=f"{len(rows)} observations",
        )
        print(f"  wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
