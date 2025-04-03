from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import numpy as np 
import traceback

app = Flask(__name__)

# --- Configuration & Column Names from your notebook ---
DATA_FILE_PATH = os.path.join('data', 'data.csv')
# Columns used for filtering/display (ensure these match data.csv EXACTLY)
COL_YEAR = 'year' 
COL_INST_TYPE = 'institute_type' # IIT/NIT
COL_ROUND = 'round_no'
COL_QUOTA = 'quota' # AI, HS, OS, AP, GO, JK, LA
COL_POOL = 'pool' # Gender-Neutral, Female-Only
COL_INST_SHORT = 'institute_short'
COL_PROG_NAME = 'program_name'
COL_PROG_DUR = 'program_duration'
COL_DEGREE = 'degree_short'
COL_CATEGORY = 'category' # GEN, OBC-NCL, SC, ST, *-PWD, *-EWS
COL_OPEN_RANK = 'opening_rank'
COL_CLOSE_RANK = 'closing_rank'
COL_IS_PREP = 'is_preparatory' 
# --- End Configuration ---

# --- Data Loading Function ---
def load_data():
    """Loads and preprocesses the dataset from data.csv."""
    try:
        if not os.path.exists(DATA_FILE_PATH):
             error_msg = f"Error: Data file not found at {DATA_FILE_PATH}. Please ensure 'data.csv' is in the 'data' directory."
             print(error_msg)
             return None, error_msg
            
        try:
            df = pd.read_csv(DATA_FILE_PATH)
        except UnicodeDecodeError:
            df = pd.read_csv(DATA_FILE_PATH, encoding='latin1')
        
        print(f"Initial rows loaded: {len(df)}")

        # Drop the empty 'Unnamed: 13' column if it exists
        if 'Unnamed: 13' in df.columns:
            df.drop(columns=['Unnamed: 13'], inplace=True)
            print("Dropped 'Unnamed: 13' column.")
        
        # --- Basic Preprocessing ---
        required_cols = [
            COL_YEAR, COL_INST_TYPE, COL_ROUND, COL_QUOTA, COL_POOL, 
            COL_INST_SHORT, COL_PROG_NAME, COL_PROG_DUR, COL_DEGREE, 
            COL_CATEGORY, COL_OPEN_RANK, COL_CLOSE_RANK, COL_IS_PREP
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            error_msg = f"Error: Dataset is missing required columns: {', '.join(missing)}. Please check data.csv headers."
            print(error_msg)
            return None, error_msg

        # Convert ranks to numeric, coercing errors. Crucial for comparison.
        df[COL_OPEN_RANK] = pd.to_numeric(df[COL_OPEN_RANK], errors='coerce')
        df[COL_CLOSE_RANK] = pd.to_numeric(df[COL_CLOSE_RANK], errors='coerce')
        
        # Drop rows where closing rank is invalid (NaN) as they can't be used for prediction
        initial_rows = len(df)
        df.dropna(subset=[COL_CLOSE_RANK], inplace=True)
        rows_dropped = initial_rows - len(df)
        if rows_dropped > 0:
            print(f"Dropped {rows_dropped} rows due to invalid closing rank.")

        # Ensure rank columns are integers after handling NaNs
        df[COL_CLOSE_RANK] = df[COL_CLOSE_RANK].astype(int)
        # Fill NaN opening ranks with a placeholder if needed, then convert
        df[COL_OPEN_RANK] = df[COL_OPEN_RANK].fillna(-1).astype(int) 

        # Standardize text columns used for filtering (case-insensitive matching where appropriate)
        # Convert to string first to avoid errors on potential numeric/mixed types
        df[COL_QUOTA] = df[COL_QUOTA].astype(str).str.strip().str.upper()
        df[COL_POOL] = df[COL_POOL].astype(str).str.strip() # Keep original case from notebook: Gender-Neutral, Female-Only
        df[COL_CATEGORY] = df[COL_CATEGORY].astype(str).str.strip().str.upper()
        df[COL_INST_TYPE] = df[COL_INST_TYPE].astype(str).str.strip().str.upper()
        df[COL_INST_SHORT] = df[COL_INST_SHORT].astype(str).str.strip()
        df[COL_PROG_NAME] = df[COL_PROG_NAME].astype(str).str.strip()
        df[COL_DEGREE] = df[COL_DEGREE].astype(str).str.strip()

        # Convert year and round to appropriate types
        df[COL_YEAR] = df[COL_YEAR].astype(int)
        df[COL_ROUND] = df[COL_ROUND].astype(int)

        print(f"Dataset loaded and preprocessed successfully. Final rows: {len(df)}")
        # print(df.info()) # Uncomment for debugging
        return df, None

    except FileNotFoundError: # This case is handled by the os.path.exists check above
        pass # Error already generated
    except Exception as e:
        error_msg = f"Error during data loading or processing: {e}"
        print(error_msg)
        traceback.print_exc() # Print detailed traceback for server logs
        return None, f"Error: Could not load or process the data file. Check server logs for details."

# --- Load data on application start ---
df_colleges, load_error = load_data()

# --- Prepare data for dropdowns --- 
def get_dropdown_options(df):
    options = {}
    default_options = {
        'years': [], 'rounds': [], 'quotas': [], 
        'pools': [], 'categories': [], 'institute_types': []
    }
    if df is None:
        return default_options
        
    try:
        options['years'] = sorted(df[COL_YEAR].unique(), reverse=True)
        options['rounds'] = sorted(df[COL_ROUND].unique())
        # Filter out potential empty strings or unexpected values after conversion
        options['quotas'] = sorted([q for q in df[COL_QUOTA].unique() if q and pd.notna(q)])
        options['pools'] = sorted([p for p in df[COL_POOL].unique() if p and pd.notna(p)])
        options['categories'] = sorted([c for c in df[COL_CATEGORY].unique() if c and pd.notna(c)])
        options['institute_types'] = sorted([it for it in df[COL_INST_TYPE].unique() if it and pd.notna(it)])
        return options
    except Exception as e:
        print(f"Error generating dropdown options: {e}")
        traceback.print_exc()
        return default_options # Return empty lists if error occurs

dropdown_options = get_dropdown_options(df_colleges)

# --- Route for the main page ---
@app.route('/', methods=['GET'])
def index():
    """Renders the main prediction form."""
    return render_template('index.html', load_error=load_error, dropdowns=dropdown_options)

# --- Route for handling the prediction request (API) ---
@app.route('/predict', methods=['POST'])
def predict():
    """Filters colleges based on user input and returns results as JSON."""
    if df_colleges is None:
        return jsonify({"error": load_error or "Dataset not available. Check server logs."}), 500

    try:
        data = request.get_json()
        if not data:
             return jsonify({"error": "Invalid request data."}), 400

        # --- Extract and Validate Inputs ---
        try:
            user_rank = int(data.get('rank'))
            if user_rank <= 0:
                raise ValueError("Rank must be a positive integer.")
        except (ValueError, TypeError, AttributeError):
            return jsonify({"error": "Invalid Rank provided. Please enter a positive whole number."}), 400

        # Get other filters, converting to uppercase/correct format for matching
        category = data.get('category', '').strip().upper()
        quota = data.get('quota', '').strip().upper()
        pool = data.get('pool', '').strip() # Match case from data 
        inst_type = data.get('institute_type', '').strip().upper()
        year_str = data.get('year', '')
        round_str = data.get('round_no', '')

        # --- Filtering Logic --- 
        # Start with a copy to avoid modifying the global DataFrame
        filtered_df = df_colleges.copy()

        # Apply mandatory rank filter first
        filtered_df = filtered_df[filtered_df[COL_CLOSE_RANK] >= user_rank]
        
        # Apply mandatory text filters
        if category:
             filtered_df = filtered_df[filtered_df[COL_CATEGORY] == category]
        else: # Category is required by form JS, but double-check
             return jsonify({"error": "Category is required."}), 400
             
        if pool: 
             filtered_df = filtered_df[filtered_df[COL_POOL] == pool]
        else: # Pool is required by form JS
            return jsonify({"error": "Gender Pool is required."}), 400

        # Apply optional filters
        if quota:
            filtered_df = filtered_df[filtered_df[COL_QUOTA] == quota]
        if inst_type:
            filtered_df = filtered_df[filtered_df[COL_INST_TYPE] == inst_type]
        
        # Handle optional numeric filters (Year, Round)
        try:
            if year_str:
                filtered_df = filtered_df[filtered_df[COL_YEAR] == int(year_str)]
            if round_str:
                 filtered_df = filtered_df[filtered_df[COL_ROUND] == int(round_str)]
        except ValueError:
             # Should not happen if dropdowns are populated correctly, but handle anyway
             return jsonify({"error": "Invalid Year or Round number format."}), 400

        # Sort by closing rank (best rank first)
        filtered_df.sort_values(by=COL_CLOSE_RANK, ascending=True, inplace=True)

        # Select and format results - Keep relevant columns from your notebook context
        result_cols = [COL_INST_SHORT, COL_PROG_NAME, COL_DEGREE, COL_YEAR, COL_ROUND, COL_CLOSE_RANK]
        # Limit results to avoid overwhelming the user (e.g., top 250)
        results = filtered_df[result_cols].head(250).to_dict('records')

        return jsonify({"colleges": results})

    except Exception as e:
        print(f"Error during prediction processing: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred processing your request. Please try again."}), 500

# --- Run the App ---
if __name__ == '__main__':
    # Set debug=False for production environments
    app.run(host='0.0.0.0', port=5000, debug=True) 