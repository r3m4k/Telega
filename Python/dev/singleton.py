# System imports
import threading

# External imports

# User imports

##########################################################

"""
Лучше использовать функцию, а не класс Singleton, тк
при создании объекта будет вызван метод __init__, 
в котором может происходить выделение ресурсов, а 
предотвращение повторного выделение ресурсов требует
дополнительного подхода, который не получилось разработать
"""
def singleton(class_):
    instances = {}

    def get_instance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return get_instance