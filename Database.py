import datetime
import re
import json
import WebCrawler
#import GMail
from os.path import exists as file_exists
from time import sleep


import logging
logging.basicConfig(filename='example.log', level=logging.DEBUG, format='%(asctime)s %(message)s')

class Database:

    def __init__(self, webcrawler:WebCrawler) -> None:
        self.webcrawler = webcrawler
        self.error_interval_factor = 1

        self.cars = {}
        self.users = {}
        self.last_update = None
        self.last_change = None
        self.search = list()
        self.audio = False

        if file_exists('./db.json'):
            with open('db.json', 'r') as file:
                data = json.load(file)
                self.cars = data['cars']
                self.last_update = datetime.datetime.fromisoformat(data['last_update'])
                self.last_change = datetime.datetime.fromisoformat(data['last_change'])
                self.users = data['users']

        if not 'local' in self.users:
            self.users['local'] = {
                'search': '',
                'sent': {}
            }

        self.run = False
        self.exception_status = None

    def update_database(self, cars_webresponse: dict, time_now:int=None):
        """Updates the internal databse with the values from the web response"""

        if time_now == None:
            time_now:int=datetime.datetime.now().timestamp()

        updated = []

        # Loop the keys retrieved from the web
        for car_webresponse in cars_webresponse.values():
            car_key = car_webresponse['attributes']['CarID']
            if car_key not in self.cars:
                # key in webresponse but not database -> added
                self.cars[car_key] = {"web_data" : {}, "meta_data" : {}}
                self.cars[car_key]["web_data"] = car_webresponse
                self.cars[car_key]["meta_data"] = {
                    "available" : True,
                    "time_added" : [time_now],
                    "time_changed" : [],
                    "time_removed" : [],
                }
                updated.append(car_key)
            else:
                # key in webresponse and database -> maybe changed
                if self.cars[car_key]["web_data"] != car_webresponse:
                    # Car was changed
                    self.cars[car_key]["web_data"] = car_webresponse
                    self.cars[car_key]["meta_data"]["time_changed"].append(time_now)
                    updated.append(car_key)
                if self.cars[car_key]["meta_data"]["available"] == False:
                    # Car exists already in database but was unavailable prior
                    self.cars[car_key]["meta_data"]["available"] = True
                    self.cars[car_key]["meta_data"]["time_added"].append(time_now)
                else:
                    # Car did not change
                    pass

        # keys in database but not in web -> removed
        car_ids_webresonse = list(map(lambda car_webresponse: car_webresponse['attributes']['CarID'], cars_webresponse.values()))
        keys_not_in_pool = self.cars.keys() - car_ids_webresonse
        for car_key in keys_not_in_pool:
            car_database_removed = self.cars[car_key]
            if car_database_removed["meta_data"]["available"] == True:
                car_database_removed["meta_data"]["available"] = False
                car_database_removed["meta_data"]["time_removed"].append(time_now)
                updated.append(car_key)

        time_now = datetime.datetime.now()
        self.last_update = time_now
        if len(updated) > 0:
            self.last_change = time_now
        
        # write to file
        with open('db.json', 'w') as file:
            db_data = {
                "cars": self.cars,
                "last_update": self.last_update,
                "last_change": self.last_change,
                "users": self.users
            }
            json.dump(db_data, file, default=json_serial, indent=4)

    def generate_mail_html(self, car_keys):
        
        lines_out = 'I just found following cars for you:<br/>'

        for car in [self.cars[car_key] for car_key in car_keys]:
            lines_out += f'{car["web_data"]["productInfo"]["productName"]}<br/>'
            lines_out += f'<a href="{car["web_data"]["productInfo"]["productURL"]}">(WeAreAudi-Link)</a><br/>'
            lines_out += f'<a href="{car["web_data"]["productInfo"]["productURL"].replace("https://vtp.audi.com/", "https://portal.epp.audi.vwg/001_vtpmfc/")}">(AudiMyNet-Link)</a><br/>'
            lines_out += f'<img src="https:{car["web_data"]["productInfo"]["productThumbnail"]}"/><br/><br/>'
            # Image Links are too long to be packed into a <a> tag
            #lines_out += f'image link: <a href="{car["web_data"]["productInfo"]["productThumbnail"]}">Image-Link</a><br/>'

        return lines_out


    def update_user_data(self):

        car = self.cars[list(self.cars)[0]]

        for user in self.users.values():
            car_keys_to_notify = []
            car_keys_to_check = self.cars.keys() - user['sent'].keys()
            for car_key in car_keys_to_check:
                car = self.cars[car_key]
                car_name = car['web_data']['productInfo']['productName']
                if re.search(user['search'],car_name):
                    car_keys_to_notify.append(car_key)

            if len(car_keys_to_notify) > 0:
                html_mail_content = self.generate_mail_html(car_keys_to_notify)
                for car_key in car_keys_to_notify:
                    user['sent'][car_key] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                import os
                if self.audio and os.name == 'nt':
                    import winsound
                    frequency = 2500  # Set Frequency To 2500 Hertz
                    duration = 500  # Set Duration To 1000 ms == 1 second
                    winsound.Beep(frequency, duration)
                        
                # TODO: proper error handling
                #import GMail # Here to not show up as error when actually not using GMail package
                #GMail.SendMessage('lyxo.dev@gmail.com', user['mail'], 'New Cars in MFC Pool', html_mail_content, "")
                #pass


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))