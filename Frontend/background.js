import { api } from './api/backend.js';

console.log("BACKGROUND SERVICE WORKER STARTED");


async function sendWebsiteMetadata(tab) {

    if (!tab) {
        console.log("NO TAB RECEIVED");
        return;
    }

    const metadata = {
        tab_id: tab.id,
        title: tab.title ?? "",
        url: tab.url ?? "",
        favicon: tab.favIconUrl ?? "",
        timestamp: new Date().toISOString()
    };

    console.log("COLLECTED WEBSITE METADATA:", metadata);

    try {
        const response = await api.logWebsiteMetadata(metadata);

        console.log(
            "METADATA SENT SUCCESSFULLY:",
            response
        );

    } catch (error) {

        console.error(
            "FAILED TO SEND WEBSITE METADATA:",
            error
        );
    }
}


/* User switches tabs */
chrome.tabs.onActivated.addListener(async (activeInfo) => {

    console.log("TAB ACTIVATED:", activeInfo);

    try {
        const tab = await chrome.tabs.get(activeInfo.tabId);

        await sendWebsiteMetadata(tab);

    } catch (error) {
        console.error("FAILED TO GET ACTIVE TAB:", error);
    }
});


/* Current active page finishes loading */
chrome.tabs.onUpdated.addListener(async (
    tabId,
    changeInfo,
    tab
) => {

    if (
        changeInfo.status === "complete" &&
        tab.active
    ) {

        console.log("ACTIVE TAB UPDATED:", tabId);

        await sendWebsiteMetadata(tab);
    }
});