import os
import re
import xml.etree.ElementTree as ET
import time
import json
import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

CACHE_FILE = 'release_notes_cache.json'
CACHE_EXPIRATION = 3600  # 1 hour

def parse_entry_content(html_content, date, link):
    """
    Parses Google Cloud release note HTML content which typically has:
    <h3>Type</h3>
    <p>Description...</p>
    And splits it into individual updates.
    """
    if not html_content:
        return []
    
    # Normalize line breaks and whitespace
    html_content = html_content.strip()
    
    # If there are no <h3> tags, treat the entire block as one general update
    if '<h3>' not in html_content:
        # Generate a unique ID for indexing and referencing
        update_id = re.sub(r'[^a-zA-Z0-9]', '_', f"{date}_general").lower()
        return [{
            'id': update_id,
            'date': date,
            'link': link,
            'type': 'General',
            'description': html_content
        }]
        
    parts = re.split(r'<h3>', html_content)
    updates = []
    idx = 0
    for part in parts:
        if not part.strip():
            continue
        subparts = part.split('</h3>', 1)
        if len(subparts) == 2:
            update_type = subparts[0].strip()
            description = subparts[1].strip()
        else:
            update_type = 'General'
            description = part.strip()
            
        update_id = re.sub(r'[^a-zA-Z0-9]', '_', f"{date}_{update_type}_{idx}").lower()
        updates.append({
            'id': update_id,
            'date': date,
            'link': link,
            'type': update_type,
            'description': description
        })
        idx += 1
    return updates

def get_release_notes(force_refresh=False):
    """
    Fetches the BigQuery release notes from the XML feed and parses it.
    Uses a local JSON cache to keep performance high and avoid excessive external requests.
    """
    if not force_refresh and os.path.exists(CACHE_FILE):
        # Check cache age
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age < CACHE_EXPIRATION:
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass  # Fallback to fetching live
                
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get('https://docs.cloud.google.com/feeds/bigquery-release-notes.xml', headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        
        all_updates = []
        for entry in root.findall('atom:entry', namespaces):
            title_elem = entry.find('atom:title', namespaces)
            date = title_elem.text if title_elem is not None else 'Unknown Date'
            
            link_elem = entry.find("atom:link[@rel='alternate']", namespaces)
            if link_elem is None:
                link_elem = entry.find("atom:link", namespaces)
            link = link_elem.attrib.get('href', '') if link_elem is not None else ''
            
            content_elem = entry.find('atom:content', namespaces)
            content_html = content_elem.text if content_elem is not None else ''
            
            # Parse individual updates from HTML
            entry_updates = parse_entry_content(content_html, date, link)
            all_updates.extend(entry_updates)
            
        # Write to cache
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_updates, f, ensure_ascii=False, indent=2)
            
        return all_updates
    except Exception as e:
        # Fallback to stale cache if loading fails
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        raise e

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/release-notes')
def release_notes_api():
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    try:
        notes = get_release_notes(force_refresh=force_refresh)
        return jsonify({
            'success': True,
            'notes': notes,
            'cached_at': time.ctime(os.path.getmtime(CACHE_FILE)) if os.path.exists(CACHE_FILE) else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
