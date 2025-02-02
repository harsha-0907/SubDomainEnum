from dotenv import load_dotenv
from typing import List
import time
import socket
import logging
import requests
import urllib.parse
import os
import re
from bs4 import BeautifulSoup
import json

load_dotenv()
class GoogleQuery:
    _baseUrl = "https://www.googleapis.com/customsearch/v1"
    def __init__(self, domain):
        self.cx, self.api_key, self.user_agent = os.getenv("cx"), os.getenv("api_key") ,os.getenv("user_agent")
        self.headers = {"User-Agent": self.user_agent, "Connection": "keep-alive"}
        self.params = {"key":self.api_key, "cx": self.cx}
        self._domain = domain

    def queryGoogle(self, query):
        try:
            self.params['q'] = query
            self.params["highRange"] = "100"
            self.params["lowRange"] = "0"
            _resp = requests.get(GoogleQuery._baseUrl, headers=self.headers,
                params=self.params, allow_redirects=True, timeout=3)
            time.sleep(1)
            resp = _resp.json()
            if _resp.status_code == 400:
                # logging.error(f"""Error occured while searching for subdomains: {' '.join(error['reason'] for error in resp["error"]["errors"])}""")
                logging.critical("API Token(s) is invalid")
                return dict()
            else:
                logging.info("Data Obtained")
                return resp
                
        except Exception as _e:
            logging.critical(f"Error in GoogleQuery - {_e}")
            return dict()

    def searchHandler(self, exceptions: List = []):
        if self._domain:
            baseRequest = f"site:*.{self._domain}"
            if exceptions:
                _addOn = f" -".join(exception for exception in exceptions)
                baseRequest = baseRequest + " -" + _addOn
            return self.queryGoogle(baseRequest)
        else:
            return dict()
    
    def parseGoogleResult(self, json_data):
        # The json_data will either be empty or a dictionary with valid search results
        _newSubdomains = list()
        if json_data:
            if "items" in json_data:
                urls = set(url["displayLink"] for url in json_data["items"])
                for url in urls:
                    if self._domain in url:
                        _pos = url.find(self._domain)
                        if _pos > 0:
                            _newSubdomains.append(url[:_pos-1])
        return _newSubdomains

    def fetchSubDomains(self):
        subdomains = []; _newSubdomains = []
        if self._domain:
            while True:
                searchAgain=False
                _newSubdomains = self.parseGoogleResult(self.searchHandler(subdomains))
                for _subdomain in _newSubdomains:
                    if _subdomain not in subdomains:
                        subdomains.append(_subdomain)
                        searchAgain = True
                # print(subdomains)
                if not searchAgain:
                    # If we don't have anymore new subdomains -> break
                    break
        return subdomains

class Crtsh:
    def __init__(self, domain: str = None):
        self._baseUrl = "https://crt.sh/"
        self._headers = {"User-Agent": os.getenv("user_agent")}
        self._domain = domain
    
    def getRawDomainData(self,  retries: int = 0):
        # Max 3 retries allowed
        try:
            self._params = {"q": self._domain}
            _resp = requests.get(self._baseUrl, headers=self._headers, params=self._params, allow_redirects=True)
            if _resp.status_code >= 400:
                if retries < 3:
                    retries += 1
                    return self.getRawDomainData(retires)
                else:
                    return None
            else:
                return _resp.text
        
        except Exception as e:
            # Return None to indicate empty data from the website
            return None

    def parseData(self, html_data):
        _subdomains = set()
        try:
            logging.info("Parsing the Results from Crt.sh")
            soup0 = BeautifulSoup(html_data, "html5lib")
            _tables = soup0.find_all("table")
            soup1 = BeautifulSoup(str(_tables[-1]) ,'html5lib')
            _tableRows = soup1.find_all("tr");  number_of_table_rows = len(_tableRows)
            pattern = r"<td.*</td>"
            for _table_row in _tableRows[1:]:
                _table_row_data = re.findall(pattern, str(_table_row))
                _subdomain = _table_row_data[4][4:-5]
                
                if self._domain in _subdomain and '*' not in _subdomain and _subdomain not in _subdomains:
                    _subdomains.add(_subdomain)
        except Exception as _e:
            print(f"Error in Crt.sh:  {_e}")
        
        finally:
            print(len(_subdomains))
            return list(_subdomains)

    def fetchSubDomains(self):
        if self._domain:
            logging.info("Obtaining Assets from crt.sh")
            raw_html = self.getRawDomainData()
            if raw_html:
                # Parse the document & obtain the urls
                return self.parseData(raw_html)
        return []

class SubDomainEnumerator():
    def __init__(self, domain: str = None):
        self._domain = domain
        self.googleSearchEngine = GoogleQuery(self._domain)
        self.crtsh = Crtsh(self._domain)

    def fetchSubDomains(self):
        _subdomains_crtsh = self.crtsh.fetchSubDomains()
        _subdomains_google_query = self.googleSearchEngine.fetchSubDomains()
        if _subdomains_google_query:
            _subdomains_google_query = [__subdomain + '.' + self._domain for __subdomain in _subdomains_google_query]
        
        self._subdomains = _subdomains_crtsh
        for __subdomain in _subdomains_google_query:
            if __subdomain not in self._subdomains:
                self._subdomains.append(__subdomain)
        
        print(f"Scanning the urls for active response - {len(self._subdomains)}")
        self.filterActiveDomains()
        self.saveData()
        return self._activeSubdomains
    def filterActiveDomains(self):
        # Here we will filter the domains to see if the domain is active or not
        # We will return raw subdomains in case domains use any  technique to block the scans from occuring
        self._activeSubdomains = []
        for _subdomain in self._subdomains:
            secure = False
            _subdomain = self.isActive(_subdomain)
            if _subdomain:
                self._activeSubdomains.append(_subdomain)
        pass
        return self._activeSubdomains
    def isActive(self, _subdomain):
        # Check if the subdomain is active
        try:
            print(f"Testing Asset {_subdomain}: ", end='')
            resp = requests.get(url=f"https://{_subdomain}", headers={"User-Agent": os.getenv("user_agent")}, timeout=5)
            if resp is not None:
                # The subdomain(https) is active
                # Any error code means that the server is present but may or maynot accept the request
                print(f"Active ({resp.status_code})")
                return "https://"+_subdomain
            else:
                resp = requests.get(url=f"http://{_subdomain}", headers={"User-Agent": os.getenv("user_agent")}, timeout=3)
                if resp is not None:
                    # The insecure version (http) is Active
                    print(f"Active ({resp.status_code})")
                    return "http://"+_subdomain
                else:
                    # The subdomain is in-active
                    print(f"In-Active ({resp})")
                    return None
        except socket.gaierror as _e:
            # Error while resolving domains name or host name
            print("In-Active (Connection Timeout)")
            return None
        except Exception as _e:
            print(f"In-Active ({_e})")
            return None
    def saveData(self):
        with open(f"{self._domain}.txt", 'w') as file:
            file.write("\n".join(_subdomain for _subdomain in self._activeSubdomains))
        logging.info(f"Subdomains can be found in {os.getcwd()}/{self._domain}.{os.getenv('file_extension')}")

obj = SubDomainEnumerator(input("Domain (example.com): "))
subdomains = obj.fetchSubDomains()
