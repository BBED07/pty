import os
import random
import textwrap
import warnings
import psycopg2
from psycopg2 import sql
import unicodedata
warnings.filterwarnings("ignore", category=DeprecationWarning)


# Database connection parameters
DATABASE_URL = "postgresql://vocabulary_bmsr_user:g5MPKnua7FkUBWy1gMRDcBonGSyiHsNy@dpg-cufneh5ds78s73fmpbug-a.frankfurt-postgres.render.com/vocabulary_bmsr"

def initialize_database():
    """Create the necessary database table if it doesn't exist"""
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()
    
    # Create the vocabulary table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id SERIAL PRIMARY KEY,
            english VARCHAR(255) NOT NULL,
            portuguese VARCHAR(255) NOT NULL,
            example TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create a unique index on the english word
        CREATE UNIQUE INDEX IF NOT EXISTS idx_vocabulary_english 
        ON vocabulary(english);
        
        -- Create a function to update the updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Create a trigger to automatically update the updated_at column
        DROP TRIGGER IF EXISTS update_vocabulary_updated_at ON vocabulary;
        CREATE TRIGGER update_vocabulary_updated_at
            BEFORE UPDATE ON vocabulary
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    conn.commit()
    cur.close()
    conn.close()

    
def normalize_text(text):
    """Normalize Unicode text to NFC form"""
    return unicodedata.normalize('NFC', text)

def add_word():
    """Add a new word pair with an example sentence"""
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
    
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO vocabulary (english, portuguese, example)
            VALUES (%s, %s, %s)
        """, (english, portuguese, example_sentence))
        conn.commit()
        print(f"Added: {english} -> {portuguese} | Example: {example_sentence}")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error adding word: {e}")
    finally:
        cur.close()
        conn.close()

def quiz_user():
    """Quiz the user with corrections and requiring a correct retry"""
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()
    
    # Check if there are any words in the database
    cur.execute("SELECT COUNT(*) FROM vocabulary")
    if cur.fetchone()[0] == 0:
        print("No vocabulary loaded!")
        cur.close()
        conn.close()
        return

    def do_quiz(quiz_items):
        correct = 0
        attempted = 0
        incorrect_words = []

        for english, portuguese, example in quiz_items:
            attempted += 1
            answer = input(f"{english}: ").strip().lower()

            if answer in ['exit', 'quit']:
                print(f"\nQuiz ended. You got {correct}/{attempted} correct.")
                print("\nWords to review:")
                for eng, port, _ in incorrect_words:
                    print(f"{eng} -> {port}")
                return None

            if answer == portuguese.lower():
                print("Correct!")
                print(f"Example: {example}")
                correct += 1
            else:
                print(f"Wrong. The correct answer is '{portuguese}'")
                incorrect_words.append((english, portuguese, example))

        print(f"\nQuiz completed! You got {correct}/{attempted} correct.")
        if incorrect_words:
            print("\nWords to review:")
            for eng, port, _ in incorrect_words:
                print(f"{eng} -> {port}")
        
        return incorrect_words

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
        cur.close()
        conn.close()
        return

    if choice == '1':
        # Get total word count
        cur.execute("SELECT COUNT(*) FROM vocabulary")
        total_words = cur.fetchone()[0]
        
        while True:
            try:
                start_num = input(f"\nEnter start number (1-{total_words}, or press Enter for beginning, 0 to cancel): ").strip()
                if start_num == "0":
                    cur.close()
                    conn.close()
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
                    cur.close()
                    conn.close()
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

        cur.execute("""
            SELECT english, portuguese, example 
            FROM vocabulary 
            ORDER BY english 
            OFFSET %s LIMIT %s
        """, (start_idx, end_idx - start_idx))
        selected_items = cur.fetchall()
    else:
        # Get total word count
        cur.execute("SELECT COUNT(*) FROM vocabulary")
        total_words = cur.fetchone()[0]
        
        while True:
            try:
                num = input(f"\nHow many words to quiz (max {total_words}, 0 to cancel)? ")
                if num == "0":
                    cur.close()
                    conn.close()
                    return
                num = int(num)
                if 0 < num <= total_words:
                    break
                print(f"Please enter a number between 1 and {total_words}")
            except ValueError:
                print("Please enter a valid number")
        
        cur.execute("""
            SELECT english, portuguese, example 
            FROM vocabulary 
            ORDER BY RANDOM() 
            LIMIT %s
        """, (num,))
        selected_items = cur.fetchall()

    print("\nQuiz time! Type the Portuguese word for the given English word.")
    print("(Type 'exit' or 'quit' to end the quiz)")
    
    # Start main quiz loop
    current_items = selected_items
    while current_items:
        incorrect_words = do_quiz(current_items)
        if incorrect_words is None:  # User chose to exit
            break
        if not incorrect_words:  # All correct
            break
        print("\nStarting review of incorrect words...")
        current_items = incorrect_words

    cur.close()
    conn.close()

# Continue with the rest of the functions (view_vocabulary, edit_word, export_vocabulary, delete_word)
# following the same pattern of replacing JSON operations with PostgreSQL queries...

def main():
    try:
        initialize_database()
        
        while True:
            print("\nVocabulary Notebook")
            print("1. Add a new word")
            print("2. Take a quiz")
            print("3. View vocabulary")
            print("4. Edit a word")
            print("5. Delete a word")
            print("6. Export to file")
            print("7. Exit")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                add_word()
            elif choice == "2":
                quiz_user()
            elif choice == "3":
                view_vocabulary()
            elif choice == "4":
                edit_word()
            elif choice == "5":
                delete_word()
            elif choice == "6":
                export_vocabulary()
            elif choice == "7":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check your database connection settings and try again.")

if __name__ == "__main__":
    main()
