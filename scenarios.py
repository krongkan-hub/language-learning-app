from dataclasses import dataclass, field
from typing import List
import random

@dataclass
class Task:
    goal: str
    hint: str
    done_when: str
    difficulty: str = "standard"  # "standard" or "advanced" (C1: negotiation,
                                  # justification, multi-step reasoning)
    # Optional ambient/environmental premise the learner's goal reacts to
    # (loud music, a dirty table, etc.). The actor shares this space, so unlike
    # a learner-initiated ask that needs no grounding, the fact only exists if
    # the actor makes it observably true in its OWN dialogue first — otherwise
    # the learner's complaint comes out of nowhere. Injected into the actor/
    # greeting prompt via build_task_setup_block; never seen by the task judge.
    scene_hint: str = ""
    # Rough conversational stage the task belongs to, used only to order a
    # session so objectives appear when they plausibly could:
    #   1 = opening (arrival/check-in: reservations, ID, spelling a name)
    #   2 = middle (the bulk of requests; the default)
    #   3 = closing (payment, receipts, billing disputes, farewells)
    # A billing dispute at the moment of check-in, or a goodbye up front, reads
    # as broken; phase keeps them in a believable order without hard-gating.
    phase: int = 2
    # True when this task presupposes a prior conversational exchange — an
    # order already placed, a drink received, a prior complaint. The session
    # builder will never place a reactive task as the first task.
    reactive: bool = False

@dataclass
class Scenario:
    name: str
    place: str
    role: str
    speaker: str
    tasks: List[Task]
    # Optional pool of session-level obstacles. One is picked at random per
    # playthrough and injected into the actor prompt for flavour — never used
    # by the task judge. Empty means "no complication this scenario".
    complications: List[str] = field(default_factory=list)

    def get_session_tasks(self, num_tasks=10, advanced_ratio=0.7) -> List[Task]:
        """Returns a session biased toward advanced (C1-style) tasks, with
        standard tasks filling the remainder."""
        advanced = [t for t in self.tasks if t.difficulty == "advanced"]
        standard = [t for t in self.tasks if t.difficulty == "standard"]
        random.shuffle(advanced)
        random.shuffle(standard)

        num_advanced = min(len(advanced), round(num_tasks * advanced_ratio))
        num_standard = min(len(standard), num_tasks - num_advanced)
        session = advanced[:num_advanced] + standard[:num_standard]

        if len(session) < num_tasks:
            leftover = advanced[num_advanced:] + standard[num_standard:]
            session += leftover[:num_tasks - len(session)]

        random.shuffle(session)
        # Stable sort by conversational stage: opening tasks first, closing
        # tasks last, everything else in between. Stability preserves the
        # random order within each phase, so replays still vary.
        session.sort(key=lambda t: t.phase)

        # Guarantee the first phase-2 task is not reactive — reactive tasks
        # presuppose a prior exchange (an order placed, a drink received, etc.)
        # and read as nonsensical at the start of a conversation.
        first_mid = next((i for i, t in enumerate(session) if t.phase == 2), None)
        if first_mid is not None and session[first_mid].reactive:
            swap = next((j for j in range(first_mid + 1, len(session))
                         if session[j].phase == 2 and not session[j].reactive),
                        None)
            if swap is not None:
                session[first_mid], session[swap] = session[swap], session[first_mid]

        return session

# Scenario 1: Coffee Shop
coffee_shop_tasks = [
    Task("Order a regular black coffee", "You want to buy this. Order a black coffee.", "Learner ordered a black coffee."),
    Task("Ask for the price", "You need information. Ask how much it costs.", "Learner asked about the price or total."),
    Task("Ask for a medium size", "You have a specific preference. Specify that you want a medium.", "Learner specified medium size."),
    Task("Ask what the most popular drink is", "You need information. Ask for a recommendation/popular item.", "Learner asked what is popular."),
    Task("Say you want it to go (takeaway)", "You must inform them. Tell them it's for takeout.", "Learner said to go or takeaway."),
    Task("Ask for extra napkins", "You need information. Ask for some napkins.", "Learner asked for napkins."),
    Task("Use the word 'sweet'",
         "Sweet means having the taste of sugar, not bitter. You need information. Ask if the drink is very sweet.", "Learner used the word 'sweet'."),
    Task("Pay with a credit card", "You need to communicate this. Say you'll pay by card.", "Learner mentioned paying with a card.", phase=3),
    Task("Ask where the restroom is", "You need information. Ask for the restroom/toilet.", "Learner asked for the restroom location."),
    Task("Say you changed your mind about the order", "You need to communicate this. Say you want to change your order.", "Learner expressed a change of mind.", reactive=True),
    Task("Ask if they have any vegan pastries", "You need information. Ask about vegan food options.", "Learner asked about vegan items."),
    Task("Ask for a receipt", "You need something. Request your receipt.", "Learner asked for a receipt.", phase=3),
    Task("Order an iced latte", "You want to buy this. Order an iced latte.", "Learner ordered an iced latte."),
    Task("Use the word 'decaf'",
         "Decaf means coffee that has had the caffeine removed. You need information. Ask for decaf.", "Learner used the word 'decaf'."),
    Task("Complain that the coffee is too cold", "You need to communicate this. Say your coffee is cold.", "Learner complained about cold coffee.", reactive=True),
    Task("Ask for the wifi password", "You need information. Ask for the wifi password.", "Learner asked for the wifi password."),
    Task("Ask what time they close", "You need information. Ask about closing time.", "Learner asked what time the shop closes."),
    Task("Order a blueberry muffin", "You want to buy this. Order a muffin.", "Learner ordered a blueberry muffin."),
    Task("Say you have a loyalty card", "This is important context. Mention your loyalty or stamp card.", "Learner mentioned a loyalty card.", phase=3),
    Task("Ask if you can pay with cash", "You need information. Ask to pay in cash.", "Learner asked to pay with cash.", phase=3),
    Task("Use the word 'bitter'",
         "Bitter means having a sharp, not-sweet taste, like dark chocolate or black coffee. You need to communicate this. Say you don't like bitter coffee.", "Learner used the word 'bitter'."),
    Task("Ask for extra sugar", "You need information. Ask for more sugar.", "Learner asked for extra sugar."),
    Task("Ask for skim milk", "You need information. Ask for skim milk.", "Learner requested skim milk."),
    Task("Ask if there are any seasonal drinks", "You need information. Ask about seasonal or special drinks.", "Learner asked about seasonal specials."),
    Task("Say your friend is coming to pay", "You need to communicate this. Say you are waiting for a friend to pay.", "Learner mentioned a friend will pay.", phase=3),
    Task("Ask for a cup holder", "You need information. Ask for a sleeve or cup holder.", "Learner asked for a cup holder or sleeve."),
    Task("Ask if the beans are locally sourced", "You need information. Ask where the coffee beans are from.", "Learner asked about the origin of the beans."),
    Task("Order a hot chocolate", "You want to buy this. Order a hot chocolate.", "Learner ordered a hot chocolate."),
    Task("Say the music is too loud", "You have a delicate request. Politely ask them to turn down the music.", "Learner complained about loud music.",
         scene_hint="music is playing over the shop's speakers, and it's turned up high — upbeat and loud enough to talk over."),
    Task("Ask for a glass of tap water", "You need information. Ask for tap water.", "Learner requested tap water."),
    Task("Use the word 'recommendation'",
         "Recommendation means a suggestion about what is good or worth choosing. You need information. Ask for a recommendation.", "Learner used the word 'recommendation'."),
    Task("Ask if the pastries are fresh today", "You need information. Ask if the food is fresh.", "Learner asked if pastries were baked today."),
    Task("Say you have an allergy to nuts", "This is important context. Mention a nut allergy.", "Learner mentioned a nut allergy."),
    Task("Ask for a larger cup but same amount of coffee", "You need information. Ask for room for milk.", "Learner asked for room for milk/larger cup."),
    Task("Leave a tip", "You need to communicate this. Say you are leaving a tip.", "Learner explicitly mentioned giving a tip.", phase=3),
    Task("Ask how long the wait is", "You need information. Ask about the wait time.", "Learner asked how long the order will take."),
    Task("Ask for a paper straw", "You need information. Ask for a straw.", "Learner asked for a paper straw."),
    Task("Say you accidentally spilled your drink", "You made a mistake. Apologize for spilling.", "Learner mentioned spilling their drink.", reactive=True),
    Task("Ask for a replacement drink", "You need information. Ask for a new drink.", "Learner asked for a replacement.", reactive=True),
    Task("Use the word 'flavor'",
         "Flavor means the specific taste of a food or drink. You need information. Ask about different flavors.", "Learner used the word 'flavor'."),
    Task("Ask if you can sit anywhere", "You need information. Ask about seating.", "Learner asked if seating is open/free."),
    Task("Say the table is dirty", "You noticed a problem. Point out a dirty table.", "Learner mentioned a dirty table.",
         scene_hint="the shop is slammed, and used cups and crumbs are piling up on the tables because no one has had a chance to clear them yet."),
    Task("Order two espressos", "You want to buy this. Order two shots of espresso.", "Learner ordered two espressos."),
    Task("Ask if they sell whole beans", "You need information. Ask to buy coffee bags/beans.", "Learner asked about buying whole beans."),
    Task("Use the word 'caffeine'",
         "Caffeine means the natural stimulant in coffee and tea that makes you feel more awake. You need information. Ask about caffeine levels.", "Learner used the word 'caffeine'."),
    Task("Say you want the drink extra hot", "You need information. Ask for the drink to be very hot.", "Learner asked for an extra hot drink."),
    Task("Ask if they do a student discount", "You need information. Ask about discounts.", "Learner asked about a student discount.", phase=3),
    Task("Say 'keep the change'", "You must inform them. Tell them to keep the change.", "Learner told the cashier to keep the change.", phase=3),
    Task("Ask for a wooden stirrer", "You need information. Ask for a stirrer.", "Learner asked for a stirrer."),
    Task("Say thank you and goodbye", "You need to communicate this. Say goodbye.", "Learner thanked the staff and said goodbye.", phase=3),
    # B2 multi-clause tasks
    Task("Turn down their recommendation and explain why",
         "They've suggested something. Say no politely, and give a real reason.",
         "Learner declined the suggestion AND gave a reason for declining.", "advanced", reactive=True),
    Task("Weigh up two drinks, then pick one",
         "Mention both options, say what makes them different, and commit to one.",
         "Learner referred to two options AND stated a preference with a justification.", "advanced"),
    Task("Point out a problem with your order without being rude",
         "Something isn't right. Raise it politely and say what you'd like done.",
         "Learner raised a problem AND requested or proposed a resolution, using polite or softening language.", "advanced", reactive=True),
    Task("Say you didn't catch that and ask them to repeat",
         "You missed something. Ask them to say it again, and be specific about which part.",
         "Learner signalled they didn't understand AND specified what they need repeated or explained.", "advanced"),
    Task("Explain that you're in a hurry without sounding rude",
         "You have ten minutes. Communicate the pressure and find out what's quickest.",
         "Learner conveyed time pressure AND asked for a faster option or for reassurance about timing.", "advanced"),
    Task("Guess what an unfamiliar item is, then check",
         "You don't know what it is. Say what you think it might be, then ask.",
         "Learner used hedging language such as might, probably, I think, or sounds like AND asked a follow-up question.", "advanced"),
    Task("Ask for the drink to be made differently",
         "You want a change to the standard version. Ask, and say what to do if it isn't possible.",
         "Learner requested a modification AND offered a fallback or asked what is possible.", "advanced", reactive=True),
    Task("Politely disagree with something they said",
         "You see it differently. Say so without being blunt, and back it up.",
         "Learner expressed disagreement using softening language AND supported it with a reason.", "advanced"),
    Task("Keep the small talk going",
         "They've made a casual remark. Answer it and give them something back.",
         "Learner responded to the remark AND added a related comment or question of their own.", "advanced"),
    # C1 tasks: negotiation, escalation, trade-offs
    Task("Negotiate when your order isn't available",
         "The size or drink you want is out of stock. Weigh it against an alternative, and commit to one.",
         "Learner acknowledged the unavailability AND compared it to an alternative AND committed to a substitute with a reason.", "advanced", reactive=True),
    Task("Dispute a billing mistake",
         "You were charged for something you didn't order. Point out exactly what's wrong, and ask for it to be corrected.",
         "Learner identified the specific billing error AND requested a correction, without being accusatory.", "advanced", phase=3),
    Task("Escalate after the first fix wasn't enough",
         "Your first request for a fix wasn't sufficient. Push back and explain why the first offer doesn't solve it.",
         "Learner acknowledged the initial response AND explained why it was insufficient AND asked for a further remedy.", "advanced", reactive=True),
    Task("Persuade them to make an off-menu request",
         "Ask for a modification that isn't standard. Explain exactly what you want and why it matters to you.",
         "Learner requested a specific non-standard modification AND gave a reason for wanting it.", "advanced"),
    Task("Raise a hypothetical about running late",
         "Ask what would happen if you had to leave before your order is ready — held, remade, or refunded?",
         "Learner posed a hypothetical about being unable to wait AND asked what the barista would do about it.", "advanced"),
    Task("Negotiate a loyalty discount",
         "Ask if there's a discount or loyalty perk available, and give a reason you think you qualify.",
         "Learner asked about a discount or perk AND gave a justification for requesting it.", "advanced"),
    Task("Push back diplomatically after tasting your drink",
         "Something you already received doesn't taste right. Say so tactfully, and ask specifically what they can do about it.",
         "Learner raised a specific quality issue with the drink they received AND requested a specific remedy.", "advanced", reactive=True),
    Task("Weigh a health trade-off out loud",
         "You're deciding between two drinks for a specific reason (caffeine, sugar, etc). Explain the trade-off and ask for their opinion.",
         "Learner explained a personal constraint relevant to the choice AND asked for the barista's recommendation based on it.", "advanced"),
    Task("Clarify a mismatched order",
         "What arrived isn't quite what you asked for. Explain the mismatch precisely and propose how to fix it.",
         "Learner pinpointed the specific mismatch between what was ordered and what was received AND proposed a fix.", "advanced", reactive=True),
    Task("Question whether it's worth the price",
         "Ask where the beans/ingredients come from, then follow up connecting that to whether it's worth the price.",
         "Learner asked about the origin or quality of the product AND followed up connecting it to value or price.", "advanced"),
]

# Scenario 2: Pharmacy
pharmacy_tasks = [
    Task("Ask for painkillers", "You need to communicate this. Say you have a headache and need medicine.", "Learner asked for painkillers or headache medicine."),
    Task("Ask about side effects", "You need information. Ask if the medicine makes you sleepy.", "Learner asked about side effects or drowsiness."),
    Task("Use the word 'prescription'",
         "Prescription means a written order from a doctor allowing you to buy a specific medicine. You need to communicate this. Say you have a prescription from a doctor.", "Learner used the word 'prescription'."),
    Task("Ask for a thermometer", "You need information. Ask where the thermometers are.", "Learner asked to buy a thermometer."),
    Task("Say you have a sore throat", "This is important context. Mention your throat hurts.", "Learner mentioned a sore throat."),
    Task("Ask for cough drops", "You need information. Ask for lozenges or cough drops.", "Learner asked for cough drops."),
    Task("Ask how often to take the medicine", "You need information. Ask about the dosage schedule.", "Learner asked how many times a day to take it."),
    Task("Use the word 'allergy'",
         "Allergy means a condition where your body reacts badly to something that's usually harmless to others. You need to communicate this. Say you have an allergy to penicillin.", "Learner used the word 'allergy'."),
    Task("Ask for band-aids/plasters", "You need information. Ask for bandages.", "Learner asked for band-aids or plasters."),
    Task("Ask for eye drops", "You need to communicate this. Say your eyes are dry.", "Learner asked for eye drops."),
    Task("Say you have a fever", "This is important context. Mention you have a high temperature.", "Learner mentioned having a fever."),
    Task("Ask for cold medicine", "You need information. Ask for medicine for a cold.", "Learner asked for cold medicine."),
    Task("Use the word 'symptoms'",
         "Symptoms means the signs that show something is wrong with your health, like a cough or a headache. Describe your symptoms.", "Learner used the word 'symptoms'."),
    Task("Ask if the medicine needs to be taken with food", "You need information. Ask if you should eat before taking it.", "Learner asked if it should be taken with food."),
    Task("Ask for a smaller pack", "You need to communicate this. Say the box is too big.", "Learner asked for a smaller quantity."),
    Task("Ask for generic brand", "You need information. Ask for a cheaper generic version.", "Learner asked for generic medicine."),
    Task("Use the word 'dizzy'",
         "Dizzy means feeling like everything around you is spinning, and you might lose your balance. You need to communicate this. Say you feel dizzy.", "Learner used the word 'dizzy'."),
    Task("Ask for sunscreen", "You need information. Ask for sun protection.", "Learner asked for sunscreen."),
    Task("Ask for insect repellent", "You need information. Ask for bug spray.", "Learner asked for insect repellent."),
    Task("Ask if you need to keep it in the fridge", "You need information. Ask about storage instructions.", "Learner asked if it needs refrigeration."),
    Task("Say you lost your prescription", "You need to clarify the situation. Explain you lost the paper.", "Learner said they lost their prescription."),
    Task("Ask to speak to the pharmacist", "You need something. Request the main pharmacist.", "Learner asked to speak to the pharmacist."),
    Task("Ask for a refill", "You need information. Ask to refill an old prescription.", "Learner asked for a prescription refill."),
    Task("Use the word 'pharmacy'",
         "Pharmacy means a shop where medicines are sold. You want to be sure. Verify you are at the right pharmacy.", "Learner used the word 'pharmacy'."),
    Task("Ask for vitamins", "You need information. Ask for vitamin C.", "Learner asked for vitamins."),
    Task("Ask for a covid test", "You need information. Ask for a rapid test.", "Learner asked for a covid/antigen test."),
    Task("Say your stomach hurts", "This is important context. Mention a stomachache.", "Learner mentioned stomach pain."),
    Task("Ask for antacids", "You need information. Ask for digestion medicine.", "Learner asked for stomach medicine/antacids."),
    Task("Ask what the expiration date is", "You need information. Ask when it expires.", "Learner asked about the expiration date."),
    Task("Use the word 'insurance'",
         "Insurance means a plan you pay into that covers certain costs, like medical bills, when you need them. You need information. Ask if they take your insurance.", "Learner used the word 'insurance'."),
    Task("Say you need it urgently", "This is important context. Mention it is an emergency.", "Learner said they need it right away."),
    Task("Ask for a paper bag", "You need information. Ask for a bag.", "Learner asked for a paper bag."),
    Task("Ask if there is a generic alternative", "You need information. Ask for a generic version.", "Learner asked for a generic version."),
    Task("Say you have a rash", "This is important context. Mention a skin rash.", "Learner mentioned a rash."),
    Task("Ask for ointment", "You need information. Ask for skin cream/ointment.", "Learner asked for ointment."),
    Task("Use the word 'pregnant'",
         "Pregnant means expecting a baby. You need information. Ask if it's safe for pregnant women.", "Learner used the word 'pregnant'."),
    Task("Ask for baby formula", "You need information. Ask where baby formula is.", "Learner asked for baby formula."),
    Task("Ask how long it will take to prepare", "You need information. Ask about wait time.", "Learner asked how long to prepare the prescription."),
    Task("Say you will come back later", "You need to communicate this. Say you'll return in an hour.", "Learner said they will come back.", phase=3),
    Task("Ask for the receipt for insurance", "You need information. Ask for a detailed receipt.", "Learner asked for an insurance receipt.", phase=3),
    Task("Use the word 'dose'",
         "Dose means the specific amount of medicine you should take at one time. You need information. Ask what the correct dose is.", "Learner used the word 'dose'."),
    Task("Ask for liquid medicine instead of pills", "You need to communicate this. Say you can't swallow pills.", "Learner asked for liquid medicine."),
    Task("Say it's for a child", "You have a specific preference. Specify the patient is a child.", "Learner said the medicine is for a child."),
    Task("Ask what age it is suitable for", "You need information. Ask the minimum age.", "Learner asked about age restrictions."),
    Task("Ask for a measuring cup", "You need information. Ask for a cup to measure liquid.", "Learner asked for a measuring cup or spoon."),
    Task("Use the word 'effective'",
         "Effective means actually working, producing the result you want. You need information. Ask how fast it is effective.", "Learner used the word 'effective'."),
    Task("Ask for hand sanitizer", "You need information. Ask for hand gel.", "Learner asked for hand sanitizer."),
    Task("Ask for a medical mask", "You need information. Ask for face masks.", "Learner asked for a mask."),
    Task("Say thank you and leave", "It's time to go. End the conversation politely.", "Learner thanked the pharmacist and left.", phase=3),
    # B2 multi-clause tasks
    Task("Describe how you're feeling, then narrow it down",
         "Start general, then get specific when they ask.",
         "Learner described a general complaint AND added a specific detail such as when it started or what makes it worse.", "advanced"),
    Task("Ask what happens if it doesn't agree with you",
         "Find out what to watch for and what to do about it.",
         "Learner asked about possible effects AND asked what action to take if they occur.", "advanced"),
    Task("Say you've already tried something and it didn't help",
         "Tell them what you tried and what happened, then ask what else there is.",
         "Learner named a previous attempt AND described the outcome AND asked for an alternative.", "advanced"),
    Task("Check the instructions by saying them back",
         "Repeat what they told you in your own words to confirm you've got it.",
         "Learner restated the instructions in their own words AND asked for confirmation.", "advanced", reactive=True),
    Task("Explain a restriction and ask what fits",
         "There's something you can't take. Explain it and ask what would work instead.",
         "Learner stated a constraint AND asked for a suitable alternative.", "advanced"),
    Task("Turn down what they suggest and ask for something else",
         "Decline politely, say why, and ask what else they'd recommend.",
         "Learner declined AND gave a reason AND asked for another option.", "advanced", reactive=True),
    # C1 tasks: negotiation, escalation, trade-offs
    Task("Raise a drug-interaction concern",
         "You're already taking something else. Ask if the new medication is safe to combine with it, and say what you're currently taking.",
         "Learner named what they're currently taking AND asked specifically about interaction risk.", "advanced"),
    Task("Negotiate around an insurance issue",
         "Your insurance doesn't seem to cover this. Explain the issue and ask what your options are.",
         "Learner explained the coverage problem AND asked for alternative options.", "advanced"),
    Task("Push for a second opinion diplomatically",
         "You're not fully convinced by the first recommendation. Say so tactfully and ask for more explanation or an alternative.",
         "Learner expressed polite skepticism about the recommendation AND asked for further explanation or an alternative.", "advanced", reactive=True),
    Task("Explain an urgent substitution need",
         "What you need is out of stock. Explain why you need it urgently and ask for the closest substitute.",
         "Learner explained the urgency AND asked for a specific substitute.", "advanced"),
    Task("Weigh long-term side effects out loud",
         "Ask about long-term risks of a treatment, then reason out loud about whether the benefit is worth it.",
         "Learner asked about long-term effects AND weighed the trade-off aloud AND asked for the pharmacist's opinion.", "advanced"),
    Task("Request documentation for a specific purpose",
         "You need proof of purchase or a note for insurance or work. Explain exactly why, and ask what they can provide.",
         "Learner explained the specific reason documentation is needed AND asked what the pharmacist can provide.", "advanced"),
    Task("Raise a dosage concern for a special circumstance",
         "Explain a circumstance that might affect dosage (age, pregnancy, an existing condition) and ask them to confirm it's safe.",
         "Learner disclosed the relevant circumstance AND asked for confirmation of safety or an adjusted dosage.", "advanced"),
    Task("Contest a mismatch between the label and what you were told",
         "Something on the label seems to contradict what you were told earlier. Point out the discrepancy and ask them to clarify.",
         "Learner identified the specific discrepancy AND asked for clarification.", "advanced", reactive=True),
    Task("Negotiate switching to a cheaper alternative",
         "Ask if there's a generic or cheaper version, and ask how it compares in effectiveness.",
         "Learner asked about a cheaper alternative AND asked how it compares in effectiveness.", "advanced"),
    Task("Explain a past bad reaction and ask for reassurance",
         "You had a bad experience with something similar before. Explain what happened and ask if this one is different.",
         "Learner described a past negative reaction AND asked whether the current option carries the same risk.", "advanced"),
]

# Scenario 3: Hotel Check-in
hotel_tasks = [
    Task("Say you have a reservation", "You need to communicate this. Say you want to check in.", "Learner stated they have a reservation.", phase=1),
    Task("Spell your last name", "They need precise details. Spell out your name.", "Learner spelled their name.", phase=1),
    Task("Provide your passport", "You need to communicate this. Say here is my passport.", "Learner offered their ID or passport.", phase=1),
    Task("Ask for a quiet room", "You need information. Ask for a room away from the elevator.", "Learner asked for a quiet room."),
    Task("Use the word 'upgrade'",
         "Upgrade means a change to something better than what you originally booked, like a nicer room. You need information. Ask if a room upgrade is possible.", "Learner used the word 'upgrade'."),
    Task("Ask what time breakfast is", "You need information. Ask about breakfast hours.", "Learner asked about breakfast times."),
    Task("Ask where the breakfast room is", "You need information. Ask for directions to breakfast.", "Learner asked where breakfast is served."),
    Task("Ask for the wifi password", "You need information. Ask for internet access.", "Learner asked for the wifi password."),
    Task("Ask what time checkout is", "You need information. Ask about checkout time.", "Learner asked when they must check out."),
    Task("Request a late checkout", "You need information. Ask to leave at 1 PM.", "Learner requested a late checkout."),
    Task("Use the word 'deposit'",
         "Deposit means an amount of money paid in advance as a guarantee, which may be returned later. You need information. Ask about the security deposit.", "Learner used the word 'deposit'."),
    Task("Say the AC in your room is broken", "You are not satisfied. Complain about the air conditioning.", "Learner mentioned broken AC.", reactive=True),
    Task("Ask for a different room", "You need something. Request to change rooms.", "Learner asked for a room change.", reactive=True),
    Task("Ask for an extra key card", "You need information. Ask for another room key.", "Learner asked for an extra key."),
    Task("Ask for a wake-up call", "You need something. Request a wake-up call for 7 AM.", "Learner requested a wake-up call."),
    Task("Use the word 'luggage'",
         "Luggage means your bags and suitcases. You need information. Ask if you can leave your bags.", "Learner used the word 'luggage'."),
    Task("Ask for extra towels", "You need something. Request more towels.", "Learner asked for extra towels."),
    Task("Ask where the gym is", "You need information. Ask for the fitness center.", "Learner asked for the gym."),
    Task("Ask if the pool is heated", "You need information. Ask about the swimming pool.", "Learner asked if the pool is heated."),
    Task("Use the word 'included'",
         "Included means already part of the price, with nothing extra to pay for it. You need information. Ask if breakfast is included.", "Learner used the word 'included'."),
    Task("Ask for a city map", "You need information. Ask if they have a map.", "Learner asked for a map."),
    Task("Ask for a restaurant recommendation", "You need information. Ask for a good local place to eat.", "Learner asked for a restaurant recommendation."),
    Task("Ask them to book a taxi", "You need something. Request a taxi for tomorrow.", "Learner asked the hotel to book a taxi."),
    Task("Use the word 'airport'",
         "Airport means the place where planes take off and land. You need information. Ask how far the airport is.", "Learner used the word 'airport'."),
    Task("Say you lost your room key", "Report a lost key.", "Learner said they lost their key.", reactive=True),
    Task("Ask for an adapter", "You need information. Ask for a power adapter.", "Learner asked for a plug adapter."),
    Task("Say the room is too noisy", "You are not satisfied. Complain about noise.", "Learner complained about noise.", reactive=True),
    Task("Ask for room service", "You need information. Ask how to order food to the room.", "Learner asked about room service."),
    Task("Use the word 'housekeeping'",
         "Housekeeping means the hotel staff and service that cleans the rooms. You need information. Ask for housekeeping to clean the room.", "Learner used the word 'housekeeping'.", reactive=True),
    Task("Ask if there is a laundry service", "You need information. Ask about washing clothes.", "Learner asked about laundry service."),
    Task("Say you didn't take anything from the minibar", "There is a misunderstanding. Deny minibar charges.", "Learner said they didn't use the minibar.", phase=3),
    Task("Ask for an iron", "You need information. Ask for an ironing board.", "Learner asked for an iron."),
    Task("Use the word 'blanket'",
         "Blanket means a thick piece of cloth used to keep warm in bed. You need information. Ask for an extra blanket.", "Learner used the word 'blanket'."),
    Task("Ask if tap water is safe to drink", "You need information. Ask about drinking water.", "Learner asked if tap water is safe."),
    Task("Say your TV isn't working", "Report a broken TV.", "Learner reported the TV is broken.", reactive=True),
    Task("Ask to speak to the manager", "You need something. Request the manager.", "Learner asked for the manager."),
    Task("Ask for the nearest subway station", "You need information. Ask for transport directions.", "Learner asked for the subway/train station."),
    Task("Use the word 'receipt'",
         "Receipt means a piece of paper that proves you paid for something. You need information. Ask for a final receipt.", "Learner used the word 'receipt'.", phase=3),
    Task("Ask if you can pay with two different cards", "You have a payment preference. Split the payment.", "Learner asked to split payment on cards.", phase=3),
    Task("Say you enjoyed your stay", "You want to show appreciation. Give a compliment.", "Learner said they had a good stay.", phase=3),
    Task("Ask for a double bed instead of two singles", "You need something. Request a different bed type.", "Learner requested a double/king bed."),
    Task("Use the word 'view'",
         "View means what you can see from a window. You need information. Ask for a room with a nice view.", "Learner used the word 'view'."),
    Task("Say you are checking out early", "This is important context. Mention an early departure.", "Learner mentioned leaving early.", phase=3),
    Task("Ask if there is a shuttle bus", "You need information. Ask about the airport shuttle.", "Learner asked about a shuttle bus."),
    Task("Say the bathroom has no soap", "You are not satisfied. Complain about missing amenities.", "Learner mentioned missing soap.", reactive=True),
    Task("Ask for a smoking area", "You need information. Ask where you can smoke.", "Learner asked for a smoking area."),
    Task("Ask if pets are allowed", "You need information. Ask about bringing a dog.", "Learner asked about pet policy."),
    Task("Use the word 'confirm'",
         "Confirm means to say definitely that something is correct or will happen. You need information. Ask them to confirm your departure date.", "Learner used the word 'confirm'."),
    Task("Thank the receptionist", "You need to communicate this. Say thanks and bye.", "Learner thanked the receptionist.", phase=3),
    # B2 multi-clause tasks
    Task("Report a problem with the room and say what you'd like done",
         "Describe the issue clearly, then make a specific request.",
         "Learner described a problem AND made a specific request about how to resolve it.", "advanced", reactive=True),
    Task("Ask to check out later and give a reason",
         "You need extra time. Explain why and ask whether it's possible.",
         "Learner requested a later checkout AND gave a reason for needing it.", "advanced"),
    Task("Compare the two rooms they offer and choose",
         "Ask about the difference, weigh it up out loud, then decide.",
         "Learner referred to both options AND chose one with a justification.", "advanced"),
    Task("Ask for directions, then repeat them back",
         "Get the directions, then confirm you've understood by saying them again.",
         "Learner asked for directions AND restated them to confirm.", "advanced"),
    Task("Raise a discrepancy with your booking calmly",
         "Something doesn't match what you booked. Point it out politely and ask how to sort it.",
         "Learner identified a discrepancy AND asked how it can be resolved, without accusatory language.", "advanced"),
    Task("Decline the upgrade they're offering",
         "Say no to the upsell, politely, with a reason.",
         "Learner declined the offer AND gave a reason.", "advanced"),
    # C1 tasks: negotiation, escalation, trade-offs
    Task("Negotiate an early check-in with a fallback",
         "You arrived early and your room isn't ready. Explain why it matters, and negotiate an alternative like luggage storage.",
         "Learner explained why early check-in matters to them AND negotiated a concrete alternative.", "advanced"),
    Task("Dispute a billing discrepancy with specifics",
         "The final bill doesn't match what you were quoted. Point out exactly which charge is wrong and ask for it to be corrected.",
         "Learner identified the specific incorrect charge AND asked for a correction or explanation.", "advanced", phase=3),
    Task("Escalate after the first fix wasn't sufficient",
         "The first solution they offered doesn't fully solve your problem. Explain why, and ask for something more.",
         "Learner explained why the initial resolution was insufficient AND requested a further remedy.", "advanced", reactive=True),
    Task("Negotiate a special room request with a fallback",
         "You need something specific (quiet room, high floor) for a real reason. Explain why, and ask what to do if it's not available.",
         "Learner explained the reason for the request AND asked for a fallback option if unavailable.", "advanced"),
    Task("Demand a concrete resolution to a noise complaint",
         "It was too loud to sleep. Describe the problem specifically and ask for both an apology and a concrete fix.",
         "Learner described the noise problem specifically AND requested a concrete resolution.", "advanced", reactive=True),
    Task("Push back on being charged for something unused",
         "You're being billed for a service or amenity you never used. Point it out and ask for it to be removed.",
         "Learner identified the specific unused charge AND requested its removal.", "advanced", phase=3),
    Task("Reason through a cancellation policy hypothetically",
         "Ask what happens if you need to leave a day early, and reason out loud about whether it's worth it given any fee.",
         "Learner asked about the cancellation or early-departure policy AND reasoned about whether it's worth it given the cost.", "advanced", phase=3),
    Task("Negotiate luggage storage around an inconvenient schedule",
         "Your flight is much later than checkout. Explain the gap and negotiate a solution for your bags and your time.",
         "Learner explained the scheduling gap AND negotiated a specific solution.", "advanced"),
    Task("Contest a mismatch with your original booking",
         "What you're being offered doesn't match your original booking confirmation. Point out the exact mismatch and ask for it to be honored.",
         "Learner identified the specific mismatch with the original booking AND asked for it to be honored or corrected.", "advanced", reactive=True),
    Task("Compare a same-tier alternative and decide",
         "Your exact room type isn't available. Ask what's comparable, weigh it against your original request, and decide.",
         "Learner asked for a comparable alternative AND compared it against the original request AND made a decision.", "advanced", reactive=True),
]


SCENARIOS = [
    Scenario(
        name="Coffee Shop",
        place="A busy local coffee shop",
        role="You are a friendly but busy barista.",
        speaker="Barista",
        tasks=coffee_shop_tasks,
        complications=[
            "you're completely out of oat milk today",
            "the espresso machine is broken, so no espresso-based drinks can be made",
            "there's an order mix-up and the customer's number matches someone else's order",
            "you're badly short-staffed, so every order has a long wait",
            "the card reader is down, so it's cash-only right now",
        ]
    ),
    Scenario(
        name="Pharmacy",
        place="A neighborhood pharmacy",
        role="You are a knowledgeable and helpful pharmacist.",
        speaker="Pharmacist",
        tasks=pharmacy_tasks,
        complications=[
            "the brand-name medicine is out of stock and only a generic substitute is available",
            "the computer system is down, so prescriptions can't be looked up electronically",
            "there's a national shortage of a common medicine the customer may want",
            "anything needing a pharmacist's final sign-off has a wait because you're the only one on shift",
        ]
    ),
    Scenario(
        name="Hotel Check-in",
        place="The reception desk of a 4-star hotel",
        role="You are a professional hotel receptionist.",
        speaker="Receptionist",
        tasks=hotel_tasks,
        complications=[
            "the room they booked isn't ready yet because housekeeping is running late",
            "the hotel is overbooked, so their exact room type may not be available",
            "the elevator is out of service, so upper floors are only reachable by stairs",
            "there's a citywide event tonight, so the area is noisy and the hotel is full",
        ]
    ),
]
