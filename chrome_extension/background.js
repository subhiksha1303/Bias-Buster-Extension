chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "analyzeNews") {
        fetch("https://biasbuster-pjrg.onrender.com", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ news_text: request.text })
        })
        .then(response => response.json())
        .then(data => sendResponse({ result: data }))
        .catch(error => sendResponse({ error: "Failed to analyze news." }));
        return true;
    }
});
