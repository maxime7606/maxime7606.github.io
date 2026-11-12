"""Récupère les derniers articles de plusieurs flux RSS/Atom et écrit veille.json.
Aucune librairie externe : uniquement la bibliothèque standard de Python.
"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# categorie -> liste de (nom affiché, URL du flux)
FLUX = {
    "dev": [
        ("Symfony", "https://feeds.feedburner.com/symfony/blog"),
        ("Korben", "https://korben.info/feed"),
    ],
    "cyber": [
        ("CERT-FR", "https://www.cert.ssi.gouv.fr/alerte/feed/"),
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
        ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ],
    "composants": [
        ("Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
        ("Numerama", "https://www.numerama.com/feed/"),
    ],
}

PAR_CATEGORIE = 5      # nombre d'articles gardés par catégorie
PAR_FLUX = 5           # nombre d'articles lus par flux
ATOM = "{http://www.w3.org/2005/Atom}"


def lire_date(texte):
    """Convertit une date RSS (RFC 822) ou Atom (ISO 8601) en datetime UTC."""
    if not texte:
        return None
    texte = texte.strip()
    try:
        d = parsedate_to_datetime(texte)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(texte.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def lire_flux(nom, url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (veille-portfolio)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        racine = ET.fromstring(r.read())

    articles = []
    # RSS : <item> ; Atom : <entry>
    for it in racine.iter("item"):
        titre = (it.findtext("title") or "").strip()
        lien = (it.findtext("link") or "").strip()
        date = lire_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
        articles.append((titre, lien, date))
    for it in racine.iter(ATOM + "entry"):
        titre = (it.findtext(ATOM + "title") or "").strip()
        lien_el = it.find(ATOM + "link")
        lien = lien_el.get("href", "") if lien_el is not None else ""
        date = lire_date(it.findtext(ATOM + "updated") or it.findtext(ATOM + "published"))
        articles.append((titre, lien, date))

    resultat = []
    for titre, lien, date in articles[:PAR_FLUX]:
        if titre and lien:
            resultat.append({
                "titre": titre,
                "lien": lien,
                "source": nom,
                "date": date.isoformat() if date else None,
            })
    return resultat


def main():
    sortie = {"maj": datetime.now(timezone.utc).isoformat(), "categories": {}}
    for categorie, flux in FLUX.items():
        articles = []
        for nom, url in flux:
            try:
                trouves = lire_flux(nom, url)
                print(f"OK     {nom}: {len(trouves)} articles")
                articles += trouves
            except Exception as e:
                print(f"ERREUR {nom}: {e}")
        # plus récents d'abord ; les articles sans date vont à la fin
        articles.sort(key=lambda a: a["date"] or "", reverse=True)
        sortie["categories"][categorie] = articles[:PAR_CATEGORIE]

    with open("veille.json", "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=2)
    print("veille.json écrit.")


if __name__ == "__main__":
    main()
