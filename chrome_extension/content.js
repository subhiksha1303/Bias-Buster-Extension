chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "extractText") {
        sendResponse({ text: extractArticleText() });
    }
});

function extractArticleText() {
    let paragraphs = document.querySelectorAll("article p, div p, span, section");
    let fullText = "";
    paragraphs.forEach(p => {
        if (p.innerText.length > 30) {
            fullText += p.innerText + " ";
        }
    });
    return fullText.trim();
}

