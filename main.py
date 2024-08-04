import json

from bots import BasicBot
from utils import DataInteractor

from config import TOKEN, ADMIN_IDS

if __name__ == '__main__':
    di = DataInteractor()
    print(list(di.data.keys()))
    projects_data = json.load(open('projects.json', 'r'))

    bot = BasicBot(
        token=TOKEN,
        data_interactor=di,
        projects_data=projects_data
    )
    for admin_id in ADMIN_IDS:
        bot.add_admin(admin_id, admin_id)
    while True:
        try:
            bot.start()
        except KeyboardInterrupt:
            print('Shutting down...')
            exit(0)
        except Exception as e:
            print(e)

