# StoryOne Bot

Ein automatischer Bot zum Erstellen und Veröffentlichen von Geschichten auf StoryOne.

## Features

- Automatische Generierung von Geschichten mit GPT-4
- Erstellung passender Titel
- Generierung von Bildern mit DALL-E 3
- Automatisches Hochladen auf StoryOne
- Selenium-basierte Web-Automation

## Installation

1. Repository klonen:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Virtuelle Umgebung erstellen und aktivieren:
```bash
python -m venv venv
source venv/bin/activate  # Für Unix/MacOS
# oder
.\venv\Scripts\activate  # Für Windows
```

3. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

4. `.env` Datei erstellen und API-Keys eintragen:
```
OPENAI_API_KEY=your_openai_api_key
GOOGLE_BOOKS_API_KEY=your_google_books_api_key
EMAIL=your_storyone_email
PASSWORD=your_storyone_password
```

## Verwendung

1. Aktivieren Sie die virtuelle Umgebung
2. Führen Sie das Skript aus:
```bash
python 2024_12_26_Bot_Story_One.py
```

## Abhängigkeiten

- Python 3.x
- Selenium
- OpenAI
- python-dotenv
- requests
- Pillow

## Lizenz

MIT 