#pragma once

#include "Mutex.h"

class SharedTable {
private:
    unsigned char table[100] = {};
    Mutex mutex;
    bool protectionActive;

public:
    SharedTable(bool protection);
    void fill(unsigned char value);
    bool verify();
    void setProtection(bool active);
};