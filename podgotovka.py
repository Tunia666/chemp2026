'''class A:
    def myMethod(self, x):
        return x ** 2
    m1 = "My IQ is:" #создание свойства m1
    m2 = myMethod  # создание свойства m2

b = "test" #создание объекта b
print (b.m1 + ' ' + str(b.m2(9)))
print (b.m1 )'''

'''class YesInit:
    def __init__(self, one="none", two="none"):
        self.fname = one
        self.sname = two

obj1 = YesInit("Chris","Rock")
print(obj1.fname + ' ' + obj1.sname)
obj1 = YesInit()
print(obj1.fname + ' ' + obj1.sname)'''

'''class Line:
    def __init__(self, p1, p2):
        self.line = (p1, p2)

    def __del__(self):
        print("Удаляется линия %s - %s" % self.line)
b = Line("Привет ", "МИр!")'''

'''Наследование'''

'''class Par1(object):
    # наследуем один базовый класс - object
    def name1(self): return 'Par1'


class Par2(object):
    def name2(self): return 'Par2'


class Child(Par1):
    # создадим класс, наследующий Par1, Par2 (и, опосредованно, object)
    def name2(self): return 'Child'


x = Child()
print(x.name1() + ' ' + x.name2())'''

'''class YesInit: #абстрактный класс
    def __init__(self, one="none", two="none"):
        self.fname = one
        self.sname = two

class User(YesInit):
    pass
obj1 = User("Chriseeee","Rock")
obj2 = User("Chrie","Rock")
print(obj1.fname + ' ' + obj1.sname)
print(obj2.fname + ' ' + obj2.sname)
'''


'''class Child(Parent):

    def __init__(self):
        super(Child, self).__init__(self)

class A(object):
        def __init__(self):
            print(u'конструктор класса A')

# Потомок класса А
class B(A):
        def __init__(self):
            print(u'конструктор класса B')
            super(B, self).__init__()'''

'''class Count:
    def _init_ (self, a,b,):
        self.a = a
        self.b = b
    def sum (self, a, b):
        return a+b
    def raz (self, a, b):
        return a-b
    def pro (self, a, b):
        return a*b
    def delen (self, a, b):
        return a/b

obj = Count(30,5)
print (f"Сумма: {obj.sum()}, \n Разность {obj.raz()}, \n Произведение: {obj.pro()}")

class Count2(Count):
    pass
obj2 = Count2()
print (obj2.sum(8,8))'''

class Music:
    def __init__(self):
        pass
