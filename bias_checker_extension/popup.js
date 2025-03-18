document.addEventListener("DOMContentLoaded", function () {
    const analyzeButton = document.getElementById("analyze-button");
    
    if (analyzeButton) {
        analyzeButton.addEventListener("click", function () {
            console.log("Analyze button clicked!");

            // Request content script to extract article text
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                chrome.scripting.executeScript({
                    target: { tabId: tabs[0].id },
                    files: ["content.js"]
                });
            });
        });
    } else {
        console.error("Analyze button not found!");
    }
});

// Listen for response from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "news_analysis") {
        document.getElementById("result").innerText = message.result;
    }
});