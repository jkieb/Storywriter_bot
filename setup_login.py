"""
setup_login.py – Einmalig ausführen um die Login-Session zu speichern.
Danach braucht storybot.py nie mehr einzuloggen.

Ausführen:
    source venv/bin/activate
    python3 setup_login.py
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

AUTH_FILE = Path("generated_stories/session.json")
AUTH_FILE.parent.mkdir(exist_ok=True)

print("=" * 55)
print("  StoryOne Login-Setup")
print("=" * 55)
print()
print("Ein Browser öffnet sich. Bitte:")
print("  1. Cookie-Banner wegklicken")
print("  2. Newsletter-Popup schließen")
print("  3. Einloggen mit deinen Zugangsdaten")
print()
print("Der Bot erkennt automatisch wenn du eingeloggt bist.")
print("=" * 55)
input("Drücke ENTER um den Browser zu öffnen ...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.set_viewport_size({"width": 1400, "height": 900})

    page.goto("https://www.story.one/en/start-writing/?type=story#/")

    print("\n⏳ Warte auf deinen Login ...")
    print("   (Du hast 3 Minuten Zeit)\n")

    logged_in = False
    for i in range(180):  # 3 Minuten
        try:
            # Prüfen ob Create-Chapter Seite sichtbar ist = eingeloggt
            if page.locator("textarea[placeholder='Chapter Title']").count() > 0:
                logged_in = True
                break
        except Exception:
            pass
        time.sleep(1)
        if i % 15 == 14:
            remaining = 180 - i - 1
            print(f"   Noch {remaining}s ...")

    if logged_in:
        # Session speichern
        context.storage_state(path=str(AUTH_FILE))
        print(f"\n✅ Login erfolgreich!")
        print(f"💾 Session gespeichert: {AUTH_FILE}")
        print("\nDu kannst den Browser jetzt schließen.")
        print("Starte den Bot mit: bash start.sh")
    else:
        print("\n❌ Timeout – kein Login erkannt.")
        print("   Bitte nochmal versuchen.")

    time.sleep(5)
    browser.close()
