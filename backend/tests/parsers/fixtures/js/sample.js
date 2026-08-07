import fs from "fs";
import path from "path";
import { readFile } from "fs/promises";

export const VERSION = "1.0";

const PI = 3.14;

export class Animal {
    constructor(name) {
        this.name = name;
    }

    speak() {
        return "Hello";
    }

    static create(name) {
        return new Animal(name);
    }
}

export function add(a, b) {
    return a + b;
}

const subtract = function (a, b) {
    return a - b;
};

const multiply = (a, b) => {
    return a * b;
};

const divide = (a, b) => a / b;

const utils = {
    greet(name) {
        return `Hello ${name}`;
    },

    square: (x) => x * x,

    cube: function (x) {
        return x * x * x;
    }
};

export default Animal;