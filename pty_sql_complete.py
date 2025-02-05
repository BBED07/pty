import os
import random
import textwrap
import warnings
import psycopg2
from psycopg2 import sql
import unicodedata
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from fpdf2 import FPDF
except ImportError:
    from fpdf import FPDF

# 数据库连接
DATABASE_URL = "postgresql://vocabulary_bmsr_user:g5MPKnua7FkUBWy1gMRDcBonGSyiHsNy@dpg-cufneh5ds78s73fmpbug-a.frankfurt-postgres.render.com/vocabulary_bmsr"

def get_db_connection():
    """创建并返回数据库连接"""
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def normalize_text(text):
    """标准化Unicode文本为NFC形式"""
    return unicodedata.normalize('NFC', text)

def add_word():
    """添加新单词及示例句子"""
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
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO words (english, portuguese, example)
            VALUES (%s, %s, %s)
        """, (english, portuguese, example_sentence))
        conn.commit()
        print(f"Added: {english} -> {portuguese} | 示例: {example_sentence}")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"添加单词时出错: {e}")
    finally:
        cur.close()
        conn.close()

def quiz_user():
    """测试用户并要求正确重试"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 检查是否有单词
    cur.execute("SELECT COUNT(*) FROM words")
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
                if incorrect_words:
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
        # 获取总单词数
        cur.execute("SELECT COUNT(*) FROM words")
        total_words = cur.fetchone()[0]
        
        while True:
            try:
                start_num = input(f"\nEnter start number (1-{total_words}, or press Enter for beginning, 0 to cancel)): ").strip()
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
                print(f"Enter a number between 0 and {total_words}")
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
                print(f"Please enter a number between {start_idx + 1} and {total_words}.")
            except ValueError:
                print("Please enter a valid number")

        cur.execute("""
            SELECT english, portuguese, example 
            FROM words 
            ORDER BY english 
            OFFSET %s LIMIT %s
        """, (start_idx, end_idx - start_idx))
        selected_items = cur.fetchall()
    else:
        # 获取总单词数
        cur.execute("SELECT COUNT(*) FROM words")
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
                print(f"Please enter a number between 1 and {total_words}.")
            except ValueError:
                print("Please enter a valid number")
        
        cur.execute("""
            SELECT english, portuguese, example 
            FROM words 
            ORDER BY RANDOM() 
            LIMIT %s
        """, (num,))
        selected_items = cur.fetchall()

    print("\nQuiz time! Type the Portuguese word for the given English word.")
    print("(Type 'exit' or 'quit' to end the quiz)")
    
    # 开始主测试循环
    current_items = selected_items
    while current_items:
        incorrect_words = do_quiz(current_items)
        if incorrect_words is None:  # 用户选择退出
            break
        if not incorrect_words:  # 全部正确
            break
        print("\nStarting review of incorrect words...")
        current_items = incorrect_words

    cur.close()
    conn.close()

def view_vocabulary():
    """查看词汇表"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM words")
    if cur.fetchone()[0] == 0:
        print("No words in the vocabulary. Add some first!")
        cur.close()
        conn.close()
        return

    print("\nView Options:")
    print("0. Back to main menu")
    print("1. View complete list")
    print("2. Search words")
    
    choice = input("\nChoose an option: ").strip()
    
    if choice == "0":
        cur.close()
        conn.close()
        return
    elif choice == "1":
        cur.execute("""
            SELECT english, portuguese, example, created_at 
            FROM words 
            ORDER BY english
        """)
        words = cur.fetchall()

        print("\nVocabulary:")
        print(f"{'ID':<5}{'English':<30}{'Portuguese':<30}{'Created_Time':<20}{'Example'}")
        print("-" * 160)
        
        for idx, (english, portuguese, example, created_at) in enumerate(words, 1):
            created_at_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else ""
            wrapped_lines = textwrap.wrap(example, width=75)
            
            # 打印第一行，包含所有列
            first_line = wrapped_lines[0] if wrapped_lines else ""
            print(f"{idx:<5}{english:<30}{portuguese:<30}{created_at_str:<20}{first_line}")
            
            # 打印剩余的示例句子行，保持适当的缩进
            for line in wrapped_lines[1:]:
                print(f"{'':<5}{'':<30}{'':<30}{'':<20}{line}")
    
    elif choice == "2":
        print("\nEnter part of the English or Portuguese word to search (0 to cancel):")
        word = input().strip()
        
        if word == "0":
            cur.close()
            conn.close()
            return
            
        if not word:
            print("No input provided. Please try again.")
            cur.close()
            conn.close()
            return
            
        # 搜索匹配的单词
        cur.execute("""
            SELECT english, portuguese, example, created_at, updated_at 
            FROM words 
            WHERE LOWER(english) LIKE LOWER(%s) 
               OR LOWER(portuguese) LIKE LOWER(%s)
            ORDER BY english
        """, (f"%{word}%", f"%{word}%"))
        
        matches = cur.fetchall()
        
        if not matches:
            print("No matching words found.")
            cur.close()
            conn.close()
            return
            
        if len(matches) > 1:
            print("\nMultiple matches found:")
            for idx, (english, portuguese, example, created_at, updated_at) in enumerate(matches, 1):
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else ""
                print(f"{idx}. {english} -> {portuguese} (Created Time: {created_at_str})")
                
            while True:
                try:
                    select = int(input("\nSelect a number to view details (0 to cancel): "))
                    if select == 0:
                        cur.close()
                        conn.close()
                        return
                    if 1 <= select <= len(matches):
                        selected_word = matches[select - 1]
                        break
                    print(f"Please enter a number between 0 and {len(matches)}.")
                except ValueError:
                    print("Please enter a valid number")
        else:
            selected_word = matches[0]
        
        english, portuguese, example, created_at, updated_at = selected_word
        print(f"\nDetailed information:")
        print(f"English: {english}")
        print(f"Portuguese: {portuguese}")
        print(f"Example: {example}")
    
    else:
        print("Invalid choice. Please try again.")

    cur.close()
    conn.close()

def edit_word():
    """编辑单词"""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\nEnter part of the English or Portuguese word to search (0 to cancel):")
    word = input().strip()
    
    if word == "0":
        cur.close()
        conn.close()
        return
        
    if not word:
        print("No input provided. Please try again.")
        cur.close()
        conn.close()
        return
        
    # 搜索匹配的单词
    cur.execute("""
        SELECT english, portuguese, example 
        FROM words 
        WHERE LOWER(english) LIKE LOWER(%s) 
           OR LOWER(portuguese) LIKE LOWER(%s)
        ORDER BY english
    """, (f"%{word}%", f"%{word}%"))
    
    matches = cur.fetchall()
    
    if not matches:
        print("No matching words found. Please try again.")
        cur.close()
        conn.close()
        return
        
    if len(matches) > 1:
        print("\nMultiple matches found:")
        for idx, (english, portuguese, example) in enumerate(matches, 1):
            print(f"{idx}. {english} -> {portuguese} | Example: {example}")
            
        while True:
            try:
                select = int(input("\nSelect the number of the word you want to edit (0 to cancel): "))
                if select == 0:
                    cur.close()
                    conn.close()
                    return
                if 1 <= select <= len(matches):
                    selected_word = matches[select - 1]
                    break
                print(f"Please enter a number between 1 and {len(matches)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        selected_word = matches[0]
    
    english, portuguese, example = selected_word
    print(f"\nSelected: {english} -> {portuguese} | Example: {example}")
    print("(Press Enter to keep the current value, or enter 0 to cancel)")
    
    new_english = input("Enter the new English word: ").strip()
    if new_english == "0":
        cur.close()
        conn.close()
        return
        
    new_portuguese = input("Enter the new Portuguese word: ").strip()
    if new_portuguese == "0":
        cur.close()
        conn.close()
        return
    if new_portuguese:
        new_portuguese = normalize_text(new_portuguese)
        
    new_example = input("Enter a new example sentence: ").strip()
    if new_example == "0":
        cur.close()
        conn.close()
        return
    if new_example:
        new_example = normalize_text(new_example)

    try:
        # 构建更新语句
        update_fields = []
        update_values = []
        
        if new_english:
            update_fields.append("english = %s")
            update_values.append(new_english)
        
        if new_portuguese:
            update_fields.append("portuguese = %s")
            update_values.append(new_portuguese)
            
        if new_example:
            update_fields.append("example = %s")
            update_values.append(new_example)
            
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        if update_fields:
            update_query = f"""
                UPDATE words 
                SET {', '.join(update_fields)}
                WHERE english = %s
            """
            update_values.append(english)
            
            cur.execute(update_query, update_values)
            conn.commit()
            print("Success!")
            
            # 显示更新后的信息
            cur.execute("""
                SELECT english, portuguese, example 
                FROM words 
                WHERE english = %s
            """, (new_english if new_english else english,))
            
            updated_word = cur.fetchone()
            print(f"Updated: {updated_word[0]} -> {updated_word[1]} | Example: {updated_word[2]}")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"更新单词时出错: {e}")
    finally:
        cur.close()
        conn.close()

def delete_word():
    """删除单词"""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\nDelete Options:")
    print("0. Back to main menu")
    print("1. Delete by word")
    print("2. Delete by number")
    
    choice = input("\nChoose an option: ").strip()
    
    if choice == "0":
        cur.close()
        conn.close()
        return
    elif choice == "1":
        print("\nEnter part of the English or Portuguese word to search:")
        word = input().strip()
        
        if not word:
            print("No input provided. Please try again.")
            cur.close()
            conn.close()
            return
            
        # 搜索匹配的单词
        cur.execute("""
            SELECT english, portuguese, example 
            FROM words 
            WHERE LOWER(english) LIKE LOWER(%s) 
               OR LOWER(portuguese) LIKE LOWER(%s)
            ORDER BY english
        """, (f"%{word}%", f"%{word}%"))
        
        matches = cur.fetchall()
        
        if not matches:
            print("No matching words found.")
            cur.close()
            conn.close()
            return
            
        if len(matches) > 1:
            print("\nMultiple matches found:")
            for idx, (english, portuguese, example) in enumerate(matches, 1):
                print(f"{idx}. {english} -> {portuguese} | Example: {example}")
                
            while True:
                try:
                    select = int(input("\nSelect the number of the word you want to delete (0 to cancel): "))
                    if select == 0:
                        cur.close()
                        conn.close()
                        return
                    if 1 <= select <= len(matches):
                        english = matches[select - 1][0]
                        break
                    print(f"Please enter a number between 0 and {len(matches)}")
                except ValueError:
                    print("Please enter a valid number")
        else:
            english = matches[0][0]
            
    elif choice == "2":
        cur.execute("SELECT english, portuguese FROM words ORDER BY english")
        words = cur.fetchall()
        
        print("\nVocabulary:")
        for idx, (english, portuguese) in enumerate(words, 1):
            print(f"{idx}. {english} -> {portuguese}")
        
        while True:
            try:
                num = int(input(f"\nEnter the number to delete (1-{len(words)}, 0 to cancel): "))
                if num == 0:
                    cur.close()
                    conn.close()
                    return
                if 1 <= num <= len(words):
                    english = words[num - 1][0]
                    break
                print(f"Please enter a number between 1 and {len(words)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        print("Invalid choice. Please try again.")
        cur.close()
        conn.close()
        return
        
    # 执行删除
    try:
        cur.execute("SELECT portuguese, example FROM words WHERE english = %s", (english,))
        word_info = cur.fetchone()
        if word_info:
            portuguese, example = word_info
            print(f"\nFound word: {english} -> {portuguese}")
            print(f"Example: {example}")
            
        confirm = input("Are you sure you want to delete this word? (y/n): ").strip().lower()
        if confirm == 'y':
            cur.execute("DELETE FROM words WHERE english = %s", (english,))
            conn.commit()
            print("Word deleted successfully.")
        else:
            print("Deletion cancelled.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"删除单词时出错: {e}")
    finally:
        cur.close()
        conn.close()

def export_vocabulary():
    """导出词汇表"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM words")
    if cur.fetchone()[0] == 0:
        print("No vocabulary to export.")
        cur.close()
        conn.close()
        return

    base_path = "/Users/nandong/Library/Mobile Documents/com~apple~CloudDocs"
    
    while True:
        choice = input("\nExport format (1 for text, 2 for PDF, 0 to cancel): ").strip()
        if choice in ['0', '1', '2']:
            break
        print("Invalid choice. Please enter 0, 1 or 2.")
    
    if choice == '0':
        cur.close()
        conn.close()
        return
        
    include_examples = input("Include example sentences? (y/n): ").strip().lower()
    while include_examples not in ['y', 'n']:
        include_examples = input("Please enter 'y' or 'n': ").strip().lower()

    # 获取所有单词
    cur.execute("""
        SELECT english, portuguese, example 
        FROM words 
        ORDER BY english
    """)
    words = cur.fetchall()

    if choice == '1':
        export_file = os.path.join(base_path, "vocabulary.txt")
        try:
            with open(export_file, "w", encoding='utf-8') as file:
                for english, portuguese, example in words:
                    if include_examples == 'y':
                        file.write(f"{english} -> {portuguese} | Example: {example}\n")
                    else:
                        file.write(f"{english} -> {portuguese}\n")
            print(f"\nVocabulary exported to: {export_file}")
        except Exception as e:
            print(f"导出词汇表时出错: {e}")
    else:
        export_file = os.path.join(base_path, "vocabulary.pdf")
        export_as_pdf(words, export_file, include_examples)

    cur.close()
    conn.close()

def export_as_pdf(words, export_file, include_examples):
    """导出词汇表为PDF文件"""
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
            wrap_widths = [0, 50, 50]
        
        line_height = 8

        def add_header():
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(col_widths[0], line_height, "ID", 1, 0, 'C', True)
            pdf.cell(col_widths[1], line_height, "English", 1, 0, 'C', True)
            pdf.cell(col_widths[2], line_height, "Portuguese", 1, 0, 'C', True)
            if include_examples == 'y':
                pdf.cell(col_widths[3], line_height, "Example", 1, 1, 'C', True)
            else:
                pdf.ln()
        
        add_header()
        
        for idx, (english, portuguese, example) in enumerate(words, 1):
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                add_header()
            
            if include_examples == 'y':
                eng_lines = textwrap.wrap(english, width=wrap_widths[1])
                port_lines = textwrap.wrap(portuguese, width=wrap_widths[2])
                example_lines = textwrap.wrap(example, width=wrap_widths[3])
                max_lines = max(len(eng_lines) or 1, len(port_lines) or 1, len(example_lines) or 1)
            else:
                eng_lines = textwrap.wrap(english, width=wrap_widths[1])
                port_lines = textwrap.wrap(portuguese, width=wrap_widths[2])
                max_lines = max(len(eng_lines) or 1, len(port_lines) or 1)
            
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

def main():
    """主程序"""
    # 确保数据库表存在
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 创建words表（如果不存在）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY,
                english VARCHAR(255) UNIQUE NOT NULL,
                portuguese VARCHAR(255) NOT NULL,
                example TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except psycopg2.Error as e:
        print(f"初始化数据库时出错: {e}")
        return
    finally:
        cur.close()
        conn.close()

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

if __name__ == "__main__":
    main()
