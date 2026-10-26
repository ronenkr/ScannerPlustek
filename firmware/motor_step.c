/*
 * GT6816 parameterised stepper program.
 *
 * Drives the four phase lines (PPHDR bits 3..0 = PD0..PD3) with the full-step
 * or half-step table from Plustek's cism603.fw.  The host patches the PARAMS
 * block (fixed code address 0x0800) in the image before uploading; see
 * scripts/gt6816_ctl.py "run-motor".  Volatile code RAM only: nothing writes
 * the EEPROM.  The watchdog is fed on every step, the coils are switched off
 * (phase lines low) when the move ends, and an 8-byte completion marker
 * "MOTR" + steps(LE16) + 0xA5 + 0x00 is sent on bulk IN 1 so the host can time the run.
 *
 * PARAMS layout (little-endian):
 *   [0] mode        0 = full step (4 phases), 1 = half step (8 phases)
 *   [1] direction   0 = phase index increases, 1 = decreases
 *   [2..3] steps    number of (full or half) steps
 *   [4..7] start    Timer 0 counts per step at the start of the move (slow), 32-bit
 *   [8..11] run     Timer 0 counts per step at cruise speed (fast), 32-bit
 *   [12..13] ramp   steps spent accelerating (and decelerating)
 */
#include <stdint.h>
#include <8051.h>

#define REG(address) (*(volatile __xdata uint8_t *)(address))

#define PPHSR     0xFFA1u
#define PPHDR     0xFFA2u
#define PPDSR     0xFFA3u
#define WATCHDOG  0xFF96u
#define DMA3_CONTROL      0xFFA9u
#define DMA3_AUTORELOAD   0xFFB2u
#define DMA3_BYTE_COUNT8  0xFFC2u
#define DMA3_BANKED_CTRL2 0xFFC3u
#define USB_DSTR0         0xFFD0u
#define USB_BANK_SELECT   0xFFB0u

__code __at(0x0800) const volatile uint8_t PARAMS[16] = {0, 0, 20, 0, 0x00, 0x60, 0, 0, 0x00, 0x60, 0, 0, 0, 0, 0, 0};

static const __code uint8_t full_step[4] = {0x0F, 0x0B, 0x0A, 0x0E};
static const __code uint8_t half_step[8] = {0x0F, 0x03, 0x0B, 0x08, 0x0A, 0x02, 0x0E, 0x0C};

static void feed(void)
{
    REG(WATCHDOG) = 0x68u;
    REG(WATCHDOG) = 0x01u;
}

/* wait up to 65535 Timer 0 counts (16-bit mode) */
static void wait_short(uint16_t counts)
{
    uint16_t reload = (uint16_t)(0u - counts);
    TR0 = 0;
    TH0 = (uint8_t)(reload >> 8);
    TL0 = (uint8_t)reload;
    TF0 = 0;
    TR0 = 1;
    while (!TF0) {
    }
    TR0 = 0;
    feed();
}

/* wait an arbitrary number of counts by chaining 16-bit waits */
static void wait_counts(uint32_t counts)
{
    while (counts > 0xFFFFul) {
        wait_short(0xFFFFu);
        counts -= 0xFFFFul;
    }
    if (counts) {
        wait_short((uint16_t)counts);
    }
}

static void send_marker(uint16_t steps)
{
    uint8_t bank, i;
    const uint8_t marker[8] = {'M', 'O', 'T', 'R', (uint8_t)steps, (uint8_t)(steps >> 8), 0xA5u, 0x00u};

    for (i = 0; i < 8; ++i) {
        REG(USB_DSTR0 + i) = marker[i];
    }
    bank = REG(USB_BANK_SELECT);
    REG(USB_BANK_SELECT) = (uint8_t)(bank | 0x80u);
    REG(DMA3_BANKED_CTRL2) = 0x20u;
    REG(USB_BANK_SELECT) = bank;
    REG(DMA3_AUTORELOAD) = 0x00u;
    REG(DMA3_BYTE_COUNT8) = 8u;
    REG(DMA3_CONTROL) = 0xF2u;
}

void main(void)
{
    uint8_t mode = PARAMS[0], dir = PARAMS[1], index = 0, mask;
    uint16_t steps = (uint16_t)PARAMS[2] | ((uint16_t)PARAMS[3] << 8);
    uint32_t start = (uint32_t)PARAMS[4] | ((uint32_t)PARAMS[5] << 8) | ((uint32_t)PARAMS[6] << 16) | ((uint32_t)PARAMS[7] << 24);
    uint32_t run = (uint32_t)PARAMS[8] | ((uint32_t)PARAMS[9] << 8) | ((uint32_t)PARAMS[10] << 16) | ((uint32_t)PARAMS[11] << 24);
    uint16_t ramp = (uint16_t)PARAMS[12] | ((uint16_t)PARAMS[13] << 8);
    uint16_t i, edge;
    uint32_t span;

    TMOD = 0x01u;
    REG(PPHSR) = 0x00u;
    REG(PPDSR) = 0x80u; /* DATA_OE */
    REG(PPHDR) = 0x00u;
    mask = mode ? 7u : 3u;
    if (start < run) {
        start = run;
    }
    span = start - run;
    if (ramp > steps / 2u) {
        ramp = steps / 2u;
    }

    wait_short(0xFFFFu); /* short lead-in so the host is ready */

    for (i = 0; i < steps; ++i) {
        uint32_t counts = run;
        if (ramp) {
            edge = (i < ramp) ? i : ((steps - 1u - i) < ramp ? (steps - 1u - i) : ramp);
            if (edge < ramp) {
                counts = start - (span * edge) / ramp;
            }
        }
        index = (uint8_t)((dir ? (index - 1u) : (index + 1u)) & mask);
        REG(PPHDR) = (uint8_t)(0xF0u | (mode ? half_step[index] : full_step[index]));
        wait_counts(counts);
    }
    REG(PPHDR) = 0x00u;
    send_marker(steps);
    for (;;) {
        feed(); /* idle with coils off; the host bus-resets and reloads the scan firmware */
    }
}
