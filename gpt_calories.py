import os

import openai
import re


def meal_calories(request):
    openai.api_key = os.getenv('API_KEY')
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user",
                   "content":
                       f"Представь, что ты калькулятор калорий. Отвечай одним числом - калорий в приеме пищи."
                       f"{request}. Посчитай калории в приеме пищи."}])

    response_text = completion.choices[0].message.content
    response = re.split("[ \-]+", response_text)
    if len(response) > 15:
        return False
    numbers = []
    for word in response:
        if word.isdigit():
            numbers.append(int(word))

    return response_text, (max(numbers) if numbers else False)
