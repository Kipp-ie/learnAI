import flet as ft
import requests
import json
import asyncio
import os # Voor het ophalen van omgevingsvariabelen

# Firebase gerelateerde globale variabelen uit de Canvas-omgeving (niet direct gebruikt door Flet's Python backend voor API-aanroepen in dit voorbeeld)
# Voor een Flet-app zouden deze doorgaans worden afgehandeld via omgevingsvariabelen of een veilig configuratiesysteem
# als de Flet-app zelf moest communiceren met Firebase-services.
__app_id = os.environ.get('CANVAS_APP_ID', 'flet-quiz-app') # Terugval voor lokaal testen
__firebase_config = os.environ.get('CANVAS_FIREBASE_CONFIG', '{}')
__initial_auth_token = os.environ.get('CANVAS_INITIAL_AUTH_TOKEN', '')

# Gemini API configuratie
# BELANGRIJK: Voer hier uw Gemini API-sleutel in, of stel deze in als een omgevingsvariabele (bijv. GEMINI_API_KEY).
# U kunt uw API-sleutel verkrijgen via Google AI Studio: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyA2BIlqvka-ucA1Sq2HFxW7HpnBqrwZEwk"

# De basis-URL voor de Gemini API
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

async def main(page: ft.Page):
    """
    De hoofd functie van de Flet applicatie.
    Initialiseert de UI en de logica voor het genereren van quizvragen.
    """
    page.title = "Samenvatting Overhoor App"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 800
    page.window_height = 600
    page.bgcolor = ft.Colors.BLUE_GREY_50 # Een zachte achtergrondkleur (gecorrigeerd naar ft.Colors)
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap", # Laad het Inter lettertype
    }
    page.theme = ft.Theme(font_family="Inter") # Pas het Inter lettertype toe op de hele pagina

    # UI-elementen
    summary_input = ft.TextField(
        label="Plak hier je samenvatting",
        multiline=True,
        min_lines=10,
        max_lines=20,
        width=600,
        hint_text="Type of plak hier de tekst die je wilt overhoren (bijv. aantekeningen, een hoofdstuk).",
        border_radius=ft.border_radius.all(10), # Afgeronde hoeken
        filled=True,
        bgcolor=ft.Colors.WHITE, # Gecorrigeerd naar ft.Colors
        content_padding=15,
        autofocus=True,
    )

    quiz_area = ft.Column(
        [
            ft.Text("Quiz Vragen", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900), # Gecorrigeerd naar ft.Colors
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15,
        visible=False, # Initieel niet zichtbaar
        width=700, # Breedte van de quizsectie
    )

    loading_indicator = ft.ProgressRing(width=30, height=30, stroke_width=3, visible=False, color=ft.Colors.ORANGE_600) # Gecorrigeerd naar ft.Colors
    status_message = ft.Text("", color=ft.Colors.RED_500, size=14, weight=ft.FontWeight.BOLD) # Gecorrigeerd naar ft.Colors

    # Dictionary om verwijzingen naar de feedback tekstcontroles op te slaan
    feedback_controls = {}

    def check_answer(e, correct_answer, question_index):
        """
        Controleert of het geselecteerde antwoord correct is en geeft feedback.
        """
        selected_answer = e.control.value
        # Haal de feedback tekstcontrole op via de opgeslagen referentie
        feedback_text_control = feedback_controls.get(question_index)

        if feedback_text_control:
            if selected_answer == correct_answer:
                feedback_text_control.value = f"Correct! '{correct_answer}'"
                feedback_text_control.color = ft.Colors.GREEN_700 # Groen voor correct (gecorrigeerd naar ft.Colors)
            else:
                feedback_text_control.value = f"Niet correct. Het juiste antwoord was: '{correct_answer}'"
                feedback_text_control.color = ft.Colors.RED_700 # Rood voor incorrect (gecorrigeerd naar ft.Colors)
            feedback_text_control.update() # Update alleen het feedbackelement
        else:
            print(f"Fout: Feedback control voor vraag {question_index} niet gevonden.") # Debugging

    async def generate_quiz_questions(e):
        """
        Genereert quizvragen met behulp van de Gemini API op basis van de ingevoerde samenvatting.
        """
        summary_text = summary_input.value
        if not summary_text.strip():
            status_message.value = "Plak eerst een samenvatting in het tekstveld voordat u vragen genereert."
            status_message.update()
            return

        # Controleer of de API-sleutel is opgegeven
        if not GEMINI_API_KEY:
            status_message.value = "Geen Gemini API-sleutel gevonden. Voer deze in de code in of als omgevingsvariabele."
            status_message.update()
            return

        # Reset status en toon laadindicator
        status_message.value = ""
        loading_indicator.visible = True
        quiz_area.visible = False # Verberg de vorige quizresultaten
        quiz_area.controls.clear() # Wis de vorige quizvragen
        feedback_controls.clear() # Wis ook de opgeslagen referenties
        page.update()

        # Prompt voor de Gemini API om meerkeuzevragen te genereren in een specifiek JSON-formaat
        prompt = (
            f"Creëer 5 meerkeuzevragen (inclusief het juiste antwoord en 3 onjuiste antwoorden) gebaseerd op de volgende samenvatting. "
            f"Geef de uitvoer op in een strikt JSON-formaat, met een array van objecten, waarbij elk object een 'vraag' (string), "
            f"een array 'antwoorden' (van strings, inclusief alle 4 opties) en 'correct_antwoord' (string) bevat. "
            f"Zorg ervoor dat het JSON-formaat correct is en gemakkelijk kan worden geparset. "
            f"Samenvatting: \n\n{summary_text}"
        )

        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]

        payload = {
            "contents": chat_history,
            "generationConfig": {
                "responseMimeType": "application/json", # Vraag om een JSON-antwoord
                "responseSchema": { # Definieer het schema van het verwachte JSON-antwoord
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "vraag": {"type": "STRING"},
                            "antwoorden": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"}
                            },
                            "correct_antwoord": {"type": "STRING"}
                        },
                        "propertyOrdering": ["vraag", "antwoorden", "correct_antwoord"] # Definieer de volgorde van eigenschappen
                    }
                }
            }
        }

        headers = {'Content-Type': 'application/json'} # Headers voor de HTTP-aanvraag

        try:
            # Voer de HTTP POST-aanvraag uit naar de Gemini API
            # asyncio.to_thread wordt gebruikt om de blocking requests.post-oproep asynchroon uit te voeren
            # zodat de UI niet bevriest. De API-sleutel wordt toegevoegd als queryparameter.
            response = await asyncio.to_thread(
                lambda: requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, data=json.dumps(payload))
            )
            response.raise_for_status() # Roept een HTTPError op voor foutieve statuscodes (4xx of 5xx)

            result = response.json() # Parseer de JSON-respons

            if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                raw_json_str = result["candidates"][0]["content"]["parts"][0]["text"]
                # Soms omhult het model JSON in een markdown codeblok; verwijder dit indien aanwezig.
                if raw_json_str.startswith("```json") and raw_json_str.endswith("```"):
                    raw_json_str = raw_json_str[7:-3].strip()

                parsed_quiz = json.loads(raw_json_str) # Parseer de JSON-string naar een Python-object

                quiz_area.controls.append(ft.Text("Quiz Vragen", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)) # Gecorrigeerd naar ft.Colors

                # Loop door de gegenereerde vragen en voeg ze toe aan de UI
                for i, q_data in enumerate(parsed_quiz):
                    question_text = q_data.get("vraag", "Geen vraag gevonden")
                    answers = q_data.get("antwoorden", [])
                    correct_answer = q_data.get("correct_antwoord", "")

                    # Maak de feedback tekstcontrole en sla de referentie op
                    feedback_text_control = ft.Text(
                        "",
                        size=14,
                        color=ft.Colors.BLACK, # Gecorrigeerd naar ft.Colors
                        weight=ft.FontWeight.BOLD,
                    )
                    feedback_controls[i] = feedback_text_control # Sla de referentie op

                    # Kaart voor elke vraag
                    question_card = ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(f"Vraag {i+1}: {question_text}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800), # Gecorrigeerd naar ft.Colors
                                    ft.Divider(height=10, color=ft.Colors.BLUE_GREY_200), # Gecorrigeerd naar ft.Colors
                                    ft.RadioGroup(
                                        content=ft.Column(
                                            [
                                                ft.Radio(value=ans, label=ans, fill_color=ft.Colors.ORANGE_500) # Oranje radiobutton, favoriete kleur van de gebruiker (gecorrigeerd naar ft.Colors)
                                                for ans in answers
                                            ]
                                        ),
                                        on_change=lambda e, correct=correct_answer, q_idx=i: check_answer(e, correct, q_idx)
                                    ),
                                    feedback_text_control # Voeg de feedback tekstcontrole toe
                                ]
                            ),
                            padding=20,
                        ),
                        elevation=8, # Verhoogde schaduw voor betere visuele scheiding
                        margin=ft.margin.symmetric(vertical=10),
                        width=700,
                        # Meer afgeronde hoeken
                        # Gecorrigeerd naar ft.Colors
                    )
                    quiz_area.controls.append(question_card)

                quiz_area.visible = True # Maak de quizsectie zichtbaar
            else:
                status_message.value = "Kon geen quizvragen genereren. De API gaf een onverwacht antwoord."

        except requests.exceptions.RequestException as req_err:
            status_message.value = f"Netwerkfout bij het verbinden met de Gemini API: {req_err}"
        except json.JSONDecodeError as json_err:
            status_message.value = f"Fout bij het parsen van het JSON-antwoord van de API. Dit kan duiden op een ongeldig formaat van de AI: {json_err}"
        except Exception as e:
            status_message.value = f"Een onverwachte fout is opgetreden: {e}"
        finally:
            loading_indicator.visible = False # Verberg laadindicator
            page.update() # Update de pagina UI

    # Hoofdlay-out van de pagina
    page.add(
        ft.Column(
            [
                ft.Text("Samenvatting Overhoor App", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900), # Gecorrigeerd naar ft.Colors
                ft.Text(
                    "Plak je samenvatting en laat Gemini API je overhoren met meerkeuzevragen.",
                    size=16,
                    color=ft.Colors.BLUE_GREY_700, # Gecorrigeerd naar ft.Colors
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Divider(height=20, color=ft.Colors.BLUE_GREY_300), # Visuele scheiding (gecorrigeerd naar ft.Colors)

                summary_input, # Tekstveld voor samenvatting

                ft.Row(
                    [
                        ft.ElevatedButton(
                            text="Onderwerpen Overhoren",
                            icon=ft.Icons.QUIZ_ROUNDED, # Gecorrigeerd naar ft.Icons
                            on_click=generate_quiz_questions,
                            bgcolor=ft.Colors.ORANGE_600, # Gebruikers favoriete kleur: Oranje (gecorrigeerd naar ft.Colors)
                            color=ft.Colors.WHITE, # Gecorrigeerd naar ft.Colors
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(10)),
                                padding=ft.padding.all(15),
                                animation_duration=200,
                            ),
                        ),
                        loading_indicator, # Laadindicator naast de knop
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                ),
                status_message, # Voor foutmeldingen of statusupdates
                ft.Divider(height=30, color=ft.Colors.BLUE_GREY_300), # Gecorrigeerd naar ft.Colors

                quiz_area, # Container voor de quizvragen
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True, # Zorgt ervoor dat de kolom de beschikbare ruimte vult
            scroll=ft.ScrollMode.AUTO, # Voeg scrollen toe als de inhoud te groot wordt
        )
    )

# De app starten. Voor lokaal testen:
ft.app(target=main)
# Om deze Flet-app lokaal uit te voeren:
# 1. Zorg ervoor dat u Flet en Requests hebt geïnstalleerd:
#    pip install flet requests
# 2. Voeg uw Gemini API-sleutel toe aan de variabele GEMINI_API_KEY in de code.
#    Of stel deze in als een omgevingsvariabele genaamd GEMINI_API_KEY.
# 3. Voer het script uit: python uw_script_naam.py
# Flet zal standaard een webserver starten en de app in uw browser openen.
