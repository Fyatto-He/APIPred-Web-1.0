import sqlite3

DB_PATH = "aptamers.db"

class AptamerDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Create the aptamer library table if it does not exist"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS aptamers (
                id INTEGER PRIMARY KEY,
                sequence TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def insert_aptamer(self, sequence):
        """Insert a new aptamer sequence"""
        self.cursor.execute("INSERT INTO aptamers (sequence) VALUES (?)", (sequence,))
        self.conn.commit()

    def search_best_match(self, num_results=10):
        """
        Retrieves the top aptamer sequences. Modify this if using scoring.
        """
        self.cursor.execute("SELECT sequence FROM aptamers LIMIT ?", (num_results,))
        return [row[0] for row in self.cursor.fetchall()]

# Create an instance
aptamer_db = AptamerDatabase()
with open("/Users/catherinezhang/Desktop/APIPred/backend/database/sequence.txt", "r") as file:
    for line in file:
        aptamer_db.insert_aptamer(line.strip())
