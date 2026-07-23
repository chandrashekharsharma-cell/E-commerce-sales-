"""
06_build_dashboard.py
-----------------------
Injects dashboard/dashboard_data.json into dashboard/template.html to
produce the final, self-contained dashboard/novacart_dashboard.html
(no external data file needed at runtime — everything is inlined).
"""
import json

with open("dashboard/dashboard_data.json") as f:
    data = json.load(f)

with open("dashboard/template.html") as f:
    template = f.read()

placeholder = "/*{{DASHBOARD_DATA}}*/"
assert placeholder in template, "Placeholder not found in template!"

final_html = template.replace(placeholder, json.dumps(data))

with open("dashboard/novacart_dashboard.html", "w") as f:
    f.write(final_html)

print(f"Built dashboard/novacart_dashboard.html ({len(final_html)/1024:.1f} KB)")
