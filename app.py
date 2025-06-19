import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template_string, request

app = Flask(__name__)

# Een eenvoudige HTML-sjabloon voor het uploadformulier
# In een groter project zou dit in een 'templates' map staan
HTML_FORM_TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Excel Analyser</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type="file"], input[type="submit"] { padding: 10px 15px; margin-top: 10px; border-radius: 5px; border: 1px solid #ddd; cursor: pointer; }
        input[type="submit"] { background-color: #007bff; color: white; border-color: #007bff; }
        input[type="submit"]:hover { background-color: #0056b3; }
        pre { background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; }
        img { max-width: 100%; height: auto; display: block; margin: 20px 0; border: 1px solid #ddd; }
        h1, h2 { color: #0056b3; }
        .error { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload je Excel-bestand voor Analyse</h1>
        <form method="POST" enctype="multipart/form-data" action="/analyze">
            <input type="file" name="file" accept=".xlsx, .xls">
            <input type="submit" value="Upload & Analyseer">
        </form>
        <hr>
        <p><em>Let op: Deze tool toont basisinformatie en histogrammen van numerieke kolommen.</em></p>
    </div>
</body>
</html>
"""

# HTML-sjabloon voor de resultatenpagina
RESULTS_TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Analyse Resultaten</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        pre { background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; }
        img { max-width: 100%; height: auto; display: block; margin: 20px auto; border: 1px solid #ddd; }
        h1, h2 { color: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .back-link { display: block; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Analyse Resultaten voor {{ filename }}</h1>

        <h2>DataFrame Informatie:</h2>
        <pre>{{ df_info }}</pre>

        <h2>Eerste 5 rijen van de data:</h2>
        {{ df_head_html | safe }}

        <h2>Beschrijvende Statistieken:</h2>
        {{ df_describe_html | safe }}

        {% if plot_url %}
        <h2>Histogrammen van Numerieke Kolommen:</h2>
        <img src="data:image/png;base64,{{ plot_url }}" alt="Histogrammen">
        {% else %}
        <p>Geen numerieke kolommen gevonden om te plotten, of de plot is mislukt.</p>
        {% endif %}

        <a href="/" class="back-link">Upload een ander bestand</a>
    </div>
</body>
</html>
"""

@app.route('/')
def upload_file():
    """Route voor de startpagina met het uploadformulier."""
    return render_template_string(HTML_FORM_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze_excel():
    """Route om het geüploade Excel-bestand te analyseren en te visualiseren."""
    if 'file' not in request.files:
        return render_template_string(RESULTS_TEMPLATE, filename="Geen bestand",
                                       df_info="<span class='error'>Geen bestand geselecteerd.</span>",
                                       df_head_html="", df_describe_html="", plot_url="")

    file = request.files['file']
    if file.filename == '':
        return render_template_string(RESULTS_TEMPLATE, filename="Geen bestand",
                                       df_info="<span class='error'>Geen bestand geselecteerd.</span>",
                                       df_head_html="", df_describe_html="", plot_url="")

    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            # Lees het Excel-bestand in een Pandas DataFrame
            df = pd.read_excel(file)

            # --- Analyse voor output in HTML ---
            # DataFrame Info
            # df.info() geeft een tekstuele output, die we kunnen omleiden
            buf = io.StringIO()
            df.info(buf=buf)
            df_info_output = buf.getvalue()

            # Eerste 5 rijen als HTML-tabel
            df_head_html = df.head().to_html(classes='table table-striped')

            # Beschrijvende Statistieken als HTML-tabel
            df_describe_html = df.describe().to_html(classes='table table-striped')

            # --- Data Visualisatie (Histogram) ---
            plot_url = ""
            numeric_cols = df.select_dtypes(include=['number']).columns

            if not numeric_cols.empty:
                # Maak een figuur voor de histogrammen
                fig, ax = plt.subplots(figsize=(12, 8))
                df[numeric_cols].hist(ax=ax)
                plt.suptitle('Histogrammen van Numerieke Kolommen', y=1.02)
                plt.tight_layout(rect=[0, 0.03, 1, 0.98])

                # Sla de plot op in een in-memory buffer
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png')
                img_buffer.seek(0) # Ga naar het begin van de buffer
                # Converteer naar base64 string voor inbedding in HTML
                plot_url = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                plt.close(fig) # Sluit de figuur om geheugen vrij te maken

            return render_template_string(RESULTS_TEMPLATE,
                                          filename=file.filename,
                                          df_info=df_info_output,
                                          df_head_html=df_head_html,
                                          df_describe_html=df_describe_html,
                                          plot_url=plot_url)

        except Exception as e:
            return render_template_string(RESULTS_TEMPLATE, filename="Fout bij verwerking",
                                           df_info=f"<span class='error'>Er is een fout opgetreden: {e}</span>",
                                           df_head_html="", df_describe_html="", plot_url="")
    else:
        return render_template_string(RESULTS_TEMPLATE, filename="Ongeldig bestand",
                                       df_info="<span class='error'>Ongeldig bestandstype. Upload een .xlsx of .xls bestand.</span>",
                                       df_head_html="", df_describe_html="", plot_url="")

# Alleen uitvoeren als het script direct wordt aangeroepen (voor lokale ontwikkeling)
if __name__ == '__main__':
    app.run(debug=True)
