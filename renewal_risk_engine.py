"""Explainable renewal risk and next-best-action recommendations (synthetic data).
Run from repository root: python renewal_risk_engine.py
"""
import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'outputs' / 'customer_health_scores.csv'
DEST = ROOT / 'outputs' / 'renewal_action_plan.csv'


def assess(row, today=None):
    today = today or date.today()
    days = (date.fromisoformat(row['renewal_date']) - today).days
    health = int(row['health_score'])
    adoption = float(row['product_adoption_pct'])
    usage = float(row['usage_change_30d_pct'])
    escalations = int(row['critical_escalations_90d'])
    engagement = row['executive_engagement'].strip().lower()
    arr = int(float(row['arr_usd']))
    reasons = []
    score = 0

    if health < 60:
        score += 30; reasons.append('Low customer health')
    elif health < 80:
        score += 15; reasons.append('Moderate customer health')
    if usage <= -20:
        score += 20; reasons.append('Usage decline of at least 20%')
    elif usage < -10:
        score += 10; reasons.append('Declining product usage')
    if engagement == 'low':
        score += 20; reasons.append('Low executive engagement')
    if escalations >= 2:
        score += 15; reasons.append('Multiple critical escalations')
    elif escalations == 1:
        score += 7; reasons.append('Recent critical escalation')
    if adoption < 50:
        score += 10; reasons.append('Low product adoption')
    if 0 <= days <= 90:
        score += 15; reasons.append('Renewal within 90 days')
    elif days < 0:
        reasons.append('Renewal date has passed; verify contract status')
    score = min(score, 100)
    risk = 'High' if score >= 60 else 'Medium' if score >= 30 else 'Low'
    priority = 'P1' if risk == 'High' and 0 <= days <= 90 else 'P2' if risk == 'High' or (risk == 'Medium' and 0 <= days <= 90) else 'P3' if risk == 'Medium' else 'P4'

    if days < 0:
        action = 'Verify renewal outcome and update contract records before prioritizing.'
        priority = 'Review'
    elif engagement == 'low' and 0 <= days <= 90:
        action = 'Re-engage executive sponsor; confirm value outcomes and agree a renewal recovery plan.'
    elif escalations >= 2:
        action = 'Lead a cross-functional escalation review; assign owners and communicate resolution milestones.'
    elif usage <= -20 or adoption < 50:
        action = 'Run an adoption diagnostic and agree a 30-day usage recovery plan with the customer.'
    elif 0 <= days <= 90:
        action = 'Confirm renewal stakeholders, business outcomes, commercial timeline and next steps.'
    elif risk == 'Low' and row['expansion_potential'].strip().lower() == 'high':
        action = 'Validate expansion needs and schedule a value-led growth discussion.'
    else:
        action = 'Continue account success plan; review health signals at the next CSM check-in.'

    return {**row, 'days_to_renewal': days, 'renewal_risk_score': score,
            'renewal_risk_level': risk, 'action_priority': priority,
            'risk_drivers': '; '.join(reasons) if reasons else 'No material rule-based flags',
            'recommended_action': action,
            'arr_at_risk_usd': arr if risk == 'High' and days >= 0 else 0}


def main():
    if not SOURCE.exists():
        raise SystemExit('Missing outputs/customer_health_scores.csv. Run python health_scoring.py first.')
    with SOURCE.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit('No customer records found.')
    result = [assess(r) for r in rows]
    order = {'P1': 0, 'P2': 1, 'P3': 2, 'P4': 3, 'Review': 4}
    result.sort(key=lambda r: (order[r['action_priority']], -int(r['renewal_risk_score']), -int(r['arr_usd'])))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with DEST.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    print(f'Processed {len(result)} accounts')
    print(f'High risk: {sum(r["renewal_risk_level"] == "High" for r in result)}')
    print(f'P1 actions: {sum(r["action_priority"] == "P1" for r in result)}')
    print(f'Rule-flagged high-risk ARR: ${sum(r["arr_at_risk_usd"] for r in result):,}')
    print(f'Output: {DEST}')
    print('Note: Risk scores are heuristic indicators, not churn probabilities.')


if __name__ == '__main__':
    main()
