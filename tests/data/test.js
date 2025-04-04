function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    sayHello() {
        return `Hi, I'm ${this.name}`;
    }
}

const main = () => {
    const person = new Person("Alice", 30);
    console.log(person.sayHello());
    console.log(greet("World"));
};

main();