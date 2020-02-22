import requests
import pandas as pd
import re
import dateutil
from bs4 import BeautifulSoup as soup


class NewsItem:
    """
    Класс, инициализируюемый HTML содержимым новости. На lenta.ru есть несколько различных типов новостей.
    Для удобства парсинга у объектов класса присутствует атрибут type, определяемый методом define_item_type.
    В соответсвии с типом новости, используется один из методов парсинга (parse_main_news, parse_longread_article,
    и т. д.). Данные методы инициализируют основные атрибуты класса, такие как заголовок новости (title), ссылку на
    новость (link), дату публикации (date) и категорию (category).
    """
    def __init__(self, item):
        self.item = item
        self.type = None
        self.link = None
        self.title = None
        self.date = None
        self.category = None

    def define_item_type(self):
        css_class = self.item["class"]
        if "item" in css_class:
            if len(css_class) == 1:
                self.type = "main_news"
            elif "news" in css_class:
                self.type = "longread_news"
            elif "article" in css_class or "extlink" in css_class:
                self.type = "longread_articles"
        elif "first-item" in css_class:
            self.type = "first_news"
        elif "b-tabloid__topic" in css_class:
            if "news" in css_class:
                self.type = "tabloid_news"
            elif "article" in css_class:
                self.type = "tabloid_articles"

    def get_data_by_item_type(self, date_regexp):
        if self.type == "main_news":
            self.parse_main_news(date_regexp)
        elif self.type == "first_news":
            self.parse_first_news(date_regexp)
        elif self.type == "longread_news":
            self.parse_longread_news(date_regexp)
        elif self.type == "longread_articles":
            self.parse_longread_articles(date_regexp)
        elif self.type == "tabloid_news":
            self.parse_tabloid_news(date_regexp)
        elif self.type == "tabloid_articles":
            self.parse_tabloid_articles(date_regexp)

    def parse_main_news(self, date_regexp):
        self.link = self.item.a["href"]
        self.title = self.item.a.text.rstrip() if self.item.a.text[2] != ":" else self.item.a.text[5:].rstrip()
        timestamp = re.search(date_regexp, self.link).group(0)
        self.date = dateutil.parser.parse(timestamp).date()
        self.category = "news"

    def parse_first_news(self, date_regexp):
        self.link = self.item.a["href"]
        self.title = self.item.h2.a.text[5:].rstrip()
        timestamp = re.search(date_regexp, self.link).group(0)
        self.date = dateutil.parser.parse(timestamp).date()
        self.category = "news"

    def parse_longread_news(self, date_regexp):
        titles_div = self.item.find("div", {"class": "titles"})

        self.link = titles_div.h3.a["href"]
        self.title = titles_div.h3.a.text.rstrip()
        timestamp = re.search(date_regexp, self.link).group(0)
        self.date = dateutil.parser.parse(timestamp).date()
        self.category = "news"

    def parse_longread_articles(self, date_regexp):
        titles_div = self.item.find("div", {"class": "titles"})
        pic_link = self.item.find("a", {"class": "picture"})

        self.link = titles_div.h3.a["href"]
        self.title = titles_div.h3.a.text.rstrip()
        try:
            timestamp = re.search(date_regexp, pic_link["href"]).group(0)
        except AttributeError:
            timestamp = re.search(date_regexp, pic_link.img["src"]).group(0)
        self.date = dateutil.parser.parse(timestamp).date()
        self.category = "articles"

    def parse_tabloid_news(self, date_regexp):
        self.link = self.item.a["href"]
        self.title = self.item.a.text.rstrip()
        timestamp = re.search(date_regexp, self.link).group(0)
        self.date = dateutil.parser.parse(timestamp).date()
        self.category = "news"

    def parse_tabloid_articles(self, date_regexp):
        self.link = self.item.a["href"]
        self.title = self.item.a.span.text.rstrip()
        try:
            timestamp = re.search(date_regexp, self.link).group(0)
        except AttributeError:
            img_link = self.item.a.img["src"]
            timestamp = re.search(date_regexp, img_link).group(0)
        self.date = dateutil.parser.parse(timestamp).date()
        self.category = "articles"


def parse_src_html(url):
    """
    Функция для парсинга главной страницы lenta.ru. Возвращает содержимое страницы в виде обеккта библиотеки
    BeautifulSoup для дальнейшей работы.
    """
    with requests.Session() as curr_session:
        curr_session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"
            "78.0.3904.108 YaBrowser/19.12.3.320 Yowser/2.5 Safari/537.36"
        }

    src_html_page = curr_session.get(url).text
    with open("parsed_html.html", "w+", encoding="UTF-8") as f:
        f.write(src_html_page)

    with open("parsed_html.html", "r", encoding="UTF-8") as f:
        parsed_html = soup(f, "html.parser")

    return parsed_html


def main(file_path, news_date, news_category=None):
    url = "https://lenta.ru"
    page_soup = parse_src_html(url)
    # получение всех элементов сайта, содержащих новости и статьи
    items = page_soup.find_all("div", {"class": ["first-item", "item", "b-tabloid__topic"]})
    date_regexp = r"(\d{2}-\d{2}-\d{4}|\d{4}/\d{2}/\d{2})"

    res_df = pd.DataFrame()
    news_datetime = dateutil.parser.parse(news_date).date()

    for item in items:
        # создание экземпляра класса
        news_item = NewsItem(item)
        # вызов методов для инициализации основных атрибутов класса
        news_item.define_item_type()
        news_item.get_data_by_item_type(date_regexp)

        # получение атрибутов класса для дальнейшей записи в DataFrame
        date = news_item.date
        title = news_item.title
        link = news_item.link
        category = news_item.category

        # фильтрация по дате и категории
        if date != news_datetime or (category != news_category and news_category is not None):
            continue
        # дополнение относительных внутренних ссылок на lenta.ru до абсолютных
        if "http" not in link:
            link = url + link

        res_df = res_df.append({"date": date, "title": title, "link": link, "category": category}, ignore_index=True)

    # удаление дублирующихся новостей (могут присутствовать в новостной части сайта и таблоиде одновременно)
    res_df = res_df.drop_duplicates()
    # экспорт в pickle-файл
    res_df.to_pickle(file_path)


if __name__ == "__main__":
    FILE_PATH = "pickled_news.pkl"
    NEWS_DATE = "22.02.2020"
    NEWS_CATEGORY = "articles"
    main(FILE_PATH, NEWS_DATE, NEWS_CATEGORY)
