// Function to check if the page contains a news article
function isNewsPage() {
    // Check for common news article selectors
    const articleSelectors = [
        "article", 
        ".article", 
        ".post",    
        ".story",   
        ".news"     
    ];

    for (const selector of articleSelectors) {
        if (document.querySelector(selector)) {
            return true;
        }
    }

    return false;
}

function extractNewsContent() {
    let articleText = "";
    const elements = document.querySelectorAll("p"); // Extract all paragraph content
    
    elements.forEach((el) => {
        if (el.innerText.length > 50) { // Avoid short text fragments
            articleText += el.innerText + " ";
        }
    });

    return articleText.trim();
}

// Send extracted text to background script
chrome.runtime.sendMessage({
    type: "news_content",
    text: extractNewsContent()
});

// Listen for response from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "news_analysis") {
        const result = message.data;
        let displayText = "";

        if (result.status === "real") {
            displayText += `**Bias Score:** ${result.bias_score}/100\n\n`;
            displayText += "✅ This news is real. Here are the objective summary and other perspectives:\n\n";
            displayText += `**Objective Summary:** ${result.objective_summary}\n\n`;
            result.perspectives.forEach((perspective, index) => {
                displayText +=`${index + 1}. **${perspective.source}** (${perspective.sentiment})\n`;
                displayText += `   "${perspective.title}"\n`;
                displayText += `   [Read more](${perspective.url})\n\n`;
            });
        }
        else {
            displayText = "❌ This news seems to be fake. No reliable sources found.";
        }

        alert(displayText); 
    }
});


// Function to extract news content
function extractNewsContent() {
    let articleText = "";
    const elements = document.querySelectorAll("p"); // Extract all paragraph content

    elements.forEach((el) => {
        if (el.innerText.length > 50) { // Avoid short text fragments
            articleText += el.innerText + " ";
        }
    });

    return articleText.trim();
}
