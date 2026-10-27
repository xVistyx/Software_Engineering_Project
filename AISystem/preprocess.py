{
            "tab_id": 66848723,
            "title": "Why the Earth is actually 100% flat | Science | The Guardian",
            "url": "https://www.theguardian.com/science/brain-flapping/2016/jan/26/earth-totally-flat-conspiracy-bob",
            "description": "<strong>Dean Burnett:</strong> Rapper B.o.B. has been criticised for publicly insisting the Earth is flat. You may think his claims are ludicrous, but the truth is: they don\u2019t go far enough",
            "favicon": "",
            "timestamp": "2026-10-26T16:35:17.618Z",
            "block": null,
            "currently_open": true,
            "currently_active": false,
            "time_spent": 5.8115812499963795,
            "is_related": null
        }

def preprocess(page: dict):
    parts = []
    if page.get("title"):
        parts.append(f"Title of the page: {page['title']}")
    if page.get("description"):
        parts.append(f"Search query: {page["description"]}")
    return parts

