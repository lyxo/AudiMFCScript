import threading
from time import sleep

from requests import HTTPError as RequestsHTTPError
from requests import ConnectionError as RequestsConnectionError

from Database import Database
from WebCrawler import WebCrawler


class Watchdog:
    
    def __init__(self, webcrawler:WebCrawler, database:Database, update_interval:int=60) -> None:
        self.webcrawler = webcrawler
        self.database = database
        self.run = False
        self.exception_status = None
        self.error_interval_factor = 1
        self.update_interval = update_interval

    def start(self):
        self.run = True
        update_thread = threading.Thread(target=self.update, args=(), daemon=True, name='MFC_Watchdog')
        update_thread.start()

    def update(self):
        while self.run:
            try:
                # We reset the session completely in every cycle because otherwise we won't receive all updates, sometimes even 0 results
                self.webcrawler.reset_session()
                # We have to login again after resetting the session. If we have cookies stored it will check if those still work and skip the actual login step
                self.webcrawler.mfc_login()
                cars = self.webcrawler.GET_mfc_pooldata()
                self.database.update_database(cars)
                self.database.update_user_data()
                self.exception_status = None
                self.error_interval_factor = 1
                sleep(self.update_interval)
            except (RequestsHTTPError, RequestsConnectionError) as ex:
                self.exception_status = ex
                sleep(self.update_interval * self.error_interval_factor)
                self.error_interval_factor += 1
                continue        


    def stop(self):
        self.run = False
        

