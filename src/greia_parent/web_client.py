from __future__ import annotations


def render_parent_web_app() -> str:
    """Render a fail-closed page when the pinned Parent client is unavailable.

    Production Parent management has exactly one browser implementation: the
    integrity-pinned static client under ``/usr/share/greia-parent``. This
    fallback deliberately contains no management controls and no sample data;
    silently serving a second embedded application would make a broken or stale
    deployment look healthy and can expose behavior different from the reviewed
    Parent client.
    """

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Greia Parents unavailable</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f7f7f4;color:#242424;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:36rem;margin:2rem;padding:2rem;background:white;border:1px solid #ddd;border-radius:1rem;box-shadow:0 4px 20px #00000010}
h1{margin-top:0;font-size:1.5rem}p{line-height:1.55;color:#555}
</style>
</head>
<body>
<main role="alert">
<h1>Greia Parents is not installed correctly</h1>
<p>The reviewed Parent application could not be loaded from this Greia. No substitute or sample interface has been started.</p>
<p>Repair the pinned Parent client deployment and reload this page.</p>
</main>
</body>
</html>
"""
