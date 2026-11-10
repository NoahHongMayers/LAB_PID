#include "SharedValue.h"

float SharedValue::read() {
    mutex.take();
    float currentValue = value;
    mutex.release();
    return currentValue;
}

void SharedValue::write(float valueToWrite) {
    mutex.take();
    value = valueToWrite;
    mutex.release();
}