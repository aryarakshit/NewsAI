import os
import json
import time
import random
from flask import Flask, render_template, request, jsonify
from ddgs import DDGS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Mock Data (Fallback) ---
MOCK_NEWS = [
    {
        "title": "AI Breakthrough in Climate Modeling",
        "url": "https://example.com/ai-climate",
        "source": "TechDaily",
        "body": "Scientists have developed a new AI model that predicts climate patterns with unprecedented accuracy...",
        "image": "https://picsum.photos/seed/climate/800/600"
    },
    {
        "title": "Global Markets Rally on Tech Earnings",
        "url": "https://example.com/markets-rally",
        "source": "FinanceWorld",
        "body": "Major tech companies reported record earnings this quarter, driving a global stock market rally...",
        "image": "https://picsum.photos/seed/markets/800/600"
    },
    {
        "title": "New Mars Rover Sends Stunning Images",
        "url": "https://example.com/mars-rover",
        "source": "SpaceNews",
        "body": "The latest rover to land on Mars has sent back high-resolution images of the red planet's surface...",
        "image": "https://picsum.photos/seed/mars/800/600"
    },
    {
        "title": "The Future of Electric Vehicles",
        "url": "https://example.com/ev-future",
        "source": "AutoTrends",
        "body": "Electric vehicle adoption is accelerating as battery technology improves and costs come down...",
        "image": "https://picsum.photos/seed/ev/800/600"
    }
]

# --- Services ---

class SearchService:
    def __init__(self):
        self.cache_file = "search_cache.json"
        self.cache = self._load_cache()
        self.ddgs = DDGS()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f)

    def search_news(self, query="latest technology news", max_results=10):
        # Check cache first
        cache_key = f"{query}_{max_results}"
        current_time = time.time()
        
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # Check if cache is fresh (less than 15 minutes old)
            if isinstance(cached_data, dict) and "timestamp" in cached_data:
                if current_time - cached_data["timestamp"] < 900: # 900 seconds = 15 mins
                    print(f"Returning cached results for: {query}")
                    return cached_data["results"]

        print(f"Fetching fresh results for: {query}")
        results = []
        try:
            # DDGS news search with retry and timelimit for fresh results
            ddgs_results = None
            for attempt in range(3):
                try:
                    # First attempt: Try getting fresh news (past day)
                    if attempt == 0:
                        ddgs_results = self.ddgs.news(query, max_results=max_results, timelimit='d')
                    # Second attempt: Try past week
                    elif attempt == 1:
                        ddgs_results = self.ddgs.news(query, max_results=max_results, timelimit='w')
                    # Third attempt: Any time
                    else:
                        ddgs_results = self.ddgs.news(query, max_results=max_results)
                    
                    # Convert generator to list to check if empty
                    if ddgs_results:
                        ddgs_results = list(ddgs_results)
                    
                    if ddgs_results:
                        break
                except Exception as e:
                    print(f"Search attempt {attempt+1} failed: {e}")
                    time.sleep(2)
            
            if ddgs_results:
                for r in ddgs_results:
                    # Basic image validation
                    image_url = r.get('image')
                    if not image_url or not image_url.startswith('http'):
                        image_url = f"https://picsum.photos/seed/{random.randint(0,1000)}/800/600"

                    results.append({
                        "title": r.get('title'),
                        "url": r.get('url'),
                        "source": r.get('source') or "Unknown Source",
                        "body": r.get('body') or r.get('title') or "No content available for this article.",
                        "image": image_url,
                        "date": r.get('date') or "Recently"
                    })
            
            # Update cache with timestamp
            if results:
                self.cache[cache_key] = {
                    "timestamp": current_time,
                    "results": results
                }
                self._save_cache()
            else:
                print("Search returned no results. Falling back to Mock Data.")
                return MOCK_NEWS
            
        except Exception as e:
            print(f"Search API Error: {e}")
            print("Falling back to Mock Data")
            return MOCK_NEWS

        return results

class AIService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.ddgs = DDGS()

    def list_models(self):
        try:
            return [m.name for m in genai.list_models()]
        except Exception as e:
            return [str(e)]

    def _generate_with_retry(self, prompt, retries=3):
        for attempt in range(retries):
            try:
                return self.model.generate_content(prompt)
            except Exception as e:
                if "429" in str(e) and attempt < retries - 1:
                    wait_time = 2 ** attempt # 1s, 2s, 4s
                    print(f"DEBUG: API Rate Limit (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise e

    def analyze_article(self, text, headline):
        prompt = f"""
        Analyze this news article:
        Headline: {headline}
        Content: {text}

        Provide a JSON response with:
        1. "summary": A comprehensive summary (3-4 sentences) that covers the main event and context.
        2. "key_points": A list of 2-4 short, informative bullet points that fill in the gaps or add important details.
        3. "bias_score": A number from 1 (Left) to 10 (Right), where 5 is Neutral.
        4. "bias_label": A string like "Leans Left", "Neutral", "Leans Right".
        5. "tone": One word describing the tone (e.g., "Alarmist", "Objective", "Optimistic").
        6. "trust_score": A number 1-100 based on the content quality (heuristic).
        """
        try:
            print(f"DEBUG: Generating AI content for: {headline}")
            response = self._generate_with_retry(prompt)
            # Basic cleanup to ensure JSON parsing if the model adds markdown
            txt = response.text.replace('```json', '').replace('```', '')
            print(f"DEBUG: AI Response: {txt[:100]}...") # Log first 100 chars
            return json.loads(txt)
        except Exception as e:
            print(f"DEBUG: AI Error: {e}")
            # Fallback to simulated data so UI looks good even if API fails
            return {
                "summary": f"AI Error ({str(e)}). Showing simulated content for: '{headline}'",
                "key_points": ["Simulated Point 1", "Simulated Point 2"],
                "bias_score": random.randint(3, 8),
                "bias_label": random.choice(["Leans Left", "Neutral", "Leans Right"]),
                "tone": random.choice(["Objective", "Critical", "Supportive"]),
                "trust_score": random.randint(60, 95)
            }

    def get_pov(self, headline, original_url=None):
        print(f"DEBUG: Getting POVs for: {headline}")
        
        # Strategy 1: Try to find real articles first
        related_articles = []
        try:
            # Search for the headline
            results = self.ddgs.news(headline, max_results=10, timelimit='w')
            
            # Filter results
            seen_domains = set()
            if original_url:
                from urllib.parse import urlparse
                try:
                    seen_domains.add(urlparse(original_url).netloc)
                except:
                    pass

            for r in results:
                url = r.get('url')
                if not url or url == original_url:
                    continue
                try:
                    domain = urlparse(url).netloc
                    if domain not in seen_domains:
                        related_articles.append(r)
                        seen_domains.add(domain)
                        if len(related_articles) >= 2:
                            break
                except:
                    continue
        except Exception as e:
            print(f"POV Search Error: {e}")

        # Strategy 2: If we have 2 real articles, use them (Best Case)
        if len(related_articles) >= 2:
            article_a = related_articles[0]
            article_b = related_articles[1]
            
            prompt = f"""
            Analyze these two news articles covering the headline: "{headline}"

            Article A:
            Source: {article_a.get('source')}
            Title: {article_a.get('title')}
            Snippet: {article_a.get('body')}

            Article B:
            Source: {article_b.get('source')}
            Title: {article_b.get('title')}
            Snippet: {article_b.get('body')}

            Generate 2 distinct Points of View (POV) based on these specific articles.
            Return a JSON array of objects:
            [
                {{
                    "source_type": "{article_a.get('source')}",
                    "perspective": ["Point 1 from Article A", "Point 2 from Article A"],
                    "source_link": "{article_a.get('url')}"
                }},
                {{
                    "source_type": "{article_b.get('source')}",
                    "perspective": ["Point 1 from Article B", "Point 2 from Article B"],
                    "source_link": "{article_b.get('url')}"
                }}
            ]
            Keep bullet points to ONE sentence maximum.
            """
            try:
                response = self._generate_with_retry(prompt)
                txt = response.text.replace('```json', '').replace('```', '')
                return json.loads(txt)
            except Exception as e:
                print(f"AI POV Generation Error (Strategy 1): {e}")
                # Fall through to Strategy 3

        # Strategy 3: Generate POVs first, THEN find real links for them (Fallback)
        print("DEBUG: Falling back to Strategy 3 (Generate then Search)")
        prompt = f"""
        For the news headline: "{headline}"
        Generate 2 distinct Points of View (POV) that might exist on this topic.
        Return a JSON array of objects:
        - "source_type": e.g., "Conservative Outlet", "Progressive Blog", "Mainstream Media"
        - "perspective": 2-4 short bullet points
        
        Do NOT include "source_link".
        """
        
        povs = []
        try:
            response = self._generate_with_retry(prompt)
            txt = response.text.replace('```json', '').replace('```', '')
            povs = json.loads(txt)
        except Exception as e:
            print(f"AI POV Error (Strategy 3): {e}")
            return []

        # Now find real links for these generated POVs
        for pov in povs:
            try:
                # Search for the perspective type + headline to find a matching article
                # e.g. "Conservative view [headline]" or "[Source Name] [headline]"
                search_query = f"{pov.get('source_type')} {headline}"
                print(f"DEBUG: Searching for link for POV: {search_query}")
                
                link_results = self.ddgs.news(search_query, max_results=1)
                link_results_list = list(link_results)
                
                if link_results_list:
                    # Found a real link!
                    pov['source_link'] = link_results_list[0].get('url')
                    # Optionally update source name if we found a real one
                    if link_results_list[0].get('source'):
                         pov['source_type'] = f"{pov['source_type']} ({link_results_list[0].get('source')})"
                else:
                    # Last resort: Search just the headline again to get ANY link
                    fallback_results = self.ddgs.news(headline, max_results=1)
                    fallback_list = list(fallback_results)
                    if fallback_list:
                        pov['source_link'] = fallback_list[0].get('url')
            except Exception as e:
                print(f"Link Search Error: {e}")
                
        return povs

search_service = SearchService()
ai_service = AIService()

# --- Global Data ---
ANALYSIS_CACHE = {} # Key: Article URL or Title, Value: {analysis, povs}
MAX_CACHE_SIZE = 50

SAVED_ARTICLES_FILE = 'saved_articles.json'

def load_saved_articles():
    if os.path.exists(SAVED_ARTICLES_FILE):
        try:
            with open(SAVED_ARTICLES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading saved articles: {e}")
            return []
    return []

def save_articles_to_file():
    try:
        with open(SAVED_ARTICLES_FILE, 'w') as f:
            json.dump(SAVED_ARTICLES, f, indent=4)
    except IOError as e:
        print(f"Error saving articles: {e}")

SAVED_ARTICLES = load_saved_articles()

# --- Routes ---

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/api/models')
def list_models():
    return jsonify(ai_service.list_models())

@app.route('/api/news')
def get_news():
    query = request.args.get('q', 'breaking news latest headlines')
    # Simple input validation
    if len(query) > 100:
        query = query[:100]
    
    news = search_service.search_news(query)
    return jsonify(news)

@app.route('/api/save_news', methods=['POST'])
def save_news():
    try:
        article = request.json
        if not article or not isinstance(article, dict):
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        # Check if already saved (by url or title)
        for saved in SAVED_ARTICLES:
            if saved.get('url') == article.get('url') or saved.get('title') == article.get('title'):
                return jsonify({"status": "already_saved"})
        
        SAVED_ARTICLES.append(article)
        save_articles_to_file()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error saving news: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/remove_news', methods=['POST'])
def remove_news():
    try:
        article = request.json
        if not article or 'url' not in article:
             return jsonify({"status": "error", "message": "Missing URL"}), 400

        global SAVED_ARTICLES
        initial_count = len(SAVED_ARTICLES)
        SAVED_ARTICLES = [a for a in SAVED_ARTICLES if a.get('url') != article.get('url')]
        
        if len(SAVED_ARTICLES) < initial_count:
            save_articles_to_file()
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"})
            
    except Exception as e:
        print(f"Error removing news: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/news/<int:index>')
def news_detail(index):
    query = request.args.get('q', 'breaking news latest headlines')
    news_list = search_service.search_news(query)
    
    if 0 <= index < len(news_list):
        article = news_list[index]
        
        # Unique key for caching (prefer URL, fallback to Title)
        article_key = article.get('url') or article.get('title')
        
        # Check Global Cache
        if article_key in ANALYSIS_CACHE:
            print(f"Returning cached analysis for: {article.get('title')}")
            cached_data = ANALYSIS_CACHE[article_key]
            return render_template('news_detail.html', 
                                 article=article, 
                                 analysis=cached_data['analysis'], 
                                 povs=cached_data['povs'],
                                 is_saved=any(a.get('url') == article.get('url') for a in SAVED_ARTICLES))
        
        # Generate fresh analysis
        analysis = ai_service.analyze_article(article.get('body', ''), article.get('title', ''))
        povs = ai_service.get_pov(article.get('title', ''), article.get('url'))
        
        # Cache result with limit
        if len(ANALYSIS_CACHE) >= MAX_CACHE_SIZE:
            # Remove a random item or oldest (simple approach: clear 20% if full, or just pop one)
            # For simplicity, just clear the cache if it gets too big to avoid complex LRU logic for now
            print("Cache limit reached, clearing analysis cache.")
            ANALYSIS_CACHE.clear()

        ANALYSIS_CACHE[article_key] = {
            'analysis': analysis,
            'povs': povs
        }
        
        return render_template('news_detail.html', 
                             article=article, 
                             analysis=analysis, 
                             povs=povs,
                             is_saved=any(a.get('url') == article.get('url') for a in SAVED_ARTICLES))
    
    return "Article not found", 404

@app.route('/saved_news/<int:index>')
def saved_news_detail(index):
    if 0 <= index < len(SAVED_ARTICLES):
        article = SAVED_ARTICLES[index]
        
        # Unique key for caching
        article_key = article.get('url') or article.get('title')
        
        # Check Global Cache
        if article_key in ANALYSIS_CACHE:
            cached_data = ANALYSIS_CACHE[article_key]
            return render_template('news_detail.html', 
                                 article=article, 
                                 analysis=cached_data['analysis'], 
                                 povs=cached_data['povs'],
                                 is_saved=True)
        
        # Generate fresh analysis
        analysis = ai_service.analyze_article(article.get('body', ''), article.get('title', ''))
        povs = ai_service.get_pov(article.get('title', ''), article.get('url'))
        
        # Cache result
        if len(ANALYSIS_CACHE) >= MAX_CACHE_SIZE:
            ANALYSIS_CACHE.clear()

        ANALYSIS_CACHE[article_key] = {
            'analysis': analysis,
            'povs': povs
        }
        
        return render_template('news_detail.html', 
                             article=article, 
                             analysis=analysis, 
                             povs=povs,
                             is_saved=True)
    
    return "Saved article not found", 404

@app.route('/settings')
def settings():
    return render_template('settings.html', saved_news=SAVED_ARTICLES)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
