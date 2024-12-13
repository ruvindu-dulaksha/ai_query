import os
import pdfplumber
import docx
import requests
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox

# Directly set the API keys and tokens
HF_API_KEY = "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"  # Hugging Face API key
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Paths for uploaded documents
UPLOAD_PATH = "uploads"
os.makedirs(UPLOAD_PATH, exist_ok=True)

# SQLite Database setup for storing document contents
DB_PATH = "documents.db"

# Initialize the database (if it doesn't exist)
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_name TEXT,
                        content TEXT)''')
    conn.commit()
    conn.close()

# Functidef storon to store document content in the database
e_document(file_name, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO documents (file_name, content) VALUES (?, ?)", (file_name, content))
    conn.commit()
    conn.close()

# Function to extract text from documents
def extract_content(file_path):
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    else:
        raise ValueError("Unsupported file format")

# Function to send query to Hugging Face API
def query_huggingface_api(prompt):
    data = {
        "inputs": prompt,
        "parameters": {"max_length": 500}
    }

    # Make a request to Hugging Face API
    response = requests.post(HF_API_URL, headers=HEADERS, json=data)

    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        return f"Error: {response.status_code} - {response.text}"

# Function to handle file upload
def upload_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf"), ("Word Files", "*.docx"), ("Text Files", "*.txt")])
    if file_path:
        try:
            # Extract content from document
            content = extract_content(file_path)

            # Store document content in the database
            store_document(os.path.basename(file_path), content)

            # Display success message
            result_box.delete("1.0", tk.END)
            result_box.insert(tk.END, f"Document '{os.path.basename(file_path)}' uploaded and processed successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Error processing document: {e}")

# Function to handle query input
def send_query():
    query = query_entry.get()
    if query:
        try:
            # Search the database for relevant documents
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT file_name, content FROM documents")
            documents = cursor.fetchall()
            conn.close()

            # Identify the most relevant document based on the query
            relevant_doc = None
            highest_relevance_score = 0

            for file_name, content in documents:
                relevance_score = content.lower().count(query.lower()) + file_name.lower().count(query.lower())
                if relevance_score > highest_relevance_score:
                    relevant_doc = (file_name, content)
                    highest_relevance_score = relevance_score

            if relevant_doc:
                file_name, document_content = relevant_doc

                # Truncate document content to 3000 characters to fit within the token limit
                document_content = document_content[:3000]

                # Send query and document content to Hugging Face API
                prompt = f"Document Title: {file_name}\nDocument Content: {document_content}\n\nAnswer this query based on the document content:\n{query}"
                response = query_huggingface_api(prompt)

                # Display response in the result box
                result_box.delete("1.0", tk.END)
                result_box.insert(tk.END, response or "No relevant information found.")
            else:
                result_box.delete("1.0", tk.END)
                result_box.insert(tk.END, "No relevant document found for your query.")
        except Exception as e:
            messagebox.showerror("Error", f"Error processing query: {e}")
    else:
        messagebox.showwarning("Input Error", "Please enter a query.")

# Set up the Tkinter window
root = tk.Tk()
root.title("AI Document and Query Processor")
root.geometry("600x500")  # Set larger window size

# Set up the upload button
frame = tk.Frame(root)
frame.pack(pady=10)

upload_button = tk.Button(frame, text="Upload Document", command=upload_file, width=20, height=2)
upload_button.grid(row=0, column=0, padx=10)

# Set up the query entry field and send button
query_label = tk.Label(root, text="Enter your query:", font=("Arial", 12))
query_label.pack(pady=10)

query_entry = tk.Entry(root, width=50, font=("Arial", 12))
query_entry.pack(pady=5)

send_button = tk.Button(root, text="Send Query", command=send_query, width=20, height=2)
send_button.pack(pady=10)

# Set up the result text box with larger font for readability
result_box = tk.Text(root, height=10, width=60, font=("Arial", 12), wrap="word")
result_box.pack(pady=10)

# Initialize the database
init_db()

# Run the Tkinter main loop
root.mainloop()
