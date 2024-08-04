import json
import os

import vk_api

from config import TOKEN


class Sender():
    def __init__(self, api):
        self.api = api

    def __call__(self, text, *args, **kwargs):
        return self.api.messages.send(message=text, random_id=0, **kwargs)


class DataInteractor:

    def __init__(self, filename='data.json'):
        self.filename = filename
        self.refresh_data()

    def refresh_data(self):
        if not os.path.exists(self.filename):
            print("Data file not found. Creating empty file.")
            with open(self.filename, 'w') as f:
                f.write('{}')
        with open(self.filename) as f:
            self.data = json.load(f)

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False)


class ProjectsInteractor:
    def __init__(self, data_interactor: DataInteractor, projects_data: dict[str, dict]):
        self.data_interactor = data_interactor
        self.projects_data = projects_data

    @property
    def free_places(self):
        resp = {}
        for pn in self.projects_data.keys():
            num_parts = self.get_participants(pn, mode='count')
            resp[pn] = self.projects_data[pn]['max_users'] - num_parts
        return resp

    def get_participants(self, project_name: str, mode='count'):

        def get_user_link_by_id(vk_id):
            vk_session = vk_api.VkApi(token=TOKEN)
            vk = vk_session.get_api()
            _user_data = vk.users.get(user_id=vk_id)[0]
            return [f"@id{vk_id}({_user_data['last_name']} {_user_data['first_name']})"]

        data_formers = {
            'ids': lambda x: [x],
            'links': get_user_link_by_id,
            'count': lambda x: 1
        }

        participants = [] if mode != 'count' else 0
        self.data_interactor.refresh_data()
        for user_id, user_data in self.data_interactor.data.items():
            if user_data['project'] == project_name:
                participants += data_formers[mode](user_id)
        return participants

    def find_project_for_participant(self, user_id):
        user_data = self.data_interactor.data.get(user_id)
        if (pn := user_data.get('project', None)) is None:
            priority_dict = {
                pn: int(user_data[pn]) for pn in self.projects_data.keys()
            }
            priority_list = sorted(
                list(priority_dict.keys()),
                key=lambda x: (priority_dict[x], self.free_places[x]),
                reverse=True
            )
            for pn in priority_list:
                if self.free_places[pn] >= 1:
                    self.data_interactor.data[user_id]['project'] = pn
                    self.data_interactor.save()
                    self.data_interactor.refresh_data()
                    break
            else:
                pn = priority_list[0]
            print(self.data_interactor.data[user_id])
        return pn

    def dump_data(self, filename='projects.json'):
        with open(filename, 'w') as f:
            json.dump(self.projects_data, f, ensure_ascii=False)
