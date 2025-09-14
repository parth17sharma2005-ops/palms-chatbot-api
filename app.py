from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import traceback
from chat import get_chat_response, save_lead, is_business_email
import os
from werkzeug.utils import secure_filename
import pdfplumber

app = Flask(__name__)

# Enable CORS for all domains (you can restrict this to your WordPress domain)
CORS(app, origins=["*"])  # For production, replace with your WordPress domain

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        print("Received chat request")  # Debug log

        message = request.form.get('message')
        file = request.files.get('file')
        pdf_text = ''

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            with pdfplumber.open(filepath) as pdf:
                pdf_text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        elif request.is_json:
            data = request.get_json()
            message = data.get("message")
            pdf_text = ''

        if not message:
            return jsonify({"error": "No message field in request"}), 400

        print(f"User message: {message}")  # Debug log

        # Get chat response (now returns dict with response and show_demo_popup)
        chat_result = get_chat_response(message, extra_context=pdf_text)
        
        print(f"Chat result type: {type(chat_result)}")  # Debug log
        print(f"Chat result: {chat_result}")  # Debug log
        
        # Handle both old format (string) and new format (dict) for compatibility
        if isinstance(chat_result, str):
            bot_response = chat_result
            show_demo_popup = False
            show_options = False
        else:
            bot_response = chat_result.get('response', 'Sorry, I encountered an error.')
            show_demo_popup = chat_result.get('show_demo_popup', False)
            show_options = chat_result.get('show_options', False)
        
        print(f"Bot response: {bot_response}")  # Debug log
        print(f"Show demo popup: {show_demo_popup}")  # Debug log
        print(f"Show options: {show_options}")  # Debug log

        response_json = {
            "response": bot_response,
            "show_demo_popup": show_demo_popup,
            "show_options": show_options
        }
        print(f"Final JSON response: {response_json}")  # Debug log

        return jsonify(response_json)

    except Exception as e:
        print(f"Error in /chat endpoint: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

from chat import save_lead, is_business_email

@app.route("/save_lead", methods=["POST"])
def save_lead_route():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    if not name or not email:
        return jsonify({"success": False, "message": "Name and email required."}), 400
    if not is_business_email(email):
        return jsonify({"success": False, "message": "Please provide a business email address."}), 400
    save_lead(name, email)
    return jsonify({"success": True, "message": "Thank you! Our sales team will contact you soon."})

@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route("/leads", methods=["GET"])
def view_leads():
    """View all captured leads"""
    import csv
    import os
    
    leads_file = os.path.join(os.path.dirname(__file__), "leads.csv")
    leads = []
    
    if os.path.exists(leads_file):
        with open(leads_file, 'r', newline='') as file:
            reader = csv.DictReader(file)
            leads = list(reader)
    
    # Return as HTML table for easy viewing
    html = """
    <html>
    <head>
        <title>PALMS™ Chatbot Leads</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #2F5D50; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #2F5D50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .download { background: #3A80BA; color: white; padding: 10px 20px; 
                       text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>PALMS™ Chatbot Demo Leads</h1>
        <a href="/leads/download" class="download">📥 Download CSV</a>
        <p><strong>Total Leads:</strong> """ + str(len(leads)) + """</p>
        <table>
            <tr><th>Name</th><th>Email</th></tr>
    """
    
    for lead in leads:
        html += f"<tr><td>{lead.get('Name', '')}</td><td>{lead.get('Email', '')}</td></tr>"
    
    html += """
        </table>
        <p style="margin-top: 40px; color: #666;">
            <small>Leads are captured when visitors fill out the demo form in your chatbot widget.</small>
        </p>
    </body>
    </html>
    """
    
    return html

@app.route("/leads/download", methods=["GET"])
def download_leads():
    """Download leads as CSV file"""
    import csv
    import os
    from flask import send_file
    
    leads_file = os.path.join(os.path.dirname(__file__), "leads.csv")
    
    if os.path.exists(leads_file):
        return send_file(leads_file, as_attachment=True, download_name="palms_chatbot_leads.csv")
    else:
        return jsonify({"error": "No leads file found"}), 404

@app.route("/clients")
def clients():
    return render_template("clients.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/products")
def products():
    return render_template("products.html")

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/locations")
def locations():
    return render_template("locations.html")

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(debug=True, host="127.0.0.1", port=8000)