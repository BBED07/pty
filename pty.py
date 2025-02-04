import json
import random
import textwrap
import os
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from fpdf2 import FPDF
except ImportError:
    from fpdf import FPDF
import unicodedata

# File to store the vocabulary
VOCAB_FILE = "/Users/nandong/Library/Mobile Documents/com~apple~CloudDocs/vocabulary.json"

# Load vocabulary from the file
def load_vocabulary():
    try:
        with open(VOCAB_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save vocabulary to the file
def save_vocabulary(vocabulary):
    with open(VOCAB_FILE, "w") as file:
        json.dump(vocabulary, file, ensure_ascii=False, indent=4)

def normalize_text(text):
    # 将组合字符转换为单个字符（NFC 形式）
    return unicodedata.normalize('NFC', text)

# Add a new word pair with an example sentence
def add_word(vocabulary):
    english = input("Enter the English word (0 to cancel): ").strip()
    if english == "0":
        return
        
    portuguese = input("Enter the Portuguese word (0 to cancel): ").strip()
    if portuguese == "0":
        return
    portuguese = normalize_text(portuguese)
    
    example_sentence = input(f"Enter an example sentence for '{english}' (0 to cancel): ").strip()
    if example_sentence == "0":
        return
    example_sentence = normalize_text(example_sentence)
    
    vocabulary[english] = {'portuguese': portuguese, 'example': example_sentence}
    print(f"Added: {english} -> {portuguese} | Example: {example_sentence}")

# Quiz the user with corrections and requiring a correct retry
def quiz_user(vocabulary):
    if not vocabulary:
        print("No vocabulary loaded!")
        return

    def do_quiz(quiz_items):
        correct = 0
        attempted = 0
        incorrect_words = []

        for english, data in quiz_items:
            attempted += 1
            answer = input(f"{english}: ").strip().lower()

            if answer in ['exit', 'quit']:
                print(f"\nQuiz ended. You got {correct}/{attempted} correct.")
                print("\nWords to review:")
                for eng, port in incorrect_words:
                    print(f"{eng} -> {port}")
                return None  # 返回None表示用户退出

            if answer == data['portuguese'].lower():
                print("Correct!")
                print(f"Example: {data['example']}")
                correct += 1
            else:
                print(f"Wrong. The correct answer is '{data['portuguese']}'")
                incorrect_words.append((english, data['portuguese']))

        print(f"\nQuiz completed! You got {correct}/{attempted} correct.")
        if incorrect_words:
            print("\nWords to review:")
            for eng, port in incorrect_words:
                print(f"{eng} -> {port}")
        
        return incorrect_words  # 返回错误单词列表

    print("\nChoose quiz mode:")
    print("0. Back to main menu")
    print("1. Quiz by alphabetical range")
    print("2. Quiz random words")
    
    while True:
        choice = input("Enter your choice (0-2): ").strip()
        if choice in ['0', '1', '2']:
            break
        print("Invalid choice. Please enter 0, 1 or 2.")
    
    if choice == '0':
        return

    if choice == '1':
        # 按字母排序
        sorted_items = sorted(vocabulary.items())
        total_words = len(sorted_items)
        
        while True:
            try:
                start_num = input(f"\nEnter start number (1-{total_words}, or press Enter for beginning, 0 to cancel): ").strip()
                if start_num == "0":
                    return
                if start_num == "":
                    start_idx = 0
                    break
                start_idx = int(start_num) - 1
                if 0 <= start_idx < total_words:
                    break
                print(f"Please enter a number between 0 and {total_words}")
            except ValueError:
                print("Please enter a valid number")

        while True:
            try:
                end_num = input(f"Enter end number ({start_idx + 1}-{total_words}, or press Enter for end, 0 to cancel): ").strip()
                if end_num == "0":
                    return
                if end_num == "":
                    end_idx = total_words
                    break
                end_idx = int(end_num)
                if start_idx + 1 <= end_idx <= total_words:
                    break
                print(f"Please enter a number between {start_idx + 1} and {total_words}")
            except ValueError:
                print("Please enter a valid number")

        selected_items = sorted_items[start_idx:end_idx]
    else:
        # 随机选择
        while True:
            try:
                num = input(f"\nHow many words to quiz (max {len(vocabulary)}, 0 to cancel)? ")
                if num == "0":
                    return
                num = int(num)
                if 0 < num <= len(vocabulary):
                    break
                print(f"Please enter a number between 1 and {len(vocabulary)}")
            except ValueError:
                print("Please enter a valid number")
        
        selected_items = random.sample(list(vocabulary.items()), num)

    print("\nQuiz time! Type the Portuguese word for the given English word.")
    print("(Type 'exit' or 'quit' to end the quiz)")
    
    # 开始主quiz循环
    current_items = selected_items
    while current_items:
        incorrect_words = do_quiz(current_items)
        if incorrect_words is None:  # 用户选择退出
            return
        if not incorrect_words:  # 全部答对
            break
        print("\nStarting review of incorrect words...")
        current_items = [(eng, vocabulary[eng]) for eng, _ in incorrect_words]

# View all words in the vocabulary with example sentences
def view_vocabulary(vocabulary):
    if not vocabulary:
        print("No words in the vocabulary. Add some first!")
        return

    print("\nView Options:")
    print("0. Back to main menu")
    print("1. View complete list")
    print("2. Search words")
    
    choice = input("\nChoose an option: ").strip()
    
    if choice == "0":
        return
    elif choice == "1":
        print("\nVocabulary List:")
        sorted_vocabulary = sorted(vocabulary.items())

        # Print header for table
        print(f"{'No.':<5}{'English':<30}{'Portuguese':<30}{'Example'}")
        print("-" * 160)
        # Print each word in a row
        for idx, (english, data) in enumerate(sorted_vocabulary, start=1):
            wrapped_lines = textwrap.wrap(data['example'], width=100)
            
            # Print first line with all columns
            first_line = wrapped_lines[0] if wrapped_lines else ""
            print(f"{idx:<5}{english:<30}{data['portuguese']:<30}{first_line}")
            
            # Print remaining lines with proper indentation
            for line in wrapped_lines[1:]:
                print(f"{'':<5}{'':<30}{'':<30}{line}")
    
    elif choice == "2":
        print("\nEnter part of the English or Portuguese word to search (0 to cancel):")
        word = input().strip()
        
        if word == "0":
            return
            
        if not word:
            print("No input provided. Please try again.")
            return
            
        matches = []
        word = word.lower()
        
        # Search for matching words
        for english, data in sorted(vocabulary.items()):
            if (word in english.lower() or 
                word in data['portuguese'].lower()):
                matches.append((english, data))
        
        if not matches:
            print("No matching words found.")
            return
            
        if len(matches) > 1:
            # Display all matches briefly
            print("\nMultiple matches found:")
            for idx, (english, data) in enumerate(matches, 1):
                print(f"{idx}. {english} -> {data['portuguese']}")
                
            # Let user select a specific word
            while True:
                try:
                    select = int(input("\nSelect a number to view details (0 to cancel): "))
                    if select == 0:
                        return
                    if 1 <= select <= len(matches):
                        english, data = matches[select - 1]
                        break
                    print(f"Please enter a number between 0 and {len(matches)}")
                except ValueError:
                    print("Please enter a valid number")
        else:
            english, data = matches[0]
        
        # Display detailed information for the selected word
        print(f"\nDetailed information:")
        print(f"English: {english}")
        print(f"Portuguese: {data['portuguese']}")
        print(f"Example: {data['example']}")
    
    else:
        print("Invalid choice. Please try again.")

# Edit a word in the vocabulary
def edit_word(vocabulary):
    if not vocabulary:
        print("No words in the vocabulary. Add some first!")
        return

    print("\nEnter part of the English or Portuguese word to search (0 to cancel):")
    choice = input().strip()
    
    if choice == "0":
        return
        
    if not choice:
        print("No input provided. Please try again.")
        return
        
    matches = []
    choice = choice.lower()
    
    # Search for matching words
    for english, data in sorted(vocabulary.items()):
        if (choice in english.lower() or 
            choice in data['portuguese'].lower()):
            matches.append((english, data))
    
    if not matches:
        print("No matching words found. Please try again.")
        return
    
    if len(matches) > 1:
        print("\nMultiple matches found:")
        for idx, (english, data) in enumerate(matches, 1):
            print(f"{idx}. {english} -> {data['portuguese']} | Example: {data['example']}")
        
        while True:
            try:
                select = int(input("\nSelect the number of the word you want to edit (0 to cancel): "))
                if select == 0:
                    return
                if 1 <= select <= len(matches):
                    selected_word = matches[select - 1]
                    break
                print(f"Please enter a number between 1 and {len(matches)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        selected_word = matches[0]
        
    english, data = selected_word
    print(f"\nSelected: {english} -> {data['portuguese']} | Example: {data['example']}")
    print("(Press Enter to keep the current value, or enter 0 to cancel)")
    
    new_english = input("Enter the new English word: ").strip()
    if new_english == "0":
        return
        
    new_portuguese = input("Enter the new Portuguese word: ").strip()
    if new_portuguese == "0":
        return
    if new_portuguese:
        new_portuguese = normalize_text(new_portuguese)
        
    new_example = input("Enter a new example sentence: ").strip()
    if new_example == "0":
        return
    if new_example:
        new_example = normalize_text(new_example)

    # Update the word
    if new_english:
        del vocabulary[english]  # Remove the old key
        english = new_english
    if new_portuguese:
        data['portuguese'] = new_portuguese
    if new_example:
        data['example'] = new_example

    vocabulary[english] = data
    print(f"Updated to: {english} -> {data['portuguese']} | Example: {data['example']}")

# Export vocabulary to a text file
def export_vocabulary(vocabulary):
    if not vocabulary:
        print("No vocabulary to export.")
        return

    base_path = "/Users/nandong/Library/Mobile Documents/com~apple~CloudDocs"
    
    while True:
        choice = input("\nExport format (1 for text, 2 for PDF, 0 to cancel): ").strip()
        if choice in ['0', '1', '2']:
            break
        print("Invalid choice. Please enter 0, 1 or 2.")
    
    if choice == '0':
        return
        
    include_examples = input("Include example sentences? (y/n): ").strip().lower()
    while include_examples not in ['y', 'n']:
        include_examples = input("Please enter 'y' or 'n': ").strip().lower()

    if choice == '1':
        export_file = os.path.join(base_path, "vocabulary.txt")
        try:
            with open(export_file, "w", encoding='utf-8') as file:
                for english, data in sorted(vocabulary.items()):
                    if include_examples == 'y':
                        file.write(f"{english} -> {data['portuguese']} | Example: {data['example']}\n")
                    else:
                        file.write(f"{english} -> {data['portuguese']}\n")
            print(f"\nVocabulary exported to: {export_file}")
        except Exception as e:
            print(f"Error exporting vocabulary: {e}")
    else:
        export_file = os.path.join(base_path, "vocabulary.pdf")
        export_as_pdf(vocabulary, export_file, include_examples)

def export_as_pdf(vocabulary, export_file, include_examples):
    try:
        class PDF(FPDF):
            def __init__(self):
                super().__init__()
                self.set_compression(True)
            
            def header(self):
                pass
            
            def footer(self):
                pass
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        
        if include_examples == 'y':
            col_widths = [10, 40, 40, 100]
            wrap_widths = [0, 22, 22, 45]
        else:
            col_widths = [10, 90, 90]
            wrap_widths = [0, 50, 0]
        
        line_height = 8

        def add_header():
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(col_widths[0], line_height, "No.", 1, 0, 'C', True)
            pdf.cell(col_widths[1], line_height, "English", 1, 0, 'C', True)
            pdf.cell(col_widths[2], line_height, "Portuguese", 1, 0, 'C', True)
            if include_examples == 'y':
                pdf.cell(col_widths[3], line_height, "Example", 1, 1, 'C', True)
            else:
                pdf.ln()
        
        add_header()
        
        for idx, (english, data) in enumerate(sorted(vocabulary.items()), 1):
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                add_header()
            
            portuguese = normalize_text(data['portuguese'])
            example = normalize_text(data['example']) if include_examples == 'y' else ''
            
            if include_examples == 'y':
                eng_lines = textwrap.wrap(english, width=wrap_widths[1])
                port_lines = textwrap.wrap(portuguese, width=wrap_widths[2])
                example_lines = textwrap.wrap(example, width=wrap_widths[3])
                max_lines = max(len(eng_lines) or 1, len(port_lines) or 1, len(example_lines) or 1)
            else:
                eng_lines = textwrap.wrap(english, width=wrap_widths[1])
                port_lines = [portuguese]
                max_lines = max(len(eng_lines) or 1, 1)
            
            start_y = pdf.get_y()
            
            pdf.cell(col_widths[0], line_height * max_lines, str(idx), 1, 0, 'C')
            
            x_positions = [pdf.get_x()]
            pdf.cell(col_widths[1], line_height * max_lines, '', 1, 0)
            x_positions.append(pdf.get_x())
            pdf.cell(col_widths[2], line_height * max_lines, '', 1, 0)
            x_positions.append(pdf.get_x())
            if include_examples == 'y':
                pdf.cell(col_widths[3], line_height * max_lines, '', 1, 1)
            else:
                pdf.ln()
            
            for i in range(max_lines):
                pdf.set_xy(x_positions[0], start_y + i * line_height)
                if i < len(eng_lines):
                    pdf.cell(col_widths[1], line_height, eng_lines[i], 0, 0)
                
                pdf.set_xy(x_positions[1], start_y + i * line_height)
                if i < len(port_lines):
                    try:
                        pdf.cell(col_widths[2], line_height, port_lines[i], 0, 0)
                    except:
                        text = unicodedata.normalize('NFKD', port_lines[i])
                        text = ''.join([c for c in text if not unicodedata.combining(c)])
                        pdf.cell(col_widths[2], line_height, text, 0, 0)
                
                if include_examples == 'y':
                    pdf.set_xy(x_positions[2], start_y + i * line_height)
                    if i < len(example_lines):
                        try:
                            pdf.cell(col_widths[3], line_height, example_lines[i], 0, 0)
                        except:
                            text = unicodedata.normalize('NFKD', example_lines[i])
                            text = ''.join([c for c in text if not unicodedata.combining(c)])
                            pdf.cell(col_widths[3], line_height, text, 0, 0)
            
            pdf.set_y(start_y + max_lines * line_height)
        
        pdf.output(export_file)
        print(f"\nVocabulary exported to: {export_file}")
    except Exception as e:
        print(f"Error exporting vocabulary: {e}")

# Delete a word from vocabulary
def delete_word(vocabulary):
    if not vocabulary:
        print("No words in the vocabulary. Add some first!")
        return
        
    print("\nDelete Options:")
    print("0. Back to main menu")
    print("1. Delete by word")
    print("2. Delete by number")
    
    choice = input("\nChoose an option: ").strip()
    
    if choice == "0":
        return
    elif choice == "1":
        print("\nEnter part of the English or Portuguese word to search:")
        word = input().strip()
        
        if not word:
            print("No input provided. Please try again.")
            return
            
        matches = []
        word = word.lower()
        
        # Search for matching words
        for english, data in list(vocabulary.items()):
            if (word in english.lower() or 
                word in data['portuguese'].lower()):
                matches.append((english, data))
        
        if not matches:
            print("No matching words found.")
            return
            
        if len(matches) > 1:
            print("\nMultiple matches found:")
            for idx, (english, data) in enumerate(matches, 1):
                print(f"{idx}. {english} -> {data['portuguese']} | Example: {data['example']}")
                
            while True:
                try:
                    select = int(input("\nSelect the number of the word you want to delete (0 to cancel): "))
                    if select == 0:
                        return
                    if 1 <= select <= len(matches):
                        english, data = matches[select - 1]
                        break
                    print(f"Please enter a number between 1 and {len(matches)}")
                except ValueError:
                    print("Please enter a valid number")
        else:
            english, data = matches[0]
        
        print(f"\nFound word: {english} -> {data['portuguese']}")
        print(f"Example: {data['example']}")
        
        confirm = input("Are you sure you want to delete this word? (y/n): ").strip().lower()
        if confirm == 'y':
            del vocabulary[english]
            print("Word deleted successfully.")
        else:
            print("Deletion cancelled.")
            
    elif choice == "2":
        sorted_items = sorted(vocabulary.items())
        print("\nVocabulary List:")
        for idx, (english, data) in enumerate(sorted_items, 1):
            print(f"{idx}. {english} -> {data['portuguese']}")
        
        while True:
            try:
                num = input(f"\nEnter the number to delete (1-{len(vocabulary)}, 0 to cancel): ")
                if num == "0":
                    return
                num = int(num)
                if 1 <= num <= len(vocabulary):
                    english, data = sorted_items[num - 1]
                    print(f"\nSelected: {english} -> {data['portuguese']}")
                    print(f"Example: {data['example']}")
                    
                    confirm = input("Are you sure you want to delete this word? (y/n): ").strip().lower()
                    if confirm == 'y':
                        del vocabulary[english]
                        print("Word deleted successfully.")
                    else:
                        print("Deletion cancelled.")
                    break
                print(f"Please enter a number between 1 and {len(vocabulary)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        print("Invalid choice. Please try again.")

# Main menu
def main():
    vocabulary = load_vocabulary()

    while True:
        print("\nVocabulary Notebook")
        print("1. Add a new word")
        print("2. Take a quiz")
        print("3. View vocabulary")
        print("4. Edit a word")
        print("5. Delete a word")
        print("6. Export to text file")
        print("7. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_word(vocabulary)
            save_vocabulary(vocabulary)
        elif choice == "2":
            quiz_user(vocabulary)
        elif choice == "3":
            view_vocabulary(vocabulary)
        elif choice == "4":
            edit_word(vocabulary)
            save_vocabulary(vocabulary)
        elif choice == "5":
            delete_word(vocabulary)
            save_vocabulary(vocabulary)
        elif choice == "6":
            export_vocabulary(vocabulary)
        elif choice == "7":
            save_vocabulary(vocabulary)
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
