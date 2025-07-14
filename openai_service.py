import openai
import os
from typing import Dict, Optional
import logging

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logging.error("OpenAI API key not found in environment variables")
    
    def generate_business_card(self, profile_data: Dict) -> Optional[str]:
        """Генерация визитки на основе данных профиля"""
        try:
            # Формируем промпт для генерации визитки
            prompt = self._create_business_card_prompt(profile_data)
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты - эксперт по созданию профессиональных визиток и резюме. 
                        Создавай привлекательные, структурированные визитки в формате Markdown.
                        Используй эмодзи для улучшения визуального восприятия.
                        Визитка должна быть краткой, но информативной, подчеркивать уникальность человека."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Failed to generate business card: {e}")
            return None
    
    def _create_business_card_prompt(self, profile_data: Dict) -> str:
        """Создание промпта для генерации визитки"""
        prompt = f"""
Создай профессиональную визитку в формате Markdown на основе следующих данных:

**Имя:** {profile_data.get('first_name', '')} {profile_data.get('last_name', '')}
**О себе:** {profile_data.get('bio', '')}
**Продукт/Услуги:** {profile_data.get('product_info', '')}
**Лучшие кейсы:** {profile_data.get('case_studies', '')}
**Мотивация для нетворкинга:** {profile_data.get('networking_motive', '')}
**Жизненные ценности:** {profile_data.get('life_values', '')}
**Образ жизни:** {profile_data.get('lifestyle', '')}
**Социальные сети:** {profile_data.get('social_link', '')}

Требования к визитке:
1. Используй структурированный формат с заголовками
2. Добавь подходящие эмодзи для каждого раздела
3. Сделай текст привлекательным и профессиональным
4. Подчеркни уникальные качества и достижения
5. Визитка должна быть объемом 200-400 слов
6. Используй Markdown форматирование (заголовки, списки, выделение)

Создай визитку, которая поможет этому человеку выделиться в профессиональном сообществе и найти единомышленников.
"""
        return prompt
    
    def regenerate_business_card(self, profile_data: Dict, previous_card: str) -> Optional[str]:
        """Перегенерация визитки с учетом предыдущей версии"""
        try:
            prompt = f"""
Создай новую версию профессиональной визитки в формате Markdown на основе следующих данных:

**Данные профиля:**
**Имя:** {profile_data.get('first_name', '')} {profile_data.get('last_name', '')}
**О себе:** {profile_data.get('bio', '')}
**Продукт/Услуги:** {profile_data.get('product_info', '')}
**Лучшие кейсы:** {profile_data.get('case_studies', '')}
**Мотивация для нетворкинга:** {profile_data.get('networking_motive', '')}
**Жизненные ценности:** {profile_data.get('life_values', '')}
**Образ жизни:** {profile_data.get('lifestyle', '')}
**Социальные сети:** {profile_data.get('social_link', '')}

**Предыдущая версия визитки:**
{previous_card}

Создай НОВУЮ версию визитки, которая:
1. Отличается от предыдущей по структуре и подаче информации
2. Использует другие эмодзи и акценты
3. Подчеркивает другие аспекты личности и профессионализма
4. Сохраняет профессиональный тон, но с новым подходом
5. Остается в пределах 200-400 слов
"""
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты - эксперт по созданию профессиональных визиток и резюме. 
                        Создавай привлекательные, структурированные визитки в формате Markdown.
                        Каждая новая версия должна отличаться от предыдущей по подаче и акцентам."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Failed to regenerate business card: {e}")
            return None

# Создаем глобальный экземпляр сервиса OpenAI
openai_service = OpenAIService()

