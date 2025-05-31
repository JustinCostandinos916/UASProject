import pymysql

class Config:
    # Database configuration
    def __init__(self):
        self.mysql = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='',
        )