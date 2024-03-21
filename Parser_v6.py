import aiohttp
import asyncio
import json
import re
import sys
import time
from bs4 import BeautifulSoup
#Импортируем все необходимое

class DataManager: #Класс для работы с json-файлами
    def __init__(self, products_file="rsr_products.json", manufacturer_file="rsr_manufacturer.json",
                 prices_file="rsr_prices.json"):
        self.products_file = products_file
        self.manufacturer_file = manufacturer_file
        self.prices_file = prices_file

    def load_data(self, filename): #Загрузка json
        with open(filename, 'r', encoding='UTF-8') as file:
            return json.load(file)

    def save_data(self, data, filename): #Сохранение json
        with open(filename, 'w', encoding='UTF-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def get_products_data(self):
        return self.load_data(self.products_file) 

    def get_manufacturer_id(self, name): #Получение айди производителя
        data = self.load_data(self.manufacturer_file)
        for item in data:
            if item['name'] == name:
                return item['id']
        return None

    def get_product_ids_by_manufacturer(self, manufacturer_id, data_from_products): #Получение айди продуктов производителя
        result = []
        for item in data_from_products:
            if manufacturer_id == item['manufacturer_id']:
                result.append(item['id'])
        return result

    def update_price(self, id_product, price): #Обновление цены
        data_from = self.load_data(self.prices_file)
        for item in data_from:
            if item['id_product'] == id_product:
                item['price'] = price
                break
        self.save_data(data_from, self.prices_file)


class Scraper: #Класс для парсинга
    async def get_price_with_symbol(self, session, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                 '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                tags = soup.find_all('meta')
                match = re.search(r'купить за (\d+\.\d+) руб.', str(tags[4]))
                if match:
                    price = match.group(1)
                    return float(price)
            return None


class PriceUpdater: #Класс для алгоритмов update и update_all
    def __init__(self):
        self.data_manager = DataManager()
        self.scraper = Scraper()

    async def update(self, name): #Обновление для продуктов одного производителя
        data_from_products = self.data_manager.get_products_data()
        manufacturer_id = self.data_manager.get_manufacturer_id(name)
        if manufacturer_id:
            id_products = self.data_manager.get_product_ids_by_manufacturer(manufacturer_id, data_from_products)
            print(id_products)
            print(f"{len(id_products)} products found")
            async with aiohttp.ClientSession() as session:
                tasks = []
                for i in id_products:
                    for j in data_from_products:
                        if i == j['id']:
                            etm = "https://www.etm.ru/cat/nn/" + j['etm_id'].split("-")[0]
                            tasks.append(self.scraper.get_price_with_symbol(session, etm))
                prices = await asyncio.gather(*tasks)
                for i, price in zip(id_products, prices):
                    self.data_manager.update_price(i, price)

    async def update_all(self): #Обновление для всех продуктов
        data_from_products = self.data_manager.get_products_data()
        async with aiohttp.ClientSession() as session:
            tasks = []
            for item in data_from_products: 
                etm = "https://www.etm.ru/cat/nn/" + item['etm_id'].split("-")[0]
                tasks.append(self.scraper.get_price_with_symbol(session, etm))
            prices = await asyncio.gather(*tasks)
            for item, price in zip(data_from_products, prices):
                self.data_manager.update_price(item['id'], price)


def main(args): #Функция для вызова различных методов класса
    price_updater = PriceUpdater() #Инициализируем экземпляр класса
    match len(args):
        case 1:
            print("-update Manufacturer - Update the prices of a certain manufacturer")
            print("-update_all - Update prices of all manufacturers")
            print("-help - Find out the list of commands")
        case _:
            match args[1]:
                case "-help":
                    print("-update Manufacturer - Update the prices of a certain manufacturer")
                    print("-update_all - Update prices of all manufacturers")
                    print("-help - Find out the list of commands")
                case "-update":
                    asyncio.run(price_updater.update(" ".join(args[2:])))
                    print("Program finished.")
                case "-update_all":
                    asyncio.run(price_updater.update_all())
                    print("Program finished.")
                case _:
                    print("Command not found")


if __name__ == "__main__": #Точка входа
    start = time.time()
    main(sys.argv)
    end = time.time()
    print("The time of execution of the program is:", (end - start) * 10 ** 3, "ms")
