import os
from bson.json_util import dumps
from bson.objectid import ObjectId
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
from flask import send_file
from io import BytesIO



app = Flask(__name__)

# SECURITY REQUIREMENT:
# You MUST set a secret_key to use sessions. 
# It encrypts the "badge" so hackers can't fake it.
#app.secret_key = 'super_secret_random_key_here'
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# This dictionary stores the login info. 
# Without this, Python gives a "NameError".
ADMIN_CREDENTIALS = {
    'username': 'admin', 
    'password': '123'
}

# --- 1. CONNECT TO DATABASE ---
client = MongoClient("mongodb://localhost:27017/") 

# Create a database named 'biscast_db'
db = client.biscast_db 

# Create a collection (table) named 'alumni'
alumni_collection = db.alumni 

#@app.route('/') for Graduates
@app.route('/graduate-tracer')
def home():
    return render_template('index.html')

# --- ROUTE 1: The Login Page (GET) ---
@app.route('/admin-login')
def login_page():
    # If already logged in, send straight to dashboard
    if session.get('is_logged_in'):
        return redirect(url_for('dashboard_page'))
        
    return render_template('admin.html')

# --- ROUTE 2: The Logic (POST) ---
@app.route('/admin', methods=['POST'])
def login_logic():
    # 1. Get what the user typed in the HTML form
    user_input = request.form.get('username')
    pass_input = request.form.get('password')

    # 2. Compare input vs your hardcoded dictionary
    if user_input == ADMIN_CREDENTIALS['username'] and pass_input == ADMIN_CREDENTIALS['password']:
        
        # SUCCESS: Give them the "Badge" (Session)
        session['is_logged_in'] = True
        session['username'] = user_input
        return redirect(url_for('dashboard_page'))
        
    else:
        # FAIL: Reload HTML with an error message
        return render_template('admin.html', error="Wrong username or password!")

@app.route('/admin-dashboard')
def dashboard_page():
    # We check if the 'is_admin' badge exists in their session
    if not session.get('is_logged_in'):
        # If they don't have the badge, KICK THEM OUT to the login page
        return redirect(url_for('login_page'))

    # If they pass the check, show the dashboard with username
    username = session.get('username', 'Guest')
    return render_template('alumni-list.html', username=username)

# --- ROUTE: Logout ---
@app.route('/logout')
def logout():
    # Destroy the session (Throw away the badge)
    session.pop('is_logged_in', None)
    session.clear()
    
    # Send them back to the Login Page
    return redirect(url_for('login_page'))


@app.route('/add_alumni', methods=['POST'])
def add_alumni():
    try:
        data = request.json
        # The fix is here: use an underscore (_)
        alumni_collection.insert_one(data)
        
        return jsonify({"message": "Alumni added successfully!"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Error adding data"}), 500
    
@app.route('/delete_alumni/<id>', methods=['DELETE'])
def delete_alumni(id):
    try:
        # 1. Convert the string ID from the URL into a MongoDB ObjectId
        record_id = ObjectId(id)
        
        # 2. Attempt to delete the record from your collection
        # Replace 'collection' with your actual variable name (e.g., db.alumni, alumni_collection)
        result = alumni_collection.delete_one({'_id': record_id})
        
        # 3. Check if a document was actually deleted
        if result.deleted_count == 1:
            return jsonify({'success': True, 'message': 'Deleted successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Record not found'}), 404
            
    except Exception as e:
        # Handle errors (like invalid ID format)
        print(f"Error deleting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# --- 2. GET ONE ROUTE (For Editing) ---
@app.route('/get_one_alumni/<id>', methods=['GET'])
def get_one_alumni(id):
    try:
        # Find the specific student
        student = alumni_collection.find_one({'_id': ObjectId(id)})
        
        if student:
            # Convert ObjectId to string so JSON can read it
            student['_id'] = str(student['_id'])
            return jsonify(student)
        else:
            return jsonify({'error': 'Student not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- 3. UPDATE ROUTE (To save the changes) ---
@app.route('/update_alumni/<id>', methods=['POST'])
def update_alumni(id):
    try:
        data = request.json # Get the updated JSON from frontend
        
        # We use $set to update the fields provided
        result = alumni_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': data}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            return jsonify({'success': True, 'message': 'Updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'No changes made'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_alumni', methods=['GET'])
def get_alumni():
    #find alumni
    alumni_cursor = alumni_collection.find()

    #convert BSON to JSON
    alumni_list = list(alumni_cursor)

    # We need to convert the strange ObjectId to a normal string
    for alumni in alumni_list:
        alumni['_id'] = str(alumni['_id'])
    return jsonify(alumni_list)

# --- PDF REPORT GENERATION ROUTE ---
try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.pdfgen import canvas
except ImportError:
    pass  # If not installed, user must run: pip install reportlab

@app.route('/generate_pdf_report', methods=['GET'])
def generate_pdf_report():
    alumni_cursor = alumni_collection.find()
    alumni_list = list(alumni_cursor)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Adjustable margins and spacing
    left_margin = 30
    right_margin = 30
    top_margin = 40
    row_height = 18
    col_width = 110
    
    y = height - top_margin
    p.setFont("Helvetica-Bold", 16)
    p.drawString(left_margin, y, "Graduate Tracer Alumni Report")
    y -= 30
    
    p.setFont("Helvetica", 9)
    headers = ["Student ID", "Name", "City", "Year Gradated", "Program", "Gender", "Employment"]
    
    # Draw header row with border
    x = left_margin
    for i, header in enumerate(headers):
        p.rect(x, y - row_height, col_width, row_height)
        p.drawString(x + 5, y - row_height + 4, header)
        x += col_width
    
    y -= row_height
    
    def wrap_text(text, max_width, font_name, font_size):
        """Wrap text to fit within max_width"""
        p.setFont(font_name, font_size)
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if p.stringWidth(test_line, font_name, font_size) < max_width - 10:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        return lines
    
    # Draw data rows with borders
    for alumni in alumni_list:
        firstName = alumni.get('personal_info', {}).get('first_name', 'N/A')
        lastName = alumni.get('personal_info', {}).get('last_name', 'N/A')
        city = alumni.get('contact_info', {}).get('city', 'N/A')
        year_grad = alumni.get('personal_info', {}).get('year_grad', 'N/A')
        program = alumni.get('personal_info', {}).get('program', 'N/A')
        gender = alumni.get('personal_info', {}).get('gender', 'N/A')
        employment = alumni.get('employment_data', {}).get('status', 'N/A')
        
        row = [
            str(alumni.get('student_id', 'N/A')),
            f"{firstName} {lastName}",
            city,
            str(year_grad),
            program,
            gender,
            employment
        ]
        
        # Wrap text for each cell and find max lines needed
        wrapped_cells = [wrap_text(cell, col_width, "Helvetica", 9) for cell in row]
        max_lines = max(len(lines) for lines in wrapped_cells)
        dynamic_row_height = row_height * max_lines
        
        # Draw each cell with border and wrapped text
        x = left_margin
        for cell_lines in wrapped_cells:
            p.rect(x, y - dynamic_row_height, col_width, dynamic_row_height)
            text_y = y - row_height + 4
            for line in cell_lines:
                p.drawString(x + 5, text_y, line)
                text_y -= row_height
            x += col_width
        
        y -= dynamic_row_height
        
        # New page if needed
        if y < 50:
            p.showPage()
            y = height - top_margin
    
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="alumni_report.pdf", mimetype='application/pdf')

# --- 3. RUN THE SERVER ---
if __name__ == '__main__':
    app.run(debug=True)