# System imports


# External imports
from multiprocessing.managers import BaseManager, NamespaceProxy


# User imports


##########################################################

"""
По умолчанию NamespaceProxy позволяет нам обращаться ко всем публичным функциям
и читать и изменять все публичные поля класса, поэтому ничего не изменяем.
Фактически, добавили эти классы для читаемости кода.
"""

class MyManager(BaseManager):
    pass

class COM_PortProxy(NamespaceProxy):
    pass

class DecodeProxy(NamespaceProxy):
    pass