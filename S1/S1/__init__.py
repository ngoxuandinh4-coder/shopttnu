import pymysql

# Giả lập thư viện mysqlclient
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

# Tắt kiểm tra phiên bản và tính năng RETURNING của Django 6.0
from django.db.backends.mysql.base import DatabaseWrapper
DatabaseWrapper.check_database_version_supported = lambda self: None
DatabaseWrapper.features_class.can_return_columns_from_insert = property(lambda self: False)