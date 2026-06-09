"""Master checklist of everything to update when moving address.

Each item: a stable id, display name, category, rough timing, a practical
hint, and (where one exists) a link to the official change-of-address page.
UK-leaning defaults (DVLA, HMRC, Royal Mail, council tax) with generic items
that apply anywhere; users can add their own items through the UI.
"""

# Timing buckets shown as badges in the UI, in chronological order.
WHEN_ASAP = "As soon as date is known"
WHEN_BEFORE = "1–2 weeks before"
WHEN_MOVE = "Moving week"
WHEN_AFTER = "After the move"

CATEGORIES = [
    "Mail & post",
    "Government & official",
    "Banking & finance",
    "Insurance",
    "Utilities & home services",
    "Health",
    "Work & education",
    "Subscriptions & shopping",
    "People & other",
]


def _item(id, name, category, when, hint, link=None):
    return {
        "id": id,
        "name": name,
        "category": category,
        "when": when,
        "hint": hint,
        "link": link,
        "status": "todo",      # todo | in_progress | done | na
        "notes": "",
        "custom": False,
    }


MASTER_CHECKLIST = [
    # ---- Mail & post -----------------------------------------------------
    _item("mail-redirect", "Postal redirection (Royal Mail)", "Mail & post",
          WHEN_ASAP,
          "Set up at least 3 weeks before the move. Catches everything you "
          "forget on this list — do it first.",
          "https://www.royalmail.com/personal/receiving-mail/redirection"),

    # ---- Government & official -------------------------------------------
    _item("electoral-roll", "Electoral roll / voter registration",
          "Government & official", WHEN_AFTER,
          "Re-register at the new address. Also helps your credit score.",
          "https://www.gov.uk/register-to-vote"),
    _item("driving-licence", "Driving licence (DVLA)",
          "Government & official", WHEN_AFTER,
          "Free to update and legally required. Takes minutes online.",
          "https://www.gov.uk/change-address-driving-licence"),
    _item("vehicle-logbook", "Vehicle log book V5C (DVLA)",
          "Government & official", WHEN_AFTER,
          "Update the V5C for every vehicle you keep. Free online.",
          "https://www.gov.uk/change-address-log-book"),
    _item("hmrc", "HMRC (income tax, self assessment)",
          "Government & official", WHEN_AFTER,
          "One update covers income tax, NI and child benefit records.",
          "https://www.gov.uk/tell-hmrc-change-of-address"),
    _item("council-tax-old", "Council tax — close account at old address",
          "Government & official", WHEN_BEFORE,
          "Tell the old council your move-out date for a final bill.",
          "https://www.gov.uk/find-local-council"),
    _item("council-tax-new", "Council tax — register at new address",
          "Government & official", WHEN_AFTER,
          "Register with the new council; ask about discounts (single "
          "occupancy etc.).",
          "https://www.gov.uk/find-local-council"),
    _item("tv-licence", "TV Licence", "Government & official", WHEN_BEFORE,
          "Move your licence to the new address — it doesn't follow you "
          "automatically.",
          "https://www.tvlicensing.co.uk/check-if-you-need-one/moving-home"),
    _item("dwp-benefits", "DWP — benefits / state pension",
          "Government & official", WHEN_AFTER,
          "Universal Credit, state pension, child benefit and any other "
          "benefits each need updating.",
          "https://www.gov.uk/tell-dwp-change-of-circumstances"),
    _item("parking-permit", "Parking permits", "Government & official",
          WHEN_AFTER,
          "Cancel the old resident permit and apply for one in the new area "
          "if needed."),

    # ---- Banking & finance -------------------------------------------------
    _item("current-accounts", "Current / checking accounts",
          "Banking & finance", WHEN_BEFORE,
          "Update each bank via its app or online banking — usually "
          "under Profile → Personal details."),
    _item("savings-accounts", "Savings accounts & ISAs", "Banking & finance",
          WHEN_BEFORE,
          "Easy to forget dormant accounts — statements at an old "
          "address are a fraud risk."),
    _item("credit-cards", "Credit cards", "Banking & finance", WHEN_BEFORE,
          "Update every issuer, including store cards you rarely use."),
    _item("mortgage-landlord", "Mortgage lender / landlord & letting agent",
          "Banking & finance", WHEN_ASAP,
          "Give contractual notice if renting; tell your lender your "
          "correspondence address if you keep the property."),
    _item("loans-finance", "Loans & car finance", "Banking & finance",
          WHEN_BEFORE,
          "Personal loans, car finance (PCP/HP) and buy-now-pay-later "
          "accounts."),
    _item("pensions", "Pension providers", "Banking & finance", WHEN_AFTER,
          "Workplace and private pensions — lost-pension tracing is a "
          "pain later, update now."),
    _item("investments", "Investment / brokerage accounts",
          "Banking & finance", WHEN_AFTER,
          "Brokers, robo-advisers, share registrars and crypto exchanges."),
    _item("nsandi", "NS&I / Premium Bonds", "Banking & finance", WHEN_AFTER,
          "Prize warrants go to the registered address.",
          "https://www.nsandi.com/"),
    _item("paypal-payments", "PayPal & payment apps", "Banking & finance",
          WHEN_AFTER,
          "PayPal, Wise, Revolut etc. — billing address affects card "
          "verification."),

    # ---- Insurance ---------------------------------------------------------
    _item("home-insurance", "Home & contents insurance", "Insurance",
          WHEN_ASAP,
          "Must reflect the insured address or cover is void. Arrange cover "
          "for the new home from exchange/completion day."),
    _item("car-insurance", "Car insurance", "Insurance", WHEN_ASAP,
          "Legally required to update — the premium is recalculated for "
          "the new postcode."),
    _item("life-insurance", "Life insurance & income protection", "Insurance",
          WHEN_AFTER, "Correspondence address only — quick call or "
          "online form."),
    _item("health-insurance", "Private health / dental insurance", "Insurance",
          WHEN_AFTER, "May also change your hospital list and premium."),
    _item("pet-insurance", "Pet insurance", "Insurance", WHEN_AFTER,
          "Premiums vary by postcode; also update the microchip database."),
    _item("breakdown-cover", "Breakdown cover", "Insurance", WHEN_AFTER,
          "AA / RAC / Green Flag — home-start cover uses your address."),

    # ---- Utilities & home services ----------------------------------------
    _item("energy", "Electricity & gas", "Utilities & home services",
          WHEN_MOVE,
          "Take final meter readings (photograph them) on move-out day; "
          "open an account at the new address and read those meters too."),
    _item("water", "Water & sewerage", "Utilities & home services", WHEN_MOVE,
          "Close the old account with a final reading; register at the new "
          "address."),
    _item("broadband", "Broadband / internet", "Utilities & home services",
          WHEN_ASAP,
          "Book the move or new installation early — lead times run "
          "2–4 weeks."),
    _item("mobile", "Mobile phone provider", "Utilities & home services",
          WHEN_AFTER, "Billing address update; check signal at the new "
          "address before renewing."),
    _item("landline-tv", "Landline / TV package", "Utilities & home services",
          WHEN_BEFORE, "Often bundled with broadband — move or cancel "
          "together."),
    _item("home-services", "Cleaner / gardener / window cleaner",
          "Utilities & home services", WHEN_BEFORE,
          "Cancel or transfer regular household services."),

    # ---- Health ------------------------------------------------------------
    _item("gp", "GP / doctor", "Health", WHEN_AFTER,
          "Register with a practice near the new address; repeat "
          "prescriptions follow your registration.",
          "https://www.nhs.uk/service-search/find-a-gp"),
    _item("dentist", "Dentist", "Health", WHEN_AFTER,
          "Find a practice taking new patients — NHS lists fill fast."),
    _item("optician", "Optician", "Health", WHEN_AFTER,
          "Transfer your prescription history to a new branch."),
    _item("vet-microchip", "Vet & pet microchip database", "Health",
          WHEN_AFTER,
          "Register with a new vet and update the microchip record — "
          "it's the address on the chip that gets pets home."),
    _item("pharmacy", "Pharmacy / repeat prescriptions", "Health", WHEN_AFTER,
          "Re-point your nominated pharmacy for electronic prescriptions."),

    # ---- Work & education --------------------------------------------------
    _item("employer", "Employer HR / payroll", "Work & education", WHEN_BEFORE,
          "Payslips, P60s and pension correspondence all use this address."),
    _item("schools", "Schools / nurseries", "Work & education", WHEN_ASAP,
          "If changing catchment areas, contact the new council's admissions "
          "team as early as possible."),
    _item("professional-bodies", "Professional bodies & alumni",
          "Work & education", WHEN_AFTER,
          "Memberships, licences to practise, university alumni offices."),

    # ---- Subscriptions & shopping ------------------------------------------
    _item("amazon-retail", "Amazon & online retail default addresses",
          "Subscriptions & shopping", WHEN_MOVE,
          "Change the default delivery address the day you move — "
          "mis-delivered parcels rarely come back."),
    _item("streaming", "Streaming & app-store billing",
          "Subscriptions & shopping", WHEN_AFTER,
          "Netflix/Spotify etc., plus Apple ID and Google account billing "
          "addresses."),
    _item("subscription-boxes", "Subscription boxes & magazines",
          "Subscriptions & shopping", WHEN_BEFORE,
          "Meal kits, magazines, coffee clubs — anything that ships on "
          "a schedule."),
    _item("gym", "Gym membership", "Subscriptions & shopping", WHEN_BEFORE,
          "Transfer to a nearer branch or give notice — contracts often "
          "need 30 days."),
    _item("loyalty", "Loyalty schemes & store accounts",
          "Subscriptions & shopping", WHEN_AFTER,
          "Nectar, Boots, supermarket delivery accounts, airline miles."),
    _item("food-delivery", "Food delivery apps", "Subscriptions & shopping",
          WHEN_AFTER,
          "Deliveroo/Uber Eats/Just Eat saved addresses — before you "
          "hungrily order to the old flat."),

    # ---- People & other ------------------------------------------------------
    _item("friends-family", "Friends & family", "People & other", WHEN_AFTER,
          "Send the new address around — the generated letter below "
          "works for this too."),
    _item("charities", "Charities & regular donations", "People & other",
          WHEN_AFTER, "Direct-debit charities and membership organisations "
          "(National Trust etc.)."),
    _item("deliveries-neighbour", "Old neighbours / new occupants",
          "People & other", WHEN_MOVE,
          "Leave a forwarding note for anything the redirect misses."),
]
