import os
import json
import fitz  # PyMuPDF
import pytesseract
import cv2
from PIL import Image
from gpt4all import GPT4All
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class StudyBot:
    def __init__(self):
        try:
            # Load GPT4All model
            self.model = GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf", model_path="models/")
        except Exception as e:
            logging.error(f"Failed to load GPT4All model: {str(e)}")
            exit(1)

        # Initialize formula storage (JSON file)
        self.formulas_file = "formulas.json"
        self.formulas_db = {}
        self.init_formulas_db()

        # Initialize indexed content DB
        self.indexed_db = {}

    def validate_and_fix_json(self):
        try:
            # Attempt to load the JSON file
            with open(self.formulas_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if the "formulas" key exists and is a dictionary
            if not isinstance(data.get("formulas", {}), dict):
                raise ValueError("Invalid structure: 'formulas' key is not a dictionary.")
            
            logging.info("JSON file is valid.")
            return data  # Return the valid data

        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
            logging.error(f"Invalid JSON file: {str(e)}. Resetting to default.")
            # Reset the JSON file to a valid default state
            default_data = {"formulas": {}}
            with open(self.formulas_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data  # Return the default data

    def init_formulas_db(self):
        data = self.validate_and_fix_json()
        self.formulas_db = data.get("formulas", {})

    def normalize_query(self, query):
        """Normalize the query to handle similar variations."""
        filler_words = ['the', 'a', 'an', 'of', 'for', 'to', 'in', 'formula', 'equation']
        words = query.lower().split()
        normalized = ' '.join(word for word in words if word not in filler_words)
        return normalized.strip()

    def get_formula(self, query):
        query_normalized = self.normalize_query(query)
        logging.info(f"Original query: '{query}' normalized to: '{query_normalized}'")
        
        if query_normalized in self.formulas_db:
            logging.info(f"Formula for '{query_normalized}' found in database.")
            return f"📘 From Database:\n{self.formulas_db[query_normalized]}"
        
        logging.info(f"Formula for '{query_normalized}' not found. Generating...")
        structured_prompt = f"""
Provide a structured response for {query} using this exact format:

### Formula
Plain text: [Write the formula using simple characters like ^, *, /, sqrt()]
LaTeX: [Write the formula using LaTeX notation between $$ symbols]

### Definition
[Brief definition in 1-2 sentences]

### Components
- [variable]: [meaning] [unit if applicable]

### Example
Given: [input values]
Step 1: [show substitution with plain text formula]
Step 2: [show calculation]
Result: [final answer with unit]

### Notes
- [key point 1]
- [key point 2]
"""
        response = self.model.generate(structured_prompt)
        self.formulas_db[query_normalized] = response
        try:
            with open(self.formulas_file, 'w', encoding='utf-8') as f:
                json.dump({"formulas": self.formulas_db}, f, indent=2)
            logging.info(f"Formula for '{query_normalized}' saved to formulas.json.")
        except Exception as e:
            logging.error(f"Failed to save formula to file: {str(e)}")
        
        return f"🧮 **Formula Result:**\n{response}"

    def extract_text_from_image_page(self, page, save_path="images/page.png"):
        pix = page.get_pixmap(dpi=300)
        pix.save(save_path)
        img = cv2.imread(save_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)
        processed_path = save_path.replace(".png", "_processed.png")
        cv2.imwrite(processed_path, thresh)
        return pytesseract.image_to_string(Image.open(processed_path))

    def extract_full_pdf_content(self, file_path):  # Remove max_pages parameter
        full_text = ""
        try:
            with fitz.open(file_path) as doc:
                total_pages = len(doc)
                logging.info(f"Processing all {total_pages} pages...")
                
                for i, page in enumerate(doc):
                    # Log progress every 5 pages
                    if i % 5 == 0:
                        logging.info(f"Processing page {i+1}/{total_pages}")
                    
                    page_text = page.get_text().strip()
                    if not page_text:
                        page_text = self.extract_text_from_image_page(page, f"images/page_{i}.png")
                    full_text += f"\n=== Page {i+1} ===\n{page_text}\n"
                    
                logging.info(f"Completed processing {total_pages} pages")
                return full_text
        except Exception as e:
            logging.error(f"Error processing PDF: {str(e)}")
            raise

    def split_text_into_chunks(self, text, chunk_size=1000):
        chunks = []
        while text:
            chunk = text[:chunk_size]
            cutoff = chunk.rfind("\n\n")
            if cutoff == -1:
                cutoff = len(chunk)
            chunks.append(text[:cutoff].strip())
            text = text[cutoff:].strip()
        return chunks

    def index_chapter(self, file_path):
        try:
            logging.info(f"Starting in-depth study of: {file_path}")
            filepath = os.path.join("documents", file_path)
            
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {file_path}")
                
            raw_text = self.extract_full_pdf_content(filepath)
            chunks = self.split_text_into_chunks(raw_text)
            self.indexed_db = {f"chunk_{i}": chunk for i, chunk in enumerate(chunks)}
            
            logging.info(f"Successfully indexed {len(chunks)} chunks")
            return f"""✅ In-depth Study completed:
- Full PDF processed successfully
- Created {len(chunks)} content chunks
- Ready for detailed queries
- Use 'query <your question>' to ask questions"""
    
        except Exception as e:
            logging.error(f"Failed to index chapter: {str(e)}")
            raise

    def answer_from_chapter(self, question):
        matches = []
        for chunk in self.indexed_db.values():
            if any(word in chunk.lower() for word in question.lower().split()):
                matches.append(chunk)
        context = "\n\n".join(matches[:3])
        prompt = f"""
Answer the question using the following textbook content:

{context}

Question: {question}
Answer:
"""
        return self.model.generate(prompt)

    def summarize_chapter(self):
        all_text = "\n\n".join(self.indexed_db.values())
        prompt = f"""
Summarize this chapter in bullet points. Include:
- Key laws and concepts
- Important formulas (in simple plain text)
- Key figures or diagrams if mentioned
- Applications or implications if explained

{all_text[:8000]}
"""
        return self.model.generate(prompt)

    def query_pdf(self, filename, question):
        try:
            text = ""
            filepath = os.path.join("documents", filename)
            if not os.path.exists(filepath):
                logging.error(f"File '{filename}' not found.")
                return f"❌ Error: File '{filename}' not found."
            with fitz.open(filepath) as doc:
                for i, page in enumerate(doc):
                    if i >= 10:
                        break
                    text += page.get_text()

            if not text.strip():
                logging.warning("The document is empty or unreadable.")
                return "❌ Error: The document is empty or unreadable."

            response = self.model.generate(
                f"Answer based on this document:\n{text[:10000]}\n\nQuestion: {question}\nAnswer:"
            )
            return f"📄 PDF Answer:\n{response}"
        except Exception as e:
            logging.error(f"Error processing PDF query: {str(e)}")
            return f"❌ Error: {str(e)}"

    def list_files(self):
        try:
            files = [f for f in os.listdir("documents") if f.endswith('.pdf')]
            return files
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            return []

    def indepth_query(self, question):
        """Get detailed answers after in-depth study"""
        if not self.indexed_db:
            raise ValueError("Please complete In-depth Study first")
        
        # Use more context chunks for detailed answers
        matches = []
        for chunk in self.indexed_db.values():
            if any(word in chunk.lower() for word in question.lower().split()):
                matches.append(chunk)
        
        context = "\n\n".join(matches[:5])  # Use more context chunks
        prompt = f"""
Provide a detailed answer using this textbook content:

{context}

Question: {question}
Please structure your answer with:
- Main explanation
- Key concepts involved
- Examples if applicable
- Related topics or connections

Answer:
"""
        return "📚 Detailed Answer:\n" + self.model.generate(prompt)

    def search_query(self, question):
        """General search using GPT model"""
        prompt = f"""
Provide a detailed answer to this question:

Question: {question}

Please structure your response with:
- Main explanation
- Key points and concepts
- Examples or applications
- Related topics
- Additional resources (if relevant)

Answer:
"""
        return "🔍 Search Result:\n" + self.model.generate(prompt)

def main():
    bot = StudyBot()
    print("🔍 AI Study Bot - Type 'help' for commands")
    
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            print("❌ Please enter a command. Type 'help' for available commands.")
            continue

        if user_input.lower() in ['exit', 'quit']:
            break
        elif user_input.lower() == 'help':
            print("\nCommands:")
            print("ask <question> - Get a formula")
            print("search <question> - General knowledge search")  # Add this
            print("pdf <filename> <question> - Query a PDF")
            print("list - Show available PDFs")
            print("index <filename> - Study PDF in-depth")
            print("query <question> - Ask detailed question after indexing")
            print("summary - Summarize the chapter")
            print("exit - Quit")
        elif user_input.lower() == 'list':
            files = bot.list_files()
            print("\nAvailable PDFs:" if files else "\nNo PDFs found")
            for f in files:
                print(f"- {f}")
        elif user_input.lower().startswith('pdf '):
            parts = user_input.split(maxsplit=2)
            if len(parts) < 3:
                print("Usage: pdf filename.pdf 'your question'")
            else:
                print(bot.query_pdf(parts[1], parts[2]))
        elif user_input.lower().startswith('index '):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print("Usage: index filename.pdf")
            else:
                print(bot.index_chapter(parts[1]))
        elif user_input.lower() == 'summary':
            print(bot.summarize_chapter())
        elif user_input.lower().startswith('ask '):
            print(bot.get_formula(user_input[4:]))
        elif user_input.lower().startswith('query '):
            if not bot.indexed_db:
                print("❌ Please index a PDF chapter first using 'index filename.pdf'")
            else:
                question = user_input[6:].strip()
                print(bot.indepth_query(question))
        elif user_input.lower().startswith('search '):
            question = user_input[7:].strip()
            print(bot.search_query(question))
        else:
            print("❌ Invalid command. Type 'help' for available commands.")

if __name__ == "__main__":
    main()
