from flask import Flask, flash, redirect, render_template, request, url_for, session
from config import Config
import os, pdfkit

class Portal:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = '!@#$123456&*()'
        self.con = Config()
        self.routes()