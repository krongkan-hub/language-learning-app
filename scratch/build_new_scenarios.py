import sys
import os

new_code = '''
# Scenario 71: Emergency Room Triage Desk
scenario_70_tasks = [
    Task("Describe acute symptoms and pain level", "State what is wrong clearly and rate your pain.", "Learner described specific physical symptoms and indicated severity or pain level.", phase=1),
    Task("Provide medical history and allergy info", "Mention any existing medical conditions or allergies.", "Learner disclosed relevant medical history or drug allergies.", phase=1),
    Task("Inquire about estimated wait time", "Ask how long before a doctor can examine you.", "Learner asked about the estimated waiting time for medical assessment.", phase=1),
    Task("Use the word 'triage'", "Triage means sorting patients by medical urgency. Ask how triage priority works.", "Learner used the word 'triage'."),
    Task("Request pain management options while waiting", "Ask if there is safe temporary pain relief available.", "Learner asked for temporary pain relief or medication while waiting."),
    Task("Explain why your condition requires urgent evaluation", "State clearly why you cannot wait several hours.", "Learner explained why their symptoms require immediate medical attention.", difficulty="advanced", reactive=True),
    Task("Ask if family or companions can wait in the triage room", "Inquire about visitor policies in the ER.", "Learner asked if a companion or family member is permitted to stay with them."),
    Task("Use the word 'numbness'", "Numbness means lack of sensation or feeling. Describe experiencing numbness.", "Learner used the word 'numbness'."),
    Task("Clarify insurance co-pay or registration requirements", "Ask about administrative check-in documents.", "Learner asked about administrative check-in or insurance documentation.", phase=3),
    Task("Request a glass of water and check if fasting is required", "Ask if you are allowed to drink water before tests.", "Learner asked if drinking water is permitted prior to doctor examination."),
    Task("Ask for a wheelchair or mobility assistance", "Request assistance moving to the waiting bay.", "Learner requested a wheelchair or physical mobility assistance."),
    Task("Use the word 'vital'", "Vital signs include blood pressure and heart rate. Ask if your vitals can be checked again.", "Learner used the word 'vital'."),
    Task("Negotiate priority assessment after symptoms worsen", "Politely inform the nurse that your condition has escalated.", "Learner communicated worsening symptoms and requested re-evaluation of triage priority.", difficulty="advanced", reactive=True),
    Task("Confirm contact details for test result notification", "Ensure the hospital has your updated phone number.", "Learner verified contact details for follow-up or test notification.", phase=3),
    Task("Thank the triage nurse for their care", "Conclude the intake politely.", "Learner thanked the nurse and acknowledged instructions.", phase=3)
]

# Scenario 72: Flight Delay & Ticket Cancellation Desk
scenario_71_tasks = [
    Task("Explain your missed connection due to flight delay", "State your original flight details and the delay.", "Learner explained how the flight delay caused a missed connecting flight.", phase=1),
    Task("Request immediate rebooking on the next available flight", "Ask to be placed on the earliest departure.", "Learner requested rebooking on the earliest available flight.", phase=1),
    Task("Ask for a hotel voucher for an overnight delay", "Inquire about complimentary lodging for long delays.", "Learner asked for a hotel voucher or accommodation assistance for an overnight stay.", phase=2),
    Task("Use the word 'compensation'", "Compensation means payment or vouchers for inconvenience. Inquire about statutory delay compensation.", "Learner used the word 'compensation'."),
    Task("Request meal and beverage vouchers", "Ask for food vouchers while waiting at the terminal.", "Learner asked for meal or refreshment vouchers."),
    Task("Contest airline responsibility for missed connection", "Politely challenge the claim that weather excuses all care obligations.", "Learner argued politely that the airline bears responsibility for connection care.", difficulty="advanced", reactive=True),
    Task("Inquire about baggage transfer for rebooked flights", "Ask whether checked luggage will automatically transfer.", "Learner asked if checked baggage will be transferred to the new flight."),
    Task("Use the word 'itinerary'", "Itinerary means your travel schedule and flight details. Ask for an updated printed itinerary.", "Learner used the word 'itinerary'."),
    Task("Ask for a full refund option if rebooking is unsuitable", "Inquire about ticket cancellation and refund terms.", "Learner asked about ticket refund options if the alternative flight time is unacceptable.", phase=3),
    Task("Request access to the airline service lounge during delay", "Ask if lounge access can be granted given the length of wait.", "Learner requested temporary airline lounge access while waiting."),
    Task("Ask to speak to a duty supervisor regarding policy exceptions", "Request escalation if the front clerk cannot authorize vouchers.", "Learner requested to speak with a supervisor or manager.", difficulty="advanced", reactive=True),
    Task("Use the word 'disruption'", "Disruption means disturbance to regular service. Acknowledge the severe flight disruption.", "Learner used the word 'disruption'."),
    Task("Negotiate endorsement onto a partner airline flight", "Ask if you can be rebooked on a competing or partner carrier.", "Learner proposed being rebooked on a partner or alternative airline flight.", difficulty="advanced"),
    Task("Confirm final gate assignment and boarding time", "Verify the details of your new boarding pass.", "Learner verified the departure time, gate, or seat assignment for the new flight.", phase=3),
    Task("Thank the agent for resolving your travel issue", "Conclude the exchange politely.", "Learner expressed appreciation for the agent's assistance.", phase=3)
]

# Scenario 73: Insurance Claim Dispute Call
scenario_72_tasks = [
    Task("State your claim reference number and incident date", "Provide your claim identifier to the adjuster.", "Learner stated their insurance policy or claim reference number.", phase=1),
    Task("Describe the property damage incident clearly", "Explain what happened and the extent of the damage.", "Learner described the specific cause and scope of property damage.", phase=1),
    Task("Dispute the initial claim rejection or low payout offer", "Politely challenge the adjuster's low estimate.", "Learner expressed disagreement with the claim valuation or denial rationale.", phase=2),
    Task("Use the word 'deductible'", "Deductible means the amount you pay out-of-pocket before insurance kicks in. Clarify the deductible calculation.", "Learner used the word 'deductible'."),
    Task("Offer to provide contractor repair estimates and photos", "Mention supporting documentation you have prepared.", "Learner offered to submit photographic evidence or independent repair estimates."),
    Task("Argue against a pre-existing condition clause", "Explain why the damage occurred directly from the covered event.", "Learner argued that the damage was directly caused by the insured event rather than pre-existing wear.", difficulty="advanced", reactive=True),
    Task("Ask for clarification on specific policy wording", "Inquire about the exact section clause cited by the adjuster.", "Learner requested an explanation of the specific policy clause or exclusion cited."),
    Task("Use the word 'reimbursement'", "Reimbursement means repayment for expenses incurred. Ask about the timeline for reimbursement.", "Learner used the word 'reimbursement'."),
    Task("Request an independent adjuster re-inspection", "Ask for a second assessment by an un-biased inspector.", "Learner requested a second inspection by an independent adjuster.", difficulty="advanced"),
    Task("Ask if temporary living expenses are covered during repair", "Inquire about displacement coverage under your policy.", "Learner asked about coverage for temporary living or displacement expenses."),
    Task("Escalate the dispute to a senior claims supervisor", "Politely request escalation to a claims manager.", "Learner requested escalation to a senior claims supervisor or ombudsman.", difficulty="advanced", reactive=True),
    Task("Use the word 'coverage'", "Coverage refers to the scope of protection provided by insurance. Inquire about total coverage limits.", "Learner used the word 'coverage'."),
    Task("Negotiate a compromise settlement amount", "Propose a reasonable payout figure to resolve the dispute.", "Learner proposed a compromised payout figure to settle the claim amicably.", difficulty="advanced", phase=3),
    Task("Confirm required paperwork submission deadline", "Ask when supporting documents must be uploaded.", "Learner confirmed the deadline and process for submitting additional evidence.", phase=3),
    Task("Conclude call politely while confirming next steps", "Summarize agreed action items before hanging up.", "Learner summarized agreed next steps and thanked the adjuster.", phase=3)
]

# Scenario 74: Tech Startup Co-Founder Equity & Role Alignment
scenario_73_tasks = [
    Task("State your proposed technical role and key responsibilities", "Outline what you will contribute to the startup.", "Learner defined their proposed technical role and core responsibilities.", phase=1),
    Task("Discuss equity percentage split between co-founders", "Raise the topic of equity distribution.", "Learner brought up equity allocation and proposed or discussed equity split percentages.", phase=1),
    Task("Negotiate a 4-year vesting schedule with a 1-year cliff", "Propose standard vesting terms to protect equity.", "Learner proposed a 4-year vesting schedule with a 1-year cliff period.", phase=2),
    Task("Use the word 'equity'", "Equity means ownership stake in the company. Mention equity expectations.", "Learner used the word 'equity'."),
    Task("Clarify IP assignment and pre-existing code ownership", "Ensure clear boundaries on intellectual property.", "Learner clarified IP assignment and ownership of prior software assets."),
    Task("Address concerns regarding initial salary vs equity trade-off", "Discuss reduced cash compensation during early funding.", "Learner discussed salary expectations relative to equity compensation in early stages.", difficulty="advanced", reactive=True),
    Task("Ask about fundraising milestones and runway expectations", "Inquire about investor timelines and cash runway.", "Learner asked about current runway, valuation, or fundraising targets."),
    Task("Use the word 'dilution'", "Dilution means reduction in equity percentage as new shares are issued to investors. Ask about anti-dilution terms.", "Learner used the word 'dilution'."),
    Task("Negotiate board seats and voting rights structure", "Discuss decision-making authority between founders.", "Learner discussed board representation or major voting threshold requirements.", difficulty="advanced"),
    Task("Set clear boundaries regarding part-time vs full-time commitment", "Specify when you will transition to 100% full-time.", "Learner stated conditions for transitioning to full-time commitment."),
    Task("Propose a co-founder dispute resolution mechanism", "Suggest how deadlocks between equal partners should be resolved.", "Learner proposed a deadlock resolution or mediation mechanism.", difficulty="advanced", reactive=True),
    Task("Use the word 'vesting'", "Vesting means earning equity over time. Discuss vesting milestone terms.", "Learner used the word 'vesting'."),
    Task("Agree on initial equity split subject to legal review", "Summarize consensus on equity and roles.", "Learner summarized agreed equity terms subject to legal documentation.", phase=3),
    Task("Confirm timeline for drafting the co-founders agreement", "Ask when legal documents will be prepared.", "Learner agreed on a timeline for drafting the formal co-founders agreement.", phase=3),
    Task("Express enthusiasm for building the company together", "Conclude the discussion on a positive, aligned note.", "Learner expressed optimism and commitment to partnership.", phase=3)
]

# Scenario 75: Traffic Police Roadside Stop
scenario_74_tasks = [
    Task("Greet officer politely and ask reason for the traffic stop", "Remain calm and ask why you were pulled over.", "Learner greeted the officer respectfully and asked why they were stopped.", phase=1),
    Task("Provide driver's license, registration, and insurance proof", "Hand over your identification documents.", "Learner offered their driver's license, vehicle registration, or insurance document.", phase=1),
    Task("Explain minor speed adjustment due to traffic flow", "Politely state your driving context without arguing.", "Learner explained their driving speed in the context of surrounding traffic flow.", phase=2),
    Task("Use the word 'registration'", "Registration is official documentation of vehicle ownership. Present valid registration.", "Learner used the word 'registration'."),
    Task("Point out recent road sign changes or poor visibility", "Mention factors affecting speed limit visibility.", "Learner noted poor lighting, obscured road signs, or recent speed zone changes."),
    Task("Politely request a written warning instead of a traffic ticket", "Ask for leniency based on a clean driving record.", "Learner requested a warning rather than a formal traffic ticket.", difficulty="advanced", reactive=True),
    Task("Ask for clarification on the exact speed recorded by radar", "Inquire about the officer's speed detection measurement.", "Learner asked about the radar measurement or recorded speed reading."),
    Task("Use the word 'citation'", "Citation means an official summons or traffic ticket. Inquire about citation details.", "Learner used the word 'citation'."),
    Task("Ask about the procedure for contesting the ticket in court", "Inquire about court appearance dates and appeal process.", "Learner asked about the process for contesting the ticket in traffic court.", difficulty="advanced"),
    Task("Check whether your driving record has previous infractions", "Confirm if officer sees a clean record on file.", "Learner mentioned having a clean driving history."),
    Task("Remain calm and decline consent for voluntary vehicle search politely", "Set a legal boundary respectfully.", "Learner declined a voluntary vehicle search politely and calmly.", difficulty="advanced", reactive=True),
    Task("Use the word 'compliance'", "Compliance means obeying laws and regulations. Affirm your commitment to traffic rules.", "Learner used the word 'compliance'."),
    Task("Accept the citation or warning document without argument", "Acknowledge receipt of paper copy.", "Learner accepted the document and signed or acknowledged receipt.", phase=3),
    Task("Ask if it is safe to merge back into traffic", "Verify permission to drive away.", "Learner asked if they are free to go and safely re-enter traffic.", phase=3),
    Task("Wish the officer a safe shift", "Conclude interaction respectfully.", "Learner offered a polite closing remark to the officer.", phase=3)
]

# Scenario 76: Landlord Maintenance & Rent Escalation Dispute
scenario_75_tasks = [
    Task("Identify maintenance issues requiring urgent repair", "List problems like leaks, broken heating, or electrical faults.", "Learner reported specific property maintenance issues needing repair.", phase=1),
    Task("Dispute recent notice of a sudden rent increase", "State that the proposed rent increase is unreasonable.", "Learner contested a proposed rent increase notice.", phase=1),
    Task("Condition rent increase acceptance on immediate maintenance fixes", "Link rent adjustments to completed repairs.", "Learner conditioned any rent adjustment on prompt completion of pending maintenance.", phase=2),
    Task("Use the word 'lease'", "Lease means the formal rental agreement. Cite clauses in your lease agreement.", "Learner used the word 'lease'."),
    Task("Point out local tenant rights and rent control limits", "Mention statutory limits on annual rent increases.", "Learner cited tenant rights or legal rent increase caps."),
    Task("Refuse unannounced landlord entries without 24-hour notice", "Politely enforce privacy rights under the lease.", "Learner insisted on receiving formal 24-hour notice before landlord visits.", difficulty="advanced", reactive=True),
    Task("Provide evidence of past maintenance requests sent in writing", "Show proof of earlier ignored requests.", "Learner cited previous written notices regarding unresolved repairs."),
    Task("Use the word 'maintenance'", "Maintenance means keeping property in good repair. Request a clear maintenance schedule.", "Learner used the word 'maintenance'."),
    Task("Propose withholding partial rent in escrow until repairs are made", "Mention legal escrow mechanisms for unresolved health hazards.", "Learner proposed placing rent in escrow until critical repairs are completed.", difficulty="advanced"),
    Task("Ask for written confirmation of repair completion dates", "Request a binding schedule from the landlord.", "Learner asked for written commitment on repair timelines."),
    Task("Negotiate a lower rent increase percentage in exchange for lease extension", "Offer a longer lease term for a smaller increase.", "Learner offered a longer lease extension in exchange for a capped rent increase.", difficulty="advanced", reactive=True),
    Task("Use the word 'deposit'", "Deposit means security money held by landlord. Inquire about security deposit terms.", "Learner used the word 'deposit'."),
    Task("Summarize agreed terms of rent and maintenance schedule", "Confirm consensus before signing addendum.", "Learner summarized agreed rent terms and repair commitments.", phase=3),
    Task("Request a written addendum to the lease agreement", "Ask for formal documentation of the agreement.", "Learner requested a signed addendum capturing the negotiated terms.", phase=3),
    Task("Conclude meeting professionally with the landlord", "Part on respectful, clear business terms.", "Learner concluded the conversation professionally.", phase=3)
]

# Scenario 77: Customs Import Duties & Tariff Hearing
scenario_76_tasks = [
    Task("Declare commercial goods shipment details and invoice value", "State the contents and commercial invoice value of imported items.", "Learner declared the description and total invoice value of imported goods.", phase=1),
    Task("Inquire about harmonized tariff code classification for your items", "Ask how customs categorizes your products.", "Learner asked about tariff classification under the harmonized system.", phase=1),
    Task("Dispute an inflated customs valuation or duty assessment", "Challenge an excessively high duty tax calculation.", "Learner disputed an official customs valuation assessment.", phase=2),
    Task("Use the word 'tariff'", "Tariff means a tax or duty on imports. Inquire about applicable tariff rates.", "Learner used the word 'tariff'."),
    Task("Present certificates of origin for preferential trade duty rates", "Offer documentation proving origin under trade agreements.", "Learner submitted or referenced certificates of origin for duty reduction."),
    Task("Argue that items are commercial trade samples not intended for resale", "Request duty exemption for non-commercial samples.", "Learner argued that imported items are non-resale trade samples eligible for exemption.", difficulty="advanced", reactive=True),
    Task("Ask for clarification on import licensing requirements", "Inquire about necessary permits for restricted goods.", "Learner asked about mandatory import licenses or regulatory permits."),
    Task("Use the word 'exemption'", "Exemption means freedom from tax or duty obligations. Inquire about tax exemption criteria.", "Learner used the word 'exemption'."),
    Task("Request temporary bonded warehouse storage while appealing duty rate", "Ask to hold goods safely without paying full duty immediately.", "Learner requested holding goods in a bonded warehouse pending appeal.", difficulty="advanced"),
    Task("Inquire about acceptable payment methods for customs duties", "Ask how import taxes can be paid on-site.", "Learner asked about payment methods for customs duties."),
    Task("Escalate classification dispute to a senior customs auditor", "Request official administrative review of tariff code.", "Learner requested administrative review by a senior customs inspector.", difficulty="advanced", reactive=True),
    Task("Use the word 'declaration'", "Declaration is official statement of goods entering country. Reference your import declaration.", "Learner used the word 'declaration'."),
    Task("Pay calculated duties or sign formal appeal form", "Complete financial or legal clearance step.", "Learner arranged duty payment or signed formal appeal paperwork.", phase=3),
    Task("Request stamped release documentation for port authority pickup", "Ask for cargo release permit.", "Learner requested stamped customs release authorization.", phase=3),
    Task("Thank customs officer for facilitating clearance", "Conclude meeting professionally.", "Learner thanked the officer for assisting with clearance.", phase=3)
]

# Scenario 78: Executive Performance Review & Promotion Request
scenario_77_tasks = [
    Task("Summarize major accomplishments and revenue contributions over the past year", "Present key metric wins and project results.", "Learner highlighted major achievements and quantifiable contributions over the review period.", phase=1),
    Task("Formally request promotion to senior leadership title", "State your goal to advance to the next career level.", "Learner explicitly requested promotion to a target senior title.", phase=1),
    Task("Justify promotion request using team leadership and expanded responsibilities", "Explain how your actual work already matches the higher title.", "Learner demonstrated that their actual responsibilities already align with the higher role.", phase=2),
    Task("Use the word 'milestone'", "Milestone means significant stage or goal reached. Cite key milestones delivered.", "Learner used the word 'milestone'."),
    Task("Propose a performance-aligned compensation increase", "Request a salary adjustment linked to project impact.", "Learner proposed a salary increase aligned with performance metrics."),
    Task("Respond diplomatically to constructive feedback regarding delegation", "Acknowledge areas for growth without becoming defensive.", "Learner accepted constructive feedback constructively and outlined improvements.", difficulty="advanced", reactive=True),
    Task("Present 360-degree feedback testimonials from cross-functional peers", "Reference positive feedback from key stakeholders.", "Learner cited endorsement from cross-functional partners or team members."),
    Task("Use the word 'benchmark'", "Benchmark means standard against which performance is measured. Reference industry benchmarks.", "Learner used the word 'benchmark'."),
    Task("Negotiate a mid-year review target if immediate promotion is delayed", "Agree on concrete milestones to secure promotion within 6 months.", "Learner negotiated specific mid-year criteria for promotion if immediate title change is deferred.", difficulty="advanced"),
    Task("Outline strategic goals for leading the department next quarter", "Share your vision for driving team growth.", "Learner presented strategic objectives for the upcoming year."),
    Task("Address executive budget constraints by proposing phased equity or bonus terms", "Propose flexible compensation terms if base salary pool is tight.", "Learner proposed flexible compensation structuring such as performance bonuses or equity.", difficulty="advanced", reactive=True),
    Task("Use the word 'leadership'", "Leadership means guiding and empowering a team. Highlight your leadership vision.", "Learner used the word 'leadership'."),
    Task("Confirm agreed promotion timeline and written review summary", "Summarize consensus reached with director.", "Learner confirmed agreed promotion timeline and compensation steps.", phase=3),
    Task("Request formal submission of promotion paperwork to HR", "Ask for next administrative step.", "Learner asked the director to submit formal promotion recommendation to HR.", phase=3),
    Task("Express gratitude for mentorship and ongoing support", "Conclude review on an aligned, inspiring note.", "Learner thanked the director for support and guidance.", phase=3)
]

# Scenario 79: Bank Loan & Mortgage Officer Meeting
scenario_78_tasks = [
    Task("State target loan amount and property purchase price", "Specify how much financing you require.", "Learner stated target loan amount and property purchase price.", phase=1),
    Task("Provide proof of income, tax returns, and employment stability", "Present financial credentials.", "Learner summarized proof of income, employment history, or tax documentation.", phase=1),
    Task("Compare fixed-rate vs variable-rate mortgage options", "Ask about pros and cons of fixed interest rates.", "Learner compared fixed-rate and adjustable-rate loan terms with the officer.", phase=2),
    Task("Use the word 'amortization'", "Amortization means paying off a debt with regular payments over time. Inquire about amortization schedule.", "Learner used the word 'amortization'."),
    Task("Request waiver or reduction of bank origination and processing fees", "Ask if administrative fees can be discounted.", "Learner asked for discounts or waivers on loan origination fees."),
    Task("Explain debt-to-income ratio calculations and existing assets", "Clarify your monthly debt obligations.", "Learner explained their debt-to-income ratio and liquid asset reserves.", difficulty="advanced", reactive=True),
    Task("Ask about pre-payment penalty terms for early payoff", "Inquire if paying off the mortgage early incurs fees.", "Learner asked whether early loan payoff triggers pre-payment penalties."),
    Task("Use the word 'collateral'", "Collateral is property pledged as security for repayment of a loan. Reference property collateral.", "Learner used the word 'collateral'."),
    Task("Negotiate rate-lock extension during underwriting delay", "Request extending your locked interest rate window.", "Learner requested extending interest rate lock window during appraisal or underwriting delay.", difficulty="advanced"),
    Task("Inquire about private mortgage insurance requirements", "Ask if PMI is required and how to remove it.", "Learner asked about Private Mortgage Insurance (PMI) threshold and removal conditions."),
    Task("Address low property appraisal value relative to purchase price", "Propose solutions if appraisal falls short of purchase offer.", "Learner discussed remedies if property appraisal comes in lower than agreed purchase price.", difficulty="advanced", reactive=True),
    Task("Use the word 'underwriting'", "Underwriting is process where financial institution evaluates risk of lending. Inquire about underwriting status.", "Learner used the word 'underwriting'."),
    Task("Request formal pre-approval letter for seller submission", "Ask for official pre-approval document.", "Learner requested a pre-approval letter to submit with home offer.", phase=3),
    Task("Confirm expected loan closing date and escrow deposit details", "Verify closing timeline.", "Learner verified estimated closing date and down payment wire details.", phase=3),
    Task("Thank mortgage officer for expert financial guidance", "Conclude consultation politely.", "Learner expressed appreciation for the officer's advice.", phase=3)
]

# Scenario 80: Wedding & Event Planner Consultation
scenario_79_tasks = [
    Task("Outline event scope, estimated guest count, and overall vision", "Describe what kind of event or wedding you are planning.", "Learner specified event type, estimated guest headcount, and design style.", phase=1),
    Task("State overall budget limits and primary spending priorities", "Discuss financial boundaries for catering, venue, and decor.", "Learner stated overall budget parameters and priority allocation areas.", phase=1),
    Task("Negotiate venue overtime and noise curfew terms", "Ask for flexibility on late-night event hours.", "Learner negotiated venue overtime rates or music curfew extensions.", phase=2),
    Task("Use the word 'contingency'", "Contingency means provision for an unexpected event. Ask for a rain contingency plan.", "Learner used the word 'contingency'."),
    Task("Request customizable catering menu options for dietary needs", "Ensure guest dietary requirements are accommodated.", "Learner requested menu adjustments for vegan, gluten-free, or religious dietary needs."),
    Task("Challenge unexpected vendor service markups and deposit terms", "Politely question hidden coordination fees.", "Learner questioned unexpected vendor markup fees or strict cancellation deposit terms.", difficulty="advanced", reactive=True),
    Task("Inquire about audio-visual and lighting equipment rentals", "Ask what technical setup is included at venue.", "Learner asked about audio-visual, lighting, or staging rental options."),
    Task("Use the word 'itinerary'", "Itinerary refers to event day timeline. Discuss wedding day master schedule.", "Learner used the word 'itinerary'."),
    Task("Negotiate vendor contract cancellation clauses due to unforeseen events", "Protect deposit funds in case of rescheduling.", "Learner negotiated flexible contract cancellation or force majeure terms with planner.", difficulty="advanced"),
    Task("Review seating arrangement layout and floor plan capacity", "Discuss guest flow and table setup.", "Learner discussed floor plan layout, head table placement, or guest seating capacity."),
    Task("Propose cost-reduction alternatives for floral arrangements", "Suggest seasonal flowers to stay within budget.", "Learner suggested cost-saving floral or decor alternatives.", difficulty="advanced", reactive=True),
    Task("Use the word 'logistics'", "Logistics means managing complex execution details. Discuss guest shuttle transportation logistics.", "Learner used the word 'logistics'."),
    Task("Agree on master event timeline and milestone deadlines", "Confirm key planning dates before contract signing.", "Learner agreed on master timeline for vendor bookings and tasting trials.", phase=3),
    Task("Request formal itemized proposal and contract draft", "Ask planner for detailed cost breakdown.", "Learner requested formal itemized event contract draft.", phase=3),
    Task("Express excitement for collaborating on the event", "Conclude consultation on a positive note.", "Learner expressed confidence and enthusiasm for working together.", phase=3)
]
'''

with open('app/scenarios/builtins.py', 'r') as f:
    content = f.read()

# Insert new tasks right before SCENARIOS = [
insertion_point = content.find('SCENARIOS = [')
if insertion_point == -1:
    print("Could not find SCENARIOS = [")
    sys.exit(1)

updated_content = content[:insertion_point] + new_code + "\n\n" + content[insertion_point:]

# Now insert the 10 new Scenario definitions into SCENARIOS list before the closing bracket ]
scenarios_end_point = updated_content.rfind(']')
if scenarios_end_point == -1:
    print("Could not find end of SCENARIOS list")
    sys.exit(1)

new_scenarios_objs = '''
    Scenario(
        name="Emergency Room Triage Desk",
        place="An emergency hospital triage reception",
        role="You are an ER triage nurse on a busy night shift.",
        speaker="Nurse Morgan",
        tasks=scenario_70_tasks,
        complications=['high patient volume delay', 'triage priority classification', 'missing identification paperwork']
    ),
    Scenario(
        name="Flight Delay & Ticket Cancellation Desk",
        place="An international airport customer service counter during severe weather delays",
        role="You are a stressed airline customer service supervisor.",
        speaker="Supervisor Karen",
        tasks=scenario_71_tasks,
        complications=['flight fully booked until tomorrow', 'hotel voucher quota exceeded', 'lost luggage tracking system delay']
    ),
    Scenario(
        name="Insurance Claim Dispute Call",
        place="An insurance claims resolution office",
        role="You are a senior claims adjuster evaluating a disputed property damage claim.",
        speaker="Adjuster Miller",
        tasks=scenario_72_tasks,
        complications=['deductible clause dispute', 'photo documentation missing', 'policy limit restriction']
    ),
    Scenario(
        name="Tech Startup Co-Founder Equity & Role Alignment",
        place="A quiet conference room at a co-working space",
        role="You are a prospective technical co-founder discussing vesting schedules and equity split.",
        speaker="Founder Sam",
        tasks=scenario_73_tasks,
        complications=['1-year cliff requirement', 'IP assignment clause', 'equity dilution threshold']
    ),
    Scenario(
        name="Traffic Police Roadside Stop",
        place="The side of a highway after being pulled over by traffic police",
        role="You are a highway patrol officer conducting a traffic stop.",
        speaker="Officer Vance",
        tasks=scenario_74_tasks,
        complications=['construction zone speed limit', 'expired vehicle inspection sticker', 'license verification system delay']
    ),
    Scenario(
        name="Landlord Maintenance & Rent Escalation Dispute",
        place="Inside a rented apartment during an unannounced property inspection",
        role="You are a strict property landlord inspecting maintenance issues.",
        speaker="Landlord Mr. Sterling",
        tasks=scenario_75_tasks,
        complications=['unresolved plumbing leak', 'sudden 10% rent increase notice', 'security deposit deduction dispute']
    ),
    Scenario(
        name="Customs Import Duties & Tariff Hearing",
        place="A commercial port customs clearance office",
        role="You are a senior customs inspector evaluating imported commercial goods.",
        speaker="Inspector Zhao",
        tasks=scenario_76_tasks,
        complications=['harmonized tariff code mismatch', 'commercial vs personal classification dispute', 'duty tax payment method requirement']
    ),
    Scenario(
        name="Executive Performance Review & Promotion Request",
        place="A manager's office during an annual review meeting",
        role="You are a department director leading an annual performance review.",
        speaker="Director Henderson",
        tasks=scenario_77_tasks,
        complications=['department budget freeze on promotions', '360-degree feedback review', 'quarterly target goal metrics']
    ),
    Scenario(
        name="Bank Loan & Mortgage Officer Meeting",
        place="A private consultation office at a commercial bank",
        role="You are a mortgage loan officer reviewing a home buyer's application.",
        speaker="Loan Officer Arthur",
        tasks=scenario_78_tasks,
        complications=['debt-to-income ratio limit', 'appraisal value shortfall', 'variable vs fixed rate lock window']
    ),
    Scenario(
        name="Wedding & Event Planner Consultation",
        place="A luxury event planning boutique showroom",
        role="You are an experienced wedding and event designer.",
        speaker="Planner Celeste",
        tasks=scenario_79_tasks,
        complications=['outdoor venue weather contingency plan', 'catering dietary restriction surcharge', 'vendor deposit cancellation policy']
    ),
'''

final_content = updated_content[:scenarios_end_point] + new_scenarios_objs + updated_content[scenarios_end_point:]

with open('app/scenarios/builtins.py', 'w') as f:
    f.write(final_content)

print("Successfully added 10 new scenarios to builtins.py!")
