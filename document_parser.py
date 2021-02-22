import requests
from bs4 import BeautifulSoup

import database


class DocumentsParser:

    def __init__(
            self, urls, statements, preliminary_protocols, final_protocols):
        self.domain_name = 'https://obraz.tmbreg.ru'
        self.urls: list[str] = urls
        self.statements: dict[str: str] = statements
        self.preliminary_protocols: dict[str: str] = preliminary_protocols
        self.final_protocols: dict[str: str] = final_protocols

    def get_documents(self, url) -> dict[str: str]:
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        documents = soup.select_one('.itemIntroText').find_all('p')

        documents_urls = {}
        for document in documents:
            if document.text != 'Архив' and document.find('a') is not None:
                document_url = self.domain_name + \
                               document.find('a').get_attribute_list('href')[0]
                documents_urls[document.text] = document_url

        return documents_urls

    def check_for_new_documents(self) -> list[dict[str:str]]:
        statements_from_website = self.get_documents(self.urls[0])
        preliminary_protocols_from_website = self.get_documents(self.urls[1])
        final_protocols_from_website = self.get_documents(self.urls[2])

        new_documents: list[dict] = [
            {
                key: statements_from_website[key]
                for key in set(statements_from_website.keys()). \
                symmetric_difference(set(self.statements.keys()))
            },
            {
                key: preliminary_protocols_from_website[key]
                for key in set(preliminary_protocols_from_website.keys()). \
                symmetric_difference(set(self.preliminary_protocols.keys()))
            },
            {
                key: final_protocols_from_website[key]
                for key in set(final_protocols_from_website.keys()). \
                symmetric_difference(set(self.final_protocols.keys()))
            }
        ]

        self.statements.update(new_documents[0])
        self.preliminary_protocols.update(new_documents[1])
        self.final_protocols.update(new_documents[2])

        if len(new_documents[0].keys()) != 0:
            for key in new_documents[0].keys():
                database.cursor.execute(
                    "INSERT INTO statements(subject, url) VALUES (%s, %s)",
                    (key, new_documents[0][key])
                )
                database.connection.commit()
        if len(new_documents[1].keys()) != 0:
            for key in new_documents[1].keys():
                database.cursor.execute(
                    "INSERT INTO preliminary_protocols(subject, url) "
                    "VALUES (%s, %s)", (key, new_documents[1][key])
                )
                database.connection.commit()
        if len(new_documents[2].keys()) != 0:
            for key in new_documents[2].keys():
                database.cursor.execute(
                    "INSERT INTO final_protocols(subject, url) "
                    "VALUES (%s, %s)", (key, new_documents[2][key])
                )
                database.connection.commit()

        return new_documents
