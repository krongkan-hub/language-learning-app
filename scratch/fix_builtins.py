import re
import sys

def update_builtins():
    with open('app/scenarios/builtins.py', 'r') as f:
        content = f.read()

    def replace_task_by_keyword(code, kw, new_task_code):
        pos = code.find(kw)
        if pos == -1:
            print(f"ERROR: Could not find keyword {kw!r}")
            return code, False
        start = code.rfind('Task(', 0, pos)
        if start == -1:
            print(f"ERROR: Could not find Task( start for keyword {kw!r}")
            return code, False
        depth = 0
        end = -1
        for i in range(start, len(code)):
            if code[i] == '(':
                depth += 1
            elif code[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            print(f"ERROR: Could not find closing paren for keyword {kw!r}")
            return code, False

        old_task_code = code[start:end]
        print(f"REPLACING for {kw!r}:\n  OLD: {old_task_code}\n  NEW: {new_task_code}\n")
        code = code[:start] + new_task_code + code[end:]
        return code, True

    def replace_hint_in_task(code, goal_kw, old_hint_kw, new_hint_str):
        pos = code.find(goal_kw)
        if pos == -1:
            print(f"ERROR: Could not find goal kw {goal_kw!r}")
            return code, False
        hint_pos = code.find(old_hint_kw, max(0, pos - 100))
        if hint_pos == -1 or hint_pos > pos + 400:
            print(f"ERROR: Could not find hint kw {old_hint_kw!r} near {goal_kw!r}")
            return code, False
        # Find closing quote of the hint string
        # Since hints are quoted strings e.g. "..." or '...', locate the start quote and end quote
        quote_char = code[hint_pos - 1]
        if quote_char not in ('"', "'"):
            # find quote_char before hint_pos
            quote_start = code.rfind('"', pos, hint_pos)
            if quote_start == -1:
                quote_start = code.rfind("'", pos, hint_pos)
            quote_char = code[quote_start]
        else:
            quote_start = hint_pos - 1

        # find quote_end after hint_pos
        quote_end = code.find(quote_char, hint_pos + len(old_hint_kw))
        if quote_end == -1:
            print(f"ERROR: Could not find end quote for hint {old_hint_kw!r}")
            return code, False

        old_hint_full = code[quote_start + 1:quote_end]
        code = code[:quote_start + 1] + new_hint_str + code[quote_end:]
        print(f"REPLACED hint for {goal_kw!r}:\n  OLD: {old_hint_full!r}\n  NEW: {new_hint_str!r}\n")
        return code, True

    task_fixes = [
        # GROUP A - Scenario 2
        # Item 1
        ("Report a missing checked bag at the arrival baggage desk",
         'Task("Accept an upgraded seating assignment offered due to flight overbooking", "The agent explains the economy cabin is overbooked and offers a complimentary seat upgrade. Accept the offer.", "Learner accepted an upgraded seating assignment offered due to overbooking.", difficulty="advanced", phase=3, reactive=True)'),
        # Item 2
        ("Request courier delivery of a delayed luggage piece",
         'Task("Confirm baggage re-check instructions when the agent mentions an international layover", "The agent explains you must collect and re-check bags during transit. Confirm the luggage transfer steps.", "Learner confirmed baggage re-check instructions for an international layover.", difficulty="advanced", phase=3, reactive=True)'),
        # Item 3
        ("Request a copy of a lost baggage property irregularity report",
         'Task("Request a priority security lane pass after the agent mentions a tight departure window", "The agent points out your flight boards very soon. Ask for an expedited fast-track security voucher.", "Learner requested a priority security lane pass for a tight departure window.", difficulty="advanced", phase=3, reactive=True)'),
        # Item 4
        ("Request a tax refund customs validation stamp before departure",
         'Task("Agree to gate-check your carry-on roller bag when the agent warns of full overhead bins", "The agent warns overhead storage is full on the aircraft. Agree to gate-check your carry-on bag.", "Learner agreed to gate-check carry-on luggage due to limited overhead space.", difficulty="advanced", phase=3, reactive=True)'),

        # Item 5 (Tasks 20 and 42 in Sc2 -> add reactive=True)
        ("Accept an offered seat change to a window seat",
         'Task("Accept an offered seat change to a window seat", "The agent offers to switch your seat assignment. Confirm that you accept the window seat.", "Learner accepted an offered seat change to a window seat.", phase=2, reactive=True)'),
        ("Negotiate a seat reassignment away from a broken recline mechanism",
         'Task("Negotiate a seat reassignment away from a broken recline mechanism", "The agent mentions your assigned seat does not recline. Explain your long journey and request a different seat.", "Learner negotiated a seat reassignment away from a broken recline mechanism.", difficulty="advanced", phase=2, reactive=True)'),

        # GROUP B
        # Item 6: Sc42 Ski Resort DIN setting
        ("Request double checking binding DIN release setting for safety",
         'Task("Request checking that ski bindings are set correctly for your weight", "Ask the technician to verify that your safety bindings are properly adjusted for your weight.", "Learner requested checking that ski bindings are set correctly for their weight.", difficulty="advanced", phase=2)'),

        # Item 7: Sc50 Auto Repair Mechanic turbocharger wastegate
        ("turbocharger wastegate actuator",
         'Task("Ask if a loss of acceleration power indicates a costly repair", "Tell the mechanic your car lacks power when accelerating uphill and ask for an estimated repair cost.", "Learner asked if a loss of acceleration power indicates a costly repair.", difficulty="advanced", phase=3, reactive=True)'),

        # Item 8: Sc74 Tech Startup vesting
        ("Negotiate accelerated vesting upon acquisition event",
         'Task("Negotiate keeping your full equity share if the company is sold", "Propose that all your unvested shares convert immediately if the company is acquired by another firm.", "Learner negotiated keeping full equity share if the company is sold.", difficulty="advanced", phase=2, reactive=True)'),

        # Item 9: Sc77 Customs Import Duties
        ("Inquire about harmonized tariff code classification for your items",
         'Task("Inquire how your imported goods are categorized for tax duties", "Ask the officer which tax category applies to your imported products and why.", "Learner inquired how imported goods are categorized for tax duties.", phase=1)'),
        ("Request waiver of storage demurrage fees caused by customs inspection delay",
         'Task("Request a waiver of storage fees caused by inspection delays", "Ask the officer to waive extra storage fees since the delay was caused by customs inspection backlogs.", "Learner requested a waiver of storage fees caused by inspection delays.", difficulty="advanced", phase=2, reactive=True)'),

        # Extra cleanup for harmonized tariff / demurrage catalog-wide
        ("Discuss international harmonized tariff code classification for shipped electronics",
         'Task("Discuss international customs tariff classification for shipped electronics", "Inquire about entering six-digit customs codes on declarations.", "Learner discussed international customs tariff classification.", difficulty="advanced", phase=2)'),
        ("Confirm port storage facility free time limits before demurrage accrues",
         'Task("Confirm port storage facility free time limits before extra storage fees accrue", "Verify free storage window before daily holding fees begin.", "Learner confirmed port storage free window before extra storage fees start.", phase=3)'),

        # GROUP D & GROUP B VOCABULARY SUBSTITUTIONS
        # Sc39: emulsifier -> expiry
        ("emulsifier",
         'Task("Use the word \'expiry\'", "Expiry refers to the date after which a product is no longer fresh or safe to consume. Inquire about the expiry date of pre-packaged ice cream tubs.", "Learner used the word \'expiry\'.", difficulty="advanced", phase=2)'),

        # Sc9: commutation -> timetable
        ("commutation",
         'Task("Use the word \'timetable\'", "A timetable is a schedule showing times when public transport arrives and departs. Ask for a printed train timetable.", "Learner used the word \'timetable\'.", difficulty="advanced", phase=2)'),

        # Sc35: matriculation -> eligibility
        ("matriculation",
         'Task("Use the word \'eligibility\'", "Eligibility refers to meeting the necessary requirements or qualifications for admission. Inquire about scholarship eligibility criteria.", "Learner used the word \'eligibility\'.", difficulty="advanced", phase=1)'),

        # Sc67: substrate -> moisture
        ("mineral substrate is suitable for seedlings",
         'Task("Use the word \'moisture\'", "Moisture refers to the presence of liquid or water content in soil or air. Ask how to measure soil moisture levels.", "Learner used the word \'moisture\'.", phase=2)'),

        # Sc50: actuator -> estimate
        ("blend door actuator",
         'Task("Use the word \'estimate\'", "An estimate is an approximate calculation of the cost or time required for a service. Ask the mechanic for a written repair estimate.", "Learner used the word \'estimate\'.", difficulty="advanced", phase=1)'),

        # Sc50: bushing -> vibration
        ("control arm bushings",
         'Task("Use the word \'vibration\'", "Vibration refers to rapid back-and-forth movement or shaking in a vehicle. Mention that you notice a heavy steering vibration at high speeds.", "Learner used the word \'vibration\'.", difficulty="advanced", phase=2)'),

        # Sc76: deposit (duplicate) -> withholding
        ("Deposit means security money held by landlord",
         'Task("Use the word \'withholding\'", "Withholding refers to deducting or holding back funds from a payment. Ask about security deposit withholding rules upon move-out.", "Learner used the word \'withholding\'.", phase=2)'),

        # Sc76: lease (duplicate) -> provision
        ("Lease means the formal rental agreement",
         'Task("Use the word \'provision\'", "A provision is a condition or requirement stated within a legal agreement. Cite the maintenance provision in your rental contract.", "Learner used the word \'provision\'.", difficulty="advanced", phase=1)'),

        # Sc73: adjuster -> settlement
        ("insurance representative who assesses damage value",
         'Task("Use the word \'settlement\'", "A settlement is an official agreement that resolves a financial claim. Ask about the final settlement offer for your property claim.", "Learner used the word \'settlement\'.", phase=2)'),

        # Sc5: airport -> vicinity
        ("where planes take off and land",
         'Task("Use the word \'vicinity\'", "Vicinity refers to the area or neighborhood surrounding a location. Ask about convenient dining options in the hotel\'s immediate vicinity.", "Learner used the word \'vicinity\'.", phase=2)'),

        # Sc68: bartender -> hospitality
        ("person who serves drinks at a bar",
         'Task("Use the word \'hospitality\'", "Hospitality refers to the friendly and generous reception and entertainment of guests. Inquire about the premium hospitality services available in the lounge.", "Learner used the word \'hospitality\'.", difficulty="advanced", phase=2)'),

        # Sc29: concierge -> landmark
        ("staff assistant for guest services",
         'Task("Use the word \'landmark\'", "A landmark is a prominent or well-known feature of a landscape or city. Ask for directions to historical landmarks in the city center.", "Learner used the word \'landmark\'.", phase=2)'),

        # Sc80: coordinator -> oversight
        ("event manager overseeing execution",
         'Task("Use the word \'oversight\'", "Oversight refers to the management and supervision of execution. Ask about vendor management and day-of oversight responsibilities.", "Learner used the word \'oversight\'.", phase=2)'),

        # Sc20: curator -> display
        ("manager of a museum collection",
         'Task("Use the word \'display\'", "A display is a public showing of objects or artwork. Ask about the seasonal artifact display in the main gallery.", "Learner used the word \'display\'.", difficulty="advanced", phase=2)'),

        # Sc75: officer -> violation
        ("police personnel",
         'Task("Use the word \'violation\'", "A violation is an act of breaking a law or traffic regulation. Ask for clarification regarding the alleged speed violation.", "Learner used the word \'violation\'.", difficulty="advanced", phase=2)'),

        # Sc71: paramedic -> observation
        ("emergency medical responder",
         'Task("Use the word \'observation\'", "Observation refers to monitoring a patient\'s medical condition over time. Ask if overnight observation is required.", "Learner used the word \'observation\'.", difficulty="advanced", phase=2)'),

        # Sc4: pharmacy -> medication
        ("shop where medicines are sold",
         'Task("Use the word \'medication\'", "Medication refers to a substance used for medical treatment. Confirm that your prescribed medication is ready for pickup.", "Learner used the word \'medication\'.", phase=2)'),

        # Sc10: practitioner -> physician
        ("medical doctor or nurse",
         'Task("Use the word \'physician\'", "Physician refers to a qualified medical doctor. Inquire if an attending physician is available for a consultation.", "Learner used the word \'physician\'.", phase=2)'),

        # Sc35: registrar -> credential
        ("university official maintaining academic records",
         'Task("Use the word \'credential\'", "A credential is an official document attesting to academic qualification. Inquire about submitting foreign degree credentials.", "Learner used the word \'credential\'.", phase=2)'),

        # Sc8: seamstress -> tailoring
        ("alters or mends clothes",
         'Task("Use the word \'tailoring\'", "Tailoring refers to adjusting clothing for a custom fit. Inquire about complimentary tailoring services for new trousers.", "Learner used the word \'tailoring\'.", phase=2)'),

        # Sc65: supplier -> durability
        ("person or organization that provides goods",
         'Task("Use the word \'durability\'", "Durability refers to the ability to withstand wear, pressure, or damage. Inquire about the durability of the replacement shoe soles.", "Learner used the word \'durability\'.", difficulty="advanced", phase=2)'),

        # Sc76: tenant -> clause
        ("person who occupies land or property",
         'Task("Use the word \'clause\'", "A clause is a specific section or provision within a contract. Cite the repair timeline clause in your rental agreement.", "Learner used the word \'clause\'.", phase=2)'),

        # Sc16: trainer -> regimen
        ("fitness coach",
         'Task("Use the word \'regimen\'", "A regimen is a prescribed course of exercise or diet. Ask for assistance designing a personalized fitness regimen.", "Learner used the word \'regimen\'.", phase=2)')
    ]

    success_count = 0
    for kw, new_code in task_fixes:
        content, ok = replace_task_by_keyword(content, kw, new_code)
        if ok:
            success_count += 1
        else:
            print(f"FAILED TO REPLACE TASK FOR KEYWORD: {kw!r}")

    # GROUP C Hint Replacements
    hint_fixes = [
        # Item 10: Sc27
        ("Request pressing of a jacket collar that creased during transport",
         "lapel",
         "Ask to re-press a creased suit jacket collar and front edge."),
        # Item 11: Sc46 (4 hints)
        ("Inquire about wedding tuxedos custom tailoring options",
         "satin lapels",
         "Ask master tailor about tuxedo fabric and collar trim."),
        ("Ask about decorative edge stitching details along the jacket seam",
         "pick stitching",
         "Inquire if hand-sewn decorative edge stitching is included on collar."),
        ("Request tailor adjust shoulder sleeve tightness for greater freedom of movement",
         "armhole",
         "Ask tailor to loosen shoulder seam tightness for ease of movement."),
        ("Ask how the jacket collar and front can be styled",
         "peak lapel",
         "Ask tailor about broad versus slim collar width dimensions."),
        # Item 12: Sc54
        ("Negotiate cabin upgrade discount if private cabins remain unsold before departure",
         "stateroom",
         "Ask agent for last-minute private cabin discount.")
    ]

    hint_success = 0
    for goal_kw, old_hint_kw, new_hint in hint_fixes:
        content, ok = replace_hint_in_task(content, goal_kw, old_hint_kw, new_hint)
        if ok:
            hint_success += 1
        else:
            print(f"FAILED TO REPLACE HINT FOR GOAL KW: {goal_kw!r}")

    print(f"\nSummary:\nTask replacements: {success_count}/{len(task_fixes)}")
    print(f"Hint replacements: {hint_success}/{len(hint_fixes)}")

    with open('app/scenarios/builtins.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    update_builtins()
