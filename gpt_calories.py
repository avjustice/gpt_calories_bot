import os

import openai
import re


def meal_calories(request):
    numbers = None
    response_text = None
    for i in range(2):
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
            continue
        numbers = []
        for word in response:
            if word.isdigit():
                numbers.append(int(word))
        if numbers:
            break
    return response_text, (max(numbers) if numbers else False)
