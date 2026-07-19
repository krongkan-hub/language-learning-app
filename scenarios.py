from dataclasses import dataclass
from typing import List
import random

@dataclass
class Task:
    goal: str
    hint: str
    done_when: str

@dataclass
class Scenario:
    name: str
    place: str
    role: str
    tasks: List[Task]

    def get_session_tasks(self, num_tasks=10) -> List[Task]:
        """Returns a random selection of tasks for a varied session."""
        pool = list(self.tasks)
        random.shuffle(pool)
        return pool[:num_tasks]

# Scenario 1: Coffee Shop
coffee_shop_tasks = [
    Task("Order a regular black coffee", "You want to buy this. Order a black coffee.", "Learner ordered a black coffee."),
    Task("Ask for the price", "You need information. Ask how much it costs.", "Learner asked about the price or total."),
    Task("Ask for a medium size", "You have a specific preference. Specify that you want a medium.", "Learner specified medium size."),
    Task("Ask what the most popular drink is", "You need information. Ask for a recommendation/popular item.", "Learner asked what is popular."),
    Task("Say you want it to go (takeaway)", "You must inform them. Tell them it's for takeout.", "Learner said to go or takeaway."),
    Task("Ask for extra napkins", "You need information. Ask for some napkins.", "Learner asked for napkins."),
    Task("Use the word 'sweet'", "You need information. Ask if the drink is very sweet.", "Learner used the word 'sweet'."),
    Task("Pay with a credit card", "You need to communicate this. Say you'll pay by card.", "Learner mentioned paying with a card."),
    Task("Ask where the restroom is", "You need information. Ask for the restroom/toilet.", "Learner asked for the restroom location."),
    Task("Say you changed your mind about the order", "You need to communicate this. Say you want to change your order.", "Learner expressed a change of mind."),
    # (Generating the rest up to 50 for Coffee Shop...)
    Task("Ask if they have any vegan pastries", "You need information. Ask about vegan food options.", "Learner asked about vegan items."),
    Task("Ask for a receipt", "You need something. Request your receipt.", "Learner asked for a receipt."),
    Task("Order an iced latte", "You want to buy this. Order an iced latte.", "Learner ordered an iced latte."),
    Task("Use the word 'decaf'", "You need information. Ask for decaf.", "Learner used the word 'decaf'."),
    Task("Complain that the coffee is too cold", "You need to communicate this. Say your coffee is cold.", "Learner complained about cold coffee."),
    Task("Ask for the wifi password", "You need information. Ask for the wifi password.", "Learner asked for the wifi password."),
    Task("Ask what time they close", "You need information. Ask about closing time.", "Learner asked what time the shop closes."),
    Task("Order a blueberry muffin", "You want to buy this. Order a muffin.", "Learner ordered a blueberry muffin."),
    Task("Say you have a loyalty card", "This is important context. Mention your loyalty or stamp card.", "Learner mentioned a loyalty card."),
    Task("Ask if you can pay with cash", "You need information. Ask to pay in cash.", "Learner asked to pay with cash."),
    Task("Use the word 'bitter'", "You need to communicate this. Say you don't like bitter coffee.", "Learner used the word 'bitter'."),
    Task("Ask for extra sugar", "You need information. Ask for more sugar.", "Learner asked for extra sugar."),
    Task("Ask for skim milk", "You need information. Ask for skim milk.", "Learner requested skim milk."),
    Task("Ask if there are any seasonal drinks", "You need information. Ask about seasonal or special drinks.", "Learner asked about seasonal specials."),
    Task("Say your friend is coming to pay", "You need to communicate this. Say you are waiting for a friend to pay.", "Learner mentioned a friend will pay."),
    Task("Ask for a cup holder", "You need information. Ask for a sleeve or cup holder.", "Learner asked for a cup holder or sleeve."),
    Task("Ask if the beans are locally sourced", "You need information. Ask where the coffee beans are from.", "Learner asked about the origin of the beans."),
    Task("Order a hot chocolate", "You want to buy this. Order a hot chocolate.", "Learner ordered a hot chocolate."),
    Task("Say the music is too loud", "You have a delicate request. Politely ask them to turn down the music.", "Learner complained about loud music."),
    Task("Ask for a glass of tap water", "You need information. Ask for tap water.", "Learner requested tap water."),
    Task("Use the word 'recommendation'", "You need information. Ask for a recommendation.", "Learner used the word 'recommendation'."),
    Task("Ask if the pastries are fresh today", "You need information. Ask if the food is fresh.", "Learner asked if pastries were baked today."),
    Task("Say you have an allergy to nuts", "This is important context. Mention a nut allergy.", "Learner mentioned a nut allergy."),
    Task("Ask for a larger cup but same amount of coffee", "You need information. Ask for room for milk.", "Learner asked for room for milk/larger cup."),
    Task("Leave a tip", "You need to communicate this. Say you are leaving a tip.", "Learner explicitly mentioned giving a tip."),
    Task("Ask how long the wait is", "You need information. Ask about the wait time.", "Learner asked how long the order will take."),
    Task("Ask for a paper straw", "You need information. Ask for a straw.", "Learner asked for a paper straw."),
    Task("Say you accidentally spilled your drink", "You made a mistake. Apologize for spilling.", "Learner mentioned spilling their drink."),
    Task("Ask for a replacement drink", "You need information. Ask for a new drink.", "Learner asked for a replacement."),
    Task("Use the word 'flavor'", "You need information. Ask about different flavors.", "Learner used the word 'flavor'."),
    Task("Ask if you can sit anywhere", "You need information. Ask about seating.", "Learner asked if seating is open/free."),
    Task("Say the table is dirty", "You noticed a problem. Point out a dirty table.", "Learner mentioned a dirty table."),
    Task("Order two espressos", "You want to buy this. Order two shots of espresso.", "Learner ordered two espressos."),
    Task("Ask if they sell whole beans", "You need information. Ask to buy coffee bags/beans.", "Learner asked about buying whole beans."),
    Task("Use the word 'caffeine'", "You need information. Ask about caffeine levels.", "Learner used the word 'caffeine'."),
    Task("Say you want the drink extra hot", "You need information. Ask for the drink to be very hot.", "Learner asked for an extra hot drink."),
    Task("Ask if they do a student discount", "You need information. Ask about discounts.", "Learner asked about a student discount."),
    Task("Say 'keep the change'", "You must inform them. Tell them to keep the change.", "Learner told the cashier to keep the change."),
    Task("Ask for a wooden stirrer", "You need information. Ask for a stirrer.", "Learner asked for a stirrer."),
    Task("Say thank you and goodbye", "You need to communicate this. Say goodbye.", "Learner thanked the staff and said goodbye.")
]

# Scenario 2: Pharmacy
pharmacy_tasks = [
    Task("Ask for painkillers", "You need to communicate this. Say you have a headache and need medicine.", "Learner asked for painkillers or headache medicine."),
    Task("Ask about side effects", "You need information. Ask if the medicine makes you sleepy.", "Learner asked about side effects or drowsiness."),
    Task("Use the word 'prescription'", "You need to communicate this. Say you have a prescription from a doctor.", "Learner used the word 'prescription'."),
    Task("Ask for a thermometer", "You need information. Ask where the thermometers are.", "Learner asked to buy a thermometer."),
    Task("Say you have a sore throat", "This is important context. Mention your throat hurts.", "Learner mentioned a sore throat."),
    Task("Ask for cough drops", "You need information. Ask for lozenges or cough drops.", "Learner asked for cough drops."),
    Task("Ask how often to take the medicine", "You need information. Ask about the dosage schedule.", "Learner asked how many times a day to take it."),
    Task("Use the word 'allergy'", "You need to communicate this. Say you have an allergy to penicillin.", "Learner used the word 'allergy'."),
    Task("Ask for band-aids/plasters", "You need information. Ask for bandages.", "Learner asked for band-aids or plasters."),
    Task("Ask for eye drops", "You need to communicate this. Say your eyes are dry.", "Learner asked for eye drops."),
    Task("Say you have a fever", "This is important context. Mention you have a high temperature.", "Learner mentioned having a fever."),
    Task("Ask for cold medicine", "You need information. Ask for medicine for a cold.", "Learner asked for cold medicine."),
    Task("Use the word 'symptoms'", "Describe your symptoms.", "Learner used the word 'symptoms'."),
    Task("Ask if the medicine needs to be taken with food", "You need information. Ask if you should eat before taking it.", "Learner asked if it should be taken with food."),
    Task("Ask for a smaller pack", "You need to communicate this. Say the box is too big.", "Learner asked for a smaller quantity."),
    Task("Ask for generic brand", "You need information. Ask for a cheaper generic version.", "Learner asked for generic medicine."),
    Task("Use the word 'dizzy'", "You need to communicate this. Say you feel dizzy.", "Learner used the word 'dizzy'."),
    Task("Ask for sunscreen", "You need information. Ask for sun protection.", "Learner asked for sunscreen."),
    Task("Ask for insect repellent", "You need information. Ask for bug spray.", "Learner asked for insect repellent."),
    Task("Ask if you need to keep it in the fridge", "You need information. Ask about storage instructions.", "Learner asked if it needs refrigeration."),
    Task("Say you lost your prescription", "You need to clarify the situation. Explain you lost the paper.", "Learner said they lost their prescription."),
    Task("Ask to speak to the pharmacist", "You need something. Request the main pharmacist.", "Learner asked to speak to the pharmacist."),
    Task("Ask for a refill", "You need information. Ask to refill an old prescription.", "Learner asked for a prescription refill."),
    Task("Use the word 'pharmacy'", "You want to be sure. Verify you are at the right pharmacy.", "Learner used the word 'pharmacy'."),
    Task("Ask for vitamins", "You need information. Ask for vitamin C.", "Learner asked for vitamins."),
    Task("Ask for a covid test", "You need information. Ask for a rapid test.", "Learner asked for a covid/antigen test."),
    Task("Say your stomach hurts", "This is important context. Mention a stomachache.", "Learner mentioned stomach pain."),
    Task("Ask for antacids", "You need information. Ask for digestion medicine.", "Learner asked for stomach medicine/antacids."),
    Task("Ask what the expiration date is", "You need information. Ask when it expires.", "Learner asked about the expiration date."),
    Task("Use the word 'insurance'", "You need information. Ask if they take your insurance.", "Learner used the word 'insurance'."),
    Task("Say you need it urgently", "This is important context. Mention it is an emergency.", "Learner said they need it right away."),
    Task("Ask for a paper bag", "You need information. Ask for a bag.", "Learner asked for a paper bag."),
    Task("Ask if there is a generic alternative", "You need information. Ask for a generic version.", "Learner asked for a generic version."),
    Task("Say you have a rash", "This is important context. Mention a skin rash.", "Learner mentioned a rash."),
    Task("Ask for ointment", "You need information. Ask for skin cream/ointment.", "Learner asked for ointment."),
    Task("Use the word 'pregnant'", "You need information. Ask if it's safe for pregnant women.", "Learner used the word 'pregnant'."),
    Task("Ask for baby formula", "You need information. Ask where baby formula is.", "Learner asked for baby formula."),
    Task("Ask how long it will take to prepare", "You need information. Ask about wait time.", "Learner asked how long to prepare the prescription."),
    Task("Say you will come back later", "You need to communicate this. Say you'll return in an hour.", "Learner said they will come back."),
    Task("Ask for the receipt for insurance", "You need information. Ask for a detailed receipt.", "Learner asked for an insurance receipt."),
    Task("Use the word 'dose'", "You need information. Ask what the correct dose is.", "Learner used the word 'dose'."),
    Task("Ask for liquid medicine instead of pills", "You need to communicate this. Say you can't swallow pills.", "Learner asked for liquid medicine."),
    Task("Say it's for a child", "You have a specific preference. Specify the patient is a child.", "Learner said the medicine is for a child."),
    Task("Ask what age it is suitable for", "You need information. Ask the minimum age.", "Learner asked about age restrictions."),
    Task("Ask for a measuring cup", "You need information. Ask for a cup to measure liquid.", "Learner asked for a measuring cup or spoon."),
    Task("Use the word 'effective'", "You need information. Ask how fast it is effective.", "Learner used the word 'effective'."),
    Task("Ask for hand sanitizer", "You need information. Ask for hand gel.", "Learner asked for hand sanitizer."),
    Task("Ask for a medical mask", "You need information. Ask for face masks.", "Learner asked for a mask."),
    Task("Say thank you and leave", "It's time to go. End the conversation politely.", "Learner thanked the pharmacist and left.")
]

# Scenario 3: Hotel Check-in
hotel_tasks = [
    Task("Say you have a reservation", "You need to communicate this. Say you want to check in.", "Learner stated they have a reservation."),
    Task("Spell your last name", "They need precise details. Spell out your name.", "Learner spelled their name."),
    Task("Provide your passport", "You need to communicate this. Say here is my passport.", "Learner offered their ID or passport."),
    Task("Ask for a quiet room", "You need information. Ask for a room away from the elevator.", "Learner asked for a quiet room."),
    Task("Use the word 'upgrade'", "You need information. Ask if a room upgrade is possible.", "Learner used the word 'upgrade'."),
    Task("Ask what time breakfast is", "You need information. Ask about breakfast hours.", "Learner asked about breakfast times."),
    Task("Ask where the breakfast room is", "You need information. Ask for directions to breakfast.", "Learner asked where breakfast is served."),
    Task("Ask for the wifi password", "You need information. Ask for internet access.", "Learner asked for the wifi password."),
    Task("Ask what time checkout is", "You need information. Ask about checkout time.", "Learner asked when they must check out."),
    Task("Request a late checkout", "You need information. Ask to leave at 1 PM.", "Learner requested a late checkout."),
    Task("Use the word 'deposit'", "You need information. Ask about the security deposit.", "Learner used the word 'deposit'."),
    Task("Say the AC in your room is broken", "You are not satisfied. Complain about the air conditioning.", "Learner mentioned broken AC."),
    Task("Ask for a different room", "You need something. Request to change rooms.", "Learner asked for a room change."),
    Task("Ask for an extra key card", "You need information. Ask for another room key.", "Learner asked for an extra key."),
    Task("Ask for a wake-up call", "You need something. Request a wake-up call for 7 AM.", "Learner requested a wake-up call."),
    Task("Use the word 'luggage'", "You need information. Ask if you can leave your bags.", "Learner used the word 'luggage'."),
    Task("Ask for extra towels", "You need something. Request more towels.", "Learner asked for extra towels."),
    Task("Ask where the gym is", "You need information. Ask for the fitness center.", "Learner asked for the gym."),
    Task("Ask if the pool is heated", "You need information. Ask about the swimming pool.", "Learner asked if the pool is heated."),
    Task("Use the word 'included'", "You need information. Ask if breakfast is included.", "Learner used the word 'included'."),
    Task("Ask for a city map", "You need information. Ask if they have a map.", "Learner asked for a map."),
    Task("Ask for a restaurant recommendation", "You need information. Ask for a good local place to eat.", "Learner asked for a restaurant recommendation."),
    Task("Ask them to book a taxi", "You need something. Request a taxi for tomorrow.", "Learner asked the hotel to book a taxi."),
    Task("Use the word 'airport'", "You need information. Ask how far the airport is.", "Learner used the word 'airport'."),
    Task("Say you lost your room key", "Report a lost key.", "Learner said they lost their key."),
    Task("Ask for an adapter", "You need information. Ask for a power adapter.", "Learner asked for a plug adapter."),
    Task("Say the room is too noisy", "You are not satisfied. Complain about noise.", "Learner complained about noise."),
    Task("Ask for room service", "You need information. Ask how to order food to the room.", "Learner asked about room service."),
    Task("Use the word 'housekeeping'", "You need information. Ask for housekeeping to clean the room.", "Learner used the word 'housekeeping'."),
    Task("Ask if there is a laundry service", "You need information. Ask about washing clothes.", "Learner asked about laundry service."),
    Task("Say you didn't take anything from the minibar", "There is a misunderstanding. Deny minibar charges.", "Learner said they didn't use the minibar."),
    Task("Ask for an iron", "You need information. Ask for an ironing board.", "Learner asked for an iron."),
    Task("Use the word 'blanket'", "You need information. Ask for an extra blanket.", "Learner used the word 'blanket'."),
    Task("Ask if tap water is safe to drink", "You need information. Ask about drinking water.", "Learner asked if tap water is safe."),
    Task("Say your TV isn't working", "Report a broken TV.", "Learner reported the TV is broken."),
    Task("Ask to speak to the manager", "You need something. Request the manager.", "Learner asked for the manager."),
    Task("Ask for the nearest subway station", "You need information. Ask for transport directions.", "Learner asked for the subway/train station."),
    Task("Use the word 'receipt'", "You need information. Ask for a final receipt.", "Learner used the word 'receipt'."),
    Task("Ask if you can pay with two different cards", "You have a payment preference. Split the payment.", "Learner asked to split payment on cards."),
    Task("Say you enjoyed your stay", "You want to show appreciation. Give a compliment.", "Learner said they had a good stay."),
    Task("Ask for a double bed instead of two singles", "You need something. Request a different bed type.", "Learner requested a double/king bed."),
    Task("Use the word 'view'", "You need information. Ask for a room with a nice view.", "Learner used the word 'view'."),
    Task("Say you are checking out early", "This is important context. Mention an early departure.", "Learner mentioned leaving early."),
    Task("Ask if there is a shuttle bus", "You need information. Ask about the airport shuttle.", "Learner asked about a shuttle bus."),
    Task("Say the bathroom has no soap", "You are not satisfied. Complain about missing amenities.", "Learner mentioned missing soap."),
    Task("Ask for a smoking area", "You need information. Ask where you can smoke.", "Learner asked for a smoking area."),
    Task("Ask if pets are allowed", "You need information. Ask about bringing a dog.", "Learner asked about pet policy."),
    Task("Use the word 'confirm'", "You need information. Ask them to confirm your departure date.", "Learner used the word 'confirm'."),
    Task("Thank the receptionist", "You need to communicate this. Say thanks and bye.", "Learner thanked the receptionist.")
]


SCENARIOS = [
    Scenario(
        name="Coffee Shop",
        place="A busy local coffee shop",
        role="You are a friendly but busy barista.",
        tasks=coffee_shop_tasks
    ),
    Scenario(
        name="Pharmacy",
        place="A neighborhood pharmacy",
        role="You are a knowledgeable and helpful pharmacist.",
        tasks=pharmacy_tasks
    ),
    Scenario(
        name="Hotel Check-in",
        place="The reception desk of a 4-star hotel",
        role="You are a professional hotel receptionist.",
        tasks=hotel_tasks
    ),
    # Stubs for the remaining 12 scenarios
    Scenario(name="Airport Check-in", place="Airport counter", role="Airline agent", tasks=[]),
    Scenario(name="Job Interview", place="Corporate office", role="Hiring manager", tasks=[]),
    Scenario(name="Tech Support", place="Phone call", role="IT support agent", tasks=[]),
    Scenario(name="Restaurant Ordering", place="Fine dining restaurant", role="Waiter/Waitress", tasks=[]),
    Scenario(name="Bank Teller", place="Local bank branch", role="Bank teller", tasks=[]),
    Scenario(name="Apartment Viewing", place="An empty apartment", role="Real estate agent", tasks=[]),
    Scenario(name="Gym Signup", place="Local fitness center", role="Gym sales representative", tasks=[]),
    Scenario(name="Doctor's Clinic", place="Medical clinic", role="Doctor", tasks=[]),
    Scenario(name="Electronics Store", place="Tech retail store", role="Store clerk", tasks=[]),
    Scenario(name="Train Station", place="Ticket office", role="Ticket agent", tasks=[]),
    Scenario(name="Police Station", place="Local precinct", role="Police officer", tasks=[]),
    Scenario(name="Bookstore", place="Quiet bookstore", role="Bookstore clerk", tasks=[])
]
