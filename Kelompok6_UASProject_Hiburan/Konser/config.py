import pymysql

class Config:
    def __init__(self):
        self.mysql = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='tiketkonser3'
        )
