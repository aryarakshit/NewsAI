document.addEventListener('DOMContentLoaded', () => {
    const newsGrid = document.getElementById('newsGrid');
    const searchInput = document.getElementById('searchInput');

    if (newsGrid) {
        fetchNews();
    }

    if (searchInput) {
        let timeout = null;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                fetchNews(e.target.value);
            }, 800);
        });
    }

    async function fetchNews(query = '') {
        if (!newsGrid) return;

        newsGrid.innerHTML = '<div style="text-align:center; grid-column: 1/-1; padding: 50px;"><i class="fas fa-circle-notch fa-spin fa-2x" style="color: var(--accent-color);"></i></div>';

        try {
            const url = query ? `/api/news?q=${encodeURIComponent(query)}` : '/api/news';
            const response = await fetch(url);
            const news = await response.json();

            newsGrid.innerHTML = '';

            if (news.length === 0) {
                newsGrid.innerHTML = '<p style="text-align:center; grid-column: 1/-1;">No news found.</p>';
                return;
            }

            news.forEach((article, index) => {
                const card = document.createElement('div');
                card.className = 'news-card';
                card.style.animationDelay = `${index * 0.1}s`;
                card.onclick = () => window.location.href = `/news/${index}?q=${encodeURIComponent(query || 'breaking news latest headlines')}`;

                // Create Image
                const img = document.createElement('img');
                img.src = article.image;
                img.alt = "News";
                img.onerror = function () { this.src = 'https://via.placeholder.com/800x600?text=News'; };
                card.appendChild(img);

                // Create Content Container
                const content = document.createElement('div');
                content.className = 'news-content';

                // Source
                const sourceSpan = document.createElement('span');
                sourceSpan.className = 'news-source';
                sourceSpan.textContent = article.source; // Safe text insertion
                content.appendChild(sourceSpan);

                // Title
                const titleH3 = document.createElement('h3');
                titleH3.className = 'news-title';
                titleH3.textContent = article.title; // Safe text insertion
                content.appendChild(titleH3);

                card.appendChild(content);
                newsGrid.appendChild(card);
            });

        } catch (error) {
            console.error('Error fetching news:', error);
            newsGrid.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: #ff5252;">Failed to load news.</p>';
        }
    }
});

async function unsaveNews(url, elementId) {
    // Removed confirmation for smoother UX


    try {
        const response = await fetch('/api/remove_news', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        });

        const result = await response.json();

        if (result.status === 'success') {
            const element = document.getElementById(elementId);
            if (element) {
                element.style.transition = 'opacity 0.3s, transform 0.3s';
                element.style.opacity = '0';
                element.style.transform = 'scale(0.9)';
                setTimeout(() => element.remove(), 300);
            }
        } else {
            alert('Failed to remove news.');
        }
    } catch (error) {
        console.error('Error removing news:', error);
        alert('An error occurred.');
    }
}
