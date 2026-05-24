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

AUTH_FILE = STORIES_DIR / "session.json"   # gespeicherte Login-Session


def _do_login(page) -> bool:
    """Führt Login durch. Gibt True zurück wenn erfolgreich."""
    try:
        page.wait_for_selector("input[placeholder='E-mail']",
                               state="visible", timeout=15000)
        page.fill("input[placeholder='E-mail']", EMAIL)
        page.fill("input[type='password']", PASSWORD)
        page.click("button:has-text('Sign In')")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        # Prüfen ob Login erfolgreich (kein Login-Formular mehr)
        if page.locator("input[placeholder='E-mail']").count() == 0:
            print("🔐 Login erfolgreich.")
            return True
        print("❌ Login fehlgeschlagen – falsche Zugangsdaten?")
        return False
    except Exception as e:
        print(f"Login-Fehler: {e}")
        return False


def _fill_chapter(page, title: str, story: str, image_path: str):
    """Befüllt das Create-Chapter Formular."""

    # ── Titel ────────────────────────────────────────────────────────────────
    page.wait_for_selector("textarea[placeholder='Chapter Title']", timeout=15000)
    page.fill("textarea[placeholder='Chapter Title']", title[:45])
    time.sleep(0.5)
    print(f"✏️  Titel eingetragen: {title[:45]}")

    # ── Bild ─────────────────────────────────────────────────────────────────
    if image_path and os.path.exists(image_path):
        try:
            with page.expect_file_chooser(timeout=6000) as fc:
                page.click("button.edit-image-button__button--upload")
            fc.value.set_files(image_path)
            time.sleep(3)
            print("🖼️  Bild hochgeladen.")
        except Exception as exc:
            print(f"⚠️  Bild-Upload übersprungen: {exc}")

    # ── Text-Editor öffnen ───────────────────────────────────────────────────
    try:
        page.locator("div.detailsbox").filter(
            has_text="Chapter Text"
        ).locator("button.detailsbox__absolute-btn").click(timeout=6000)
    except Exception:
        page.locator("button.detailsbox__absolute-btn").last.click()

    page.wait_for_url("**#/editor**", timeout=12000)
    time.sleep(2)

    # ── Text in Quill einfügen ───────────────────────────────────────────────
    page.evaluate("""(text) => {
        const ed = document.querySelector('.ql-editor');
        if (!ed) return;
        ed.innerHTML = '';
        text.split('\\n').forEach(line => {
            const p = document.createElement('p');
            p.textContent = line;
            ed.appendChild(p);
        });
        ed.dispatchEvent(new Event('input', { bubbles: true }));
    }""", story[:3400])
    time.sleep(1)
    print("📝 Text eingetragen.")

    # ── Done → zurück ────────────────────────────────────────────────────────
    page.click("button:has-text('Done')")
    page.wait_for_url("**start-writing**", timeout=12000)
    time.sleep(2)

    # ── Als Entwurf speichern (KEIN Publish) ─────────────────────────────────
    page.click("button:has-text('Save privately')")
    time.sleep(2)
    print("💾 Als Entwurf gespeichert.")


def upload_to_storyone(title: str, story: str, image_path: str) -> None:
    """Selbstheilender Upload-Loop mit persistenter Session."""

    print("🌐 Starte Playwright ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=SLOWMO)

        for attempt in range(1, 4):          # bis zu 3 Versuche
            print(f"\n{'='*50}\n🔄 Versuch {attempt}/3\n{'='*50}")
            context = None
            try:
                # ── Session laden oder neu erstellen ──────────────────────────
                if AUTH_FILE.exists() and attempt == 1:
                    context = browser.new_context(storage_state=str(AUTH_FILE))
                    print("✅ Gespeicherte Session geladen – kein Login nötig.")
                else:
                    context = browser.new_context()

                page = context.new_page()
                page.set_viewport_size({"width": 1920, "height": 1080})

                # ── Popup-Killer per init_script ──────────────────────────────
                page.add_init_script("""
                    const kill = new MutationObserver(() => {
                        // Cookie-Banner
                        document.querySelectorAll('button').forEach(b => {
                            if (b.textContent.trim() === 'Accept all') b.click();
                        });
                        // Alle Modals schließen die KEIN Login-Input haben
                        document.querySelectorAll('button.modal__close-button').forEach(b => {
                            const m = b.closest('[class*="modal"]') || b.parentElement;
                            if (m && !m.querySelector('input[placeholder="E-mail"]'))
                                b.click();
                        });
                    });
                    kill.observe(document.documentElement,
                                 {childList:true, subtree:true});
                """)

                # ── Zur Create-Chapter Seite ──────────────────────────────────
                page.goto("https://www.story.one/en/start-writing/?type=story#/")
                page.wait_for_load_state("networkidle")
                time.sleep(3)

                # ── Login nötig? ──────────────────────────────────────────────
                if page.locator("input[placeholder='E-mail']").count() > 0:
                    print("🔑 Login erforderlich ...")
                    if AUTH_FILE.exists():
                        AUTH_FILE.unlink()      # abgelaufene Session löschen
                    if not _do_login(page):
                        raise Exception("Login fehlgeschlagen")
                    # Session für nächste Läufe speichern
                    context.storage_state(path=str(AUTH_FILE))
                    print(f"💾 Session gespeichert → {AUTH_FILE}")
                    page.goto("https://www.story.one/en/start-writing/?type=story#/")
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)

                # ── Formular ausfüllen ────────────────────────────────────────
                _fill_chapter(page, title, story, image_path)

                print("\n" + "=" * 60)
                print("✅ Geschichte als Entwurf bereit!")
                print("⏸️  Browser bleibt 5 Minuten offen.")
                print("   → Klicke auf 'Share on StoryOne' zum Veröffentlichen.")
                print("=" * 60)
                time.sleep(300)
                break  # Erfolg – Loop beenden

            except Exception as exc:
                print(f"\n❌ Fehler in Versuch {attempt}: {exc}")
                # Screenshot zur Diagnose speichern
                try:
                    ss = STORIES_DIR / f"error_attempt{attempt}.png"
                    page.screenshot(path=str(ss))
                    print(f"📸 Screenshot gespeichert: {ss}")
                except Exception:
                    pass
                # Session löschen damit nächster Versuch frisch startet
                if AUTH_FILE.exists():
                    AUTH_FILE.unlink()
                if attempt == 3:
                    print("❌ Alle 3 Versuche fehlgeschlagen.")
                else:
                    print(f"⏳ Warte 5s, dann Versuch {attempt+1} ...")
                    time.sleep(5)
            finally:
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass

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
