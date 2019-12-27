from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration

from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest

from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage

import time
import logging
import sched
import threading
import json
import os
import random


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


json_path = os.getcwd() + '\\json\\'
eng_words= json.load(open(json_path + 'english_words.json', "r", encoding='utf-8'))
ten_new_words = random.sample(eng_words, 10)
answer_keyboard= json.load(open(json_path + 'answers.json', "r", encoding='utf-8'))
Tests = {}


app = Flask(__name__)
viber = Api(BotConfiguration(
    name='EngShibe',
    avatar='https://previews.123rf.com/images/greenoptix/greenoptix1904/greenoptix190400022/123442578-illustration-shiba-inu-for-all-dog-owners-what-you-love-about-his-dog-puppy-dog-%C3%A2%E2%82%AC%E2%80%B9%C3%A2%E2%82%AC%E2%80%B9eyes-wagging-t.jpg',
    auth_token='4ac7d72339e7d0b5-f614c0688c0c27e9-a6bb05e7fe56834b',
))


class Test:
    def __init__(self, user_id, current_word = '', questions={}, correct_amount=0, wrong_amount=0, max_questions = 10):
        self.user_id = user_id
        self.current_word = current_word
        self.questions = questions
        self.correct_amount = correct_amount
        self.wrong_amount = wrong_amount
        self.max_questions = max_questions

    def load_question(self, eng_words):
        random_word = random.choice(eng_words)
        #three_random_words = []
        #for i in range(3):
        three_random_words = random.sample(eng_words,3)

        three_random_translates = []
        for word in three_random_words:
            three_random_translates.append(word['translation'])

        if random_word['word'] not in self.questions.keys():
            new_question = Question(random_word['word'], random_word['translation'], three_random_translates, random_word['examples'])
            self.questions[new_question.correct_answer] = new_question
            return new_question.correct_answer
        else:
            random_word = random.choice(eng_words)
            new_question = Question(random_word['word'], random_word['translation'], three_random_translates, random_word['examples'])
            self.questions[new_question.correct_answer] = new_question
            return new_question.correct_answer


class Question:
    def __init__(self, word, correct_answer, translations=[], examples = []):
        self.word = word
        self.correct_answer = correct_answer
        self.translations = translations
        self.examples = examples

    def check_answer(self, answer):
            if answer == self.correct_answer:
                return True
            else:
                return False


def ask_a_question(test, id):
    current_test = test
    new_question_key = current_test.load_question(eng_words)
    answers = current_test.questions[new_question_key].translations
    answers.append(current_test.questions[new_question_key].correct_answer)
    current_test.current_word = current_test.questions[new_question_key].correct_answer
    random.shuffle(answers)
    for i in range(4):
        answer_keyboard['Buttons'][i]['Text'] = answers[i]
        answer_keyboard['Buttons'][i]['ActionBody'] = answers[i]

    keyboard = answer_keyboard
    viber.send_messages(id, [
        TextMessage(
            text="Как переводится с английского слово '" + current_test.questions[new_question_key].word + "'?"),
        KeyboardMessage(keyboard=keyboard)
    ])


@app.route('/', methods=['POST'])
def incoming():
    logger.debug("received request. post data: {0}".format(request.get_data()))

    viber_request = viber.parse_request(request.get_data().decode('utf8'))
    try:
        if isinstance(viber_request, ViberMessageRequest):
            message = viber_request.message
            if viber_request.sender.id not in Tests.keys():
                Tests[viber_request.sender.id] = Test(viber_request.sender.id)

            current_test = Tests[viber_request.sender.id]
            if message.text.startswith('start'):
                ask_a_question(Tests[viber_request.sender.id], viber_request.sender.id)

            elif message.text == 'Привести пример':
                example = random.choice(current_test.questions[current_test.current_word].examples)
                viber.send_messages(viber_request.sender.id, [
                    TextMessage(
                        text=example),
                        KeyboardMessage(keyboard=answer_keyboard)
                ])

            else:
                if message.text in Tests[viber_request.sender.id].questions.keys():
                    if current_test.questions[message.text].check_answer(message.text):
                        current_test.correct_amount += 1
                        viber.send_messages(viber_request.sender.id, [
                            TextMessage(
                                text="Верно!")
                        ])
                else:
                    Tests[viber_request.sender.id].wrong_amount += 1
                    viber.send_messages(viber_request.sender.id, [
                        TextMessage(
                            text='Ответ неправильный!')
                    ])

                if (current_test.correct_amount + current_test.wrong_amount) < current_test.max_questions:
                    ask_a_question(Tests[viber_request.sender.id], viber_request.sender.id)
                else:
                    viber.send_messages(viber_request.sender.id, [
                        TextMessage(
                            text=f'Тест завершен! Ваши результаты: правильных ответов - {current_test.correct_amount}, неправильных - {current_test.wrong_amount}')
                    ])

        elif isinstance(viber_request, ViberConversationStartedRequest):
            viber.send_messages(viber_request.get_user().get_id(), [
                TextMessage(text="Этот бот предназначен для заучивания английских слов. Для начала работы введите start или нажмите на кнопку снизу.")
            ])
        elif isinstance(viber_request, ViberFailedRequest):
            logger.warning("client failed receiving message. failure: {0}".format(viber_request))

    except Exception as ex:
        print(ex)

    return Response(status=200)


def set_webhook(viber):
    viber.set_webhook('https://03c35fa0.ngrok.io')


if __name__ == "__main__":
     #scheduler = sched.scheduler(time.time, time.sleep)
     #scheduler.enter(5, 1, set_webhook, (viber,))
     #t = threading.Thread(target=scheduler.run)
     #t.start()
     app.run(host='127.0.0.1', port=80, debug=True)