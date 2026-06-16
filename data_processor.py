import os
import re
import sqlite3
import time
import datetime
import math
import yfinance as yf

# Database file location
DB_FILE = 'news_cache.db'

# Active watchlist of major US equities across sectors
WATCHLIST = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'NFLX', 
    'AMD', 'INTC', 'JPM', 'BAC', 'DIS', 'MS', 'GS', 'XOM', 'CVX', 
    'LLY', 'UNH', 'WMT', 'PLTR', 'COIN', 'NIO', 'BABA', 'MRNA'
]

# Catalyst detection rules with associated weights
CATALYST_RULES = {
    'Earnings': {
        'keywords': [r'\bearnings\b', r'\bquarterly\b', r'\beps\b', r'\brevenue\b', r'\bq[1-4]\b', r'\bbeat\b', r'\bmiss(ed)?\b', r'\bprofit(s)?\b', r'\bguidance\b'],
        'weight': 40
    },
    'M&A / Deal': {
        'keywords': [r'\bacquisition\b', r'\bacquire\s', r'\bmerge(r)?\b', r'\bbuyout\b', r'\btakeover\b', r'\bdeal\b', r'\bpartnership\b', r'\bjoint venture\b', r'\bcollaborate\b'],
        'weight': 40
    },
    'Regulatory / Law': {
        'keywords': [r'\bfda\b', r'\bapprov(al|ed)\b', r'\bclinical\b', r'\btrial(s)?\b', r'\bsec\b', r'\binvestigat(ion|e)\b', r'\blawsuit\b', r'\bsue(d)?\b', r'\bantitrust\b', r'\bcourt\b'],
        'weight': 35
    },
    'Leadership Change': {
        'keywords': [r'\bceo\b', r'\bcfo\b', r'\bresign(s|ation)?\b', r'\bnamed\b', r'\bappointed\b', r'\bstep(ping)? down\b', r'\bsuccessor\b', r'\bboard\b'],
        'weight': 30
    },
    'Analyst Action': {
        'keywords': [r'\bupgrade(d)?\b', r'\bdowngrade(d)?\b', r'\brating\b', r'\btarget price\b', r'\boutperform\b', r'\bbuy rating\b'],
        'weight': 20
    },
    'Capital Return': {
        'keywords': [r'\bbuyback(s)?\b', r'\bdividend(s)?\b', r'\brepurchase\b', r'\bsplit\b'],
        'weight': 15
    }
}

def init_db():
    """Initializes the database schema."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table for stock market tickers details
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickers_data (
            ticker TEXT PRIMARY KEY,
            price REAL NOT NULL,
            prev_close REAL NOT NULL,
            change_pct REAL NOT NULL,
            volume INTEGER NOT NULL,
            avg_volume INTEGER NOT NULL,
            volume_ratio REAL NOT NULL,
            updated_at INTEGER NOT NULL
        )
    ''')
    
    # Table for processed articles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            publish_time INTEGER NOT NULL,
            velocity_score REAL NOT NULL,
            impact_score REAL NOT NULL,
            sentiment_score REAL NOT NULL,
            investigator_take TEXT NOT NULL,
            catalysts_detected TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(ticker) REFERENCES tickers_data(ticker) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def clean_old_data():
    """Prunes articles older than 48 hours to manage database size."""
    limit_time = int(time.time()) - 172800  # 48 hours in seconds
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM articles WHERE publish_time < ?", (limit_time,))
    deleted_articles = cursor.rowcount
    
    # Delete tickers that have no articles to save space
    cursor.execute("DELETE FROM tickers_data WHERE ticker NOT IN (SELECT DISTINCT ticker FROM articles)")
    deleted_tickers = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"[CLEANUP] Pruned {deleted_articles} old articles and {deleted_tickers} orphaned tickers.")

def analyze_catalysts(text):
    """Detects financial catalysts in headlines using regex."""
    text_lower = text.lower()
    detected = []
    max_weight = 0
    
    for catalyst, rule in CATALYST_RULES.items():
        matched = False
        for pattern in rule['keywords']:
            if re.search(pattern, text_lower):
                matched = True
                break
        if matched:
            detected.append(catalyst)
            max_weight = max(max_weight, rule['weight'])
            
    return detected, max_weight

def calculate_sentiment(headline, catalysts):
    """Calculates heuristic sentiment score (-1.0 to +1.0)."""
    text = headline.lower()
    positive_words = ['beat', 'upgrades', 'gains', 'approves', 'soars', 'surges', 'growth', 'record', 'dividend', 'buyback', 'partnership', 'deal', 'agreement', 'rise', 'profit']
    negative_words = ['misses', 'downgrades', 'falls', 'declines', 'drops', 'sued', 'lawsuit', 'investigation', 'plummets', 'resign', 'slumps', 'losses', 'deficit', 'scrutiny']
    
    pos_count = sum(1 for word in positive_words if word in text)
    neg_count = sum(1 for word in negative_words if word in text)
    
    score = 0.0
    total = pos_count + neg_count
    if total > 0:
        score = (pos_count - neg_count) / total
    else:
        # Default based on catalyst types
        if 'Earnings' in catalysts or 'M&A / Deal' in catalysts:
            score = 0.1  # slightly positive speculation
        elif 'Regulatory / Law' in catalysts:
            score = -0.2  # regulatory tends to be risk-off
            
    return score

def generate_investigator_take(ticker, change_pct, volume_ratio, catalysts, headline, sentiment):
    """Generates a professional 2-sentence market investigation commentary."""
    direction = "upward" if change_pct >= 0 else "downward"
    action = "gaining" if change_pct >= 0 else "losing"
    movement_str = f"{action} {abs(change_pct):.2f}%"
    
    vol_str = ""
    if volume_ratio >= 1.8:
        vol_str = f" backed by a major trading volume surge of {volume_ratio:.1f}x the 10-day average"
    elif volume_ratio >= 1.2:
        vol_str = f" on elevated volume ({volume_ratio:.1f}x average)"
    
    cat_str = ""
    if catalysts:
        cat_str = f" triggered by a high-priority {catalysts[0]} catalyst"
    else:
        cat_str = " amid shifting market sentiment"
        
    sentence_1 = f"{ticker} shares are {movement_str}{vol_str}{cat_str}."
    
    # Sentence 2 - Strategic outlook
    if "Earnings" in catalysts:
        if sentiment >= 0:
            sentence_2 = "Strong financial performance and positive earnings sentiment are driving institutional accumulation. The technical breakout suggests continued momentum."
        else:
            sentence_2 = "Disappointing earnings figures or weak guidance are triggering rapid institutional distribution. Expect volatility to persist as analysts reset valuation models."
    elif "M&A / Deal" in catalysts:
        sentence_2 = "Corporate consolidation or strategic partnership headlines are fueling heightened retail and institutional interest. Investors should monitor formal deal disclosures for regulatory obstacles."
    elif "Regulatory / Law" in catalysts:
        if sentiment >= 0:
            sentence_2 = "Favorable regulatory decisions represent a significant commercial tailwind. Near-term price targets have shifted higher as regulatory risk dissipates."
        else:
            sentence_2 = "Regulatory investigations or litigation hurdles are generating risk-off headwinds. Continued distribution is likely until legal clarity emerges."
    elif "Leadership Change" in catalysts:
        sentence_2 = "Executive transitions introduce operational execution risks, causing immediate portfolio rebalancing. Watch for strategic plan outlines from the incoming management team."
    else:
        if change_pct > 3.0:
            sentence_2 = "The high-velocity breakout is bypassing near-term resistance levels, signifying strong buyer demand. Watch for short-term consolidations to establish new entry support."
        elif change_pct < -3.0:
            sentence_2 = "Accelerating downside momentum has violated key technical support zones on high volume. Investigators should avoid fighting the tape until a clear consolidation base forms."
        else:
            sentence_2 = "The equity is consolidating near key moving averages. The short-term trend remains neutral until a decisive volume breakout resolves the trading range."
            
    return f"{sentence_1} {sentence_2}"

def fetch_and_process():
    """Runs the data extraction, scoring, and caching pipeline."""
    print(f"[START] Executing US Market News Scan at {datetime.datetime.now()}")
    init_db()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    now_ts = int(time.time())
    articles_saved = 0
    
    for ticker in WATCHLIST:
        print(f"[SCAN] Querying ticker {ticker}...")
        try:
            # Fetch Yahoo Finance Ticker Data
            t = yf.Ticker(ticker)
            
            # Fetch Ticker News
            news = t.news
            if not news:
                print(f"  No news articles returned for {ticker}.")
                continue
                
            # Fetch Ticker Financial Metrics
            fast_info = t.fast_info
            price = fast_info.get('last_price')
            prev_close = fast_info.get('previous_close')
            
            # Fallback if fast_info is incomplete
            if price is None or prev_close is None:
                history = t.history(period="5d")
                if not history.empty:
                    price = float(history['Close'].iloc[-1])
                    prev_close = float(history['Close'].iloc[-2]) if len(history) > 1 else price
                else:
                    price, prev_close = 0.0, 0.0
                    
            change_pct = 0.0
            if prev_close > 0:
                change_pct = ((price - prev_close) / prev_close) * 100
                
            volume = fast_info.get('last_volume', 1)
            avg_volume = fast_info.get('three_month_average_volume', 1)
            
            if volume is None or volume == 0:
                volume = 1
            if avg_volume is None or avg_volume == 0:
                avg_volume = 1
                
            volume_ratio = volume / avg_volume
            
            # Save Ticker Info to DB
            cursor.execute('''
                INSERT OR REPLACE INTO tickers_data 
                (ticker, price, prev_close, change_pct, volume, avg_volume, volume_ratio, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ticker, price, prev_close, change_pct, volume, avg_volume, volume_ratio, now_ts))
            
            # Process Ticker Articles
            for item in news:
                headline = item.get('title', '')
                if not headline:
                    continue
                    
                article_id = item.get('uuid') or item.get('id') or str(hash(headline))
                url = item.get('link', '')
                summary = item.get('summary', '')
                pub_time = item.get('providerPublishTime') or item.get('publishTime') or now_ts
                
                # A. Velocity Score Calculation (exponential time decay)
                # Max 100, halves roughly every 9 hours
                hours_ago = max((now_ts - pub_time) / 3600.0, 0)
                velocity_score = 100.0 * math.exp(-0.08 * hours_ago)
                
                # B. Impact Score Calculation
                catalysts, catalyst_weight = analyze_catalysts(headline)
                
                # Volume ratio bonus
                vol_bonus = 0
                if volume_ratio >= 2.0:
                    vol_bonus = 25
                elif volume_ratio >= 1.5:
                    vol_bonus = 15
                elif volume_ratio >= 1.0:
                    vol_bonus = 5
                    
                impact_score = min(20 + catalyst_weight + vol_bonus, 100)
                
                # C. Sentiment Score
                sentiment_score = calculate_sentiment(headline, catalysts)
                
                # D. Investigator Commentary
                take = generate_investigator_take(ticker, change_pct, volume_ratio, catalysts, headline, sentiment_score)
                
                # E. Save Article
                catalysts_str = ",".join(catalysts) if catalysts else None
                cursor.execute('''
                    INSERT OR REPLACE INTO articles
                    (id, ticker, headline, summary, url, publish_time, velocity_score, impact_score, sentiment_score, investigator_take, catalysts_detected, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (article_id, ticker, headline, summary, url, pub_time, velocity_score, impact_score, sentiment_score, take, catalysts_str, now_ts))
                
                articles_saved += 1
                
        except Exception as e:
            print(f"  [ERROR] Failed to process ticker {ticker}: {str(e)}")
            continue
            
    conn.commit()
    conn.close()
    
    print(f"[COMPLETE] Processing finished. Saved {articles_saved} articles.")
    
    # Run historical data cleanup
    clean_old_data()

if __name__ == '__main__':
    fetch_and_process()
