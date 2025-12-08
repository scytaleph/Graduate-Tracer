from bson.json_util import dumps
from bson.objectid import ObjectId
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient



app = Flask(__name__)

# SECURITY REQUIREMENT:
# You MUST set a secret_key to use sessions. 
# It encrypts the "badge" so hackers can't fake it.
app.secret_key = 'super_secret_random_key_here'

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

# --- ADD THIS NEW ROUTE BELOW ---
#@app.route('/tracer-list')
#def view_list():
#    return render_template('alumni-list.html')
# --------------------------------

# --- 3. RUN THE SERVER ---
if __name__ == '__main__':
    app.run(debug=True)