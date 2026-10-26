/*
 * GT6816 slow-step motor probe.
 *
 * Drives the four phase lines (PPHDR bits 3..0, PD0..PD3) with the full-step
 * and half-step tables found in Plustek's cism603.fw, at a rate slow enough to
 * hear/see.  Volatile code-RAM program: it never touches the EEPROM.  It feeds
 * the watchdog, and always ends with all phase lines low (coils off).
 *
 * Timeline (approximate, Timer 0 overflow ~4.5 ms is an estimate):
 *   2 s lead-in, 48 full steps at ~4/s, 2 s pause, 96 half steps at ~8/s, then idle with lines low.
 */
#include <stdint.h>
#include <8051.h>

#define REG(address) (*(volatile __xdata uint8_t *)(address))

#define PPHSR    0xFFA1u
#define PPHDR    0xFFA2u
#define PPDSR    0xFFA3u
#define WATCHDOG 0xFF96u

static const __code uint8_t full_step[4] = {0x0F, 0x0B, 0x0A, 0x0E};
static const __code uint8_t half_step[8] = {0x0F, 0x03, 0x0B, 0x08, 0x0A, 0x02, 0x0E, 0x0C};

static void feed(void)
{
    REG(WATCHDOG) = 0x68u;
    REG(WATCHDOG) = 0x01u;
}

/* one Timer 0 overflow (16-bit mode) per call */
static void tick(void)
{
    TR0 = 0;
    TH0 = 0;
    TL0 = 0;
    TF0 = 0;
    TR0 = 1;
    while (!TF0) {
    }
    TR0 = 0;
    feed();
}

static void wait_ticks(uint16_t n)
{
    while (n--) {
        tick();
    }
}

void main(void)
{
    uint8_t i, j;

    TMOD = 0x01u; /* timer 0, mode 1 */
    REG(PPHSR) = 0x00u;
    REG(PPDSR) = 0x80u; /* DATA_OE: drive the parallel-port data bus */
    REG(PPHDR) = 0x00u; /* phase lines low = coils off */

    wait_ticks(450); /* ~2 s lead-in */

    for (j = 0; j < 12; ++j) { /* 12 full cycles = 48 steps at ~4/s */
        for (i = 0; i < 4; ++i) {
            REG(PPHDR) = (uint8_t)(0xF0u | full_step[i]);
            wait_ticks(55);
        }
    }
    REG(PPHDR) = 0x00u;
    wait_ticks(450);

    for (j = 0; j < 12; ++j) { /* 12 half cycles = 96 steps at ~8/s */
        for (i = 0; i < 8; ++i) {
            REG(PPHDR) = (uint8_t)(0xF0u | half_step[i]);
            wait_ticks(27);
        }
    }
    REG(PPHDR) = 0x00u;

    for (;;) {
        feed();
    }
}
