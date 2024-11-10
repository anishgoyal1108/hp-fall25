import requests
import json
from bs4 import BeautifulSoup


def get_drug_interactions(active_ingredient):
    url = f"https://www.drugs.com/drug-interactions/{active_ingredient}.html"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data for {active_ingredient}")

    soup = BeautifulSoup(response.content, "html.parser")
    interactions_list = soup.find("ul", class_="interactions ddc-list-unstyled")

    if not interactions_list:
        return []

    severity_map = {
        "int_3": "Severe",
        "int_2": "Moderate",
        "int_1": "Minor",
    }

    interactions = []
    for li in interactions_list.find_all("li"):
        severity_class = li.get("class")[0]
        if severity_class in severity_map:
            interaction = {}
            a_tag = li.find("a")
            interaction["name"] = a_tag.text
            interaction["url"] = f"https://www.drugs.com{a_tag['href']}"
            interaction["severity"] = severity_map[severity_class]
            interactions.append(interaction)
    return interactions


def get_professional_descriptions_from_interactions(interactions):
    descriptions = []
    for interaction in interactions:
        url = interaction["url"] + "?professional=1"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        interaction_details = soup.find("div", class_="interactions-reference-wrapper")
        professional_description = interaction_details.find_all("p")[1].get_text()
        descriptions.append(professional_description)
    return descriptions


def get_patient_descriptions_from_interactions(interactions):
    descriptions = []
    for interaction in interactions:
        url = interaction["url"]
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        interaction_details = soup.find("div", class_="interactions-reference-wrapper")
        patient_description = interaction_details.find_all("p")[1].get_text()
        descriptions.append(patient_description)
    return descriptions


def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def search_existing_conditions(input):
    with open("conditions.json") as f:
        conditions = json.load(f)
        min_distance = float("inf")
        closest_match = None

        for condition in conditions:
            distance = levenshtein_distance(input.lower(), condition.lower())
            ratio = 1 - distance / max(len(input), len(condition))
            if ratio > 0.5 and distance < min_distance:
                min_distance = distance
                closest_match = condition

        return closest_match


9
if __name__ == "__main__":
    active_ingredient = "ADHD"
    print(search_existing_conditions(active_ingredient))
    interactions = [
        interaction
        for interaction in get_drug_interactions(active_ingredient)
        if interaction["severity"] != "Unknown"
    ]

    for interaction, description in zip(
        interactions, get_professional_descriptions_from_interactions(interactions)
    ):
        interaction["professional_description"] = description

    for inteaction, description in zip(
        interactions, get_patient_descriptions_from_interactions(interactions)
    ):
        interaction["patient_description"] = description

    print(interactions)
