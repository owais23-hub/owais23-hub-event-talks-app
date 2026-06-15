# BigQuery Release Radar 📡

A premium web application built using **Python Flask** and **plain vanilla HTML, CSS, and JavaScript** that fetches, parses, caches, and visualizes the official Google Cloud BigQuery Release Notes.

## 🌟 Key Features

- **Live RSS/Atom Processing**: Dynamically fetches release notes from Google's official feed: `https://docs.cloud.google.com/feeds/bigquery-release-notes.xml`.
- **Granular Parsing**: Google Cloud release entries group multiple distinct items (Features, Changes, Deprecations) under a single date entry. This application parses the HTML inside the feed and breaks them down into individual granular cards, complete with separate types and source anchors.
- **Smart Caching System**: Implements a local file caching mechanism (`release_notes_cache.json`). It avoids excessive external network queries, speeds up page load times to milliseconds, and automatically falls back to stale cache if the network is down.
- **Stats Dashboard & Instant Filters**: Shows real-time statistics of Features, Changes, and Deprecations. Clicking these stat cards instantly filters the feed.
- **Interactive X (Twitter) Composer**: Click any card's **Tweet Update** button to open a custom-designed X/Twitter composer modal. It auto-formats the release note content, truncates it to fit the 280-character limit, appends official hashtags, and lets you edit the text before posting.
- **Premium Design System**: Dark-themed glassmorphism interface built from scratch using custom HSL colors, Google Fonts (Outfit & Inter), SVG logo illustrations, vector icons (Lucide), and micro-animations.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13+, Flask 3.0.3, Requests (XML Parser: built-in `xml.etree.ElementTree` and `re`)
- **Frontend**: Plain HTML5, Vanilla CSS3 (Custom grid, animations, variable-based theme), and Vanilla JavaScript (ES6+ state management, DOM triggers)

---

## 🚀 How to Run Locally

### 1. Prerequisites
Make sure Python 3.13+ is installed on your system.

### 2. Setup and Installation
From the root of the project directory, run:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start the Web Server
Launch the Flask development server:

```bash
python app.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📁 Project Structure

```text
├── app.py                     # Flask backend, XML parser, and caching logic
├── requirements.txt           # Python application requirements
├── release_notes_cache.json   # Local cache generated on fetch (auto-ignored in git)
├── templates/
│   └── index.html             # Dashboard layout & Tweet modal skeleton
└── static/
    ├── css/
    │   └── style.css          # Premium stylesheet (glassmorphism, variables, media queries)
    └── js/
        └── app.js             # Client state management, search, filtering, and share intents
```
