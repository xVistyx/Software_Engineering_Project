chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action !== "get_page_description") {
    return;
  }

  const description =
    document.querySelector('meta[name="description"]')?.content?.trim()
    ||
    document.querySelector('meta[property="og:description"]')?.content?.trim()
    ||
    "";

  sendResponse({
    description: description
  });
});