package com.repointel.demo;

import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import static java.lang.Math.max;

public class Animal {

    protected String species = "Unknown";

    public void speak() {
    }
}

interface Pet {

    void play();
}

enum Status {
    ACTIVE,
    INACTIVE
}

class Dog extends Animal implements Pet {

    private String breed = "Labrador";

    public Dog() {
    }

    @Override
    public void play() {
    }

    public String bark(int volume) {
        return "Woof";
    }

    public static Dog create() {
        return new Dog();
    }
}