class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"Hello, my name is {self.name} and I am {self.age} years old."

def main():
    person = Person("Alice", 30)
    print(person.greet())

if __name__ == "__main__":
    main()
