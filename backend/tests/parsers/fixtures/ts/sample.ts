import fs from "fs";
import path from "path";
import { readFile } from "fs/promises";

export const VERSION: string = "1.0";

const PI: number = 3.14;

interface Animal {
    speak(): void;
}

type Id = string;

enum Color {
    Red,
    Blue,
}

export class Dog implements Animal {
    constructor(
        private name: string,
    ) {}

    speak(): void {}

    static create(name: string): Dog {
        return new Dog(name);
    }
}

export function add(
    a: number,
    b: number,
): number {
    return a + b;
}

const subtract = function (
    a: number,
    b: number,
): number {
    return a - b;
};

const multiply = (
    a: number,
    b: number,
): number => {
    return a * b;
};

const divide = (
    a: number,
    b: number,
): number => a / b;

const utils = {
    greet(name: string): string {
        return `Hello ${name}`;
    },

    square: (x: number): number => x * x,

    cube: function (
        x: number,
    ): number {
        return x * x * x;
    }
};

export default Dog;