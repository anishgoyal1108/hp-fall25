import requests
from bs4 import BeautifulSoup
import string
import json
import itertools

drugs_dict = {}

two_letter_combinations = [
    "".join(pair) for pair in itertools.product(string.ascii_lowercase, repeat=2)
]

for combination in two_letter_combinations:
    url = f"https://www.drugs.com/alpha/{combination}.html?pro=1Z"
    response = requests.get(url)

    soup = BeautifulSoup(response.content, "html.parser")

    ul_element = soup.find("ul", class_="ddc-list-column-2")
    li_elements = ul_element.find_all("li") if ul_element else []

    for li in li_elements:
        a_tag = li.find("a")
        if a_tag and "href" in a_tag.attrs:
            drug_name = a_tag.text.strip()
            drug_url = "https://www.drugs.com" + a_tag["href"]
            if len(drug_name) > 1 and drug_url not in drugs_dict.values():
                drugs_dict[drug_name] = drug_url

with open("drugs.json", "w") as json_file:
    json.dump(drugs_dict, json_file, indent=4)
