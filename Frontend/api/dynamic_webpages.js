const contentElements = new Map();
const evaluatedContent = new Set();
const blockedContentIds = new Set();


let updateTimer = null;
let currentlySending = false;

console.log(
    "[LockDown] dynamic_webpages.js LOADED"
);


/*
|--------------------------------------------------------------------------
| Helpers
|--------------------------------------------------------------------------
*/

function getVideoId(url) {
    try {
        const parsedUrl = new URL(url);
        return parsedUrl.searchParams.get("v");
    } catch {
        return null;
    }
}


function cleanText(element) {
    return element?.textContent?.trim() ?? "";
}


/*
|--------------------------------------------------------------------------
| Primary YouTube content
|--------------------------------------------------------------------------
|
| This is the video the user intentionally opened.
|
*/

function getPrimaryContent() {
    if (!window.location.pathname.startsWith("/watch")) {
        return null;
    }

    const videoId = getVideoId(
        window.location.href
    );

    if (!videoId) {
        return null;
    }

    const titleElement = document.querySelector(
        "ytd-watch-metadata h1 yt-formatted-string"
    );

    const channelElement = document.querySelector(
        "ytd-watch-metadata #channel-name a"
    );

    return {
        content_id: videoId,
        source: "youtube",
        content_type: "video",
        title: cleanText(titleElement),
        url: window.location.href,
        channel: cleanText(channelElement)
    };
}


/*
|--------------------------------------------------------------------------
| Recommended YouTube content
|--------------------------------------------------------------------------
*/

function getRecommendedContent() {
    const content = [];

    const selectors = [
        "ytd-compact-video-renderer",
        "ytd-rich-item-renderer",
        "ytd-video-renderer"
    ];

    selectors.forEach(selector => {
        const cards =
            document.querySelectorAll(selector);

        cards.forEach(card => {
            processRecommendationCard(
                card,
                content
            );
        });
    });

    return content;
}


function processRecommendationCard(
    card,
    content
) {
    const titleElement =
        card.querySelector("#video-title");

    const linkElement =
        card.querySelector("a#thumbnail") ??
        card.querySelector(
            "a[href*='/watch?v=']"
        );

    if (
        !titleElement ||
        !linkElement
    ) {
        return;
    }

    const url = linkElement.href;

    if (!url) {
        return;
    }

    const videoId =
        getVideoId(url);

    if (!videoId) {
        return;
    }

    /*
     * Prevent duplicates inside this payload.
     */
    if (
        content.some(
            item =>
                item.content_id === videoId
        )
    ) {
        return;
    }

    const channelElement =
        card.querySelector("#channel-name") ??
        card.querySelector(
            "ytd-channel-name"
        );

    /*
     * Connect backend ID to actual
     * YouTube HTML element.
     */
    contentElements.set(
        videoId,
        card
    );

    /*
     * Already evaluated by backend.
     */
    if (
    evaluatedContent.has(videoId)
) {
    // YouTube may recreate a previously evaluated video card.
    if (blockedContentIds.has(videoId)) {
        applyAction(card, "hide");
    }

    return;
}

    content.push({
        content_id: videoId,
        source: "youtube",
        content_type: "video",
        title: cleanText(titleElement),
        url: url,
        channel: cleanText(channelElement)
    });
}


/*
|--------------------------------------------------------------------------
| Build payload
|--------------------------------------------------------------------------
*/

function collectYouTubeContent() {
    const primaryContent =
        getPrimaryContent();

    const recommendedContent =
        getRecommendedContent();

    return {
        page_type:
            primaryContent
                ? "youtube_watch"
                : "youtube_feed",

        primary_content:
            primaryContent,

        recommended_content:
            recommendedContent
    };
}


/*
|--------------------------------------------------------------------------
| Send to background.js
|--------------------------------------------------------------------------
*/

async function sendYouTubeContent() {
    if (currentlySending) {
        return;
    }

    const payload =
        collectYouTubeContent();

    console.log(
        "[LockDown] collected YouTube payload:",
        payload
    );

    /*
     * Nothing available to evaluate.
     */
    if (
        !payload.primary_content &&
        payload.recommended_content.length === 0
    ) {
        return;
    }

    /*
     * Don't continuously send the
     * same primary video.
     */
    if (
        payload.primary_content &&
        evaluatedContent.has(
            payload.primary_content.content_id
        )
    ) {
        payload.primary_content = null;
    }

    /*
     * After filtering previously evaluated
     * content, there may be nothing left.
     */
    if (
        !payload.primary_content &&
        payload.recommended_content.length === 0
    ) {
        return;
    }

    currentlySending = true;

    try {
        console.log(
            "[LockDown] SENDING DYNAMIC_CONTENT:",
            payload
        );

        const response =
            await chrome.runtime.sendMessage({
                type: "DYNAMIC_CONTENT",
                payload: payload
            });

        console.log(
            "[LockDown] DYNAMIC_CONTENT RESPONSE:",
            response
        );

        if (!response) {
            console.warn(
                "No dynamic-content response received."
            );
            return;
        }

        if (response.error) {
            console.error(
                "Dynamic content backend error:",
                response.error
            );
            return;
        }

        applyEvaluationResults(
            response
        );

    } catch (error) {
        console.error(
            "Could not evaluate YouTube content:",
            error
        );
    } finally {
        currentlySending = false;
    }
}


/*
|--------------------------------------------------------------------------
| Apply backend results
|--------------------------------------------------------------------------
*/

function applyEvaluationResults(response) {
    // backend.js already extracts the response's content field.
    if (!Array.isArray(response?.blocking_decisions)) {
        return;
    }

    for (const decision of response.blocking_decisions) {
        const contentId = decision.content_id;

        // Website-level blocking is handled by background.js.
        if (!contentId) continue;

        evaluatedContent.add(contentId);

        if (decision.block === true) {
            blockedContentIds.add(contentId);
        } else {
            blockedContentIds.delete(contentId);
        }

        const element = contentElements.get(contentId);

        if (element) {
            applyAction(
                element,
                decision.block === true ? "hide" : "allow"
            );
        }
    }
}

function applyAction(
    element,
    action
) {
    /*
     * Clear previous state first.
     */
    element.classList.remove(
        "lockdown-blurred",
        "lockdown-hidden"
    );

    switch (action) {
        case "blur":
            element.classList.add(
                "lockdown-blurred"
            );
            break;

        case "hide":
            element.classList.add(
                "lockdown-hidden"
            );
            break;

        case "allow":
        default:
            break;
    }
}


/*
|--------------------------------------------------------------------------
| Inject CSS
|--------------------------------------------------------------------------
*/

function injectStyles() {
    if (
        document.getElementById(
            "lockdown-dynamic-styles"
        )
    ) {
        return;
    }

    const style =
        document.createElement(
            "style"
        );

    style.id =
        "lockdown-dynamic-styles";

    style.textContent = `
        .lockdown-blurred {
            filter: blur(12px) !important;
            opacity: 0.35 !important;
            transition:
                filter 0.2s ease,
                opacity 0.2s ease;
        }

        .lockdown-hidden {
            display: none !important;
        }
    `;

    document.head.appendChild(
        style
    );
}


/*
|--------------------------------------------------------------------------
| Handle YouTube dynamic loading
|--------------------------------------------------------------------------
*/

function observeYouTube() {
    const observer =
        new MutationObserver(
            () => {
                clearTimeout(
                    updateTimer
                );

                /*
                 * YouTube causes lots
                 * of DOM mutations,
                 * so debounce them.
                 */
                updateTimer =
                    setTimeout(
                        () => {
                            sendYouTubeContent();
                        },
                        500
                    );
            }
        );

    observer.observe(
        document.body,
        {
            childList: true,
            subtree: true
        }
    );
}


/*
|--------------------------------------------------------------------------
| Detect SPA navigation
|--------------------------------------------------------------------------
|
| YouTube changes URL without always
| reloading the whole page.
|
*/

let lastUrl =
    window.location.href;


function watchUrlChanges() {
    setInterval(
        () => {
            if (
                window.location.href ===
                lastUrl
            ) {
                return;
            }

            lastUrl =
                window.location.href;

            console.log(
                "[LockDown] YouTube URL changed:",
                lastUrl
            );

            /*
             * Wait briefly for YouTube
             * to render the new page.
             */
            setTimeout(
                () => {
                    sendYouTubeContent();
                },
                500
            );

        },
        500
    );
}


/*
|--------------------------------------------------------------------------
| Start
|--------------------------------------------------------------------------
*/

function start() {
    injectStyles();

    sendYouTubeContent();

    observeYouTube();

    watchUrlChanges();
}


start();