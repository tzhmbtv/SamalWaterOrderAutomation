"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
from typing import Optional, Dict
from config import DATABASE_PATH


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Создает подключение к базе данных"""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Инициализирует базу данных и создает таблицы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                phone TEXT,
                contact_phone TEXT,
                address TEXT,
                first_name TEXT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заказов (для истории)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                total_price INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users (chat_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_user(self, chat_id: int, **kwargs):
        """
        Сохраняет или обновляет данные пользователя
        
        Args:
            chat_id: Telegram chat ID
            **kwargs: Дополнительные поля (phone, contact_phone, address, first_name, comment)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Проверяем существует ли пользователь
        cursor.execute('SELECT chat_id FROM users WHERE chat_id = ?', (chat_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Обновляем существующего пользователя
            update_fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['phone', 'contact_phone', 'address', 'first_name', 'comment']:
                    update_fields.append(f'{key} = ?')
                    values.append(value)
            
            if update_fields:
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                values.append(chat_id)
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE chat_id = ?"
                cursor.execute(query, values)
        else:
            # Создаем нового пользователя
            cursor.execute('''
                INSERT INTO users (chat_id, phone, contact_phone, address, first_name, comment)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                chat_id,
                kwargs.get('phone', ''),
                kwargs.get('contact_phone', ''),
                kwargs.get('address', ''),
                kwargs.get('first_name', ''),
                kwargs.get('comment', '')
            ))
        
        conn.commit()
        conn.close()
    
    def get_user(self, chat_id: int) -> Optional[Dict]:
        """
        Получает данные пользователя
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Словарь с данными пользователя или None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chat_id, phone, contact_phone, address, first_name, comment
            FROM users WHERE chat_id = ?
        ''', (chat_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'chat_id': row[0],
                'phone': row[1],
                'contact_phone': row[2],
                'address': row[3],
                'first_name': row[4],
                'comment': row[5]
            }
        return None
    
    def save_order(self, chat_id: int, product_id: int, product_name: str, 
                   quantity: int, total_price: int, status: str = 'pending'):
        """Сохраняет информацию о заказе"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (chat_id, product_id, product_name, quantity, total_price, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (chat_id, product_id, product_name, quantity, total_price, status))
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return order_id
    
    def update_order_status(self, order_id: int, status: str):
        """Обновляет статус заказа"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        
        conn.commit()
        conn.close()
    
    def get_user_orders(self, chat_id: int, limit: int = 10):
        """Получает последние заказы пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, product_name, quantity, total_price, status, created_at
            FROM orders
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (chat_id, limit))
        
        orders = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'product_name': row[1],
            'quantity': row[2],
            'total_price': row[3],
            'status': row[4],
            'created_at': row[5]
        } for row in orders]

