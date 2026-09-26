"""Weekly menu transcribed from the provided 21 Sep–4 Oct 2026 workbook."""

MENU_PLAN = {
    "source_title": "Menu 21st September to 4th October 2026",
    "source_period": "2026-09-21 to 2026-10-04",
    "meals": ["Breakfast", "Lunch", "Snacks", "Dinner"],
    "meal_times": {
        "Breakfast": "7:30–8:50 AM",
        "Lunch": "12:30–1:50 PM",
        "Snacks": "5:00–5:30 PM",
        "Dinner": "7:30–8:50 PM",
    },
    "days": {
        "Monday": {
            "Breakfast": "Poha + Tawa sandwich + Bread + Jam + Fruit + Milk + Tea + Cornflakes",
            "Lunch": "Dal Rajma + Lauki masala + Jeera Rice + Chapati + Salad + Plain Curd + Roti + Papad",
            "Snacks": "Aloo Patties + Masala Tea",
            "Dinner": "Dal Kali Masoor + Palak corn + Aloo Jeera + Rice + Roti + Sponge rasgulla",
        },
        "Tuesday": {
            "Breakfast": "Aloo paratha + Upma + Chutney + Milk + Tea + Cornflakes + Bread + Jam + Fruit",
            "Lunch": "Chole Masala + Kaddu Khata Meetha + Puri + Rice + Boondi Raita + Salad",
            "Snacks": "Chilli potato + Tea",
            "Dinner": "Chana dry + Mix dal + Aloo Nutri Masala + Rice + Roti + Mohan Kheer",
        },
        "Wednesday": {
            "Breakfast": "Chole Kulche + Poha + Milk + Tea + Cornflakes + Bread + Jam + Fruit",
            "Lunch": "Arhar dal + Aloo Matar ki Subzi + Rice + Roti + Raita + Salad",
            "Snacks": "Macroni + Tea",
            "Dinner": "Dal Makhani + Shahi Paneer + Roti + Rice + Rasgulla",
        },
        "Thursday": {
            "Breakfast": "Idli + SAmber + Chutney + Vegetable Daliya + Corn Flakes + Milk + Bread + Jam + Tea + Fruits",
            "Lunch": "Kadi Pakoda + Allo Bhujiya + Malka Dal + Rice + Roti + Pyaj Laccha",
            "Snacks": "Baby Pizza + Tea",
            "Dinner": "Dal Arhar + Veg machurian + Chowmein + Jeera Rice + Roti + Ice cream",
        },
        "Friday": {
            "Breakfast": "Aloo + Bhaji + Poori + Suji Haluwa + Corn Flakes + Milk + Bread + Jam + Tea + Fruits",
            "Lunch": "Chana Dal + Aloo Shimla + Jeera Rice + Mix raita + Salad + Roti",
            "Snacks": "Bread Pakoda + Tea",
            "Dinner": "Dhaba Dal + Veg Pulav + Soya Chaap + Karela Fry + Roti + Brownie",
        },
        "Saturday": {
            "Breakfast": "Pav + Bhaji + Veg Vermicilly + Cornflakes + Milk + Tea + Bread + Jam + Fruit",
            "Lunch": "Dal Tadka + Jeera Rice + MixVeg + Curd + Salad + Roti",
            "Snacks": "Aloo Ki Sabji Khasta Kachori + Lassi",
            "Dinner": "Moong Dal + Mushroom Masala + Dry Mutter + Rice + Roti + Chocolate Pastrie",
        },
        "Sunday": {
            "Breakfast": "Fried Idli + Sambar + Coconut Chutney + Veg Pulav + Chole + Bhature + Boondi Raita + Bread + Jam + Tea + Cutfruit",
            "Lunch": None,
            "Snacks": "Namkeen / Tea",
            "Dinner": "Black Chana Curry + Chilli Paneer + Aloo Tamater Sabji + Rice + Roti + Milk Cake",
        },
    },
    "assumptions": [
        "The workbook supplies menu names only. All training attendance and food-waste values are generated examples, not college measurements.",
        "The listed weekday menus are repeated across eight simulated weeks to create training scenarios.",
        "One thousand eligible students is a changeable demo starting point based on the estimate mentioned by the project team.",
        "Suggested portions add an 8% reserve. Synthetic waste uses assumed cooked portions of 0.38 kg for breakfast, 0.60 kg for lunch, 0.18 kg for snacks, and 0.55 kg for dinner, plus a generated 6%–11% preparation reserve and 20–55 g of generated plate leftovers per serving. None of these values are measured.",
        "Sunday lunch is blank in the workbook and is therefore omitted.",
    ],
}
