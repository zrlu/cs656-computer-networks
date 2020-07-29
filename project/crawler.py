from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urlparse
from collections import defaultdict
import random
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Lock

class Crawler:

    def __init__(self, init_list, num_drivers=10):
        self.init_list = init_list
        self.visited = []
        self.num_drivers = num_drivers
        self.drivers = [None for _ in range(self.num_drivers)]
        self.netloc_count = defaultdict(int)
        self.queue = Queue()
        for url in self.init_list:
            self.queue.put(url)
    

    def enque(self, urls):
        for url in self.urls:
            self.queue.put(url)


    def queue_empty(self):
        return self.queue.empty()
    

    def walk(self, driver_id):
        if self.drivers[driver_id] is None:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            self.drivers[driver_id] = webdriver.Chrome(executable_path='./chromedriver.exe', options=options)
        while True:
            try:
                url = self.queue.get(block=True, timeout=15)
                print('qsize={}, driver {}: {}'.format(self.queue.qsize(), driver_id, url))
                self.drivers[driver_id].implicitly_wait(30)
                self.drivers[driver_id].get(url)
                for link in self.links(self.drivers[driver_id]):
                    if self.netloc_count[urlparse(link).netloc] < 1000:
                        self.queue.put(link)
                        self.netloc_count[urlparse(link).netloc] += 1
            except KeyboardInterrupt:
                break
            except Exception:
                continue

    
    def links(self, driver):
        elems = driver.find_elements_by_tag_name('a')
        for elem in elems:
            href = elem.get_attribute('href')
            if href is not None and href.startswith('https'):
                yield href


    def start(self):
        futures = []
        with ThreadPoolExecutor(self.num_drivers) as executor:
            for driver_id in range(self.num_drivers):
                future = executor.submit(self.walk, driver_id)
                futures.append(future)
        for future in futures:
            _ = future.result()


    def close(self):
        for driver in self.drivers:
            driver.close()


def load_list(fn):
    lst = []
    with open(fn, 'r') as file:
        lst = list(file)
    return [line.rstrip('\n') for line in lst]


init_list = load_list('list.txt')
c = Crawler(init_list, num_drivers=10)
c.start()
