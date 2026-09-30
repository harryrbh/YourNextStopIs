"""
tourist_cities.py — the pre-defined pool of well-known tourist
destinations the app chooses from.

This is an editorial list (a judgement call, not a measured statistic),
written roughly from most to least famous. Only the SELECTION is curated:
coordinates and population still come from real GeoNames rows (see
fetch_cities.py), and every other attribute comes from a real data source.

HOW IT'S USED
------------------------------------------------------------------
  * fetch_cities.py matches every entry against GeoNames -> data/cities.csv
    (the ~300 "candidates").
  * The fetch_* scripts then gather weather, culture, airports and
    country data for the candidates.
  * select_cities.py (called by load_data.py) keeps the first 250
    candidates, in this order, that have COMPLETE data for every
    tourist attribute — so a city that has no sights, no weather record,
    no nearby airport or no country statistics is dropped and replaced by
    the next one down the list, rather than showing up half-empty.

Names are the common English names; fetch_cities.py matches them against
GeoNames' name, ASCII name and alternate names, so "Krakow" finds "Kraków".
Country codes are ISO 3166-1 alpha-2. Each (name, country) must be unique.
"""

TARGET_CITY_COUNT = 250

TOURIST_CITIES = [
    # --- The famous core ---
    ("Paris", "FR"), ("London", "GB"), ("Rome", "IT"), ("Barcelona", "ES"),
    ("Amsterdam", "NL"), ("Prague", "CZ"), ("Vienna", "AT"), ("Berlin", "DE"),
    ("Budapest", "HU"), ("Lisbon", "PT"), ("Madrid", "ES"), ("Florence", "IT"),
    ("Venice", "IT"), ("Athens", "GR"), ("Istanbul", "TR"), ("Dublin", "IE"),
    ("Edinburgh", "GB"), ("Copenhagen", "DK"), ("Stockholm", "SE"), ("Oslo", "NO"),
    ("Helsinki", "FI"), ("Brussels", "BE"), ("Munich", "DE"), ("Milan", "IT"),
    ("Naples", "IT"), ("Seville", "ES"), ("Valencia", "ES"), ("Porto", "PT"),
    ("Krakow", "PL"), ("Warsaw", "PL"), ("Dubrovnik", "HR"), ("Split", "HR"),
    ("Zagreb", "HR"), ("Ljubljana", "SI"), ("Bratislava", "SK"), ("Tallinn", "EE"),
    ("Riga", "LV"), ("Vilnius", "LT"), ("Reykjavik", "IS"), ("Zurich", "CH"),
    ("Geneva", "CH"), ("Lucerne", "CH"), ("Bern", "CH"), ("Nice", "FR"),
    ("Lyon", "FR"), ("Marseille", "FR"), ("Bordeaux", "FR"), ("Strasbourg", "FR"),
    ("Toulouse", "FR"), ("Avignon", "FR"), ("Cannes", "FR"), ("Salzburg", "AT"),
    ("Innsbruck", "AT"), ("Graz", "AT"), ("Bruges", "BE"), ("Ghent", "BE"),
    ("Antwerp", "BE"), ("Hamburg", "DE"), ("Cologne", "DE"), ("Frankfurt", "DE"),
    ("Dresden", "DE"), ("Heidelberg", "DE"), ("Nuremberg", "DE"), ("Leipzig", "DE"),
    ("Rotterdam", "NL"), ("Utrecht", "NL"), ("Bologna", "IT"), ("Verona", "IT"),
    ("Turin", "IT"), ("Genoa", "IT"), ("Siena", "IT"), ("Pisa", "IT"),
    ("Palermo", "IT"), ("Catania", "IT"), ("Syracuse", "IT"), ("Bari", "IT"),
    ("Lecce", "IT"), ("Sorrento", "IT"), ("Padua", "IT"), ("Perugia", "IT"),
    ("Lucca", "IT"), ("Cagliari", "IT"),
    # --- Iberia & islands ---
    ("Granada", "ES"), ("Cordoba", "ES"), ("Toledo", "ES"), ("Bilbao", "ES"),
    ("San Sebastian", "ES"), ("Malaga", "ES"), ("Palma", "ES"), ("Salamanca", "ES"),
    ("Santiago de Compostela", "ES"), ("Girona", "ES"), ("Cadiz", "ES"),
    ("Marbella", "ES"), ("Las Palmas de Gran Canaria", "ES"), ("Coimbra", "PT"),
    ("Faro", "PT"), ("Braga", "PT"), ("Funchal", "PT"),
    # --- Northern Europe & British Isles ---
    ("Bergen", "NO"), ("Gothenburg", "SE"), ("Malmo", "SE"), ("Aarhus", "DK"),
    ("Tromso", "NO"), ("York", "GB"), ("Bath", "GB"), ("Oxford", "GB"),
    ("Cambridge", "GB"), ("Manchester", "GB"), ("Liverpool", "GB"), ("Glasgow", "GB"),
    ("Belfast", "GB"), ("Cardiff", "GB"), ("Brighton", "GB"), ("Canterbury", "GB"),
    ("Galway", "IE"), ("Cork", "IE"), ("Tampere", "FI"), ("Turku", "FI"),
    ("Rovaniemi", "FI"), ("Luxembourg", "LU"),
    # --- Central & Eastern Europe, Balkans ---
    ("Zadar", "HR"), ("Pula", "HR"), ("Sarajevo", "BA"), ("Mostar", "BA"),
    ("Belgrade", "RS"), ("Novi Sad", "RS"), ("Skopje", "MK"), ("Ohrid", "MK"),
    ("Tirana", "AL"), ("Sofia", "BG"), ("Plovdiv", "BG"), ("Bucharest", "RO"),
    ("Brasov", "RO"), ("Sibiu", "RO"), ("Cluj-Napoca", "RO"), ("Timisoara", "RO"),
    ("Gdansk", "PL"), ("Wroclaw", "PL"), ("Poznan", "PL"), ("Lublin", "PL"),
    ("Brno", "CZ"), ("Karlovy Vary", "CZ"), ("Kosice", "SK"), ("Debrecen", "HU"),
    ("Thessaloniki", "GR"), ("Heraklion", "GR"), ("Rhodes", "GR"), ("Corfu", "GR"),
    ("Chania", "GR"), ("Nicosia", "CY"), ("Limassol", "CY"), ("Paphos", "CY"),
    ("Kyiv", "UA"), ("Lviv", "UA"), ("Odessa", "UA"), ("Chisinau", "MD"),
    ("Tbilisi", "GE"), ("Batumi", "GE"), ("Yerevan", "AM"), ("Baku", "AZ"),
    ("Antalya", "TR"), ("Izmir", "TR"), ("Bodrum", "TR"), ("Ankara", "TR"),
    # --- East Asia ---
    ("Tokyo", "JP"), ("Kyoto", "JP"), ("Osaka", "JP"), ("Nara", "JP"),
    ("Kanazawa", "JP"), ("Hiroshima", "JP"), ("Sapporo", "JP"), ("Fukuoka", "JP"),
    ("Nagasaki", "JP"), ("Kamakura", "JP"), ("Nikko", "JP"), ("Beijing", "CN"),
    ("Shanghai", "CN"), ("Xi'an", "CN"), ("Chengdu", "CN"), ("Guilin", "CN"),
    ("Hangzhou", "CN"), ("Suzhou", "CN"), ("Kunming", "CN"), ("Hong Kong", "HK"),
    ("Macau", "MO"), ("Taipei", "TW"), ("Tainan", "TW"), ("Seoul", "KR"),
    ("Busan", "KR"), ("Gyeongju", "KR"), ("Jeju", "KR"), ("Jeonju", "KR"),
    # --- Southeast Asia ---
    ("Bangkok", "TH"), ("Chiang Mai", "TH"), ("Phuket", "TH"), ("Pattaya", "TH"),
    ("Chiang Rai", "TH"), ("Krabi", "TH"), ("Hanoi", "VN"), ("Ho Chi Minh City", "VN"),
    ("Da Nang", "VN"), ("Hoi An", "VN"), ("Hue", "VN"), ("Nha Trang", "VN"),
    ("Dalat", "VN"), ("Siem Reap", "KH"), ("Phnom Penh", "KH"), ("Luang Prabang", "LA"),
    ("Vientiane", "LA"), ("Yangon", "MM"), ("Mandalay", "MM"), ("Kuala Lumpur", "MY"),
    ("George Town", "MY"), ("Malacca", "MY"), ("Kota Kinabalu", "MY"), ("Kuching", "MY"),
    ("Singapore", "SG"), ("Denpasar", "ID"), ("Yogyakarta", "ID"), ("Manila", "PH"),
    ("Cebu City", "PH"), ("Puerto Princesa", "PH"),
    # --- South & Central Asia ---
    ("Delhi", "IN"), ("Mumbai", "IN"), ("Agra", "IN"), ("Jaipur", "IN"),
    ("Udaipur", "IN"), ("Jodhpur", "IN"), ("Jaisalmer", "IN"), ("Varanasi", "IN"),
    ("Panaji", "IN"), ("Kochi", "IN"), ("Amritsar", "IN"), ("Rishikesh", "IN"),
    ("Mysore", "IN"), ("Kathmandu", "NP"), ("Pokhara", "NP"), ("Colombo", "LK"),
    ("Kandy", "LK"), ("Galle", "LK"), ("Male", "MV"), ("Thimphu", "BT"),
    ("Ulaanbaatar", "MN"), ("Samarkand", "UZ"), ("Bukhara", "UZ"), ("Tashkent", "UZ"),
    ("Almaty", "KZ"),
    # --- Middle East ---
    ("Dubai", "AE"), ("Abu Dhabi", "AE"), ("Doha", "QA"), ("Muscat", "OM"),
    ("Manama", "BH"), ("Amman", "JO"), ("Jerusalem", "IL"), ("Tel Aviv", "IL"),
    ("Haifa", "IL"), ("Beirut", "LB"), ("Isfahan", "IR"), ("Shiraz", "IR"),
    # --- Africa ---
    ("Marrakesh", "MA"), ("Fes", "MA"), ("Casablanca", "MA"), ("Rabat", "MA"),
    ("Chefchaouen", "MA"), ("Essaouira", "MA"), ("Tangier", "MA"), ("Cairo", "EG"),
    ("Luxor", "EG"), ("Aswan", "EG"), ("Alexandria", "EG"), ("Sharm el-Sheikh", "EG"),
    ("Hurghada", "EG"), ("Tunis", "TN"), ("Sousse", "TN"), ("Cape Town", "ZA"),
    ("Stellenbosch", "ZA"), ("Durban", "ZA"), ("Johannesburg", "ZA"), ("Nairobi", "KE"),
    ("Mombasa", "KE"), ("Zanzibar", "TZ"), ("Arusha", "TZ"), ("Livingstone", "ZM"),
    ("Dakar", "SN"), ("Accra", "GH"), ("Addis Ababa", "ET"), ("Kigali", "RW"),
    ("Port Louis", "MU"),
    # --- North America ---
    ("New York City", "US"), ("Los Angeles", "US"), ("San Francisco", "US"),
    ("Chicago", "US"), ("Miami", "US"), ("New Orleans", "US"), ("Boston", "US"),
    ("Washington", "US"), ("Las Vegas", "US"), ("Seattle", "US"), ("San Diego", "US"),
    ("Honolulu", "US"), ("Austin", "US"), ("Nashville", "US"), ("Savannah", "US"),
    ("Charleston", "US"), ("Santa Fe", "US"), ("Portland", "US"), ("Denver", "US"),
    ("Orlando", "US"), ("Philadelphia", "US"), ("San Antonio", "US"), ("Key West", "US"),
    ("Montreal", "CA"), ("Toronto", "CA"), ("Vancouver", "CA"), ("Quebec City", "CA"),
    ("Victoria", "CA"), ("Ottawa", "CA"), ("Halifax", "CA"),
    # --- Mexico, Central America & Caribbean ---
    ("Mexico City", "MX"), ("Cancun", "MX"), ("Playa del Carmen", "MX"), ("Oaxaca", "MX"),
    ("Merida", "MX"), ("Guanajuato", "MX"), ("San Miguel de Allende", "MX"),
    ("Puebla", "MX"), ("Guadalajara", "MX"), ("Puerto Vallarta", "MX"), ("Havana", "CU"),
    ("Varadero", "CU"), ("San Juan", "PR"), ("Santo Domingo", "DO"), ("Nassau", "BS"),
    ("Kingston", "JM"), ("Montego Bay", "JM"), ("Bridgetown", "BB"), ("San Jose", "CR"),
    ("Antigua Guatemala", "GT"), ("Panama City", "PA"),
    # --- South America ---
    ("Cartagena", "CO"), ("Bogota", "CO"), ("Medellin", "CO"), ("Lima", "PE"),
    ("Cusco", "PE"), ("Arequipa", "PE"), ("Quito", "EC"), ("Cuenca", "EC"),
    ("La Paz", "BO"), ("Sucre", "BO"), ("Santiago", "CL"), ("Valparaiso", "CL"),
    ("Buenos Aires", "AR"), ("Mendoza", "AR"), ("Salta", "AR"),
    ("San Carlos de Bariloche", "AR"), ("Rio de Janeiro", "BR"),
    ("Sao Paulo", "BR"), ("Salvador", "BR"), ("Florianopolis", "BR"),
    ("Foz do Iguacu", "BR"), ("Montevideo", "UY"),
    # --- Oceania ---
    ("Sydney", "AU"), ("Melbourne", "AU"), ("Brisbane", "AU"), ("Perth", "AU"),
    ("Adelaide", "AU"), ("Cairns", "AU"), ("Hobart", "AU"), ("Gold Coast", "AU"),
    ("Auckland", "NZ"), ("Wellington", "NZ"), ("Queenstown", "NZ"), ("Christchurch", "NZ"),
    ("Rotorua", "NZ"), ("Nadi", "FJ"), ("Papeete", "PF"),
]

# Guard against typos that would silently create duplicates.
assert len(set(TOURIST_CITIES)) == len(TOURIST_CITIES), "duplicate (city, country) in TOURIST_CITIES"
assert len({n for n, _ in TOURIST_CITIES}) == len(TOURIST_CITIES), (
    "two cities share a name — the CSVs are keyed by city name, so names must be unique"
)
