async function checkDrugExists(drug) {
  const response = await fetch("http://127.0.0.1:5000/process_current_meds", {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ drugs: drug })
  });

  const data = await response.json();

  if (data.not_found_drugs.length > 0) {
      const modal = document.getElementById("errorModal");
      modal.style.display = "block";
      document.getElementById("errorMessage").innerText = `The following drugs were not found: ${data.not_found_drugs.join(', ')}`;
      return false;
  }

  return true;
}


async function checkConditionExists(condition) {
  const response = await fetch(`http://127.0.0.1:5000/search_conditions?input=${encodeURIComponent(condition)}`);
  const data = await response.json();

  if (!data || !data[0]) {
    const modal = document.getElementById("errorModal");
    modal.style.display = "block";
    document.getElementById("errorMessage").innerText = "Condition not found.";
    return false;
  }

  return true;
}

async function checkMedicationsExist(medicationsInput) {
  const medicationsList = medicationsInput.split(',').map(medication => medication.trim());

  // Check the length of the medications list
  if (medicationsList.length > 16) {
      alert('You cannot enter more than 16 medications.');
      return false;
  }

  // Send the array of medications to the backend
  const response = await fetch("http://127.0.0.1:5000/process_current_meds", {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ drugs: medicationsList })  // Send the array here
  });

  const data = await response.json();

  // Check if any drugs weren't found
  if (data.not_found_drugs.length > 0) {
      const modal = document.getElementById("errorModal");
      modal.style.display = "block";
      document.getElementById("errorMessage").innerText = `The following medications were not found: ${data.not_found_drugs.join(', ')}`;
      return false;
  }

  return true;
}

async function checkDrugInteraction() {
  const drugInput = document.getElementById("drugInput").value;
  const conditionInput = document.getElementById("conditionInput").value;
  const medicationsInput = document.getElementById("medicationsInput").value;
  const resultsContainer = document.getElementById("results");

  const drugsList = medicationsInput.split(',').map(drug => drug.trim());

  if (drugsList.length > 16) {
      alert('You cannot enter more than 16 drugs.');
      return;
  }
  
  const drugExists = await checkDrugExists(drugsList);
  if (!drugExists) {
      return; 
  }

  const conditionExists = await checkConditionExists(conditionInput);
  if (!conditionExists) {
      return; 
  }

  const medicationsExist = await checkMedicationsExist(medicationsInput);
  if (!medicationsExist) {
      return;
  }

  resultsContainer.innerHTML = '<p>Loading...</p>';

  try {
      const response = await fetch("http://127.0.0.1:5000/check_drug_interactions", {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              drugs: drugsList.join(','),
              prescribed_drug: drugInput.trim()
          })
      });

      const data = await response.json();

      resultsContainer.innerHTML = '';
      if (data.interactions.length === 0) {
          resultsContainer.innerHTML = '<p>No interactions found.</p>';
      } else {
          data.interactions.forEach(interaction => {
              const item = document.createElement('div');
              item.className = 'result-item';
              item.innerHTML = `
                  <p><strong>${interaction.drug}</strong></p>
                  <p>Interaction: ${interaction.interaction}</p>
                  <p>Severity: <strong>${interaction.severity}</strong></p>
                  <p><strong>Professional Description:</strong> ${interaction.professional_description}</p>
                  <p><strong>Patient Description:</strong> ${interaction.patient_description}</p>
              `;
              resultsContainer.appendChild(item);
          });
      }
  } catch (error) {
      resultsContainer.innerHTML = `<p>Failed to fetch data: ${error.message}</p>`;
  }
}

window.onclick = function(event) {
  const modal = document.getElementById("errorModal");
  if (event.target == modal || event.target.classList.contains("close")) {
    modal.style.display = "none";
  }
};