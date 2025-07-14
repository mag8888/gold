import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from typing import Dict, Optional
import logging

class GoogleSheetsManager:
    def __init__(self):
        self.credentials_path = os.getenv('GOOGLE_SHEETS_CREDS')
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
        self.client = None
        self.worksheet = None
        self.init_connection()
    
    def init_connection(self):
        """Инициализация подключения к Google Sheets"""
        try:
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                logging.warning("Google Sheets credentials file not found")
                return False
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path, scope
            )
            
            self.client = gspread.authorize(credentials)
            
            # Открываем таблицу
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Пытаемся найти лист "Settings" или создаем его
            try:
                self.worksheet = spreadsheet.worksheet("Settings")
            except gspread.WorksheetNotFound:
                self.worksheet = spreadsheet.add_worksheet(title="Settings", rows="100", cols="20")
                self._init_settings_sheet()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Google Sheets connection: {e}")
            return False
    
    def _init_settings_sheet(self):
        """Инициализация листа настроек с базовыми значениями"""
        try:
            # Заголовки
            self.worksheet.update('A1:B1', [['Setting', 'Value']])
            
            # Базовые настройки
            settings_data = [
                ['report_time', '21:00'],
                ['reminder_time', '20:00'],
                ['admin_chat_id', ''],
                ['welcome_message', 'Добро пожаловать в SynergyNet!'],
                ['broadcast_enabled', 'true']
            ]
            
            self.worksheet.update('A2:B6', settings_data)
            
        except Exception as e:
            logging.error(f"Failed to initialize settings sheet: {e}")
    
    def get_setting(self, setting_key: str) -> Optional[str]:
        """Получение значения настройки из Google Sheets"""
        try:
            if not self.worksheet:
                return None
            
            # Получаем все данные из листа
            all_values = self.worksheet.get_all_values()
            
            # Ищем настройку
            for row in all_values[1:]:  # Пропускаем заголовок
                if len(row) >= 2 and row[0] == setting_key:
                    return row[1]
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to get setting {setting_key}: {e}")
            return None
    
    def set_setting(self, setting_key: str, value: str) -> bool:
        """Установка значения настройки в Google Sheets"""
        try:
            if not self.worksheet:
                return False
            
            # Получаем все данные из листа
            all_values = self.worksheet.get_all_values()
            
            # Ищем существующую настройку
            for i, row in enumerate(all_values[1:], start=2):  # Пропускаем заголовок
                if len(row) >= 2 and row[0] == setting_key:
                    # Обновляем существующую настройку
                    self.worksheet.update(f'B{i}', value)
                    return True
            
            # Если настройка не найдена, добавляем новую
            next_row = len(all_values) + 1
            self.worksheet.update(f'A{next_row}:B{next_row}', [[setting_key, value]])
            return True
            
        except Exception as e:
            logging.error(f"Failed to set setting {setting_key}: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """Получение всех настроек из Google Sheets"""
        try:
            if not self.worksheet:
                return {}
            
            all_values = self.worksheet.get_all_values()
            settings = {}
            
            for row in all_values[1:]:  # Пропускаем заголовок
                if len(row) >= 2 and row[0] and row[1]:
                    settings[row[0]] = row[1]
            
            return settings
            
        except Exception as e:
            logging.error(f"Failed to get all settings: {e}")
            return {}
    
    def is_connected(self) -> bool:
        """Проверка подключения к Google Sheets"""
        return self.client is not None and self.worksheet is not None

# Создаем глобальный экземпляр менеджера Google Sheets
sheets_manager = GoogleSheetsManager()

