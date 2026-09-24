"""Locality -> main area. Based on the block Deepika's directory gives for the
schools in each locality; localities with no directory match are placed by
geography and listed as ASSUMED so executives can confirm them."""
MAIN_AREAS = {
    'Tirur': [
        'Alathiyur', 'Alungal', 'Annara', 'Bp Angadi', 'Chamravattam', 'Chembra',
        'Chennara', 'Cheriyaparapur', 'Chirakkal', 'Edakkulam', 'Kaithakkara', 'Karathur',
        'Kadapuram', 'Kurumbathur', 'Kuttayi', 'Mangalam', 'Mangattiri', 'Muthur',
        'Nadakkavu', 'Naduvilangadi', 'Olapeedika', 'Panaghattor', 'Paravanna', 'Palapettyppara',
        'Puthiyakadappuram', 'Thattathalam', 'Thirunavaya', 'Thiruthi', 'Tirur', 'Triprangode',
        'Vettam', 'Edayathuparamba',
    ],
    'Tanur': [
        'Areekad', 'Ayyaya', 'Cheruvannur', 'Chilavil West', 'Edakadappuram', 'Iringavoor',
        'Iringavur', 'Ittilakkal', 'Kadungathukundu', 'Kalad', 'Kalpakanchery', 'Kanmanam',
        'Kattilangadi', 'Korad', 'Korangath', 'Kozhichena', 'Kuttippala', 'Manalipuzha',
        'Meenadathur', 'Nettanchola', 'Ozhur', 'Pakara', 'Parakkal', 'Parannekkad',
        'Paravannur', 'Pariyapuram', 'Ponmundam', 'Rayirimangalam', 'Tanalur', 'Tanur',
        'Thalakkadathur', 'Theyyalinagal', 'Vailathur', 'Valavannur', 'Varanakkara', 'Velliyampuram',
    ],
    'Ponnani & Edappal': [
        'Alankode', 'Athalur', 'Biyyam', 'Edappal', 'Eswaramangalam', 'Manoor',
        'Maranchery', 'Nariparamba', 'Panthavoor', 'Ponnani', 'Tavanur', 'Thalamunda',
        'Veliyancode',
    ],
    'Tirurangadi & Parappanangadi': [
        'Ariyallur', 'Chemmad', 'Cherumukku', 'Chiramangalam', 'Kachadi', 'Kaduvallur',
        'Kakkad', 'Kodakkad', 'Kodinhi', 'Kundoor', 'Moonniyur', 'Nannambra',
        'Neduva', 'Padikkal', 'Palathingal', 'Parappanangadi', 'Peruvallur', 'Thirurangadi',
        'Tirurangadi', 'Ullanam', 'Venniyur',
    ],
    'Vengara': [
        'Iringallur', 'Irumbuchola', 'Kolappuram', 'Kuttur', 'Mampuram', 'Parappur',
        'Pullithara', 'Puthuparamba', 'Thottasseriyara', 'Valakkulam', 'Valiyora',
    ],
    'Kottakkal': [
        'Kottakkal', 'Maravattom', 'Thekken Kuttoor', 'Thennala', 'Valiyaparambu',
    ],
    'Kuttippuram & Valanchery': [
        'Chottur', 'Kadampuzha', 'Karthala', 'Konnellur', 'Moodal', 'Pazhur',
        'Puthanathani', 'Randathani', 'Valanchery',
    ],
    'Malappuram, Kondotty & Perinthalmanna': [
        'Athanikkal', 'Kallingal', 'Kooriyad', 'Karuvankallu', 'Pullur', 'Puthanangadi',
    ],
}
# Placed by geography only (no Deepika block evidence) - flagged in the report.
ASSUMED = set("Alungal Chembra Chirakkal Kadapuram Kurumbathur Muthur Nadakkavu Naduvilangadi Olapeedika Panaghattor "
               "Palapettyppara Puthiyakadappuram Thattathalam Thiruthi Triprangode Edayathuparamba Theyyalinagal "
               "Parannekkad Pariyapuram Eswaramangalam Biyyam Maranchery Panthavoor Chiramangalam Kakkad Padikkal "
               "Neduva Ullanam Maravattom Thennala Valiyaparambu Karthala Pullur".split())


def area_map():
    return {loc: main for main, locs in MAIN_AREAS.items() for loc in locs}
