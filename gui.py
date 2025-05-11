import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from main import StudyBot

class StudyBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📘 StudyBot AI")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')  # Light gray background

        self.bot = StudyBot()
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        # Configure styles for widgets
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TButton', padding=5, font=('Segoe UI', 10))
        style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        style.configure('TCombobox', padding=5, font=('Segoe UI', 10))

    def create_widgets(self):
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Top frame for controls
        top_frame = ttk.Frame(main_container)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Mode selection frame
        mode_frame = ttk.LabelFrame(top_frame, text="Mode", padding="5")
        mode_frame.pack(side=tk.LEFT, padx=(0, 10))

        self.mode_var = tk.StringVar(value="ask")
        ttk.Radiobutton(mode_frame, text="Ask Formula", variable=self.mode_var, 
                       value="ask").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Query PDF", variable=self.mode_var, 
                       value="pdf").pack(side=tk.LEFT, padx=5)

        # PDF controls frame
        pdf_frame = ttk.Frame(top_frame)
        pdf_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.file_button = ttk.Button(pdf_frame, text="📂 Select PDF", command=self.select_pdf)
        self.file_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.list_btn = ttk.Button(pdf_frame, text="📄 List PDFs", command=self.list_pdfs)
        self.list_btn.pack(side=tk.LEFT)

        self.file_label = ttk.Label(pdf_frame, text="No PDF selected")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Query frame
        query_frame = ttk.LabelFrame(main_container, text="Query", padding="5")
        query_frame.pack(fill=tk.X, pady=(0, 10))

        self.query_entry = ttk.Entry(query_frame, font=("Segoe UI", 12))
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
        self.query_entry.bind("<Return>", lambda event: self.handle_query())

        self.submit_btn = tk.Button(query_frame, text="🔍 Submit", command=self.handle_query,
                                  bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"),
                                  relief=tk.FLAT, padx=20)
        self.submit_btn.pack(side=tk.LEFT)

        # Output area
        output_frame = ttk.LabelFrame(main_container, text="Response", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_box = scrolledtext.ScrolledText(
            output_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 11),
            bg='#ffffff',
            border=0
        )
        self.output_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var,
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def select_pdf(self):
        file_path = filedialog.askopenfilename(initialdir="documents", title="Select PDF",
                                               filetypes=(("PDF Files", "*.pdf"),))
        if file_path:
            self.selected_file = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
            self.file_label.config(text=f"Selected: {self.selected_file}", fg="black")
            self.status_var.set(f"Selected PDF: {self.selected_file}")

    def handle_query(self):
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a query.")
            return

        mode = self.mode_var.get()
        self.output_box.delete(1.0, tk.END)  # Clear output

        self.status_var.set("Processing...")
        self.root.update_idletasks()

        if mode == "ask":
            result = self.bot.get_formula(query)
        elif mode == "pdf":
            if not self.selected_file:
                messagebox.showerror("No File", "Please select a PDF file.")
                self.status_var.set("No PDF selected.")
                return
            result = self.bot.query_pdf(self.selected_file, query)
        else:
            result = "Invalid mode selected."

        self.output_box.insert(tk.END, result)
        self.status_var.set("Done.")

    def list_pdfs(self):
        files = self.bot.list_files()
        if files:
            msg = "Available PDFs:\n" + "\n".join(f"- {f}" for f in files)
        else:
            msg = "No PDFs found in the documents folder."
        messagebox.showinfo("PDF Files", msg)
        self.status_var.set("Listed PDFs.")

if __name__ == "__main__":
    root = tk.Tk()
    gui = StudyBotGUI(root)
    root.mainloop()
