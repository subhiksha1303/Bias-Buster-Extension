document.addEventListener('DOMContentLoaded', function() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const resultContent = document.getElementById('resultContent');
    
    analyzeBtn.addEventListener('click', function() {
        analyzeBtn.disabled = true;
        loadingDiv.style.display = 'flex';
        resultDiv.style.display = 'none';
        resultContent.innerHTML = '';
        
        chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
            let activeTab = tabs[0].id;

            // Inject content script to extract news text
            chrome.scripting.executeScript({
                target: { tabId: activeTab },
                function: extractArticleText
            }, (result) => {
                if (chrome.runtime.lastError || !result || !result[0] || !result[0].result) {
                    showError("Unable to extract news content. Please try on a different page.");
                    resetUI();
                    return;
                }

                let newsText = result[0].result;
                if (newsText.length < 100) {
                    showError("Not enough text extracted. Please try on a news article page.");
                    resetUI();
                    return;
                }

                fetch("https://biasbuster-pjrg.onrender.com", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ news_text: newsText })
                })
                .then(response => response.json())
                .then(data => {
                    displayResults(data);
                })
                .catch(error => {
                    showError("Error processing request. Please try again later.");
                    console.error(error);
                })
                .finally(() => {
                    resetUI();
                });
            });
        });
    });

    function displayResults(data) {
        loadingDiv.style.display = 'none';
        
        let resultHTML = '';
        
        // Add verdict
        const isReal = data.status === "real";
        resultHTML += `
            <div class="verdict ${isReal ? 'real' : 'fake'}">
                <i class="fas ${isReal ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                ${isReal ? '✅ Legitimate News' : '❌ Potential Bias Detected'}
            </div>
        `;
        
        // Add full unbiased news content with proper formatting
        if (data.unbiased_news) {
            resultHTML += `
                <div class="news-content">
                    <h4>Unbiased Article:</h4>
                    <div class="article-text">${formatNewsContent(data.unbiased_news)}</div>
                </div>
            `;
        }
        
        // Add perspectives if available
        if (data.perspectives && data.perspectives.length > 0) {
            resultHTML += `
                <div class="perspectives">
                    <h4>Alternative Perspectives:</h4>
                    <ul>
                        ${data.perspectives.map(article => `
                            <li>
                                <a href="${article.url}" target="_blank">
                                    <i class="fas fa-external-link-alt"></i> ${article.title}
                                    <span class="source">(${article.source})</span>
                                </a>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        } else {
            resultHTML += `
                <div class="perspectives">
                    <p>No alternative perspectives found for this topic.</p>
                </div>
            `;
        }
        
        resultContent.innerHTML = resultHTML;
        resultDiv.style.display = 'block';
    }

    function formatNewsContent(text) {
        // Remove unwanted elements
        text = text.replace(/Follow us on .+?(?=\n|$)/g, '');
        text = text.replace(/ADVERTISEMENT/g, '');
        text = text.replace(/RELATED STORIES[\s\S]+?(?=\n\n|$)/g, '');
        text = text.replace(/TOP VIDEOS[\s\S]+?(?=\n\n|$)/g, '');
        text = text.replace(/Location : .+?(?=\n|$)/g, '');
        text = text.replace(/First Published: .+?(?=\n|$)/g, '');
        text = text.replace(/News .+?(?=\n|$)/g, '');
        text = text.replace(/Read More\.\.\./g, '');
        
        // Clean up whitespace and format paragraphs
        text = text.replace(/\s+/g, ' ').trim();
        const paragraphs = text.split(/(?:\n\s*){2,}/);
        return paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
    }

    function showError(message) {
        resultContent.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
        resultDiv.style.display = 'block';
    }

    function resetUI() {
        analyzeBtn.disabled = false;
        loadingDiv.style.display = 'none';
    }
});

// Content script function to extract article text
function extractArticleText() {
    const article = document.querySelector('article');
    if (article) {
        return article.innerText.trim();
    }
    
    // Fallback to extracting from paragraphs
    let paragraphs = Array.from(document.querySelectorAll('p')).filter(p => {
        return p.innerText.length > 30 && 
               !p.closest('footer') && 
               !p.closest('header') && 
               !p.closest('nav');
    });
    
    // Sort by length and take the longest paragraphs
    paragraphs.sort((a, b) => b.innerText.length - a.innerText.length);
    paragraphs = paragraphs.slice(0, 15);
    
    return paragraphs.map(p => p.innerText.trim()).join('\n\n');
}