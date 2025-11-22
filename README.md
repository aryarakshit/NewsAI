PROJECT_NAME: News AI App

ONE_SENTENCE_PITCH: A smart, AI-powered news aggregator that gives you the full picture with real-time perspectives and bias analysis.

LONG_DESCRIPTION: 
In an era of information overload and polarized media, getting the objective truth is harder than ever. News AI App solves this by aggregating the latest headlines and using advanced AI (Gemini) to analyze each story instantly. It doesn't just show you the news; it breaks down the bias, summarizes the key points, and most importantly, finds and presents distinct points of view from real, diverse sources.

This application is designed for news junkies and critical thinkers who want to escape the echo chamber. By automatically fetching related articles from different publishers and synthesizing their perspectives, it empowers users to understand complex stories from multiple angles without opening a dozen tabs.

LIST_OF_FEATURES: 
- **AI-Powered Analysis**: Instantly summarizes articles, detects bias, and assigns a trust score.
- **Real Source Perspectives**: Automatically finds and links to "Conservative", "Progressive", and "Mainstream" articles covering the same topic.
- **Smart Search**: Fetches the freshest news using DuckDuckGo, with robust fallback strategies to ensure you never see an empty feed.
- **Save & Curate**: Bookmark important stories to your personal profile for later reading.
- **Responsive Design**: A modern, "Tekina-style" UI that looks great on desktop and mobile.

TECH_STACK_LIST: Python (Flask), Google Gemini API, DuckDuckGo Search (ddgs), HTML/CSS (Vanilla), JavaScript (Vanilla)

PREREQUISITES: Python 3.9+, pip, A Google Gemini API Key

INSTALLATION_STEPS: 
1. git clone https://github.com/yourusername/news-ai-app.git
2. cd news-ai-app
3. python -m venv venv
4. source venv/bin/activate  # On Windows: venv\Scripts\activate
5. pip install -r requirements.txt
6. Create a .env file and add your key: GEMINI_API_KEY=your_api_key_here

USAGE_EXAMPLES: 
python app.py
# Then open http://127.0.0.1:5000 in your browser

FUTURE_ROADMAP: 
- User Accounts & Cloud Sync
- Personalized News Feed based on reading habits
- Multi-language Support

LICENSE_TYPE: MIT License

YOUR_NAME_AND_CONTACT: Arya R - @aryar_dev

ANY_ACKNOWLEDGEMENTS: Thanks to the Google Gemini team for the powerful API and the open-source community for the DuckDuckGo search library.
