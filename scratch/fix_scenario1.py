import sys
import os
import re

if __name__ == '__main__':
    # Define the 69 tasks as Python Task objects string representation
    tasks_code = '''# Scenario: Airport Check-in & Security
scenario_1_tasks = [
    Task("Present your passport and booking reference code", "You have arrived at the check-in desk. Hand over your travel documents and state your confirmation number.", "Learner presented their passport AND booking reference code.", phase=1, scene_hint="The agent taps on the keyboard and looks up at the desk counter."),
    Task("Greet the agent and state your final destination", "Start the conversation politely. Greet the agent and mention the city you are flying to.", "Learner greeted the agent AND stated their final destination.", phase=1),
    Task("Confirm your flight number and departure time", "You want to make sure you are at the correct desk. Ask the agent to verify your flight details.", "Learner confirmed their flight number AND departure time.", phase=1),
    Task("Request an aisle seat for the flight", "You prefer easy access to the aisle during travel. Ask the agent if an aisle seat is available.", "Learner requested an aisle seat for the flight.", phase=1),
    Task("Ask to sit together with your travel companion", "You are traveling with a partner and want adjacent seats. Request two seats side by side.", "Learner asked to sit together with their travel companion.", phase=1),
    Task("Justify your eligibility for a transit visa exemption", "The agent asks for entry authorization. Explain why your layover duration exempts you from needing a visa.", "Learner justified their eligibility for a transit visa exemption.", difficulty="advanced", phase=1),
    Task("Confirm your emergency contact details", "The agent asks for your contact details on file. Provide your updated phone number and emergency contact info.", "Learner confirmed their emergency contact details.", phase=1, reactive=True, scene_hint="The screen prompts the agent to update missing passenger contact fields."),
    Task("Inquire about seat selection options in your fare class", "You want to check seat availability before finalizing check-in. Ask what seating options remain.", "Learner inquired about seat selection options in their fare class.", phase=1),
    Task("Explain a name spelling discrepancy on your ticket", "Your middle name was misspelled during booking. Explain the typo to the agent and request a correction.", "Learner explained a name spelling discrepancy on their ticket AND requested a correction.", difficulty="advanced", phase=1),
    Task("State your frequent flyer membership number", "You wish to accrue loyalty points for this journey. Provide your loyalty account number to the agent.", "Learner stated their frequent flyer membership number.", phase=1),

    Task("Place your suitcase onto the check-in scale", "The agent is ready to weigh your checked luggage. Inform them you are placing your bag on the scale.", "Learner placed their suitcase onto the check-in scale.", phase=2, scene_hint="A heavy rubber conveyor belt sits silent beside the metal weight scale."),
    Task("Inquire about the checked baggage weight limit", "You want to ensure your bag is within limits. Ask what the maximum weight allowance is for checked luggage.", "Learner inquired about the checked baggage weight limit.", phase=2),
    Task("Negotiate a fee waiver for a slightly overweight bag", "Your bag is one kilogram over the limit. Politely ask the agent to waive the extra charge as a courtesy.", "Learner negotiated a fee waiver for a slightly overweight bag.", difficulty="advanced", phase=2, reactive=True, scene_hint="The digital scale display flashes a red warning number over the weight limit."),
    Task("Offer to remove heavy items to avoid baggage fees", "The agent flagged your suitcase as overweight. State that you will transfer some clothes to your carry-on.", "Learner offered to remove heavy items to avoid baggage fees.", phase=2, reactive=True),
    Task("Ask for a fragile sticker on your luggage", "Your checked bag contains delicate glass souvenirs. Request that the agent tag it as fragile.", "Learner asked for a fragile sticker on their luggage.", phase=2),
    Task("Inquire if your checked bags go straight to the final destination", "You have a connecting flight. Ask if you need to retrieve and re-check your bags during the layover.", "Learner inquired whether checked bags transfer directly to the final destination.", phase=2),
    Task("Negotiate special handling arrangements for an oversized musical instrument", "You are traveling with a cello. Request delicate oversized baggage processing without excessive extra fees.", "Learner negotiated special handling arrangements for an oversized musical instrument.", difficulty="advanced", phase=2),
    Task("Request an exit row seat with extra legroom", "You are tall and want additional legroom. Ask for an exit row seat and confirm you meet safety criteria.", "Learner requested an exit row seat with extra legroom.", difficulty="advanced", phase=2),
    Task("Inquire about paid cabin upgrade availability", "You want to travel in business class. Ask about upgrade prices and seat availability for your flight.", "Learner inquired about paid cabin upgrade availability.", difficulty="advanced", phase=2),
    Task("Accept an offered seat change to a window seat", "The agent offers to switch your seat assignment. Confirm that you accept the window seat.", "Learner accepted an offered seat change to a window seat.", phase=2),
    Task("Ask about the layover duration for your connection", "You want to plan your connection time. Ask the agent how long you will wait between flights.", "Learner asked about the layover duration for their connection.", phase=2),
    Task("Request a flight change due to a schedule conflict", "Your flight time was moved unexpectedly. Explain the conflict and request an earlier departure.", "Learner requested a flight change due to a schedule conflict.", difficulty="advanced", phase=2, reactive=True, scene_hint="The departure status screen shows flight times updated in bright yellow lettering."),
    Task("Inquire about priority boarding procedures", "You want to board early with your ticket. Ask when and where priority boarding takes place.", "Learner inquired about priority boarding procedures.", phase=2),
    Task("Request permission to gate-check an oversized stroller without extra fees", "You are traveling with an infant stroller. Ask to use it up to the gate and check it free of charge.", "Learner requested permission to gate-check an oversized stroller without extra fees.", difficulty="advanced", phase=2),
    Task("Declare lithium batteries inside your carry-on bag", "You have power banks in your hand luggage. Inform staff to confirm compliance with safety regulations.", "Learner declared lithium batteries inside their carry-on bag.", phase=2),
    Task("Inquire about lounge access privileges for your ticket", "You hold a business class fare. Ask the agent if complimentary airport lounge access is included.", "Learner inquired about lounge access privileges for their ticket.", phase=2),
    Task("Ask for directions to the security screening area", "You have completed check-in paperwork. Ask the agent where the main security checkpoint is located.", "Learner asked for directions to the security screening area.", phase=2),
    Task("Confirm liquid container volume limits for hand luggage", "You are entering the security line. Ask security staff to clarify the individual liquid container capacity.", "Learner confirmed liquid container volume limits for hand luggage.", phase=2, scene_hint="A plastic bin containing confiscated bottles sits next to the security queue line."),
    Task("Ask if laptop computers must be removed from carry-on bags", "You are preparing your belongings for the scanner conveyor. Ask if electronic devices need separate trays.", "Learner asked if laptop computers must be removed from carry-on bags.", phase=2),
    Task("Clarify footwear removal requirements at security", "You are approaching the walk-through metal detector. Ask if passengers must take off their shoes.", "Learner clarified footwear removal requirements at security.", phase=2),
    Task("Explain the presence of a metal joint replacement during screening", "The metal scanner alarm sounded as you passed. Inform security staff about your medical implant.", "Learner explained the presence of a metal joint replacement during screening.", difficulty="advanced", phase=2, reactive=True, scene_hint="The archway metal detector emits an audible double beep as you step through."),
    Task("Request a private room for a manual security pat-down", "You prefer privacy for additional physical screening. Ask staff for a private inspection area.", "Learner requested a private room for a manual security pat-down.", difficulty="advanced", phase=2),
    Task("Explain the contents of a flagged carry-on bag", "An officer pulled your bag aside for inspection. Clarify that the object inside is a souvenir metal snowglobe.", "Learner explained the contents of a flagged carry-on bag.", phase=2, reactive=True, scene_hint="An officer places your carry-on bag onto a stainless steel inspection table."),
    Task("Propose alternative arrangements for a prohibited liquid container", "Your expensive liquid exceeds the volume limit. Ask if you can mail it home or return it to check-in.", "Learner proposed alternative arrangements for a prohibited liquid container.", difficulty="advanced", phase=2, reactive=True),
    Task("Ask about special meal requests for your flight", "You pre-ordered a vegetarian meal. Confirm with the agent that your dietary preference is recorded.", "Learner asked about special meal requests for their flight.", phase=2),
    Task("Complain about a severe flight delay causing a missed connection", "Your flight is delayed four hours. Express concern about your tight connection and demand a resolution.", "Learner complained about a severe flight delay causing a missed connection.", difficulty="advanced", phase=2, reactive=True, scene_hint="A chime sounds over the public address system announcing flight delays."),
    Task("Request specialized assistance for a passenger with mobility limitations", "You need help navigating the terminal. Request staff to arrange an escort or wheelchair service.", "Learner requested specialized assistance for a passenger with mobility limitations.", difficulty="advanced", phase=2),
    Task("Confirm the departure gate location and walking distance", "You want to budget your time before boarding. Ask where your gate is located and how long it takes to walk there.", "Learner confirmed the departure gate location AND walking distance.", phase=2),
    Task("Request compensation for an involuntary class downgrade", "You were moved from business to economy class due to overbooking. Request official reimbursement.", "Learner requested compensation for an involuntary class downgrade.", difficulty="advanced", phase=2, reactive=True),
    Task("Inquire about standby list procedures for an earlier flight", "You arrived early at the terminal. Ask if you can put your name on the standby list for an earlier departure.", "Learner inquired about standby list procedures for an earlier flight.", phase=2),
    Task("Ask about pet travel guidelines for cabin transport", "You are traveling with a small dog in a carrier. Confirm cabin entry rules with the agent.", "Learner asked about pet travel guidelines for cabin transport.", phase=2),
    Task("Negotiate a seat reassignment away from a broken recline mechanism", "The agent mentions your assigned seat does not recline. Explain your long journey and request a different seat.", "Learner negotiated a seat reassignment away from a broken recline mechanism.", difficulty="advanced", phase=2),
    Task("Inquire about duty-free purchase pickup locations", "You bought goods online before traveling. Ask where to collect duty-free merchandise past security.", "Learner inquired about duty-free purchase pickup locations.", phase=2),
    Task("Request meal vouchers during an extended flight delay", "Your departure was postponed by five hours. Request food and beverage vouchers for the long wait.", "Learner requested meal vouchers during an extended flight delay.", difficulty="advanced", phase=2, reactive=True),
    Task("Ask for assistance locating a lost boarding pass", "You misplaced your printed pass after security. Ask staff how to obtain a replacement document.", "Learner asked for assistance locating a lost boarding pass.", phase=2),
    Task("Confirm baggage tag destination codes", "The agent is printing luggage tags. Ask to check that the airport code matches your destination.", "Learner confirmed baggage tag destination codes.", phase=2, scene_hint="A thermal printer whirs while printing sticky barcode baggage tags."),
    Task("Negotiate hotel accommodation after a cancelled flight", "Your evening flight was cancelled until tomorrow. Request a hotel voucher and overnight transport.", "Learner negotiated hotel accommodation after a cancelled flight.", difficulty="advanced", phase=2, reactive=True),
    Task("Ask if duty-free liquids are allowed through transit security", "You bought sealed duty-free wine. Ask if it can pass through security during your connecting airport layover.", "Learner asked if duty-free liquids are allowed through transit security.", phase=2),
    Task("Inquire about family seating policies", "You want to make sure your child is seated next to you. Ask the agent to confirm family seating rules.", "Learner inquired about family seating policies.", phase=2),
    Task("Use the word 'voucher'", "A voucher is a coupon or document redeemable for specific goods or services. Inquire if the counter offers one for meals during a long wait.", "Learner used the word 'voucher'.", phase=2),
    Task("Use the word 'liable'", "Liable means legally responsible or financially obligated for an outcome. Ask whether you are held responsible for damages to fragile baggage.", "Learner used the word 'liable'.", phase=2),
    Task("Use the word 'exempt'", "Exempt means excused from a rule, duty, or payment requirement. Inquire whether your essential medical device is excused from standard carry-on limits.", "Learner used the word 'exempt'.", phase=2),
    Task("Use the word 'expedite'", "Expedite means to accelerate or speed up the progress of an action. Ask if staff can speed up your security screening for a tight connection.", "Learner used the word 'expedite'.", phase=2),
    Task("Use the word 'discrepancy'", "A discrepancy is an illogical disagreement or variance between facts or records. Point out a difference between your reservation confirmation and the monitor.", "Learner used the word 'discrepancy'.", phase=2),
    Task("Ask if quiet zone seating is available", "You want to work in a quiet environment on board. Inquire about quiet zone cabin availability.", "Learner asked if quiet zone seating is available.", phase=2),

    Task("Pay the excess baggage fee with a credit card", "The agent calculated your overweight baggage fee. Hand over your payment card to finalize the charge.", "Learner paid the excess baggage fee with a credit card.", phase=3, reactive=True, scene_hint="The payment terminal screen displays the total balance due for excess baggage."),
    Task("Ask for a payment receipt for baggage fees", "You paid for excess luggage and need proof for expense reporting. Ask the agent for an itemized receipt.", "Learner asked for a payment receipt for baggage fees.", phase=3),
    Task("Receive your printed boarding passes", "The agent is handing over your travel documents. Confirm receipt of your physical boarding passes.", "Learner received their printed boarding passes.", phase=3),
    Task("Confirm your luggage claim check stubs", "The agent attaches barcode stickers to your ticket folder. Verify that you have claim stubs for both checked bags.", "Learner confirmed their luggage claim check stubs.", phase=3),
    Task("Inquire about exact boarding time and gate closing", "You want to avoid missing your flight. Ask what time boarding begins and when the gate doors close.", "Learner inquired about exact boarding time AND gate closing.", phase=3),
    Task("Report a missing checked bag at the arrival baggage desk", "Your luggage did not appear on the carousel after arrival. Report the missing bag and provide your tracking details.", "Learner reported a missing checked bag at the arrival baggage desk.", difficulty="advanced", phase=3, reactive=True, scene_hint="An empty baggage carousel turns silently under dim terminal lighting."),
    Task("Request courier delivery of a delayed luggage piece", "The baggage claims agent confirms your suitcase was delayed on a later flight. Request free home delivery.", "Learner requested courier delivery of a delayed luggage piece.", difficulty="advanced", phase=3, reactive=True),
    Task("Confirm the lounge directions and entry pass details", "You are departing the check-in desk for the lounge. Ask the agent to confirm how to access the entrance.", "Learner confirmed the lounge directions AND entry pass details.", phase=3),
    Task("Verify your updated boarding gate after a schedule adjustment", "The departure gate was modified last minute. Confirm the new gate number with airport staff.", "Learner verified their updated boarding gate after a schedule adjustment.", phase=3, scene_hint="The gate monitor displays a flashing notice showing a gate reassignment."),
    Task("Request a copy of a lost baggage property irregularity report", "You filed a claim for damaged luggage earlier. Request a printed copy of the official property report.", "Learner requested a copy of a lost baggage property irregularity report.", difficulty="advanced", phase=3, reactive=True),
    Task("Ask where to return a borrowed luggage cart", "You are done moving your suitcases to the counter. Inquire where to return the luggage trolley.", "Learner asked where to return a borrowed luggage cart.", phase=3),
    Task("Confirm passport return before departing the counter", "You are wrapping up check-in. Make sure the agent hands back your physical passport and ID.", "Learner confirmed passport return before departing the counter.", phase=3),
    Task("Thank the agent for assistance and say goodbye", "Your check-in process is complete. Express appreciation to the agent and wish them a pleasant day.", "Learner thanked the agent for assistance AND said goodbye.", phase=3),
    Task("Request a tax refund customs validation stamp before departure", "You purchased duty-free items in town and need tax export validation. Ask for the final customs validation stamp on your form.", "Learner requested a tax refund customs validation stamp before departure.", difficulty="advanced", phase=3, reactive=True),
]'''

    # Read original file
    file_path = 'app/scenarios/builtins.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find scenario_1_tasks block start and end
    pattern = r'# Scenario: Job Interview\nscenario_1_tasks = \[\n.*?\n\]'
    match = re.search(pattern, content, flags=re.DOTALL)
    if not match:
        print("Error: Could not find scenario_1_tasks block!")
        sys.exit(1)

    print(f"Matched block lines from character {match.start()} to {match.end()}")
    new_content = content[:match.start()] + tasks_code + content[match.end():]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Successfully replaced scenario_1_tasks!")
