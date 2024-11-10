from flask import Flask, request, jsonify
import requests
import json
from bs4 import BeautifulSoup

app = Flask(__name__)


class DrugInteractionChecker:
    def __init__(self, active_ingredient):
        self.active_ingredient = active_ingredient
        self.interactions = self.get_drug_interactions()
        self.unknowns = [
            interaction
            for interaction in self.interactions
            if interaction["severity"] == "Unknown"
        ]
        self.knowns = [
            interaction
            for interaction in self.interactions
            if interaction["severity"] != "Unknown"
        ]
        self.build_interactions()

    def get_drug_interactions(self):
        url = f"https://www.drugs.com/drug-interactions/{self.active_ingredient}.html"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to retrieve data for {self.active_ingredient}")

        soup = BeautifulSoup(response.content, "html.parser")
        interactions_list = soup.find("ul", class_="interactions ddc-list-unstyled")

        if not interactions_list:
            return []

        severity_map = {
            "int_3": "Severe",
            "int_2": "Moderate",
            "int_1": "Minor",
            "int_0": "Unknown",
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

    def get_professional_descriptions_from_interactions(self, interactions):
        descriptions = []
        for interaction in interactions:
            url = interaction["url"] + "?professional=1"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")
            interaction_details = soup.find(
                "div", class_="interactions-reference-wrapper"
            )
            professional_description = interaction_details.find_all("p")[1].get_text()
            descriptions.append(professional_description)
        return descriptions

    def get_patient_descriptions_from_interactions(self, interactions):
        descriptions = []
        for interaction in interactions:
            url = interaction["url"]
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")
            interaction_details = soup.find(
                "div", class_="interactions-reference-wrapper"
            )
            patient_description = interaction_details.find_all("p")[1].get_text()
            descriptions.append(patient_description)
        return descriptions

    def build_interactions(self):
        for interaction, description in zip(
            self.knowns,
            self.get_professional_descriptions_from_interactions(self.knowns),
        ):
            interaction["professional_description"] = description

        for interaction, description in zip(
            self.knowns, self.get_patient_descriptions_from_interactions(self.knowns)
        ):
            interaction["patient_description"] = description


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

        for condition, url in conditions.items():
            distance = levenshtein_distance(input.lower(), condition.lower())
            ratio = 1 - distance / max(len(input), len(condition))
            if ratio > 0.5 and distance < min_distance:
                min_distance = distance
                closest_match = {condition: url}

        return closest_match


def search_existing_drugs(input):
    with open("drugs.json") as f:
        drugs = json.load(f)
        min_distance = float("inf")
        closest_match = None

        for drug, url in drugs.items():
            distance = levenshtein_distance(input.lower(), drug.lower())
            ratio = 1 - distance / max(len(input), len(drug))
            if ratio > 0.5 and distance < min_distance:
                min_distance = distance
                closest_match = {drug: url}

        return closest_match


def parse_drug_table(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data from {url}")

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", class_="ddc-table-secondary ddc-table-sortable")

    drugs = []
    for row in table.find("tbody").find_all("tr", class_="ddc-table-row-medication"):
        cells = row.find_all("td")
        drug = {
            "name": row.find("a", class_="ddc-text-wordbreak").text.strip(),
            "activity": cells[2].find("div")["aria-label"].split(":")[1][0:4].strip(),
            "url": row.find("a", class_="ddc-text-wordbreak")["href"],
        }
        drugs.append(drug)

    return drugs


def translate_professional_to_consumer(professional_description):
    prompt = f"Pretend you are a clinical physician. Translate the following professional drug interaction description into a more consumer-friendly description. Write the consumer-friendly description only; do not prepend anything before your response:\n\n{professional_description}"
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2:3b", "prompt": prompt, "stream": False},
    )

    if response.status_code != 200:
        raise Exception("Failed to generate response")

    response_json = response.json()
    return response_json["response"]


@app.route("/drug_interactions", methods=["GET"])
def get_drug_interactions():
    active_ingredient = request.args.get("active_ingredient")
    if not active_ingredient:
        return jsonify({"error": "active_ingredient parameter is required"}), 400

    checker = DrugInteractionChecker(active_ingredient)
    return jsonify(checker.interactions)


@app.route("/search_conditions", methods=["GET"])
def search_conditions():
    input = request.args.get("input")
    if not input:
        return jsonify({"error": "input parameter is required"}), 400

    result = search_existing_conditions(input)
    return jsonify(result)


@app.route("/search_drugs", methods=["GET"])
def search_drugs():
    input = request.args.get("input")
    if not input:
        return jsonify({"error": "input parameter is required"}), 400

    result = search_existing_drugs(input)
    return jsonify(result)


@app.route("/drug_table", methods=["GET"])
def drug_table():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url parameter is required"}), 400

    try:
        drug_data = parse_drug_table(url)
        return jsonify(drug_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/translate_description", methods=["POST"])
def translate_description():
    data = request.get_json()
    professional_description = data.get("professional_description")
    if not professional_description:
        return jsonify({"error": "professional_description parameter is required"}), 400

    try:
        consumer_description = translate_professional_to_consumer(
            professional_description
        )
        return jsonify({"consumer_description": consumer_description})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
