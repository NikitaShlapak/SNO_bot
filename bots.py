import re

import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from utils import Sender, ProjectsInteractor


class BasicBot(object):
    HELLO_WORDS = ('start', 'begin', 'начать', 'привет', 'добрый день', 'здравствуйте')
    GET_DATA = '/data'
    ADD_ADMIN = '/admin_add'
    GET_MY_ID = '/my_id'
    GET_PROJECTS_DATA = '/projects_data'
    SET_PROJECTS_DATA = '/projects_edit_max'
    AM_I_ADMIN = '/am_i_admin'
    HELP = '/help'

    START_MARKING = 'Я готов(а)!'
    MY_MARKS = 'Мои оценки'
    FINISH_MARKING = 'Готово'

    def _match_marking_pattern(self, text):
        return bool(len(re.findall(self.mark_pattern, text)) == len(self.PROJECT_NAMES) and
                    len(re.sub(self.mark_pattern, '', text).strip()) == 0)

    def __init__(self, token, data_interactor=None, projects_data=None):
        self.token = token
        self.admins = []
        self.data_interactor = data_interactor
        self.PROJECT_NAMES = list(projects_data.keys())
        self.project_interactor = ProjectsInteractor(
            data_interactor=data_interactor,
            projects_data=projects_data
        )
        self.mark_pattern = re.compile(r"\b\d{1,2}\b")

    def start(self):

        vk_session = vk_api.VkApi(token=self.token)
        vk = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)

        sender = Sender(vk)

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.from_user:
                input_text = event.text.strip()
                user_id = event.user_id
                user_data = vk.users.get(user_id=user_id)[0]

                print(user_id, input_text, vk.users.get(user_id=user_id))
                if input_text == self.GET_DATA:
                    if str(user_id) not in self.admins:
                        text = "Forbidden"
                    else:
                        text = self.get_data()
                    sender(text, user_id=user_id)
                elif input_text == self.GET_MY_ID:
                    sender(user_id, user_id=user_id)
                elif input_text == self.AM_I_ADMIN:
                    sender(str(user_id) in self.admins, user_id=user_id)
                elif input_text == self.HELP:
                    basic_commands = [
                        self.GET_MY_ID + ' - получить ваш id vk',
                        self.AM_I_ADMIN + ' - проверить, являетесь ли вы админом',
                        self.GET_PROJECTS_DATA + ' - информация о проектах',
                        self.HELP + ' - помощь',
                    ]
                    admin_commands = [
                        self.ADD_ADMIN + ' [id]' + ' - добавить админа (распространяется только на бота до перезапуска)',
                        self.SET_PROJECTS_DATA + " [a] [b] [c] ..." + ' - установить максимальное количесво участников проекта. Обязательно указать число для каждого проекта',
                        self.GET_DATA + ' - получить всю информацию о регисрациях'
                    ]
                    user_commands = basic_commands + admin_commands if str(user_id) in self.admins else basic_commands
                    text = '\n'.join(user_commands)
                    sender(text, user_id=user_id)
                elif input_text.startswith(self.ADD_ADMIN):
                    try:
                        admin_id = input_text.split()[1:]
                        assert len(admin_id) == 1, ''
                    except:
                        text = 'Invalid id'
                    else:
                        result = self.add_admin(str(user_id), admin_id[0])
                        if result:
                            text = 'Admin added'
                        else:
                            text = 'Admin not added'
                    finally:
                        sender(text, user_id=user_id)
                elif input_text.lower() in self.HELLO_WORDS:
                    kb = VkKeyboard(one_time=True)
                    kb.add_button(self.START_MARKING, color=VkKeyboardColor.SECONDARY)
                    kb = kb.get_keyboard()
                    text = f"""Привет, {user_data['first_name']}!
                    Сейчас мы определим, на какой проект тебе стоит пойти.
                    О каждом проекте тебе расскажут наставники, так что сперва послушай их всех. Тебе предстоит выставить каждому проекту оценку от 0 до 10 в зависимости от того, насколько он тебе интересен.
                    Нажми на кнопку, чтобы начать.
                    """
                    sender(text, user_id=user_id, keyboard=kb)
                elif input_text == self.START_MARKING:
                    self.data_interactor.refresh_data()
                    user_data = self.data_interactor.data.get(str(user_id), None)
                    if user_data is None:
                        user_data = {
                            pn: 0 for pn in self.PROJECT_NAMES
                        }
                        user_data['project'] = None
                        self.data_interactor.data[str(user_id)] = user_data
                        self.data_interactor.save()
                    text = "Вот список проектов и твои оценки к ним:\n"
                    text += '\n'.join(
                        f"{i + 1}. {pn} - {user_data.get(pn, 0)}" for i, pn in enumerate(self.PROJECT_NAMES))

                    text += """
                    Если ты хочешь изменить оценки - просто введи их через пробел по порядку. Если нет - жми кнопку и мы определим тебя на проект!"""

                    kb = VkKeyboard(one_time=True)
                    kb.add_button(self.FINISH_MARKING, color=VkKeyboardColor.SECONDARY)
                    kb = kb.get_keyboard()

                    sender(text.strip(), user_id=user_id, keyboard=kb)
                elif input_text == self.FINISH_MARKING:
                    if str(user_id) in self.data_interactor.data.keys():
                        pn = self.project_interactor.find_project_for_participant(user_id=str(user_id))
                        text = f"""
                        Ты записан(а) на проект {pn}.
                        """.strip()

                        sender(text, user_id=user_id)
                elif input_text == self.GET_PROJECTS_DATA:
                    if str(user_id) not in self.admins:
                        text = "\n".join([f"{i + 1}. {pn}" for i, pn in enumerate(self.PROJECT_NAMES)])
                    else:
                        data = {}
                        text = ''
                        for i, pn in enumerate([None] + self.PROJECT_NAMES):
                            data[pn] = self.project_interactor.get_participants(pn, mode='links')
                            text += f"{i}.{pn}:\n" + "; ".join(data[pn]) + '\n'
                            if pn is not None:
                                text += f"{self.project_interactor.get_participants(pn, mode='count')} из {self.project_interactor.projects_data[pn]['max_users']}\n\n"

                    sender(text, user_id=user_id)
                elif input_text.startswith(self.SET_PROJECTS_DATA):
                    new_counts = input_text.split()[1:]
                    try:
                        new_counts = list(map(int, new_counts))
                        assert len(new_counts) == len(self.PROJECT_NAMES)
                    except ValueError:
                        text = 'Invalid counts'
                    except AssertionError:
                        text = 'Invalid number of counts'
                    else:
                        for pn in self.PROJECT_NAMES:
                            self.project_interactor.projects_data[pn]['max_users'] = new_counts.pop(0)
                        self.project_interactor.dump_data()
                        text = 'Updated'
                    finally:
                        sender(text, user_id=user_id)

                    print(new_counts)
                elif self._match_marking_pattern(input_text):
                    marks = input_text.strip().split()

                    if all([0 <= int(mark) < 11 for mark in marks]):
                        user_data = {
                            pn: mark for pn, mark in zip(self.PROJECT_NAMES, marks)
                        }
                        user_data['project'] = None
                        self.data_interactor.data[str(user_id)] = user_data
                        self.data_interactor.save()
                        text = "Вот список проектов и твои оценки к ним:\n"
                        text += '\n'.join(
                            f"{i + 1}. {pn} - {marks[i]}" for i, pn in enumerate(self.PROJECT_NAMES))

                        text += """
                                            Если ты хочешь изменить оценки - просто введи их через пробел по порядку. Если нет - жми кнопку и мы определим тебя на проект!"""

                        kb = VkKeyboard(one_time=True)
                        kb.add_button(self.FINISH_MARKING, color=VkKeyboardColor.SECONDARY)
                        kb = kb.get_keyboard()

                        sender(text.strip(), user_id=user_id, keyboard=kb)

    def add_admin(self, user_id, add_id):
        if (len(self.admins) > 0 and user_id in self.admins and add_id not in self.admins) or len(self.admins) == 0:
            self.admins.append(add_id)
            return True
        else:
            return False

    def get_data(self):
        data = self.data_interactor.data
        resp = [f"{user}:\n{user_data}" for user, user_data in data.items()]
        return '\n'.join(resp)
