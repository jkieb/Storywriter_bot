"""
StoryOne Bot – komplett kostenlose Version
- Themen: aktuelle Nachrichten via RSS (kein API-Key)
- LLM: Groq API mit Llama 3.3 70B (kostenlos)
- Bilder: Pollinations.ai (kostenlos, kein Key)
- Playwright: füllt StoryOne aus, veröffentlicht NICHT automatisch
- Speichert jede Geschichte lokal als .txt Datei
"""

import time
import os
import re
import requests
import feedparser
import random
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from groq import Groq
from dotenv import load_dotenv

# ── Konfiguration ──────────────────────────────────────────────────────────────
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMAIL        = os.getenv("EMAIL")
PASSWORD     = os.getenv("PASSWORD")
SLOWMO       = 500 if os.getenv("PLAYWRIGHT_SLOWMO") == "1" else 0

STORIES_DIR = Path("generated_stories")
STORIES_DIR.mkdir(exist_ok=True)

groq_client = Groq(api_key=GROQ_API_KEY)

# ── RSS-Nachrichtenquellen (deutsch + international, kein Key nötig) ───────────
RSS_FEEDS = [
    "https://www.spiegel.de/schlagzeilen/index.rss",
    "https://www.tagesschau.de/xml/rss2/",
    "https://www.zeit.de/rss",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.dw.com/rdf/rss-de-all",
]

def fetch_current_news_topic() -> str:
    """Holt aktuelle Schlagzeilen aus RSS-Feeds und wählt ein Thema aus."""
    headlines = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                if title:
                    headlines.append(f"{title}. {summary[:150]}" if summary else title)
        except Exception as exc:
            print(f"RSS-Fehler ({feed_url}): {exc}")

    if not headlines:
        return "Eine unerwartete Begegnung verändert das Leben zweier Menschen"

    chosen = random.choice(headlines)
    print(f"📰 Gewähltes Nachrichtenthema: {chosen[:100]}...")
    return chosen


# ── Groq / Llama ───────────────────────────────────────────────────────────────

def generate_title(topic: str) -> str:
    """Generiert einen packenden Titel mit Llama 3.3."""
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein kreativer Titelgeber für Kurzgeschichten. "
                    "Deine Titel sind kurz (max. 6 Wörter), neugierig machend und emotional. "
                    "Antworte NUR mit dem Titel, ohne Anführungszeichen."
                ),
            },
            {
                "role": "user",
                "content": f"Erstelle einen fesselnden Titel für eine Geschichte basierend auf: {topic}",
            },
        ],
        max_tokens=50,
        temperature=0.9,
    )
    return resp.choices[0].message.content.strip().strip('"').strip("'")


def generate_story(topic: str) -> str:
    """Schreibt eine Kurzgeschichte mit Llama 3.3 (max. 400 Wörter)."""
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein erfahrener deutschsprachiger Kurzgeschichtenautor. "
                    "Deine Geschichten haben:\n"
                    "- Eine klare Struktur (Einleitung → Konflikt → Höhepunkt → Auflösung)\n"
                    "- Lebendige Charaktere mit Persönlichkeit\n"
                    "- Natürliche Dialoge\n"
                    "- Emotionale Tiefe und bildhafte Sprache\n"
                    "- Maximal 400 Wörter\n"
                    "Schreibe direkt die Geschichte, ohne Überschrift."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Schreibe eine fesselnde Kurzgeschichte inspiriert von diesem aktuellen Thema: {topic}\n\n"
                    "Die Geschichte muss nicht direkt über das Nachrichtenereignis sein – "
                    "lass dich davon inspirieren und erschaffe eine menschliche, emotionale Erzählung."
                ),
            },
        ],
        max_tokens=700,
        temperature=0.85,
    )
    return resp.choices[0].message.content.strip()


# ── Pollinations.ai Bildgenerierung (kostenlos, kein Key) ─────────────────────

def generate_image(story_text: str, title: str) -> str:
    """Generiert ein Bild via Pollinations.ai und speichert es lokal."""
    # Kurzen Bildprompt aus Titel + ersten Sätzen erstellen
    short_prompt = f"Artistic book cover illustration for: {title}. {story_text[:200]}"
    short_prompt = re.sub(r'[^\w\s,.!?-]', '', short_prompt)[:300]

    # Pollinations URL aufbauen
    import urllib.parse
    encoded = urllib.parse.quote(short_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&model=flux"

    print(f"🎨 Generiere Bild via Pollinations.ai ...")
    img_path = STORIES_DIR / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(resp.content)
        print(f"✅ Bild gespeichert: {img_path}")
        return str(img_path)
    except Exception as exc:
        print(f"Bildfehler: {exc}")
        return ""


# ── Lokale Speicherung ─────────────────────────────────────────────────────────

def save_story_locally(title: str, topic: str, story: str, image_path: str) -> str:
    """Speichert Geschichte als .txt Datei."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip()
    filename = STORIES_DIR / f"{timestamp}_{safe_title}.txt"

    content = f"""StoryOne Bot – Generierte Geschichte
======================================
Datum:    {datetime.now().strftime('%d.%m.%Y %H:%M')}
Titel:    {title}
Thema:    {topic[:200]}
Bild:     {image_path or 'nicht generiert'}
======================================

{story}
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"💾 Geschichte gespeichert: {filename}")
    return str(filename)


# ── Playwright – StoryOne befüllen (OHNE Veröffentlichen) ─────────────────────

def upload_to_storyone(title: str, story: str, image_path: str) -> None:
    """Öffnet StoryOne (neue Struktur 2025), loggt ein, füllt alles aus.
    Stoppt VOR dem Klick auf 'Share on StoryOne'."""

    print("🌐 Starte Playwright ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=SLOWMO)
        context = browser.new_context()
        page = context.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        # ── Popup-Killer: wird VOR dem Laden der Seite injiziert ───────────────
        # Setzt localStorage-Flags und beobachtet den DOM automatisch
        page.add_init_script("""
            // Newsletter-Popup via localStorage unterdrücken
            try {
                localStorage.setItem('newsletter_closed', '1');
                localStorage.setItem('newsletter_shown', '1');
                localStorage.setItem('popupShown', '1');
                localStorage.setItem('subscribePopupShown', '1');
                localStorage.setItem('newsletterDismissed', '1');
            } catch(e) {}

            // MutationObserver: schließt automatisch jeden Popup
            // der KEIN Login-Formular enthält
            const killer = new MutationObserver(() => {
                // Cookie-Banner
                document.querySelectorAll(
                    'button.button--style--primary'
                ).forEach(btn => {
                    if (btn.textContent.includes('Accept')) btn.click();
                });
                // Alle Close-Buttons von Nicht-Login-Modals
                document.querySelectorAll('button.modal__close-button').forEach(btn => {
                    try {
                        const modal = btn.closest('[class*="modal"]')
                                   || btn.closest('[class*="overlay"]')
                                   || btn.parentElement;
                        const isLogin = modal &&
                            (modal.querySelector('input[placeholder="E-mail"]') ||
                             modal.querySelector('input[type="email"]'));
                        if (!isLogin) btn.click();
                    } catch(e) {}
                });
            });
            killer.observe(document.documentElement,
                           { childList: true, subtree: true });
        """)

        try:
            # ── Navigation zur Login-Seite ─────────────────────────────────────
            print("⏳ Lade StoryOne ...")
            page.goto("https://www.story.one/en/start-writing/?type=story#/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # ── Login-Formular ausfüllen ───────────────────────────────────────
            print("⏳ Warte auf Login-Formular ...")
            page.wait_for_selector("input[placeholder='E-mail']",
                                   state="visible", timeout=30000)
            print("✅ Login-Formular sichtbar.")

            page.fill("input[placeholder='E-mail']", EMAIL)
            page.fill("input[type='password']", PASSWORD)
            page.click("button:has-text('Sign In')")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            print("🔐 Eingeloggt.")

            # ── Titel eintragen ────────────────────────────────────────────────
            # Titel max. 45 Zeichen (Limit der neuen Website)
            title_short = title[:45]
            page.wait_for_selector("textarea[placeholder='Chapter Title']", timeout=15000)
            page.fill("textarea[placeholder='Chapter Title']", title_short)
            time.sleep(1)

            # ── Bild hochladen (Preview Image) ────────────────────────────────
            if image_path and os.path.exists(image_path):
                try:
                    with page.expect_file_chooser(timeout=8000) as fc:
                        page.click("button.edit-image-button__button--upload")
                    fc.value.set_files(image_path)
                    time.sleep(3)
                    print("✅ Bild hochgeladen.")
                except Exception as exc:
                    print(f"⚠️  Bild-Upload Fehler: {exc}")

            # ── Text-Editor öffnen via "+" bei "Chapter Text" ─────────────────
            chapter_text_plus = page.locator(
                "div.detailsbox"
            ).filter(has_text="Chapter Text").locator("button.detailsbox__absolute-btn")
            try:
                chapter_text_plus.click(timeout=8000)
            except Exception:
                # Fallback: direkt den letzten "+" Button klicken
                page.locator("button.detailsbox__absolute-btn").last.click()
            page.wait_for_url("**#/editor**", timeout=10000)
            time.sleep(2)

            # ── Text in Quill-Editor einfügen ─────────────────────────────────
            # Quill Editor: div.ql-editor (max. ~3500 Zeichen)
            story_short = story[:3400]
            editor = page.locator("div.ql-editor").first
            editor.click()
            time.sleep(0.5)
            # Text via JavaScript einfügen (zuverlässiger als type() bei Quill)
            page.evaluate(
                """(text) => {
                    const editor = document.querySelector('.ql-editor');
                    editor.innerHTML = '';
                    const lines = text.split('\\n');
                    lines.forEach(line => {
                        const p = document.createElement('p');
                        p.textContent = line;
                        editor.appendChild(p);
                    });
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                }""",
                story_short
            )
            time.sleep(1)

            # ── "Done" klicken → zurück zur Chapter-Übersicht ─────────────────
            page.click("button:has-text('Done')")
            page.wait_for_url("**start-writing**", timeout=10000)
            time.sleep(2)

            # ── STOPP – NICHT veröffentlichen ──────────────────────────────────
            # "Save privately" speichert als Entwurf
            page.click("button:has-text('Save privately')")
            time.sleep(2)

            print("\n" + "=" * 60)
            print("✅ Geschichte als Entwurf gespeichert!")
            print("⏸️  Browser bleibt 5 Minuten offen.")
            print("   Klicke selbst auf 'Share on StoryOne' zum Veröffentlichen.")
            print("=" * 60)
            time.sleep(300)

        except Exception as exc:
            print(f"❌ Playwright-Fehler: {exc}")
            import traceback
            traceback.print_exc()
            time.sleep(30)
        finally:
            browser.close()
            print("🔒 Browser geschlossen.")


# ── Hauptprogramm ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("   StoryOne Bot – Kostenlose Version")
    print("=" * 60)

    try:
        # 1. Aktuelles Nachrichtenthema holen
        topic = fetch_current_news_topic()

        # 2. Titel generieren
        print("✍️  Generiere Titel ...")
        title = generate_title(topic)
        print(f"📖 Titel: {title}")

        # 3. Geschichte schreiben
        print("📝 Schreibe Geschichte ...")
        story = generate_story(topic)
        print(f"Geschichte ({len(story.split())} Wörter) generiert.")

        # 4. Bild generieren
        image_path = generate_image(story, title)

        # 5. Lokal speichern
        saved_path = save_story_locally(title, topic, story, image_path)

        print("\n" + "=" * 60)
        print(f"✅ FERTIG")
        print(f"📖 Titel:   {title}")
        print(f"💾 Datei:   {saved_path}")
        print(f"🖼️  Bild:    {image_path or 'nicht generiert'}")
        print("=" * 60)

        # 6. StoryOne befüllen (ohne Veröffentlichen)
        if EMAIL and PASSWORD:
            upload_to_storyone(title, story, image_path)
        else:
            print("⚠️  EMAIL/PASSWORD fehlen in .env – Playwright übersprungen.")

    except Exception as exc:
        print(f"❌ Fehler: {exc}")
        raise
