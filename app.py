from flask import Flask, render_template, request, send_file, jsonify, session
from extractor import extract_data
from trafilatura_extractor import extract_clean_text
from robots_checker import is_allowed
import re
import io
from extractor import extract_by_tags_structured
from llm_utils import ask_groq_llm
import markdown as md 
import pandas as pd

app = Flask(__name__)
app.secret_key = "d8f4b17b8f3f47c6a3a9ff2e1e6cb802"


def clean_wikipedia(text):
    text = re.sub(r'\[\d+\]', '', text)  # Remove footnote refs
    text = re.sub(r'\[edit\]', '', text)  # Remove [edit]
    text = re.sub(r'This article has multiple issues.*?talk page\.', '', text, flags=re.IGNORECASE)
    return text.strip()

def extract_tables(url):
    """Extract tables from a webpage in Full Page mode"""
    try:
        # Use your existing extraction logic
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tables = []
        for table in soup.find_all('table'):
            # Convert each table to a list of lists
            table_data = []
            for row in table.find_all('tr'):
                cols = row.find_all(['th', 'td'])
                cols = [col.text.strip() for col in cols]
                table_data.append(cols)
            tables.append(table_data)
            
        return tables
        
    except Exception as e:
        print(f"Error extracting tables: {str(e)}")
        return None

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url:
            return render_template('result.html', error="Please provide a valid URL.")
        
        mode = request.form.get('mode', 'full')
        clean_text = ""
        tables = []
        text = []
        error = ""

        # ✅ Step 1: robots.txt check
        if not is_allowed(url):
            error = "⚠️ This page is disallowed for scraping by the site's robots.txt rules."
            return render_template('result.html', tables=[], text=[], clean_text="", error=error)

        # ✅ Step 2: Clean Text Mode
        if mode == 'clean':
            clean_text = extract_clean_text(url)
            if clean_text.startswith("Error:") or clean_text.strip() == "":
                error = clean_text
                clean_text = ""
            else:
                clean_text = clean_wikipedia(clean_text)

        # ✅ Step 3: HTML Tags Filtering Mode
        elif mode == 'tags':
            from extractor import extract_by_tags

            selected_tags = request.form.getlist('tags')
            class_filter = request.form.get('class_filter', '').strip()
            id_filter = request.form.get('id_filter', '').strip()

            # ✅ Smart options
            skip_empty = 'skip_empty' in request.form
            skip_duplicates = 'skip_duplicates' in request.form
            skip_hidden = 'skip_hidden' in request.form
            depth = request.form.get('depth', 'deep')

            clean_text = extract_by_tags(
                url,
                tags=selected_tags,
                class_filter=class_filter,
                id_filter=id_filter,
                skip_empty=skip_empty,
                skip_duplicates=skip_duplicates,
                skip_hidden=skip_hidden,
                depth=depth
            )

            if clean_text.startswith("Error:") or clean_text.strip() == "":
                error = clean_text
                clean_text = ""

        # ✅ Step 4: Full Extraction
        else:
            tables, text, error = extract_data(url)

        return render_template(
            'result.html',
            tables=tables,
            text=text,
            clean_text=clean_text,
            error=error
        )

    return render_template('index.html')

@app.route('/ask_llm', methods=['POST'])
def ask_llm():
    try:
        # Accept form fields (support both names just in case)
        user_query = request.form.get('query') or request.form.get('user_query')
        extracted_text = request.form.get('extracted_text') or request.form.get('extracted_data')

        if not user_query or not extracted_text:
            return jsonify({"error": "Missing query or extracted text."}), 400

        # Call your existing LLM wrapper which should return HTML (string)
        # (make sure ask_groq_llm returns HTML table / HTML fragment)
        llm_html = ask_groq_llm(extracted_text, user_query)

        # If the wrapper returned an error string, return it as JSON error
        if isinstance(llm_html, str) and llm_html.startswith("Error"):
            return jsonify({"error": llm_html}), 500

        # Convert Markdown to HTML (including tables)
        html_content = md.markdown(llm_html, extensions=['tables'])

        # Add styling for the table
        styled_html = f"""
        <style>
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 10px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        </style>
        {html_content}
        """


        # Return HTML directly in JSON
        session['llm_html_table'] = styled_html  # ✅ store LLM output for export
        return jsonify({"html_table": styled_html})

    except Exception as e:
        return jsonify({"error": f"Error processing LLM request: {str(e)}"}), 500


@app.route('/download', methods=['POST'])
def download_data():
    try:
        dataset_type = request.form.get('dataset_type', 'extracted')
        file_format = request.form.get('format', 'csv')
        mode = request.form.get('mode', 'full')

        if dataset_type == 'llm':
            # Handle LLM analysis results
            llm_html = session.get('llm_html_table') or request.form.get('llm_table_html')
            if not llm_html:
                return "No LLM data available", 400

            try:
                df_list = pd.read_html(llm_html)
                df = df_list[0] if df_list else pd.DataFrame()
            except Exception as e:
                return f"Failed to parse LLM table: {e}", 500

        elif dataset_type == 'tables' and mode == 'full':
            # Handle Full Page mode tables export
            url = request.form.get('url')
            if not url:
                return "URL is required", 400
                
            # Extract tables from the page (you need to implement this)
            tables = extract_tables(url)
            if not tables:
                return "No tables found to export", 400
            
            # Combine all tables into one DataFrame
            df = pd.concat([pd.DataFrame(table) for table in tables], ignore_index=True)

        elif dataset_type == 'clean_text':
            # Handle Clean Text export (works for both 'clean' and 'full' modes)
            clean_text = request.form.get('clean_text', '')
            if not clean_text:
                return "No clean text available for export", 400
            
            df = pd.DataFrame({'text': [clean_text]})

        elif mode == 'tags':
            # Handle HTML Tags mode
            data = request.form
            url = data.get('url')
            tags = request.form.getlist('tags[]')
            class_filter = data.get('class_filter', '')
            id_filter = data.get('id_filter', '')
            skip_empty = data.get('skip_empty') == 'true'
            skip_duplicates = data.get('skip_duplicates') == 'true'
            skip_hidden = data.get('skip_hidden') == 'true'
            depth = data.get('depth', 'deep')

            df, error = extract_by_tags_structured(
                url, tags,
                class_filter=class_filter,
                id_filter=id_filter,
                skip_empty=skip_empty,
                skip_duplicates=skip_duplicates,
                skip_hidden=skip_hidden,
                depth=depth
            )

            if error:
                return error, 400
        else:
            # Default case for extracted data
            clean_text = request.form.get('clean_text', '')
            if clean_text:
                df = pd.DataFrame({'text': [clean_text]})
            else:
                return "No data available for export", 400

        # Common export logic
        buffer = io.BytesIO()
        if file_format == 'excel':
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                attachment_filename=f"web_data.xlsx",
                as_attachment=True
            )
        else:
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='text/csv',
                attachment_filename=f"web_data.csv",
                as_attachment=True
            )

    except Exception as e:
        return f"Error generating download: {str(e)}", 500
    
if __name__ == '__main__':
    app.run(debug=True)
