import json
import requests
import logging
import re
import pickle
import xml.etree.ElementTree as ET
from pathlib import Path
from requests import HTTPError as RequestsHTTPError

class LoggedOutException(Exception):
    pass

def save_cookies(requests_cookiejar, filename):
    with open(filename, 'wb') as f:
        pickle.dump(requests_cookiejar, f)

def load_cookies(filename):
    import pickle
    with open(filename, 'rb') as f:
        return pickle.load(f)

class WebCrawler:

    def __init__(self,user:str, password:str, proxy:str=None) -> None:
        
        self.user = user
        self.password = password
        self.logged_in = False
        self.proxy = proxy

        self.offline_file_no = 0
        # GET https://weare.audi/001_vtpmfc4we/ademanlwb/i/s/l|12,1,PRICE_MALEAS,U/controller.do
        # https://weare.audi/001_vtpmfc4we/ademanlwb/i/s|500,1,PRICE_MALEAS,U/controller.do?act=list&v=4    500 means max 500 results in response
        # https://weare.audi/001_vtpmfc4we/ademanlwb/i/s|10,AABS,AAAY,AABW,AAEL,AACZ,AACN,AAES,AABT,AABK,AACM/l|12,1,PRICE_MALEAS,U/controller.do?act=list&v=4   Filtered Example for specific vehicle models

    def save_cookies_lwp(self, cookiejar, filename):
        import http.cookiejar
        lwp_cookiejar = http.cookiejar.LWPCookieJar()
        for c in cookiejar:
            args = dict(vars(c).items())
            args['rest'] = args['_rest']
            del args['_rest']
            c = http.cookiejar.Cookie(**args)
            lwp_cookiejar.set_cookie(c)
        lwp_cookiejar.save(filename, ignore_discard=True)

    def reset_session(self) -> None:
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        if self.proxy:
            self.session.proxies.update({
                "http": "http://" + self.proxy,
                "https": "http://" + self.proxy,
                "ftp": "ftp://" + self.proxy,
            })

    def mfc_login(self) -> None:

        cookies_path = Path('./login_cookies.txt')
        if cookies_path.exists():
            try:
                self.session.cookies.update(load_cookies(cookies_path))
                #url_mfc_home = 'https://weare.audi/501_mfc/web/guest/home' # this site shows login portal or MFC Homepage if logged in
                url_mfc_home = 'https://weare.audi/501_mfc/web/guest/jump?target=poolleas'
                response:requests.Response = self.session.get(url_mfc_home)#, proxies=self.proxy_dict)
                response.raise_for_status()
                if (not 'Meine Fahrzeuge' in response.text):
                    raise RequestsHTTPError()
                self.logged_in = True
            except RequestsHTTPError as http_error:
                cookies_path.unlink() # pathlib function to delete file
                self.reset_session()
                self.mfc_login()
            #except Exception as e:
                #cookies_path.unlink() # pathlib function to delete file
                #self.mfc_login()
            
        else:
            try:
                urlLogin = "https://weare.audi/pkmslogin.form"
                postData = {"login-form-type": "pwd", "username": self.user, "password": self.password}
                response = self.session.post(urlLogin, data=postData)
                response.raise_for_status()
                if "Authentication failed" in response.text or 'Anmeldeversuche' in response.text:
                    raise requests.HTTPError('Authentication failed')
                self.logged_in = True
                save_cookies(self.session.cookies, cookies_path)
            except RequestsHTTPError as http_error:
                self.logged_in = False
                raise http_error
            #except Exception as e:
                #self.logged_in = False
                #raise e
        
    def GET_mfc_pooldata(self, vehicle_ids:list=[]) -> dict:

        # Send the http request depending on what filter settings are desired
        # TODO: Use custom User Agend to not look like a Crawler
        # After some time the site doesnt yield cars when requested. It seems to help to go back, select and deselect cars and try again. I have no idea why.
        # Thats why we first call the overview page and after that our actual request
        #url_vehiclePool_overview = "https://weare.audi/001_vtpmfc4we/ademanlwb/i/s|10,AACV/controller.do#filter/models"
        #url_vehicle_pool_JSON = "https://weare.audi/001_vtpmfc4we/ademanlwb/i/s|10," + vehicle_ids.join(",") + "/l|1000,1,PRICE_MALEAS,U/controller.do?act=list&v=4"
        url_vehicle_pool_JSON = "https://weare.audi/001_vtpmfc4we/ademanlwb/i/s/l|500,1,PRICE_MALEAS,U/controller.do?act=list&v=4"


        try:
            https_response = self.session.get(url_vehicle_pool_JSON)#, proxies=self.proxy_dict)
            logging.debug(f"Request: {url_vehicle_pool_JSON}, Response: {https_response.status_code}")
            https_response.raise_for_status()

            cookies_path = Path('./login_cookies.txt')
            save_cookies(self.session.cookies, cookies_path)
        except requests.HTTPError as http_error:
            # After some time we get locked out with a 404 error usually. Only a new session helps.
            logging.debug(f"requests.HTTPError: Code: {https_response.status_code}, Text: {https_response.text}")
            if https_response.status_code == 404:
                self.logged_in = False
            raise http_error
        except requests.ConnectionError as conn_error:
            # After some time we get a ConnectionResetError. Seems like the server wants a new session then
            # TODO: here: if connection times out at self.session.get(...) https_response will not be written and here referenced before assignment
            logging.debug(f"requests.ConnectionError: Code: {https_response.status_code}, Text: {https_response.text}")
            self.logged_in = False
            raise conn_error
        except ConnectionResetError as conn_error:
            logging.debug(f"requests.ConnectionResetError: Code: {https_response.status_code}, Text: {https_response.text}")
            self.logged_in = False
            raise conn_error
            
        xml_mfc_pooldata = json.loads(https_response.text) # If we got redirect to login page which is a html document, this will raise a JSONDecodeException
        xml_mfc_pooldata = bytes(xml_mfc_pooldata["html"], "utf-8").decode('utf-8','ignore')#.encode("utf-8")
           
        # Modify html code of received json to be valid html code  
        xml_mfc_pooldata = xml_mfc_pooldata.replace("&", "&#38;")
        xml_mfc_pooldata = re.sub(r'(<(img|input) [^>]+)>', r'\1/>', xml_mfc_pooldata)
        xml_mfc_pooldata = xml_mfc_pooldata.replace("//>", "/>")
        cars = self.parse_xml_mfc_pooldata(xml_mfc_pooldata)

        return cars
    
    def parse_xml_mfc_pooldata(self, xml_mfc_pooldata):
        # Parse the html code to get the vehicle data
        cars = {}
        tree = ET.ElementTree(ET.fromstring(xml_mfc_pooldata))
        root:ET.ElementTree = tree.getroot()
        article: ET.Element
        for article in root.iter('article'):
            div: ET.Element
            for div in article.iter('div'):
                html_class:str = div.get('class')
                if html_class and html_class == 'productTracking':
                    car = json.loads(div.get('data-product').replace('&quot;', '"'))
                    cars[div.get('id')] = car
        return cars

    # def get_extended_productinfo(self, car_id):
    #     try:
    #         https_response:requests.Response = self.session.get(f'https://weare.audi/001_vtpmfc4we/ademanlwb/i/s/l|{car_id}/controller.do?act=offer&v=11')
    #         https_response.raise_for_status()
    #         xml_vehicle_data = json.loads(https_response.text) # If we got redirect to login page which is a html document, this will raise a JSONDecodeException
    #         xml_vehicle_data = bytes(xml_vehicle_data["html"], "utf-8").decode('utf-8','ignore')#.encode("utf-8")
    #         # Modify html code of received json to be valid html code  
    #         xml_mfc_pooldata = xml_mfc_pooldata.replace("&", "&#38;")
    #         xml_mfc_pooldata = re.sub(r'(<(img|input) [^>]+)>', r'\1/>', xml_mfc_pooldata)
    #         xml_mfc_pooldata = xml_mfc_pooldata.replace("//>", "/>")

    #     except requests.HTTPError as ex:
    #         logging.debug(f"requests.HTTPError: Code: {https_response.status_code}, Text: {https_response.text}")

    #     return https_response.text

