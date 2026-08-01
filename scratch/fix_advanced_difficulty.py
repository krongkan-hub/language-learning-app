import re

with open('app/scenarios/builtins.py', 'r') as f:
    content = f.read()

# Let's update tasks in scenario_70_tasks through scenario_79_tasks so that at least 7 tasks per scenario have difficulty="advanced"

advanced_task_goals = [
    # Scenario 70
    "Explain why your condition requires urgent evaluation",
    "Negotiate priority assessment after symptoms worsen",
    "Request pain management options while waiting",
    "Clarify insurance co-pay or registration requirements",
    "Ask if family or companions can wait in the triage room",
    "Use the word 'triage'",
    "Provide medical history and allergy info",
    
    # Scenario 71
    "Ask for a hotel voucher for an overnight delay",
    "Contest airline responsibility for missed connection",
    "Ask for a full refund option if rebooking is unsuitable",
    "Ask to speak to a duty supervisor regarding policy exceptions",
    "Negotiate endorsement onto a partner airline flight",
    "Use the word 'compensation'",
    "Request access to the airline service lounge during delay",

    # Scenario 72
    "Dispute the initial claim rejection or low payout offer",
    "Argue against a pre-existing condition clause",
    "Request an independent adjuster re-inspection",
    "Escalate the dispute to a senior claims supervisor",
    "Negotiate a compromise settlement amount",
    "Use the word 'deductible'",
    "Ask for clarification on specific policy wording",

    # Scenario 73
    "Negotiate a 4-year vesting schedule with a 1-year cliff",
    "Address concerns regarding initial salary vs equity trade-off",
    "Negotiate board seats and voting rights structure",
    "Propose a co-founder dispute resolution mechanism",
    "Use the word 'equity'",
    "Use the word 'dilution'",
    "Ask about fundraising milestones and runway expectations",

    # Scenario 74
    "Politely request a written warning instead of a traffic ticket",
    "Ask for clarification on the exact speed recorded by radar",
    "Ask about the procedure for contesting the ticket in court",
    "Remain calm and decline consent for voluntary vehicle search politely",
    "Point out recent road sign changes or poor visibility",
    "Use the word 'citation'",
    "Explain minor speed adjustment due to traffic flow",

    # Scenario 75
    "Dispute recent notice of a sudden rent increase",
    "Condition rent increase acceptance on immediate maintenance fixes",
    "Refuse unannounced landlord entries without 24-hour notice",
    "Propose withholding partial rent in escrow until repairs are made",
    "Negotiate a lower rent increase percentage in exchange for lease extension",
    "Use the word 'lease'",
    "Point out local tenant rights and rent control limits",

    # Scenario 76
    "Dispute an inflated customs valuation or duty assessment",
    "Argue that items are commercial trade samples not intended for resale",
    "Request temporary bonded warehouse storage while appealing duty rate",
    "Escalate classification dispute to a senior customs auditor",
    "Use the word 'tariff'",
    "Use the word 'exemption'",
    "Present certificates of origin for preferential trade duty rates",

    # Scenario 77
    "Justify promotion request using team leadership and expanded responsibilities",
    "Respond diplomatically to constructive feedback regarding delegation",
    "Negotiate a mid-year review target if immediate promotion is delayed",
    "Address executive budget constraints by proposing phased equity or bonus terms",
    "Use the word 'benchmark'",
    "Propose a performance-aligned compensation increase",
    "Use the word 'milestone'",

    # Scenario 78
    "Request waiver or reduction of bank origination and processing fees",
    "Explain debt-to-income ratio calculations and existing assets",
    "Negotiate rate-lock extension during underwriting delay",
    "Address low property appraisal value relative to purchase price",
    "Use the word 'amortization'",
    "Use the word 'collateral'",
    "Compare fixed-rate vs variable-rate mortgage options",

    # Scenario 79
    "Negotiate venue overtime and noise curfew terms",
    "Challenge unexpected vendor service markups and deposit terms",
    "Negotiate vendor contract cancellation clauses due to unforeseen events",
    "Propose cost-reduction alternatives for floral arrangements",
    "Use the word 'contingency'",
    "Use the word 'itinerary'",
    "State overall budget limits and primary spending priorities"
]

# For each goal in advanced_task_goals, ensure difficulty="advanced" is present in Task(goal=...)
for goal in advanced_task_goals:
    pattern = r'Task\("' + re.escape(goal) + r'",\s*"([^"]+)",\s*"([^"]+)"([^)]*)\)'
    def replacer(match):
        hint = match.group(1)
        done_when = match.group(2)
        rest = match.group(3)
        if 'difficulty="advanced"' not in rest:
            if rest.strip():
                rest = rest + ', difficulty="advanced"'
            else:
                rest = ', difficulty="advanced"'
        return f'Task("{goal}", "{hint}", "{done_when}"{rest})'
    content = re.sub(pattern, replacer, content)

with open('app/scenarios/builtins.py', 'w') as f:
    f.write(content)

print("Updated advanced difficulty flags for Scenarios 71-80!")
