import requests
from bs4 import BeautifulSoup
import string
import json

conditions_dict = {}

for letter in string.ascii_lowercase:
    url = f"https://www.drugs.com/condition/{letter}.html"
    response = requests.get(url)

    soup = BeautifulSoup(response.content, "html.parser")

    main_div = soup.find("main").find("div")
    ul_elements = main_div.find_all("ul", limit=2) if main_div else []

    for ul_element in ul_elements:
        for li in ul_element.find_all("li"):
            a_tag = li.find("a")
            if a_tag and "href" in a_tag.attrs:
                condition_name = a_tag.text.strip()
                condition_url = "https://www.drugs.com" + a_tag["href"]
                if (
                    len(condition_name) > 1
                    and condition_url not in conditions_dict.values()
                ):
                    conditions_dict[condition_name] = condition_url

with open("conditions.json", "w") as json_file:
    json.dump(conditions_dict, json_file, indent=4)
