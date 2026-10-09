"""Transparent, illustrative customer health model using synthetic portfolio data.
Run from the repository root: python health_scoring.py
"""
import csv
from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'data' / 'sample_customer_portfolio.csv'
if not INPUT.exists():
    INPUT = ROOT / 'sample_customer_portfolio.csv'
OUTPUT = ROOT / 'outputs' / 'customer_health_scores.csv'


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def score_customer(r):
    adoption = clamp(float(r['product_adoption_pct']))
    usage = clamp(50 + float(r['usage_change_30d_pct']) * 2)
    # NPS here is a 0–10 respondent-style rating in the synthetic dataset.
    sentiment = clamp(float(r['nps_score']) * 10)
    cases = int(r['open_support_cases'])
    escalations = int(r['critical_escalations_90d'])
    support = clamp(100 - 7 * cases - 20 * escalations)
    engagement = {'High': 100, 'Medium': 65, 'Low': 20}.get(r['executive_engagement'], 50)
    outcomes = clamp(float(r['business_outcomes_score']))
    weighted = (0.25 * adoption + 0.20 * usage + 0.15 * sentiment +
                0.15 * support + 0.15 * engagement + 0.10 * outcomes)
    score = round(weighted)
    status = 'Healthy' if score >= 80 else 'Watch' if score >= 60 else 'At Risk'
    flags = []
    renewal_days = (date.fromisoformat(r['renewal_date']) - date.today()).days
    if r['executive_engagement'] == 'Low' and renewal_days <= 90:
        flags.append('Executive engagement risk near renewal')
    if escalations >= 2:
        flags.append('Multiple critical escalations')
    if float(r['usage_change_30d_pct']) <= -20:
        flags.append('Usage decline >=20%')
    if renewal_days < 0:
        flags.append('Renewal date passed - verify record')
    # Override only the operational attention status, not the raw health score.
    attention = 'High' if status == 'At Risk' or flags else 'Medium' if status == 'Watch' else 'Low'
    return {'health_score': score, 'health_status': status,
            'leadership_attention': attention, 'risk_flags': '; '.join(flags),
            'days_to_renewal': renewal_days}


def main():
    if not INPUT.exists():
        raise SystemExit('Missing dataset. Place sample_customer_portfolio.csv in data/ or repository root.')
    with INPUT.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit('Dataset has no customer records.')
    results = [{**row, **score_customer(row)} for row in rows]
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f'Processed {len(results)} accounts | ARR ${sum(int(r["arr_usd"]) for r in results):,}')
    for status in ('Healthy', 'Watch', 'At Risk'):
        count = sum(r['health_status'] == status for r in results)
        print(f'{status}: {count}')
    print(f'Leadership attention high: {sum(r["leadership_attention"] == "High" for r in results)}')
    print(f'Output: {OUTPUT}')

if __name__ == '__main__':
    main()
