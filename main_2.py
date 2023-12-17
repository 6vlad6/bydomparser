import time

from selenium.webdriver.common.by import By
import requests
from bs4 import BeautifulSoup

from funcs import BydomParser


need_split = False

MAIN_URL = 'https://www.bydom.by/'


parser = BydomParser(MAIN_URL)
folder_name = parser.create_folder()
driver = parser.create_driver()

time.sleep(5)

catalog_btn = driver.find_element(By.CLASS_NAME, 'btn-catalog')
catalog_btn.click()


# сбор всех категорий
categories_blocks = driver.find_element(By.CLASS_NAME, 'catalog').find_element(By.TAG_NAME, 'ul').find_elements(By.TAG_NAME, 'li')[1:-3]

categories = []

for cat_block in categories_blocks:
    cat_link = cat_block.find_element(By.TAG_NAME, 'a').get_attribute('href')
    cat_name = cat_block.find_element(By.TAG_NAME, 'img').get_attribute('alt')

    categories.append({'name': cat_name, 'link': cat_link})

# можно редактировать пул категорий, при этом должно начинаться минимум с 1 и заканчивать не позже -3 (чтобы не
# брать первую и три последние)
for category_item in categories[:1]:

    print("Началась обработка категории: ", category_item['name'])

    # заголовки продуктов
    columns = ['category', 'subcategory', 'type', 'title', 'images', 'cost', 'brand', 'description', 'article']
    category_products = []  # все товары категории

    category_r = requests.get(category_item['link'])
    time.sleep(3)
    category_page_data = BeautifulSoup(category_r.text, 'html.parser')

    # сбор подкатегорий каждой категории
    subcategories = []

    try:
        all_subcategories_block = category_page_data.find(class_='subcategories')
        subcategories_block = all_subcategories_block.find_all(class_='subcategory')

        for subcat_block in subcategories_block:
            subcat_link = subcat_block.find('a')['href'][1:]
            subcat_name = subcat_block.find('a').find('span').text

            subcategories.append({'name': subcat_name, 'link': subcat_link})
    except:
        print("Подкатегорий нет: ", category_item['name'])

    if len(subcategories) == 0:
        subcategories.append(category_item)
        need_split = True

    # сбор товаров по каждой подкатегории

    # можно выбирать разрез подкатегорий для обработки
    for subcategory in subcategories[:1]:

        print("Началась обработка подкатегории: ", subcategory['name'])

        sub_url = subcategory['link']
        if need_split:
            sub_url = sub_url.split("https://www.bydom.by/")[1]

        subcategory_r = requests.get(MAIN_URL+sub_url)
        time.sleep(3)

        subcategory_page_data = BeautifulSoup(subcategory_r.text, 'html.parser')

        max_pages = 1
        try:
            max_pages = int(subcategory_page_data.find_all(class_='page-link')[-2].text)
        except:
            print("Нет пагинации: ", subcategory['name'])

        subcategory_all_products = []  # все продукты подкатегории

        # можно выбирать разрез страниц пагинации
        for i in range(1, max_pages+1):

            subcategory_r = requests.get(MAIN_URL + sub_url+f"?page={str(i)}")
            time.sleep(3)

            subcategory_page_data = BeautifulSoup(subcategory_r.text, 'html.parser')

            products_blocks = subcategory_page_data.find_all(class_='product-item')

            for product_block in products_blocks:
                product_link = product_block.find('a')['href']

                subcategory_all_products.append(product_link)

        # можно выбирать разрез продуктов в подкатегории
        for product in subcategory_all_products[:5]:  # обработка каждого продукта в подкатегории

            product_r = requests.get(MAIN_URL+product[1:])
            time.sleep(3)

            product_page_data = BeautifulSoup(product_r.text, 'html.parser')

            data = ['-'] * 9

            data[1] = category_item['name']
            data[2] = subcategory['name']

            product_block = product_page_data.find(class_='product')

            try:
                product_title = product_block.find(class_='product-h1').text
                data[3] = product_title.strip()
            except:
                print("Не получилось взять название: ", product)

            try:
                try:
                    price_block = product_block.find('div', class_='price').find('div')
                    price = price_block.find('meta', attrs={'itemprop': 'price'})['content']
                    data[5] = price
                except:
                    price_block = product_block.find('span', class_='price')
                    price_arr = str(price_block.find('span', class_='old').text).split()
                    print(price_arr)
                    price_arr.pop()
                    price_arr[0] = ''.join(price_arr[0][1:])
                    print(price_arr)

                    price = ''.join(price_arr)
                    print(price)
                    data[5] = price
            except:
                print("Не получилось взять цену: ", product)

            try:
                brand_block = product_page_data.find(class_='brand-links')
                brand = str(str(str(brand_block.find('a', class_='filter').text).split("Все товары")[1]).split("в категории")[0]).strip()
                data[6] = brand
            except:
                print("Не получилось взять бренд: ", product)

            try:
                description_block = product_page_data.find(class_='options-cell')
                description_span = description_block.find_all('span')[1].text
                data[7] = description_span
            except:
                print("Не получилось взять характеристики: ", product)

            try:
                desc = data[7]
                data[7] = desc.strip()
            except:
                print("Не получилось убрать лишние символы в характеристиках: ", product)

            try:
                img_links = []
                images_block = product_page_data.find(class_='swiper-wrapper')
                images = images_block.find_all(class_='swiper-slide')
                for image in images:
                    img_link = image.find('a')['href']
                    img_links.append(MAIN_URL+img_link[1:])

                data[4] = img_links
            except:
                print("Не получилось взять фотографии: ", product)

            try:
                product_id = product_page_data.find(attrs={'id': 'id_model'})['value']
                data[8] = product_id
            except:
                print("Не получилось взять код товара: ", product)

            try:
                category_products.append(data)
            except:
                print("Не получилось добавить товар в общий массив: ", data)

        print("Обработана подкатегория: ", subcategory['name'], ", товаров: ", len(subcategory_all_products))

    try:
        parser.load_to_file(folder_name, category_item['name'], columns, category_products)
        print("Файл успешно создан: ", f"{folder_name}/{category_item['name']}")
    except:
        print("Не получилось загрузить товары в категории: ", category_item['name'])

    print("Обработана категория: ", category_item['name'])
    print("---")

    need_split = False
