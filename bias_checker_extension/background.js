chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "news_content") {
        console.log("Extracted news text:", message.text);  // Debugging

        fetch("https://your-render-app.onrender.com/api/analyze-news/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ news_text: message.text })
        })
        .then(response => response.text())  // Log raw response
        .then(text => {
            console.log("Raw response from API:", text);  // Debugging
            try {
                const data = JSON.parse(text);
                console.log("Parsed response JSON:", data);  // Debugging
                chrome.tabs.sendMessage(sender.tab.id, { type: "news_analysis", data: data });
            } catch (error) {
                console.error("Failed to parse JSON:", text);
            }
        })
        .catch(error => console.error("Fetch error:", error));
    }
});