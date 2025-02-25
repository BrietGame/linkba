import requests
from flask import Flask, render_template, request
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    entreprises = []
    linkedin_profiles = []
    success=False
    if request.method == 'POST' and 'departement' in request.form:
        api_key = request.form.get('api_key', '')
        search = request.form.get('search', '')
        departement = request.form.get('departement', '')
        date_min = request.form.get('date_creation_min', '')
        date_max = request.form.get('date_creation_max', '')

        print(api_key, departement, date_min, date_max)

        # Clé API Pappers (si disponible, sinon scrap manuel)
        BASE_URL = "https://api.pappers.fr/v1/recherche"

        # Paramètres de recherche
        params = {
            "q": search,  # Recherche vide pour toutes les entreprises
            "departement": departement,
            "date_creation_min": date_min,
            "date_creation_max": date_max,
            "api_key": api_key,
            "par_page": 50  # Nombre d'entreprises par page
        }

        # Récupération des entreprises
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        # Extraire les noms des entreprises et des dirigeants
        entreprises = []
        for entreprise in data.get("resultats", []):
            nom_entreprise = entreprise.get("nom_entreprise", "")
            dirigeant = entreprise.get("dirigeants", [{}])[0].get("nom", "") + " " + entreprise.get("dirigeants", [{}])[
                0].get(
                "prenom", "")
            if dirigeant.strip():
                entreprises.append({"Entreprise": nom_entreprise, "Dirigeant": dirigeant})

        # Convertir en DataFrame
        df = pd.DataFrame(entreprises)

        # Sauvegarde des données
        df.to_csv("dirigeants_pappers.csv", index=False)

        print("Données récupérées avec succès !")

        # Initialisation du WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Mode sans interface graphique
        driver = webdriver.Chrome(options=options)

        # Vérification des dirigeants sur LinkedIn
        linkedin_profiles = []
        for _, row in df.iterrows():
            profile_url = search_linkedin_profile(driver, row["Dirigeant"])
            linkedin_profiles.append(
                {"Dirigeant": row["Dirigeant"], "Entreprise": row["Entreprise"], "LinkedIn": profile_url})

        driver.quit()

        # Convertir en DataFrame et sauvegarder
        df_linkedin = pd.DataFrame(linkedin_profiles)
        df_linkedin.to_csv("linkedin_profiles.csv", index=False)

        print("Recherche LinkedIn terminée !")

        # Réouverture du WebDriver pour les invitations
        driver = webdriver.Chrome(options=options)

        driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        username = driver.find_element(By.ID, "username")
        password = driver.find_element(By.ID, "password")
        username.send_keys("VOTRE_EMAIL")
        password.send_keys("VOTRE_MOT_DE_PASSE")
        password.send_keys(Keys.RETURN)
        time.sleep(2)

        for _, row in df_linkedin.iterrows():
            send_invitation(driver, row["LinkedIn"])

        driver.quit()

        print("Toutes les invitations LinkedIn ont été envoyées !")
        success=True


    return render_template('index.html', entreprises=entreprises, linkedin_profiles=linkedin_profiles, success=success)


# Configuration Selenium pour accéder à LinkedIn
def search_linkedin_profile(driver, name):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)

    # Connexion à LinkedIn
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")

    username.send_keys("VOTRE_EMAIL")
    password.send_keys("VOTRE_MOT_DE_PASSE")
    password.send_keys(Keys.RETURN)
    time.sleep(2)

    # Recherche du dirigeant
    search_box = driver.find_element(By.XPATH, "//input[@placeholder='Rechercher']")
    search_box.send_keys(name)
    search_box.send_keys(Keys.RETURN)
    time.sleep(3)

    # Vérification des résultats
    try:
        first_result = driver.find_element(By.XPATH, "//div[contains(@class, 'entity-result__item')]//a")
        profile_url = first_result.get_attribute("href")
        return profile_url
    except:
        return None



# Envoi des invitations LinkedIn
def send_invitation(driver, profile_url):
    if profile_url:
        driver.get(profile_url)
        time.sleep(3)
        try:
            connect_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Se connecter')]")
            connect_button.click()
            time.sleep(2)
            send_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Envoyer maintenant')]")
            send_button.click()
            print(f"Invitation envoyée à {profile_url}")
        except:
            print(f"Impossible d'envoyer une invitation à {profile_url}")




if __name__ == '__main__':
    app.run(debug=True)