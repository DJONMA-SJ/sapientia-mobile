[app]
title = Sapientia Mobile
package.name = sapientiamobile
package.domain = org.sapientia.app
source.dir = .
source.include_exts = py,png,jpg,jpeg,db,ttf
source.include_patterns = Assets/*, database/*, core/*, pdfs/*
version = 1.0.0
requirements = python3,kivy,kivymd,sqlite3,reportlab,pandas,openpyxl
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1