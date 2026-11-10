#pragma once

#include "Mutex.h"

class SharedValue {
private:
    float value = 0.0;
    Mutex mutex;

public:
    float read();
    void write(float valueToWrite);
};