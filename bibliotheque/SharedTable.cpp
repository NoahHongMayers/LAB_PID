#include "SharedTable.h"

SharedTable::SharedTable(bool protection): protectionActive(protection) {}

void SharedTable::fill(unsigned char value) {

    if (protectionActive) {
        mutex.take();
    }

    unsigned char somme = 0;

    for (int i = 0; i < 99; i++) {
        table[i] = value;
        somme += value;
    }

    table[99] = somme;

    if (protectionActive) {
        mutex.release();
    }
}

bool SharedTable::verify() {

    if (protectionActive) {
        mutex.take();
    }

    unsigned char sum = 0;

    for (int i = 0; i < 99; i++) {
        sum += table[i];
    }

    bool valide = (sum == table[99]);

    if (protectionActive) {
        mutex.release();
    }

    return valide;
}

void SharedTable::setProtection(bool active) {
    protectionActive = active;
}